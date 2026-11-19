#!/usr/bin/env python3
"""Capture rootless Android memory and package exit evidence without reading game data or keys.

Example: python3 tools/android_memory_capture.py --serial SERIAL --duration 180
    --out .scratch/issue-audit/s23-baseline
Start the game yourself. If it is never observed running, the report explicitly says so.
Graphics/shared-memory counters are retained separately and must not be summed as disjoint allocations.
"""
import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess
import time


VM_ACTIVITY = {'pgmajfault', 'pswpin', 'pswpout', 'pgscan_direct', 'pgsteal_direct',
               'allocstall_dma32', 'allocstall_normal', 'allocstall_movable'}


def process_faults(source, pid):
    """Read process totals from proc stat, whose command can contain spaces or parentheses."""
    identity, separator, fields = source.rpartition(')')
    values = fields.split()
    if not separator or not identity.startswith(f'{pid} (') or len(values) < 20:
        return {}
    try:
        return {'pid': pid, 'start_ticks': int(values[19]),
                'minor': int(values[7]), 'major': int(values[9])}
    except ValueError:
        return {}


def vm_activity(source):
    return {key: int(value) for key, value in re.findall(r'^(\w+) (\d+)$', source, re.M)
            if key in VM_ACTIVITY}


def memory_values(source):
    result = {}
    for line in source.splitlines():
        match = re.fullmatch(r'([A-Za-z_()]+):\s+(\d+)\s+kB', line.strip())
        if match:
            result[match[1]] = int(match[2]) * 1024
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--serial', required=True)
    parser.add_argument('--package', default='com.aure.totk')
    parser.add_argument('--pid', type=int, help='track this gameplay PID and stop when it exits')
    parser.add_argument('--duration', type=float, default=180)
    parser.add_argument('--interval', type=float, default=5)
    parser.add_argument('--display', action='store_true', help='also sample the internal display framework mode/rate')
    parser.add_argument('--faults', action='store_true', help='sample kernel VM activity and the game process fault counters when readable')
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]*(?:\.[A-Za-z0-9_]+)+', args.package):
        parser.error('invalid Android package name')
    if args.duration <= 0 or args.interval < 1:
        parser.error('duration must be positive and interval at least one second')
    if args.pid is not None and args.pid <= 0:
        parser.error('PID must be positive')
    adb = shutil.which('adb')
    if not adb:
        parser.error('adb not found')
    args.out.mkdir(parents=True, exist_ok=False)

    def run(*command, timeout=15):
        try:
            result = subprocess.run([adb, '-s', args.serial, *command], capture_output=True,
                                    text=True, errors='replace', timeout=timeout)
            return {'returncode': result.returncode, 'stdout': result.stdout, 'stderr': result.stderr}
        except subprocess.TimeoutExpired:
            return {'returncode': -1, 'stdout': '', 'stderr': 'timed out'}

    state = run('get-state')
    if state['returncode'] or state['stdout'].strip() != 'device':
        parser.error('device unavailable or unauthorized: ' + state['stderr'].strip())
    properties = {}
    for name in ('ro.product.model', 'ro.soc.model', 'ro.build.version.release', 'ro.build.version.sdk'):
        properties[name] = run('shell', 'getprop', name)
    (args.out / 'device.json').write_text(json.dumps(properties, indent=2) + '\n')
    (args.out / 'exit-before.json').write_text(json.dumps(run('shell', 'dumpsys', 'activity', 'exit-info', args.package), indent=2) + '\n')
    started = time.monotonic()
    started_unix = time.time()
    observed, disappeared, samples = False, False, 0
    try:
        with (args.out / 'samples.jsonl').open('w') as output:
            while time.monotonic() - started < args.duration:
                tick = time.monotonic()
                pid_result = run('shell', 'pidof', args.package)
                pids = [word for word in pid_result['stdout'].split() if word.isdecimal()]
                if args.pid is not None:
                    pids = [pid for pid in pids if pid == str(args.pid)]
                sample = {'elapsed_s': round(tick - started, 3), 'pids': pids}
                meminfo = run('shell', 'cat', '/proc/meminfo')
                sample['system_bytes'] = memory_values(meminfo['stdout'])
                sample['memory_pressure'] = run('shell', 'cat', '/proc/pressure/memory')
                if args.faults:
                    sample['vm_activity'] = vm_activity(run('shell', 'cat', '/proc/vmstat')['stdout'])
                if args.display:
                    display = run('shell', 'dumpsys', 'display')
                    # Preserve the framework evidence, not a claimed hardware scanout measurement.
                    sample['display_framework'] = [line.strip() for line in display['stdout'].splitlines()
                        if ('DisplayDeviceInfo{' in line and 'type INTERNAL' in line)
                        or 'mActiveSfDisplayMode=' in line]
                if pids:
                    observed = True
                    app = pids[0] if args.pid is not None else args.package
                    sample['app_memory'] = run('shell', 'dumpsys', 'meminfo', '-a', app)
                    sample['status'] = run('shell', 'cat', '/proc/' + pids[0] + '/status')
                    sample['smaps_rollup'] = run('shell', 'cat', '/proc/' + pids[0] + '/smaps_rollup')
                    if args.faults:
                        path = f'/proc/{pids[0]}/stat'
                        data = run('shell', 'cat', path)
                        if data['returncode'] != 0:
                            data = run('shell', 'run-as', args.package, 'cat', path)
                        sample['process_faults'] = process_faults(data['stdout'], pids[0])
                elif (observed or args.pid is not None) and pid_result['returncode'] in (0, 1) and not pid_result['stderr'].strip():
                    disappeared = True
                output.write(json.dumps(sample) + '\n'); output.flush(); samples += 1
                print(f"{sample['elapsed_s']:7.1f}s game={'running' if pids else 'not running'} "
                      f"available={sample['system_bytes'].get('MemAvailable', 0) / 1048576:.0f} MiB", flush=True)
                if disappeared:
                    break
                remaining = min(args.interval - (time.monotonic() - tick), args.duration - (time.monotonic() - started))
                if remaining > 0:
                    time.sleep(remaining)
    finally:
        # Package-scoped exit records include low-memory exits even when an ordinary crash handler never ran.
        (args.out / 'exit-after.json').write_text(json.dumps(run('shell', 'dumpsys', 'activity', 'exit-info', args.package), indent=2) + '\n')
        log = run('logcat', '-d', '-t', '3000', '-v', 'threadtime', 'lmkd:I', 'lowmemorykiller:I',
                  'ActivityManager:I', 'AndroidRuntime:E', 'libc:F', '*:S')
        relevant = [line for line in log['stdout'].splitlines() if args.package in line]
        (args.out / 'package-exit-log.txt').write_text('\n'.join(relevant) + '\n')
        report = {'package': args.package, 'samples': samples, 'game_observed': observed,
                  'game_disappeared': disappeared, 'elapsed_s': round(time.monotonic() - started, 3),
                  'capture_start_host_unix_s': started_unix,
                  'qualification': 'Device evidence captured; inspect exit reason and per-category counters.' if observed
                  else 'No gameplay captured: the game process was never observed.',
                  'limits': 'No root; inaccessible proc counters retain their errors. Shared/GPU/RSS/PSS counters overlap.'}
        if args.pid is not None:
            report['target_pid'] = args.pid
        (args.out / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
        print(report['qualification'], flush=True)


if __name__ == '__main__':
    main()
