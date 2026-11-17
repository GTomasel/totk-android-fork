"""Exercise production Vulkan image suballocation against counted device-memory allocations.

No real GPU or Android memory pressure is simulated. This catches retention of completely
free image blocks and stale block-index corruption while other allocations remain live.
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
typedef struct { VkDeviceSize size, alignment; uint32_t memoryTypeBits; } VkMemoryRequirements;
typedef struct { unsigned sType; VkDeviceSize allocationSize; uint32_t memoryTypeIndex; } VkMemoryAllocateInfo;
typedef struct { VkDeviceMemory mem; VkDeviceSize off, size; int block; } vk_alloc;
static struct { struct { struct { VkDeviceSize bufferImageGranularity; } limits; } props; } V = {{{256}}};
enum { VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO = 1, VK_MEMORY_IMAGE_BLOCK, VK_MEMORY_IMAGE_DEDICATED };
static uint64_t sizes[4096], allocated, next_memory, releases;
static int fail_next;
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
int main(int argc, char **argv) {
    assert(argc == 2);
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
            for mode in ('default', 'trim', 'small', 'packed', '16MiB'):
                with self.subTest(mode=mode):
                    result = subprocess.run([str(binary), mode], env=dict(os.environ), capture_output=True,
                                            text=True, timeout=30)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
