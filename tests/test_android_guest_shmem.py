"""Exercise the production sparse-copy and replacement tracking on Linux."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class GuestShmemTest(unittest.TestCase):
    @unittest.skipUnless(sys.platform.startswith('linux'), 'requires Linux shmem semantics')
    def test_sparse_copy_preserves_holes_and_declines_replaced_ranges(self):
        compiler = shutil.which('cc')
        if not compiler:
            self.skipTest('C compiler required')
        source = r'''
#define _GNU_SOURCE
#include "guest_shmem.h"
#include <assert.h>
#include <fcntl.h>

static void test_discard(int flags, size_t page, size_t size) {
    const size_t group = GUEST_SHMEM_TRACK_BYTES;
    const size_t replaced = size - 2 * page;
    void *address = mmap(NULL, size, PROT_NONE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    assert(address != MAP_FAILED && munmap(address, size) == 0);
    uintptr_t base = (uintptr_t)address;
    guest_shmem_range range = {0};
    unsigned char *guest = guest_shmem_reserve(&range, base, size, flags);
    assert(guest == address && mprotect(guest, size, PROT_READ | PROT_WRITE) == 0);
    memset(guest, 0x31, group);
    memset(guest + group, 0x48, group);
    memset(guest + 2 * group, 0x62, group);
    assert(guest_shmem_backing_bytes(&range) == size);

    /* Capture a fallback clone at one original offset of the middle group. */
    assert(mprotect(guest + group + 2 * page, page, PROT_READ) == 0);
    assert(guest_shmem_protect_alias(&range, 1, base + group + page, 2 * page));
    assert(mprotect(guest + group + 2 * page, page, PROT_READ | PROT_WRITE) == 0);
    unsigned char *guards = mmap(NULL, 3 * page, PROT_NONE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    assert(guards != MAP_FAILED);
    unsigned char *alias = mremap(guest + group + page, 0, page, MREMAP_MAYMOVE | MREMAP_FIXED, guards + page);
    assert(alias == guards + page && alias[0] == 0x48);
    assert(guest_shmem_protect_alias(&range, 1, (uintptr_t)alias, page));
    assert(!guest_shmem_protect_alias(&range, 1, (uintptr_t)alias, 2 * page));

    int gpu_fd = memfd_create("probe-gpu", MFD_CLOEXEC);
    assert(gpu_fd >= 0 && ftruncate(gpu_fd, (off_t)replaced) == 0);
    unsigned char *staging = mmap(NULL, replaced, PROT_READ | PROT_WRITE, MAP_SHARED, gpu_fd, 0);
    assert(staging != MAP_FAILED);
    memcpy(staging, guest + page, replaced);
    assert(mmap(guest + page, replaced, PROT_READ | PROT_WRITE,
                MAP_FIXED | MAP_SHARED, gpu_fd, 0) == guest + page);
    guest_shmem_discard_stats counts = {0};
    guest_shmem_discard(&range, base + page, replaced, &counts);
    assert(counts.punched == 2 * (group - page) && counts.preserved == group && !counts.errors);
    assert(guest_shmem_backing_bytes(&range) == group + 2 * page);
    assert(alias[0] == 0x48 && alias[page - 1] == 0x48);
    assert(guest[0] == 0x31 && guest[size - 1] == 0x62);
    assert(!guest_shmem_protect_alias(&range, 1, base, 2 * page));
    for (size_t i = page; i < size - page; i++)
        assert(guest[i] == (i < group ? 0x31 : i < 2 * group ? 0x48 : 0x62));
    uint64_t old[2] = {0};
    assert(guest_shmem_occupied(&range, base + page, replaced, old));
    assert(old[0] == replaced && old[1] == group);

    /* Future registrations retain the old alias protection. */
    assert(munmap(guards, 3 * page) == 0);
    guest_shmem_discard(&range, base + page, replaced, &counts);
    assert(guest_shmem_backing_bytes(&range) == group + 2 * page);
    assert(munmap(staging, replaced) == 0 && close(gpu_fd) == 0);
    assert(munmap(guest, size) == 0);
    guest_shmem_release(&range);
}

int main(void) {
    const size_t size = 3 * GUEST_SHMEM_TRACK_BYTES;
    const size_t page = sysconf(_SC_PAGESIZE);
    void *reservation = mmap(NULL, size, PROT_NONE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    assert(reservation != MAP_FAILED);
    uintptr_t base = (uintptr_t)reservation;
    guest_shmem_range range = {0};
    int flags = MAP_SHARED | MAP_NORESERVE | MAP_FIXED_NOREPLACE;
    assert(guest_shmem_reserve(&range, base, size, flags) == MAP_FAILED);
    assert(!range.size);
    assert(munmap(reservation, size) == 0);
    unsigned char *guest = guest_shmem_reserve(&range, base, size, flags);
    assert(guest == reservation);
    assert(mprotect(guest, size, PROT_READ | PROT_WRITE) == 0);
    memset(guest + page, 17, page);
    uint64_t allocated = guest_shmem_backing_bytes(&range);
    assert(allocated > 0 && allocated < size);
    unsigned char *destination = malloc(size);
    assert(destination);
    memset(destination, 0x55, size);
    assert(guest_shmem_copy(&range, destination, base, size));
    for (size_t i = 0; i < size; i++)
        assert(destination[i] == (i >= page && i < 2 * page ? 17 : 0));
    assert(guest_shmem_backing_bytes(&range) == allocated);
    uint64_t totals[2] = {0};
    assert(guest_shmem_occupied(&range, base, size, totals));
    assert(totals[0] == size && totals[1] == allocated);
    memset(totals, 0, sizeof totals);
    assert(guest_shmem_occupied(&range, base + GUEST_SHMEM_TRACK_BYTES, page, totals));
    assert(totals[0] == page && !totals[1]);
    assert(!guest_shmem_copy(&range, destination, base - 1, 1));
    assert(!guest_shmem_copy(&range, destination, base + size - 1, 2));

    size_t offset = GUEST_SHMEM_TRACK_BYTES + page;
    assert(mmap(guest + offset, page, PROT_READ | PROT_WRITE,
                MAP_PRIVATE | MAP_ANONYMOUS | MAP_FIXED, -1, 0) == guest + offset);
    memset(guest + offset, 39, page);
    guest_shmem_note(&range, base + offset, page, GUEST_SHMEM_REPLACED);
    assert(!guest_shmem_copy(&range, destination, base + offset, page));
    assert(!guest_shmem_copy(&range, destination, base + page, size - page));
    assert(!guest_shmem_copy(&range, destination, base + GUEST_SHMEM_TRACK_BYTES, 1));
    assert(guest_shmem_copy(&range, destination, base + page, 1) && destination[0] == 17);
    assert(guest_shmem_copy(&range, destination, base + size - 1, 1) && destination[0] == 0);
    assert(guest[offset] == 39);

    int fd = range.fd;
    assert(munmap(guest, size) == 0);
    guest_shmem_release(&range);
    assert(fcntl(fd, F_GETFD) == -1 && errno == EBADF);
    free(destination);
    test_discard(flags, page, size);
    return 0;
}
'''
        with tempfile.TemporaryDirectory() as directory:
            input_path = Path(directory) / 'probe.c'
            probe = Path(directory) / 'probe'
            input_path.write_text(source)
            subprocess.run([compiler, '-O2', '-Wall', '-Wextra', '-Werror',
                            '-I', str(ROOT / 'games/totk/runtime'), str(input_path), '-o', str(probe)],
                           check=True)
            subprocess.run([str(probe)], check=True)
