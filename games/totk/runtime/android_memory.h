/* Opt-in host-cache retention profile for memory-constrained Android devices.
 * Apply after settings.env and totk.env, before live-control snapshots or any renderer workers.
 * Never shrink the guest's heap/address space or change resolution, frame generation or game timing. */
#pragma once
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#ifdef __BIONIC__
#include <malloc.h>
#endif

static inline void totk_android_memory_defaults(void) {
    const char *enabled = getenv("TOTK_LOW_MEMORY");
    if (!enabled || strcmp(enabled, "1")) return;
    /* Explicit developer values win. Upload bursts may exceed the retained capacity while active;
     * the existing slot-fence retirement path releases their surplus once they are safe to reuse. */
    setenv("TOTK_VK_STAGING_RETAIN_MB", "8", 0);
    setenv("TOTK_VK_WB_AUTO_STAGING_MB", "12", 0);
    setenv("TOTK_VK_REC_MEMORY_MB", "32", 0);
    setenv("TOTK_VK_IMAGE_FREE_EMPTY", "1", 0);
    setenv("TOTK_VK_IMAGE_BLOCK_MB", "32", 0);
    setenv("TOTK_VK_IMAGE_PACK", "0", 0);
    setenv("TOTK_VK_DESC_COMPACT", "1", 0);
    setenv("TOTK_PSO_PREWARM", "0", 0);
    setenv("TOTK_SEED_WARM_MB", "16", 0);
    fprintf(stderr, "[totk-memory] low-memory host retention: staging=%s MiB/slot, write-back staging=%s MiB, recorder=%s MiB, free-empty-image-blocks=%s, compact-descriptors=%s, pipeline-prewarm=%s, seed-warm=%s MiB, image-block=%s MiB, image-pack=%s\n",
            getenv("TOTK_VK_STAGING_RETAIN_MB"), getenv("TOTK_VK_WB_AUTO_STAGING_MB"),
            getenv("TOTK_VK_REC_MEMORY_MB"), getenv("TOTK_VK_IMAGE_FREE_EMPTY"),
            getenv("TOTK_VK_DESC_COMPACT"), getenv("TOTK_PSO_PREWARM"), getenv("TOTK_SEED_WARM_MB"),
            getenv("TOTK_VK_IMAGE_BLOCK_MB"), getenv("TOTK_VK_IMAGE_PACK"));
}

static inline void totk_android_memory_configure_allocator(void) {
#ifdef __BIONIC__
    const char *value = getenv("TOTK_ANDROID_SHORT_MALLOC_DECAY");
    if (value && !strcmp(value, "1")) {
        /* Bionic chooses the allocator's minimum release interval for freed pages. */
        int applied = mallopt(M_DECAY_TIME, 0);
        fprintf(stderr, "[totk-memory] short malloc decay: applied=%d\n", applied);
    }
#endif
}
