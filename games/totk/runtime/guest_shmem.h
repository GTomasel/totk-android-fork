/* Linux guest backing for the opt-in sparse Vulkan pool copy. */
#pragma once
#include <errno.h>
#include <fcntl.h>
#include <linux/falloc.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <sys/sysmacros.h>
#include <unistd.h>

enum { GUEST_SHMEM_TRACK_BYTES = 64 * 1024 };
enum { GUEST_SHMEM_REPLACED = 1, GUEST_SHMEM_ALIASED = 2 };
typedef struct {
    uintptr_t base;
    size_t size;
    int fd;
    unsigned char *groups;
    unsigned dev_major, dev_minor;
    uint64_t inode;
} guest_shmem_range;

/* A coarse group that has ever been remapped always falls back to the
   live virtual address. The reservation size is a multiple of 64 KiB. */
static inline void *guest_shmem_reserve(guest_shmem_range *range, uintptr_t base, size_t size, int flags) {
    if (size % GUEST_SHMEM_TRACK_BYTES) return MAP_FAILED;
    int fd = memfd_create("totk-guest", MFD_CLOEXEC);
    if (fd < 0) return MAP_FAILED;
    unsigned char *groups = calloc(size / GUEST_SHMEM_TRACK_BYTES, 1);
    struct stat info;
    if (!groups || ftruncate(fd, (off_t)size) || fstat(fd, &info)) {
        free(groups);
        close(fd);
        return MAP_FAILED;
    }
    void *p = mmap((void *)base, size, PROT_NONE, flags, fd, 0);
    if (p != (void *)base) {
        if (p != MAP_FAILED) munmap(p, size);
        free(groups);
        close(fd);
        return MAP_FAILED;
    }
    *range = (guest_shmem_range){base, size, fd, groups, major(info.st_dev), minor(info.st_dev), info.st_ino};
    return p;
}

static inline void guest_shmem_release(guest_shmem_range *range) {
    close(range->fd);
    free(range->groups);
    *range = (guest_shmem_range){0};
}

static inline void guest_shmem_note(guest_shmem_range *range, uintptr_t base, size_t size, unsigned flag) {
    uintptr_t lo = base > range->base ? base : range->base;
    uintptr_t hi = base + size;
    if (hi > range->base + range->size) hi = range->base + range->size;
    if (lo >= hi) return;
    size_t first = (lo - range->base) / GUEST_SHMEM_TRACK_BYTES;
    size_t last = (hi - 1 - range->base) / GUEST_SHMEM_TRACK_BYTES;
    for (size_t i = first; i <= last; i++) range->groups[i] |= flag;
}

/* Linux can grow a shared clone beyond its starting VMA. For our backing,
   require contiguous source offsets through the requested span so a clone
   cannot re-expose an offset already displaced by a DMA buffer. Resolve the
   actual file offset even if the source is itself an earlier clone.
   Pool replacement and NVN virtual mappings are serialized by the caller. */
static inline int guest_shmem_protect_alias(guest_shmem_range *ranges, size_t count, uintptr_t src, size_t size) {
    if (!size || size > UINTPTR_MAX - src) return 0;
    FILE *maps = fopen("/proc/self/maps", "re");
    if (!maps) return 0;
    guest_shmem_range *range = NULL;
    char *line = NULL;
    size_t capacity = 0;
    uintptr_t cursor = src, limit = src + size;
    uint64_t first_offset = 0;
    int ok = 0;
    while (getline(&line, &capacity, maps) >= 0) {
        unsigned long long lo, hi, offset, inode;
        unsigned major_id, minor_id;
        if (sscanf(line, "%llx-%llx %*4s %llx %x:%x %llu",
                   &lo, &hi, &offset, &major_id, &minor_id, &inode) != 6) break;
        if (hi <= cursor) continue;
        if (lo > cursor) break;
        offset += cursor - lo;
        if (!range) {
            for (size_t i = 0; i < count; i++) {
                guest_shmem_range *candidate = &ranges[i];
                if (candidate->size && inode == candidate->inode &&
                    major_id == candidate->dev_major && minor_id == candidate->dev_minor) {
                    range = candidate;
                    break;
                }
            }
            if (!range) { ok = 1; break; }
            if (offset > range->size || size > range->size - offset) break;
            first_offset = offset;
        } else if (inode != range->inode || major_id != range->dev_major ||
                   minor_id != range->dev_minor || offset != first_offset + (cursor - src)) break;
        if (hi >= limit) {
            guest_shmem_note(range, range->base + first_offset, size, GUEST_SHMEM_ALIASED);
            ok = 1;
            break;
        }
        cursor = hi;
    }
    free(line);
    fclose(maps);
    return ok;
}

static inline int guest_shmem_copy(guest_shmem_range *range, void *dst, uintptr_t src, size_t size) {
    if (src < range->base || !size || size > range->size || src - range->base > range->size - size)
        return 0;
    size_t offset = src - range->base;
    size_t first = offset / GUEST_SHMEM_TRACK_BYTES;
    size_t last = (offset + size - 1) / GUEST_SHMEM_TRACK_BYTES;
    for (size_t i = first; i <= last; i++)
        if (range->groups[i] & GUEST_SHMEM_REPLACED) return 0;
    size_t copied = 0;
    while (copied < size) {
        ssize_t n = pread(range->fd, (unsigned char *)dst + copied, size - copied, (off_t)(offset + copied));
        if (n < 0 && errno == EINTR) continue;
        if (n <= 0) return 0;
        copied += (size_t)n;
    }
    return 1;
}

typedef struct {
    uint64_t punched, preserved, errors;
} guest_shmem_discard_stats;

/* Advance through runs of unaliased groups, limited to the exact address
   range already replaced with a different backing. A fallback clone of a
   group protects it for the rest of the reservation's lifetime. */
static inline void guest_shmem_discard(const guest_shmem_range *range, uintptr_t base, size_t size,
                                       guest_shmem_discard_stats *stats) {
    uintptr_t lo = base > range->base ? base : range->base;
    uintptr_t hi = base + size;
    if (hi > range->base + range->size) hi = range->base + range->size;
    if (lo >= hi) return;
    size_t offset = lo - range->base, limit = hi - range->base;
    while (offset < limit) {
        size_t group = offset / GUEST_SHMEM_TRACK_BYTES;
        int aliased = range->groups[group] & GUEST_SHMEM_ALIASED;
        size_t end = (group + 1) * GUEST_SHMEM_TRACK_BYTES;
        while (end < limit && (range->groups[end / GUEST_SHMEM_TRACK_BYTES] & GUEST_SHMEM_ALIASED) == aliased)
            end += GUEST_SHMEM_TRACK_BYTES;
        if (end > limit) end = limit;
        if (aliased) stats->preserved += end - offset;
        else if (fallocate(range->fd, FALLOC_FL_PUNCH_HOLE | FALLOC_FL_KEEP_SIZE, (off_t)offset, (off_t)(end - offset)))
            stats->errors++;
        else stats->punched += end - offset;
        offset = end;
    }
}

static inline uint64_t guest_shmem_backing_bytes(const guest_shmem_range *range) {
    struct stat info;
    return fstat(range->fd, &info) ? 0 : (uint64_t)info.st_blocks * 512;
}

/* Report the intersection with an active GPU address range in bytes.
   SEEK_DATA includes file offsets with data, independent of RSS. */
static inline int guest_shmem_occupied(const guest_shmem_range *range, uintptr_t base, size_t size,
                                       uint64_t totals[2]) {
    uintptr_t lo = base > range->base ? base : range->base;
    uintptr_t hi = base + size;
    if (hi > range->base + range->size) hi = range->base + range->size;
    if (lo >= hi) return 1;
    off_t cursor = (off_t)(lo - range->base), limit = (off_t)(hi - range->base);
    totals[0] += hi - lo;
    while (cursor < limit) {
        off_t data = lseek(range->fd, cursor, SEEK_DATA);
        if (data < 0) return errno == ENXIO;
        if (data >= limit) return 1;
        off_t hole = lseek(range->fd, data, SEEK_HOLE);
        if (hole <= data) return 0;
        cursor = hole < limit ? hole : limit;
        totals[1] += (uint64_t)(cursor - data);
    }
    return 1;
}
