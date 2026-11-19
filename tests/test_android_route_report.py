"""Replay renderer and rootless device evidence without accessing Android."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools/bench'))
from route_report import device_samples, matching_exits, read_phase, report  # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from android_memory_capture import process_faults, vm_activity  # noqa: E402


def result(text, code=0):
    return {'returncode': code, 'stdout': text}


class RouteReportTest(unittest.TestCase):
    def test_optional_timeline_retains_coverage_and_uses_its_own_frame_numbers(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'game.log'
            path.write_text(
                '[frame-tl late] frame=45 target=33.3 game_iv=108.0 apply_iv=nan '
                'dominant=wake growth=66.1 ms wake_gap=99.4 walk=25.5 offcpu=4.0 gpu=10.0 '
                'gpu_tail=15.5 gpu_complete=0 acquire=0.0 lost_walks=0 lost_slots=1\n'
                '[frame-tl late] frame=46 target=33.3 game_iv=nan display_iv=66.7 '
                'dominant=gpu growth=14.1 ms gpu=21.2 gpu_tail=8.0 gpu_complete=1 '
                'slots=[7:1.0,2.0,3.0,4.0,gpu=99.0]\n')
            result = report(path, None, [read_phase('surface:1:300')])
        first, second = result['timeline_late_frames']
        self.assertEqual(first, {
            'timeline_frame': 45, 'dominant': 'wake', 'gpu_complete': False, 'lost_walks': 0, 'lost_slots': 1,
            'timings_ms': {'target': 33.3, 'game_iv': 108.0, 'growth': 66.1, 'wake_gap': 99.4,
                           'walk': 25.5, 'offcpu': 4.0, 'acquire': 0.0}})
        self.assertEqual(second['timings_ms'],
                         {'target': 33.3, 'display_iv': 66.7, 'growth': 14.1, 'gpu': 21.2, 'gpu_tail': 8.0})
        self.assertNotIn('timeline_late_frames', result['phases'][0])

    def test_long_frames_report_work_for_the_exact_frame_and_phase(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'game.log'
            path.write_text(
                '[nvn-vk] long frame 6104: 1850 ms since the last present; recording 1829.7 ms '
                '(pipelines made at the draw 1697.9, compute pipelines 0.0, seed files 79.4), '
                "GPU waits while recording 0.3 ms, the game's sync waits 0.0 ms (0), 0 CPU steps\n"
                '[nvn-vk] long frame 23943: 108 ms since the last present; recording 26.7 ms '
                '(pipelines made at the draw 0.0, compute pipelines 0.0, seed files 0.0), '
                "GPU waits while recording 0.0 ms, the game's sync waits 1.7 ms (1), 0 CPU steps\n")
            result = report(path, None, [read_phase('return:22000:24500')])
        self.assertEqual(result['long_frames'][0],
                         {'frame': 6104, 'present_ms': 1850.0, 'recording_ms': 1829.7,
                          'graphics_pipeline_ms': 1697.9, 'compute_pipeline_ms': 0.0,
                          'seed_read_ms': 79.4, 'gpu_wait_ms': 0.3, 'game_sync_wait_ms': 0.0})
        self.assertEqual(len(result['long_frames']), 2)
        self.assertEqual(result['phases'][0]['long_frames'], [result['long_frames'][1]])
        self.assertEqual(result['long_frames'][1]['graphics_pipeline_ms'], 0.0)
        self.assertEqual(result['long_frames'][1]['game_sync_wait_ms'], 1.7)

    def test_fault_deltas_require_readable_samples_of_the_same_process(self):
        def proc(pid, start, minor, major):
            stat = f'{pid} (app (game) v2) S 0 0 0 0 0 0 {minor} 0 {major} 0 0 0 0 0 0 0 0 0 {start}'
            return process_faults(stat, pid)

        def sample(pid, start, minor, major, swap):
            return {'pids': [pid], 'system_bytes': {},
                    'process_faults': proc(pid, start, minor, major),
                    'vm_activity': vm_activity(f'pswpin {swap}\npgmajfault 4\nother 99\n')}

        a = sample('12', 60, 100, 10, 1000)
        b = sample('12', 60, 114, 19, 1004)
        c = sample('12', 61, 250, 35, 1005)
        d = sample('12', 61, 255, 41, 1008)
        summary = device_samples([a, b, c, d])
        self.assertEqual(summary['process_faults'],
                         {'delta': {'major': 15, 'minor': 19}, 'intervals': {'major': 2, 'minor': 2}})
        self.assertEqual(summary['vm_activity'],
                         {'delta': {'pgmajfault': 0, 'pswpin': 8},
                          'intervals': {'pgmajfault': 3, 'pswpin': 3}})
        self.assertEqual(process_faults('13 (other) R 1', '12'), {})
        self.assertNotIn('process_faults', device_samples([a, {'pids': ['12'], 'system_bytes': {}}, d]))

    def test_frame_windows_endpoints_and_partial_capture(self):
        log = """[nvn-vk] [image-allocation-high] sub=0 blocks=33554432 dedicated=0 occupied=4194304
[nvn-vk] settled write-back memory: records 0 bytes, staging 0 bytes
[nvn-vk] frame 300: 30.0 fps over the last 300, 200 draws
[nvn-vk] memory image blocks: used/free 1.000/31.000 MiB in currently allocated blocks
[nvn-vk] memory recording: slot/snapshot arenas retained 8.0/0.0 MiB; draw packet slabs 2.0 MiB, descriptor input slabs 1.0 MiB
[nvn-vk] memory: malloc 12 MiB in use; image blocks 32 MiB + dedicated 0 MiB, 0 images retired waiting, 4 texture objects, 1 shared images, 0 write-back records, 64 retired list capacity; pools 2 (200 MiB)
[nvn-vk] [upload-partial] frame=300 uploads=3 staging_bytes_avoided=4096
[totk-gfx] [nvn] 计时 至帧 300： 帧时间 p50 33.0 / p95 42.0 / 最大 51.0 ms
[nvn-vk] settled write-back memory: records 128 bytes, staging 1024 bytes, peak staging 8192 bytes
[nvn-vk] [wb-queue] frame=600 staged=1 unstaged_sweeps_skipped=65 bounds_rebuilds=1 quiet_seals_skipped=64
[nvn-vk] [upload-prep] frame=600 heap_region_plans=2 fresh_barriers_skipped=500
[nvn-vk] [upload-partial] frame=600 uploads=8 staging_bytes_avoided=1048576
[nvn-vk] [recorder-free-pages] frame=600 calls=1 discarded_bytes=258048
[nvn-vk] frame 600: 26.1 fps over the last 300, 300 draws
[nvn-vk] frame 600, stutter: longest frame 420.0 ms, 162 frames over 33 ms, 25 over 50 ms; 33 new pipelines took 6.5 ms (longest 1.4 ms)
[nvn-vk] frame 600, texture uploads: 1605 (225.3 MiB) in 291.3 ms
[nvn-vk] walker cpu frame 600: cpu 26.009 ms/frame, wall 98.558 ms/frame, draws 3929.107/frame, cpu 6.620 us/draw, offcpu 72.549 ms/frame
[nvn-vk] [arena-peaks] sub=561 slot_allocated=8388608 slot_peak=46137344 snapshot_allocated=0 snapshot_peak=0 combined_peak=46137344
[nvn-vk] [arena-early-trim] sub=561 trims=2 released_bytes=9437184
[nvn-vk] [descriptor-idle-trim] frame=600 recorder_pools_freed=2 primary_pools_freed=2
[nvn-vk] [image-block-classes] frame=599 small_blocks=1 small_committed=8388608 small_used=4194304
[nvn-vk] [image-peaks] frame=599 peak_committed=92274688 at_peak_blocks=67108864 at_peak_dedicated=25165824 peak_occupied=50331648
[nvn-vk] [image-memory] retired_mib=36.000 retired_dedicated_mib=24.000 ready_dedicated_mib=24.000 ready_spans_mib=0.000
[nvn-vk] [image-reclaim-before-grow] runs=5 probes=3 images=1 span_bytes=0 fits_after_reclaim=0 peak_us=154.0 dedicated_runs=5 dedicated_bytes=25165824 single_span_fits=1
[nvn-vk] [image-allocation-pressure] frame=600 memory_errors=2 recovered=1
[nvn-vk] [image-realization-retry] frame=600 attempts=3 recovered=2
[nvn-vk] [image-ownership] frame=600 private_mirror_bytes=6291456 private_aux_bytes=4096
[nvn-vk] [mirror-age] frame=599 unknown=0 under120=2097152 age120_599=0 age600_3599=4194304 age3600_plus=0 blocks_entirely_age600_plus=0 dedicated_age600_plus=0
[nvn-vk] [guest-shmem] backing_bytes=9437184 sparse_copy_bytes=16777216 punched_range_bytes=3145728 preserved_alias_bytes=65536 punch_errors=0
[nvn-vk] [guest-shmem-displaced] frame=599 complete=1 covered_bytes=8388608 occupied_bytes=4194304
[nvn-vk] [pool-images] detached=2 awaiting_owners=1 retired=1 base_bytes_retired=4096
[totk-gfx] [nvn] 计时 至帧 600： 帧时间 p50 33.68 / p95 60.70 / 最大 423.16 ms
[totk-gfx] [nvn] 帧间隔 至帧 600：>16.7ms 292 / 300 帧，p99 159.29 ms
[nvn-vk] [arena-allocation-high] sub=999 slot=50331648 snapshot=0 total=50331648
[nvn-vk] settled write-back memory: records 128 bytes, staging 16384 bytes
[nvn-vk] frame 1200: 23.0 fps over the last 300, 500 draws
[nvn-vk] [upload-partial] frame=1200 uploads=10 staging_bytes_avoided=2097152
[nvn-vk] settled write-back memory: records 128 bytes, staging 9999 bytes
"""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'game.log'
            path.write_text(log)
            analyzed = report(path, None, [read_phase('return:301:630'), read_phase('straddles:1:599'),
                                           read_phase('incomplete:901:1200')])
        first, second, partial = analyzed['windows']
        self.assertEqual(first['memory']['totals']['guest_pool_mib'], 200)
        self.assertEqual(first['memory']['write_back'], {'staging_bytes': 0})
        self.assertEqual(second['memory']['write_back'], {'staging_bytes': 1024, 'peak_staging_bytes': 8192})
        self.assertEqual(second['memory']['wb-queue']['unstaged_sweeps_skipped'], 65)
        self.assertEqual(second['memory']['wb-queue']['quiet_seals_skipped'], 64)
        self.assertEqual(second['memory']['upload-prep']['fresh_barriers_skipped'], 500)
        self.assertEqual(second['memory']['recorder-free-pages']['discarded_bytes'], 258048)
        self.assertEqual(second['memory']['image-ownership']['private_mirror_bytes'], 6291456)
        self.assertEqual(second['memory']['mirror-age']['age600_3599'], 4194304)
        self.assertEqual(second['memory']['guest-shmem'],
                         {'backing_bytes': 9437184, 'sparse_copy_bytes': 16777216,
                          'punched_range_bytes': 3145728, 'preserved_alias_bytes': 65536, 'punch_errors': 0})
        self.assertEqual(second['memory']['guest-shmem-displaced']['occupied_bytes'], 4194304)
        self.assertEqual(second['memory']['pool-images']['awaiting_owners'], 1)
        self.assertEqual(second['memory']['arena-peaks']['combined_peak'], 46137344)
        self.assertEqual(second['memory']['arena-early-trim']['released_bytes'], 9437184)
        self.assertEqual(second['memory']['descriptor-idle-trim'],
                         {'frame': 600, 'recorder_pools_freed': 2, 'primary_pools_freed': 2})
        self.assertEqual(second['memory']['image-block-classes']['small_used'], 4194304)
        self.assertEqual(second['memory']['image-peaks']['peak_committed'], 92274688)
        self.assertEqual(second['memory']['image-memory']['ready_dedicated_mib'], 24.0)
        self.assertEqual(second['memory']['image-reclaim-before-grow']['dedicated_bytes'], 25165824)
        self.assertEqual(second['memory']['image-reclaim-before-grow']['single_span_fits'], 1)
        self.assertEqual(second['memory']['image-allocation-pressure']['recovered'], 1)
        self.assertEqual(second['memory']['image-realization-retry'], {'frame': 600, 'attempts': 3, 'recovered': 2})
        self.assertEqual(first['partial_uploads'], {'uploads': 3, 'staging_bytes_avoided': 4096})
        self.assertEqual(second['partial_uploads'], {'uploads': 5, 'staging_bytes_avoided': 1044480})
        self.assertEqual(partial['memory']['upload-partial']['uploads'], 10)
        self.assertNotIn('partial_uploads', partial)
        self.assertEqual(second['pipeline_builds']['total_ms'], 6.5)
        self.assertEqual(second['uploads']['mib'], 225.3)
        self.assertEqual(second['command_walker'], {'cpu_ms': 26.009, 'wall_ms': 98.558, 'off_cpu_ms': 72.549})
        self.assertEqual(second['frame_time']['p99_ms'], 159.29)
        self.assertEqual(analyzed['phases'][0]['windows'], [second])
        self.assertEqual(analyzed['phases'][1]['windows'], [first])
        self.assertEqual(analyzed['phases'][2]['windows'], [])
        self.assertNotIn('frame_time', partial)
        self.assertNotIn('write_back', partial['memory'])
        self.assertEqual([e['after_window_frame'] for e in analyzed['allocation_events']], [None, 600])

    def test_missing_counters_and_readable_psi_intervals(self):
        rows = [
            {'pids': ['12'], 'system_bytes': {'MemAvailable': 4}, 'memory_pressure': result('full total=100'),
             'display_framework': ['DisplayDeviceInfo{type INTERNAL renderFrameRate 120.00001']},
            {'pids': ['12'], 'system_bytes': {'MemAvailable': 8}, 'memory_pressure': result('full total=180', 1),
             'display_framework': ['mActiveSfDisplayMode={peakRefreshRate=120.0}']},
            {'pids': ['12'], 'memory_pressure': result('full total=200'),
             'display_framework': ['DisplayDeviceInfo{type INTERNAL renderFrameRate 60.000004']},
            {'pids': ['12'], 'memory_pressure': result('full total=225'),
             'app_memory': result('TOTAL PSS: 9 TOTAL RSS: 7 TOTAL SWAP PSS: 3')},
            {'pids': [], 'system_bytes': {'MemAvailable': 1}, 'memory_pressure': result('full total=500')},
        ]
        summary = device_samples(rows)
        self.assertEqual(summary['framework_render_hz_samples'], {120.0: 1, 60.0: 1})
        self.assertEqual(summary['MemAvailable_min_bytes'], 4)
        self.assertEqual(summary['dumpsys_app_max_bytes'], {'pss': 9216, 'rss': 7168, 'swap_pss': 3072})
        self.assertEqual(summary['system_psi_observed_stall_us'], {'full': 25})
        self.assertEqual(summary['system_psi_intervals'], {'full': 1})

    def test_exit_status_requires_current_pid_and_new_record(self):
        def record(date, pid, code, reason, status):
            return (f'timestamp={date} pid={pid} realUid=10512\n'
                    f'process=com.test.app reason={code} ({reason}) subreason=0 (UNKNOWN) status={status}\n'
                    f'importance=100 pss=0.00\n')
        previous = record('2026-01-01 08:00:00.123', 12, 3, 'LOW_MEMORY', 0)
        unrelated = record('2026-01-01 12:05:00.123', 44, 3, 'LOW_MEMORY', 0)
        current = record('2026-01-01 12:00:00.123', 12, 2, 'SIGNALED', 9)
        self.assertEqual(matching_exits(result(previous), result(current + unrelated + previous), ['12']), [
            {'timestamp_device_local': '2026-01-01 12:00:00.123', 'pid': '12', 'reason_code': 2,
             'reason': 'SIGNALED', 'status': 9, 'importance': 100},
        ])
        self.assertIsNone(matching_exits(result('', 1), result(current), ['12']))

    def test_capture_phase_uses_explicit_elapsed_range(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            (path / 'game.log').touch()
            records = [{'elapsed_s': t, 'pids': ['1'], 'system_bytes': {'MemAvailable': t}} for t in (0, 5, 10)]
            (path / 'samples.jsonl').write_text('\n'.join(map(json.dumps, records)))
            (path / 'report.json').write_text(json.dumps({'capture_start_host_unix_s': 234.0}))
            for label in ('before', 'after'):
                (path / f'exit-{label}.json').write_text(json.dumps(result('')))
            summary = report(path / 'game.log', path, [read_phase('return:1:40:4:9'), read_phase('other:41:50')])
        self.assertEqual(summary['capture']['capture_start_host_unix_s'], 234)
        self.assertEqual(summary['capture']['live_samples'], 3)
        self.assertEqual(summary['phases'][0]['device']['MemAvailable_min_bytes'], 5)
        self.assertIsNone(summary['phases'][1]['device'])


if __name__ == '__main__':
    unittest.main()
