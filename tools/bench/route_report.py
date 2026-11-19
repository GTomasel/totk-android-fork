#!/usr/bin/env python3
"""Compare Vulkan reports and a rootless Android capture for one gameplay route."""
import argparse
import collections
import json
import math
from pathlib import Path
import re

from analyze import parse_log
from benchlib import guard_output


EXIT_HEADER = re.compile(r'\btimestamp=([^\n]+?)\s+pid=(\d+)\b')
EXIT_REASON = re.compile(r'\breason=(\d+) \(([^)]+)\).*?\bstatus=(\d+)'
                         r'\s+importance=(\d+)', re.S)
DISPLAY_RATE = re.compile(r'\brenderFrameRate[ =]+([\d.]+)')
DUMPSYS_TOTALS = re.compile(r'TOTAL PSS:\s+(\d+)\s+TOTAL RSS:\s+(\d+)\s+TOTAL SWAP PSS:\s+(\d+)')
PSI_TOTAL = re.compile(r'^(some|full)\s+.*?\btotal=(\d+)\s*$', re.M)


def read_phase(spec):
    """NAME:FIRST_FRAME:LAST_FRAME[:FIRST_CAPTURE_SECOND:LAST_CAPTURE_SECOND]."""
    fields = spec.split(':')
    try:
        if len(fields) not in (3, 5) or not fields[0]:
            raise ValueError
        start, end = map(int, fields[1:3])
        if not 1 <= start <= end:
            raise ValueError
        seconds = tuple(map(float, fields[3:]))
        if seconds and (not all(map(math.isfinite, seconds)) or not 0 <= seconds[0] <= seconds[1]):
            raise ValueError
    except ValueError:
        raise argparse.ArgumentTypeError(f'invalid phase {spec!r}. Use {read_phase.__doc__}') from None
    return fields[0], (start, end), seconds


def output_of(command):
    return command.get('stdout', '') if command and command.get('returncode') == 0 else ''


def matching_exits(before, after, pids):
    """Keep new package exit records for processes observed in this capture."""
    if before.get('returncode') != 0 or after.get('returncode') != 0:
        return None

    def rows(command):
        text = output_of(command)
        headers = list(EXIT_HEADER.finditer(text))
        for index, header in enumerate(headers):
            end = headers[index + 1].start() if index + 1 < len(headers) else len(text)
            if reason := EXIT_REASON.search(text, header.end(), end):
                yield header[1], header[2], int(reason[1]), reason[2], int(reason[3]), int(reason[4])

    new_records = set(rows(after)) - set(rows(before))
    names = ('timestamp_device_local', 'pid', 'reason_code', 'reason', 'status', 'importance')
    return [dict(zip(names, row)) for row in sorted(new_records) if row[1] in pids]


def activity_deltas(rows, field, keys, identity=()):
    values, intervals = collections.Counter(), collections.Counter()
    for previous, current in zip(rows, rows[1:]):
        if not previous.get('pids') or not current.get('pids'):
            continue
        old, new = previous.get(field, {}), current.get(field, {})
        if any(key not in old or old[key] != new.get(key) for key in identity):
            continue
        for key in old.keys() & new.keys() & keys:
            if new[key] >= old[key]:
                values[key] += new[key] - old[key]
                intervals[key] += 1
    return {'delta': dict(sorted(values.items())), 'intervals': dict(sorted(intervals.items()))} if intervals else {}


def device_samples(rows):
    live = [row for row in rows if row.get('pids')]
    pids = sorted({pid for row in live for pid in row['pids']})
    summary = {'samples': len(rows), 'live_samples': len(live), 'pids': pids}
    for key in ('MemAvailable', 'SwapFree'):
        values = [row['system_bytes'][key] for row in live if key in row.get('system_bytes', {})]
        if values:
            summary[key + '_min_bytes'] = min(values)
    rates, app = collections.Counter(), collections.defaultdict(list)
    for row in live:
        for line in row.get('display_framework', ()):
            if line.startswith('DisplayDeviceInfo{') and (m := DISPLAY_RATE.search(line)):
                rates[round(float(m[1]), 2)] += 1
                break
        if m := DUMPSYS_TOTALS.search(output_of(row.get('app_memory'))):
            for key, value in zip(('pss', 'rss', 'swap_pss'), m.groups()):
                app[key].append(int(value) * 1024)
    summary['framework_render_hz_samples'] = dict(sorted(rates.items()))
    summary['dumpsys_app_max_bytes'] = {key: max(values) for key, values in app.items()}
    # Count only adjacent live samples with readable, nondecreasing PSI totals.
    stalls, spans = collections.Counter(), collections.Counter()
    pressures = [dict((k, int(v)) for k, v in PSI_TOTAL.findall(output_of(row.get('memory_pressure'))))
                 if row.get('pids') else {} for row in rows]
    for previous, current in zip(pressures, pressures[1:]):
        for key in previous.keys() & current.keys():
            if current[key] >= previous[key]:
                stalls[key] += current[key] - previous[key]
                spans[key] += 1
    summary['system_psi_observed_stall_us'] = dict(stalls)
    summary['system_psi_intervals'] = dict(spans)
    vm = activity_deltas(rows, 'vm_activity', {'pgmajfault', 'pswpin', 'pswpout', 'pgscan_direct', 'pgsteal_direct',
                                              'allocstall_dma32', 'allocstall_normal', 'allocstall_movable'})
    process = activity_deltas(rows, 'process_faults', {'minor', 'major'}, ('pid', 'start_ticks'))
    if vm:
        summary['vm_activity'] = vm
    if process:
        summary['process_faults'] = process
    return summary


def report(log, capture, phases):
    timing, gpu, fps, _, _, info = parse_log(log)
    device_rows = []
    capture_summary = None
    if capture:
        with (capture / 'samples.jsonl').open() as samples:
            device_rows = [json.loads(line) for line in samples if line.strip()]
        source = json.loads((capture / 'report.json').read_text())
        capture_summary = {
            **device_samples(device_rows),
            **{key: source.get(key) for key in ('package', 'elapsed_s', 'game_observed', 'game_disappeared',
                                               'capture_start_host_unix_s')},
        }
        before, after = (json.loads((capture / f'exit-{suffix}.json').read_text()) for suffix in ('before', 'after'))
        capture_summary['new_observed_pid_exits'] = matching_exits(before, after, capture_summary['pids'])
    memory = info['renderer_memory']
    windows = []
    for end in sorted(fps.keys() | timing.keys() | memory.keys()):
        start = max(1, end - 299)
        window = {'frames': [start, end], 'memory': memory.get(end, {})}
        if end in timing and end in fps and end >= 300:
            p50, p95, maximum = timing[end]
            window['frame_time'] = dict(fps=fps[end], p50_ms=p50, p95_ms=p95, max_ms=maximum,
                                        p99_ms=info['frame_p99'].get(end, (None, None))[0], gpu_ms=gpu.get(end))
        for name, key in (('uploads', 'upload_windows'), ('pipeline_builds', 'pipeline_windows'),
                          ('command_walker', 'walker_windows')):
            if end in info[key]:
                window[name] = info[key][end]
        current = window['memory'].get('upload-partial', {})
        keys = ('uploads', 'staging_bytes_avoided')
        previous = dict.fromkeys(keys, 0) if end == 300 else memory.get(end - 300, {}).get('upload-partial', {})
        if all(key in current and key in previous and current[key] >= previous[key] for key in keys):
            window['partial_uploads'] = {key: current[key] - previous[key] for key in keys}
        windows.append(window)
    phase_reports = []
    for name, frames, seconds in phases:
        selected = [w for w in windows if 'frame_time' in w and
                    frames[0] <= w['frames'][0] and w['frames'][1] <= frames[1]]
        long_frames = [event for event in info['renderer_long_frames'] if frames[0] <= event['frame'] <= frames[1]]
        selected_samples = [row for row in device_rows if seconds and seconds[0] <= row['elapsed_s'] <= seconds[1]]
        phase_reports.append({'name': name, 'frames': frames, 'capture_seconds': seconds or None, 'windows': selected,
                              'long_frames': long_frames,
                              'device': device_samples(selected_samples) if capture and seconds else None})
    return {'capture': capture_summary, 'phases': phase_reports, 'windows': windows,
            'allocation_events': info['allocation_events'], 'long_frames': info['renderer_long_frames'],
            'timeline_late_frames': info['timeline_late_frames']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('log', type=Path, help='game log from one run')
    parser.add_argument('--capture', type=Path, help='directory from android_memory_capture.py')
    parser.add_argument('--phase', type=read_phase, action='append', default=[], metavar='NAME:START:END[:T0:T1]',
                        help=read_phase.__doc__)
    parser.add_argument('--out', type=Path, help='write the JSON report here instead of stdout')
    args = parser.parse_args()
    try:
        result = report(args.log, args.capture, args.phase)
        encoded = json.dumps(result, indent=2) + '\n'
        if args.out:
            guard_output(args.out)
            with args.out.open('x') as output:
                output.write(encoded)
        else:
            print(encoded, end='')
    except (OSError, ValueError) as exc:
        parser.error(str(exc))


if __name__ == '__main__':
    main()
