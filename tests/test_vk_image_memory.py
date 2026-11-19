"""Exercise production Vulkan image suballocation against counted device-memory allocations.

No real GPU or Android memory pressure is simulated. This exercises block reclamation,
stable handles, allocation failure recovery, and inter-sample peaks.
"""
from pathlib import Path
import os
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ImageMemoryTests(unittest.TestCase):
    def test_empty_block_release_and_stable_live_allocations(self):
        compiler = shutil.which('cc')
        if not compiler:
            self.skipTest('C compiler required')
        production = (ROOT / 'games/totk/android/gfx/vk_res.c').read_text()
        begin = production.index('/* ---------- device memory:')
        production = production[begin:production.index('/* ---------- format support', begin)]
        prelude = r'''
#define _GNU_SOURCE
#include <assert.h>
#include <pthread.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
typedef uint64_t VkDeviceSize, VkDeviceMemory;
typedef uint32_t VkMemoryPropertyFlags;
typedef int VkResult;
typedef struct { VkDeviceSize size, alignment; uint32_t memoryTypeBits; } VkMemoryRequirements;
typedef struct { unsigned sType; VkDeviceSize allocationSize; uint32_t memoryTypeIndex; } VkMemoryAllocateInfo;
typedef struct { VkDeviceMemory mem; VkDeviceSize off, size; int block; } vk_alloc;
static struct { struct { struct { VkDeviceSize bufferImageGranularity; } limits; } props; } V = {{{256}}};
enum { VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO = 1, VK_MEMORY_IMAGE_BLOCK, VK_MEMORY_IMAGE_DEDICATED };
enum { VK_NULL_HANDLE = 0, VK_SUCCESS = 0, VK_ERROR_OUT_OF_HOST_MEMORY = -1,
       VK_ERROR_OUT_OF_DEVICE_MEMORY = -2, VK_ERROR_FEATURE_NOT_PRESENT = -8, VK_ERROR_UNKNOWN = -13 };
static uint64_t sizes[4096], allocated, next_memory, releases;
static int fail_next;
static unsigned fail_metadata_at;
static size_t moved_span_bytes;
static void *resize_metadata(void *ptr, size_t bytes) {
    if (fail_metadata_at && --fail_metadata_at == 0) return NULL;
    return realloc(ptr, bytes);
}
static void *move_spans(void *to, const void *from, size_t bytes) {
    moved_span_bytes += bytes;
    return memmove(to, from, bytes);
}
#define realloc resize_metadata
#define memmove move_spans
#define LOGV(...) do { fprintf(stderr, __VA_ARGS__); fputc('\n', stderr); } while (0)
#define vk_submit_serial() UINT64_C(123)
static int vk_pick_type(uint32_t bits, uint32_t want) { (void)want; return bits & 1 ? 0 : bits & 2 ? 1 : -1; }
static int vk_memory_allocate(const VkMemoryAllocateInfo *info, VkDeviceMemory *memory, int purpose) {
    (void)purpose;
    if (fail_next) { fail_next = 0; return -1; }
    assert(next_memory + 1 < 4096);
    *memory = ++next_memory; sizes[*memory] = info->allocationSize; allocated += info->allocationSize;
    return 0;
}
static void vk_memory_release(VkDeviceMemory memory, int purpose) {
    (void)purpose; assert(memory && sizes[memory]);
    allocated -= sizes[memory]; sizes[memory] = 0; releases++;
}
'''
        probe = r'''
static int reclaim_completed_images(enum image_reclaim_kind kind, VkDeviceSize target, const image_span_request *fit) {
    (void)kind; (void)target; (void)fit; assert(0); return 0;
}

int main(int argc, char **argv) {
    assert(argc == 2);
    assert(!unsetenv("TOTK_VK_IMAGE_PEAK_LOG"));
    assert(!unsetenv("TOTK_VK_IMAGE_RECLAIM_BEFORE_GROW"));
    if (!strcmp(argv[1], "metadata-failure")) {
        assert(!setenv("TOTK_VK_IMAGE_FREE_EMPTY", "1", 1));
        VkMemoryRequirements req = {256, 256, 1};
        vk_alloc failed;
        for (unsigned failure = 1; failure <= 2; failure++) {
            fail_metadata_at = failure;
            assert(!vk_mem_alloc(&req, 0, &failed) && !failed.mem);
            assert(!fail_metadata_at && !next_memory && !g_mem_block_allocs && !g_nblocks);
        }
        fail_next = 1;
        assert(!vk_mem_alloc(&req, 0, &failed) && !failed.mem);
        assert(!fail_next && !next_memory && !g_mem_block_allocs && !g_nblocks);

        vk_alloc valid[16];
        for (int i = 0; i < 15; i++) {
            assert(vk_mem_alloc(&req, 0, &valid[i]) && valid[i].off == (uint64_t)i * 256);
        }
        assert(g_blocks[0].nfree == 1 && g_blocks[0].capfree == 16);
        fail_metadata_at = 1;
        assert(!vk_mem_alloc(&req, 0, &failed) && !failed.mem);
        assert(!fail_metadata_at && allocated == g_mem_block_size && next_memory == 1);
        assert(g_blocks[0].live_allocations == 15 && g_blocks[0].nfree == 1 && g_mem_block_used == 15 * 256);
        assert(vk_mem_alloc(&req, 0, &valid[15]) && valid[15].off == 15 * 256);
        assert(g_blocks[0].capfree == 32);
        fail_metadata_at = 1;
        for (int i = 0; i < 16; i += 2) vk_mem_free(&valid[i]);
        assert(fail_metadata_at == 1 && g_blocks[0].nfree == 9 && g_blocks[0].live_allocations == 8);
        for (int i = 1; i < 16; i += 2) {
            assert(valid[i].mem == 1 && valid[i].off == (uint64_t)i * 256);
            vk_mem_free(&valid[i]);
        }
        assert(fail_metadata_at == 1 && !allocated && !g_mem_block_used && releases == 1);
        assert(!g_mem_pressure_events && !g_mem_pressure_recovered); // non-texture allocations never run reclaim
        return 0;
    }
    if (!strcmp(argv[1], "peaks")) {
        assert(!setenv("TOTK_VK_IMAGE_FREE_EMPTY", "1", 1));
        assert(!setenv("TOTK_VK_IMAGE_BLOCK_MB", "32", 1));
        assert(!setenv("TOTK_VK_IMAGE_PEAK_LOG", "1", 1));
        const uint64_t MiB = 1u << 20;
        VkMemoryRequirements req = {4 * MiB, 256, 1};
        vk_alloc small, dedicated, rest[2];
        assert(vk_mem_alloc(&req, 0, &small));
        req.size = 17 * MiB;
        assert(vk_mem_alloc(&req, 0, &dedicated));
        vk_mem_free(&dedicated);
        req.size = 12 * MiB;
        assert(vk_mem_alloc(&req, 0, &rest[0]));
        req.size = 16 * MiB;
        assert(vk_mem_alloc(&req, 0, &rest[1]));
        vk_mem_free(&small);
        vk_mem_free(&rest[0]);
        assert(g_mem_block_used == 16 * MiB && allocated == 32 * MiB);
        image_memory_peaks peak = image_memory_take_peaks_locked();
        assert(peak.blocks == 32 * MiB && peak.dedicated == 17 * MiB);
        assert(peak.block_used_at_commit == 4 * MiB && peak.occupied == 32 * MiB);
        assert(!g_mem_reclaim_reuses);
        vk_mem_free(&rest[1]);
        req.size = 48 * MiB;
        fail_next = 1;
        assert(!vk_mem_alloc(&req, 0, &dedicated) && !dedicated.mem);
        peak = image_memory_take_peaks_locked();
        assert(peak.blocks == 32 * MiB && !peak.dedicated);
        assert(peak.block_used_at_commit == 16 * MiB && peak.occupied == 16 * MiB);
        peak = image_memory_take_peaks_locked();
        assert(!peak.blocks && !peak.dedicated && !peak.block_used_at_commit && !peak.occupied);
        return 0;
    }
    if (!strcmp(argv[1], "fragmented")) {
        assert(!unsetenv("TOTK_VK_IMAGE_FREE_EMPTY"));
        assert(!unsetenv("TOTK_VK_IMAGE_PACK"));
        assert(!setenv("TOTK_VK_IMAGE_BLOCK_MB", "32", 1));
        VkMemoryRequirements req = {768, 256, 1};
        vk_alloc first, aligned, gap;
        assert(vk_mem_alloc(&req, 0, &first) && first.off == 0);
        req.size = 512; req.alignment = 1024;
        assert(vk_mem_alloc(&req, 0, &aligned) && aligned.off == 1024);
        assert(g_blocks[0].nfree == 2 && g_blocks[0].free[0].size == 256);
        req.size = 256; req.alignment = 256;
        assert(vk_mem_alloc(&req, 0, &gap) && gap.off == 768);
        vk_mem_free(&gap); vk_mem_free(&aligned); vk_mem_free(&first);
        assert(g_blocks[0].nfree == 1 && g_blocks[0].free[0].off == 0);
        assert(g_blocks[0].free[0].size == (32u << 20));

        vk_alloc adjacent[16];
        for (int i = 0; i < 16; i++) {
            req.size = i == 0 ? 4u << 20 : 1u << 20;
            assert(vk_mem_alloc(&req, 0, &adjacent[i]) && adjacent[i].block == 0);
        }
        for (int i = 0; i < 16; i += 2) vk_mem_free(&adjacent[i]);
        assert(g_blocks[0].nfree == 9);
        moved_span_bytes = 0;
        req.size = 1u << 20;
        for (int i = 0; i < 512; i++) {
            vk_alloc cycle;
            assert(vk_mem_alloc(&req, 0, &cycle) && cycle.off == 0);
            vk_mem_free(&cycle);
        }
        assert(g_blocks[0].nfree == 9 && moved_span_bytes == 0);
        for (int i = 1; i < 16; i += 2) vk_mem_free(&adjacent[i]);
        assert(g_blocks[0].nfree == 1 && !g_blocks[0].used && g_blocks[0].free[0].size == (32u << 20));
        return 0;
    }
    if (!strcmp(argv[1], "16MiB")) {
        assert(!setenv("TOTK_VK_IMAGE_FREE_EMPTY", "1", 1));
        assert(!setenv("TOTK_VK_IMAGE_BLOCK_MB", "16", 1));
        const uint64_t MiB = 1u << 20;
        VkMemoryRequirements req = {16 * MiB, 256, 1};
        vk_alloc whole, half[2], large;
        assert(vk_mem_alloc(&req, 0, &whole) && whole.block >= 0 && allocated == 16 * MiB);
        req.size = 8 * MiB;
        for (int i = 0; i < 2; i++) assert(vk_mem_alloc(&req, 0, &half[i]));
        assert(whole.mem != half[0].mem && half[0].mem == half[1].mem && allocated == 32 * MiB);
        req.size = 16 * MiB + 256;
        assert(vk_mem_alloc(&req, 0, &large) && large.block == -1);
        vk_mem_free(&half[0]);
        assert(sizes[half[1].mem]);
        vk_mem_free(&half[1]);
        assert(allocated == 16 * MiB + req.size);
        vk_mem_free(&whole); vk_mem_free(&large);
        assert(!allocated && !g_mem_block_bytes && !g_mem_dedicated_bytes);
        assert(g_mem_block_allocs == 2 && g_mem_block_releases == 2);
        return 0;
    }
    if (!strcmp(argv[1], "packed")) {
        assert(!setenv("TOTK_VK_IMAGE_PACK", "1", 1));
        assert(!setenv("TOTK_VK_IMAGE_FREE_EMPTY", "1", 1));
        assert(!setenv("TOTK_VK_IMAGE_BLOCK_MB", "32", 1));
        const uint64_t MiB = 1u << 20;
        VkMemoryRequirements req = {12 * MiB, 256, 1};
        vk_alloc a[6];
        for (int i = 0; i < 5; i++) {
            req.size = (i == 2 ? 8 : 12) * MiB;
            assert(vk_mem_alloc(&req, 0, &a[i]));
        }
        assert(a[0].mem == a[2].mem && a[3].mem == a[4].mem && a[0].mem != a[3].mem);
        vk_mem_free(&a[0]);
        req.size = 6 * MiB;
        assert(vk_mem_alloc(&req, 0, &a[5]) && a[5].mem == a[3].mem);
        vk_mem_free(&a[1]); vk_mem_free(&a[2]);
        assert(allocated == 32 * MiB && releases == 1 && sizes[a[5].mem]);
        for (int i = 3; i < 6; i++) vk_mem_free(&a[i]);
        assert(!allocated && releases == 2);
        assert(g_mem_block_allocs == 2 && g_mem_block_releases == 2);
        puts("packing preserved an emptyable block without changing any live handle");
        return 0;
    }
    assert(!unsetenv("TOTK_VK_IMAGE_PACK"));
    int small = !strcmp(argv[1], "small");
    int trim = small || !strcmp(argv[1], "trim");
    if (trim) assert(!setenv("TOTK_VK_IMAGE_FREE_EMPTY", "1", 1));
    else assert(!unsetenv("TOTK_VK_IMAGE_FREE_EMPTY"));
    assert(!setenv("TOTK_VK_IMAGE_BLOCK_MB", small ? "32" : "64", 1));
    const uint64_t MiB = 1u << 20;
    VkMemoryRequirements req = {16 * MiB, 256, 1};
    vk_alloc a[5];
    for (int i = 0; i < 5; i++) assert(vk_mem_alloc(&req, 0, &a[i]));
    assert(allocated == (small ? 96 : 128) * MiB && g_mem_block_bytes == allocated);
    VkDeviceMemory survivor = a[4].mem;
    int survivor_block = a[4].block;
    for (int i = 0; i < 3; i++) vk_mem_free(&a[i]);
    assert(releases == (unsigned)small && sizes[survivor] && sizes[a[3].mem]); // no partial-block eviction
    vk_mem_free(&a[3]);
    assert(allocated == (small ? 32 : trim ? 64 : 128) * MiB);
    assert(a[4].mem == survivor && a[4].block == survivor_block && sizes[survivor]);
    req.size = 64 * MiB;
    vk_alloc dedicated; assert(vk_mem_alloc(&req, 0, &dedicated) && dedicated.block == -1);
    vk_mem_free(&dedicated);
    req.size = 16 * MiB; req.memoryTypeBits = 2;
    vk_alloc other; assert(vk_mem_alloc(&req, 0, &other));
    assert(other.block != survivor_block && a[4].mem == survivor && sizes[survivor]);
    vk_mem_free(&other); vk_mem_free(&a[4]);
    assert(trim ? allocated == 0 : allocated == 192 * MiB);
    for (int i = 0; i < 100; i++) {
        vk_alloc fresh; req.memoryTypeBits = 1;
        assert(vk_mem_alloc(&req, 0, &fresh));
        assert(fresh.mem && sizes[fresh.mem] && fresh.size == req.size);
        vk_mem_free(&fresh); vk_mem_free(&fresh); // idempotent empty handle
    }
    assert(trim ? allocated == 0 : allocated == 192 * MiB);
    assert(g_nblocks <= (trim && !small ? 2 : 3)); // empty slots reused, stable metadata size
    if (trim) {
        vk_alloc failed; fail_next = 1;
        assert(!vk_mem_alloc(&req, 0, &failed) && !failed.mem && allocated == 0);
        assert(vk_mem_alloc(&req, 0, &failed)); vk_mem_free(&failed);
        assert(!allocated && !g_mem_block_bytes && !g_mem_dedicated_bytes);
    }
    puts(trim ? "empty Vulkan blocks returned; live handles and accounting preserved" : "default reuse policy preserved");
    return 0;
}
'''
        with tempfile.TemporaryDirectory(prefix='totk-image-memory-') as directory:
            source, binary = Path(directory) / 'memory.c', Path(directory) / 'memory'
            source.write_text(prelude + production + probe)
            build = subprocess.run([compiler, '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror', '-pthread',
                                    str(source), '-o', str(binary)], capture_output=True, text=True, timeout=60)
            self.assertEqual(build.returncode, 0, build.stdout + build.stderr)
            for mode in ('default', 'trim', 'small', 'packed', '16MiB', 'fragmented',
                         'metadata-failure', 'peaks'):
                with self.subTest(mode=mode):
                    result = subprocess.run([str(binary), mode], env=dict(os.environ), capture_output=True,
                                            text=True, timeout=30)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    if mode == 'peaks':
                        self.assertEqual(result.stderr.splitlines(), [
                            '[image-allocation-high] sub=123 blocks=33554432 dedicated=0 occupied=4194304',
                            '[image-allocation-high] sub=123 blocks=33554432 dedicated=17825792 occupied=22020096',
                        ])
                    else:
                        self.assertNotIn('[image-allocation-high]', result.stderr)


if __name__ == '__main__':
    unittest.main()
