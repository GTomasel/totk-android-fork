"""Production low-memory profile defaults and launch ordering, without changing guest memory or image quality."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class LowMemoryTests(unittest.TestCase):
    def test_profile_respects_explicit_values_and_starts_before_renderer_workers(self):
        compiler = shutil.which('cc')
        if not compiler:
            self.skipTest('C compiler required')
        source = r'''
#define _POSIX_C_SOURCE 200809L
#include "games/totk/runtime/android_memory.h"
#include <assert.h>
int main(void) {
    const char *names[] = {"TOTK_LOW_MEMORY", "TOTK_VK_STAGING_RETAIN_MB", "TOTK_VK_REC_MEMORY_MB", "TOTK_VK_IMAGE_FREE_EMPTY",
        "TOTK_VK_DESC_COMPACT", "TOTK_PSO_PREWARM", "TOTK_SEED_WARM_MB", "TOTK_VK_IMAGE_BLOCK_MB", "TOTK_VK_IMAGE_PACK",
        "TOTK_VK_WB_AUTO_STAGING_MB"};
    for (unsigned i = 0; i < sizeof names / sizeof *names; i++) unsetenv(names[i]);
    totk_android_memory_defaults();
    for (unsigned i = 1; i < sizeof names / sizeof *names; i++) assert(!getenv(names[i]));
    setenv("TOTK_LOW_MEMORY", "0", 1); totk_android_memory_defaults();
    assert(!getenv("TOTK_VK_STAGING_RETAIN_MB"));
    assert(!getenv("TOTK_VK_WB_AUTO_STAGING_MB"));
    setenv("TOTK_LOW_MEMORY", "1", 1); totk_android_memory_defaults();
    assert(!strcmp(getenv("TOTK_VK_STAGING_RETAIN_MB"), "8"));
    assert(!strcmp(getenv("TOTK_VK_WB_AUTO_STAGING_MB"), "12"));
    assert(!strcmp(getenv("TOTK_VK_REC_MEMORY_MB"), "32"));
    assert(!strcmp(getenv("TOTK_VK_IMAGE_FREE_EMPTY"), "1"));
    assert(getenv("TOTK_VK_DESC_COMPACT") && !strcmp(getenv("TOTK_VK_DESC_COMPACT"), "1"));
    assert(getenv("TOTK_PSO_PREWARM") && !strcmp(getenv("TOTK_PSO_PREWARM"), "0"));
    assert(getenv("TOTK_SEED_WARM_MB") && !strcmp(getenv("TOTK_SEED_WARM_MB"), "16"));
    assert(!strcmp(getenv("TOTK_VK_IMAGE_BLOCK_MB"), "32"));
    assert(!strcmp(getenv("TOTK_VK_IMAGE_PACK"), "0"));
    setenv("TOTK_VK_IMAGE_BLOCK_MB", "64", 1);
    setenv("TOTK_VK_WB_AUTO_STAGING_MB", "0", 1);
    setenv("TOTK_VK_STAGING_RETAIN_MB", "12", 1); setenv("TOTK_VK_IMAGE_FREE_EMPTY", "0", 1);
    setenv("TOTK_VK_REC_MEMORY_MB", "64", 1); setenv("TOTK_VK_IMAGE_PACK", "1", 1); totk_android_memory_defaults();
    assert(!strcmp(getenv("TOTK_VK_STAGING_RETAIN_MB"), "12"));
    assert(!strcmp(getenv("TOTK_VK_IMAGE_BLOCK_MB"), "64"));
    assert(!strcmp(getenv("TOTK_VK_WB_AUTO_STAGING_MB"), "0"));
    assert(!strcmp(getenv("TOTK_VK_REC_MEMORY_MB"), "64"));
    assert(!strcmp(getenv("TOTK_VK_IMAGE_FREE_EMPTY"), "0"));
    assert(!strcmp(getenv("TOTK_VK_IMAGE_PACK"), "1"));
    setenv("TOTK_VK_DESC_COMPACT", "0", 1); setenv("TOTK_PSO_PREWARM", "1", 1);
    setenv("TOTK_SEED_WARM_MB", "64", 1); totk_android_memory_defaults();
    assert(!strcmp(getenv("TOTK_VK_DESC_COMPACT"), "0"));
    assert(!strcmp(getenv("TOTK_PSO_PREWARM"), "1"));
    assert(!strcmp(getenv("TOTK_SEED_WARM_MB"), "64"));
    return 0;
}
'''
        with tempfile.TemporaryDirectory(prefix='totk-low-memory-') as directory:
            c, binary = Path(directory) / 'profile.c', Path(directory) / 'profile'
            c.write_text(source)
            subprocess.run([compiler, '-std=c11', '-Wall', '-Wextra', '-Werror', '-I', str(ROOT), str(c), '-o', str(binary)],
                           capture_output=True, text=True, check=True, timeout=30)
            subprocess.run([str(binary)], capture_output=True, text=True, check=True, timeout=30)
        frontend = (ROOT / 'games/totk/runtime/frontend_android.c').read_text()
        loaded = frontend.index('snprintf(p, sizeof p, "%s/totk.env", g_data); env_file(p);')
        configured = frontend.index('totk_android_memory_defaults();', loaded)
        self.assertLess(configured, frontend.index('live_ctl_start();', loaded))
        self.assertLess(configured, frontend.index('thread_sampler_start();', loaded))


if __name__ == '__main__':
    unittest.main()
