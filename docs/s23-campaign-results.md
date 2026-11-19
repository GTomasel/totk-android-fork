# S23+ campaign checkpoint for 1.1.2

The device was a Galaxy S23+ with 8 GB, Android 16, game 1.4.3, bundled Turnip, a 30 FPS cap, and the 960 × 540 handheld profile with dynamic resolution. The campaign uses direct game checkpoints. The late battery run used 256-pixel shadows, 8 MiB of upload staging retention per slot, and a 12 MiB staging budget for deferrable GPU-to-guest copies.

## Return from the Depths

| Trial | Observation |
| --- | --- |
| Prior runs in battery mode, 256-pixel and original shadows | Android recorded foreground `LOW_MEMORY` 67 s and 31 s after requesting the surface warp. |
| Short return with the 12 MiB budget | Peak write-back staging was 12.03 MiB, compared with 26.81 MiB in the short control. Both completed post-return movement. Starting temperature, charging state and process age varied. |
| Longer return with the 12 MiB budget | The same process crossed Lookout Landing, the Sky and the Depths, then completed two surface movement segments. The run stopped at the requested 40% battery threshold after 41 min 13 s, 151.3 s after requesting the return and 115.3 s after recovering control. Android recorded `EXIT_SELF` with status 0. |

The longer return measured 11.86 MiB of peak write-back staging, 3,897 MiB peak PSS, 598 MiB minimum system available memory and 16.07% maximum `PSI full avg10` during the warp. The PSS peak fell between the two earlier failing runs. Process age, weather and route timing differed. The figures describe the tested profile. Qualification still requires repeated runs.

The field averaged 29.92 real FPS over 23 complete windows. The highest window p95 was 40.90 ms. The Depths averaged 24.89 FPS over 27 complete windows, with a maximum window p95 of 92.55 ms. Two 90–120 minute sessions, screen-off recovery and the demanding-scene frame-time target remain open.

## Release policy

Low memory mode now selects the tested 12 MiB budget. Explicit read-backs keep their immediate path. Eight MiB remains the upload staging retention target. In the short pilot, 4 MiB halved the settled upload staging reserve while total PSS remained comparable and frame pacing worsened under different thermal conditions. The burst trimming option stays opt-in. Its own allocator peak fell from 104 to 96 MiB in the short pilot, while the measured overall PSS peak rose.

The native graphics menu was checked on the S23+ with and without a running game. Cancelling restart retained the existing process. Confirming restarted the game and applied the changed graphics setting. The personal save set was restored after the device work. An export matched all 32 files from the six slots by SHA-256. The raw captures and save backups are kept in the private test workspace.
