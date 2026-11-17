#!/usr/bin/env python3
"""Build a small Vulkan warm-up list from measured synchronous capture builds."""
import argparse
from pathlib import Path
import re
import struct

from merge_pso_keys import decode, encode, name, read_bounded, shader_ids


SYNC_TRACE = re.compile(
    r'\[pso-trace\] key=([0-9a-f]{16}) phase=build reason=capture-sync frame=\d+ '
    r'result=0 ms=(\d+\.\d+) flags=0 part=-1 vs=(\S+) fs=(\S+) early=\d+(?:\s|$)')


def trace_id(key):
    """Serialize the trace projection in the order used by pso_trace_key.h."""
    data = bytearray(b'TOTK-PSO-TRACE-KEY\0' + struct.pack('<I', 1))
    for shader in (name(key[:80]), name(key[80:160], optional=True)):
        data.extend(struct.pack('<I', len(shader) if shader else 0xffffffff))
        data.extend(shader)
    stage, state = key[160:164], key[164:]
    data.extend(stage)
    data.extend(state[:12 * 4])
    data.extend(state[19 * 4:75 * 4])
    data.extend(state[12 * 4:19 * 4])
    data.extend(state[75 * 4:])
    result = 14695981039346656037
    for byte in data:
        result = ((result ^ byte) * 1099511628211) & 0xffffffffffffffff
    return f'{result:016x}'


def select(records, trace, allowed, limit, minimum_ms):
    observed = {}
    for line in trace:
        match = SYNC_TRACE.search(line)
        if not match:
            continue
        identity, ms, vs, fs = match.groups()
        key = identity, vs.encode(), b'' if fs == '-' else fs.encode()
        observed[key] = max(observed.get(key, 0), float(ms))
    ranked = []
    for key, frequency, capture in records:
        vs, fs = name(key[:80]), name(key[80:160], optional=True)
        if not capture or vs[:64] not in allowed or fs and fs[:64] not in allowed:
            continue
        ms = observed.get((trace_id(key), vs, fs), 0)
        if ms >= minimum_ms:
            ranked.append((ms, key, frequency, capture))
    ranked.sort(key=lambda row: (-row[0], row[1]))
    return ranked[:limit]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('keys', type=Path, help='collection from the same session')
    parser.add_argument('trace', type=Path, help='session log with TOTK_PSO_TRACE=1')
    parser.add_argument('--shader-list', type=Path, default=Path(__file__).resolve().parents[1] / 'assets/shader_list.tsv')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--limit', type=int, choices=range(1, 33), default=8)
    parser.add_argument('--minimum-ms', type=float, default=50)
    args = parser.parse_args()
    if not 0 < args.minimum_ms <= 60000:
        parser.error('--minimum-ms must be positive and at most 60000')
    try:
        records = decode(read_bounded(args.keys))
        with args.trace.open(encoding='utf-8', errors='replace') as trace:
            selected = select(records, trace, shader_ids(args.shader_list), args.limit, args.minimum_ms)
        if not selected:
            raise ValueError('no measured capture builds matched the key list')
        args.output.write_bytes(encode([(key, frequency, capture) for _, key, frequency, capture in selected]))
    except (OSError, ValueError) as error:
        parser.exit(1, f'{error}\n')
    print(f'{len(selected)} keys, observed maximum times: ' + ', '.join(f'{row[0]:.1f} ms' for row in selected))


if __name__ == '__main__':
    main()
