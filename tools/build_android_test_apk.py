#!/usr/bin/env python3
"""Build an independently signed test app; optionally update an authorized ADB device.

The stable key and increasing version counter live outside build caches. Updates use
adb install -r -t and preserve app data. Android may require the owner to authorize
the first installation; this tool never changes device security settings.
"""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'games/totk/android'))
import build_release as release


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ndk', type=Path, required=True)
    parser.add_argument('--android-sdk', type=Path, required=True)
    parser.add_argument('--turnip', type=Path, required=True)
    parser.add_argument('--translator', type=Path, help='Android translator; otherwise built with .NET 10')
    parser.add_argument('--work', type=Path, default=ROOT / '.scratch/android-test')
    parser.add_argument('--state-dir', type=Path, default=Path.home() / '.local/share/totk-android-fork',
                        help='persistent private signing key and build counter; keep between builds')
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--jobs', type=int, default=4)
    parser.add_argument('--install', metavar='ADB_SERIAL', help='update this already-authorized device after auditing')
    args = parser.parse_args(argv)
    os.chdir(ROOT)
    work, sdk, ndk = (p.expanduser().resolve() for p in (args.work, args.android_sdk, args.ndk))
    state = args.state_dir.expanduser().resolve()
    state.mkdir(parents=True, exist_ok=True, mode=0o700)
    logs = work / 'logs'
    logs.mkdir(parents=True, exist_ok=True)
    out = args.out.expanduser().resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    key = state / 'development-signing.pem'
    # Serialize signing/counter updates, including first-key creation. A failed build
    # consumes its number, so retrying can never downgrade an installed version.
    with (state / 'development-build.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        counter = state / 'development-build-number'
        number = max(10003, int(counter.read_text()) + 1 if counter.exists() else 10003)
        counter.write_text(str(number) + '\n')
        version = release.APP_VERSION + '-dev.' + str(number)
        package = 'com.gtomasel.totk.dev'
        target_sdk = 36
        release.app(work=work, ndk=ndk, logs=logs, out=out, key=key, make_key=True, release=False,
                    turnip=args.turnip, translator=args.translator, android_sdk=sdk, version_code=number,
                    version_name=version, jobs=args.jobs, application_id=package, label='TotK Test', target_sdk=target_sdk)
        with zipfile.ZipFile(out) as apk, apk.open('lib/arm64-v8a/libtotk_xlate.so') as translator:
            source = apk.read('assets/build.txt').decode('ascii').strip().removeprefix('commit ')
            translator_sha256 = hashlib.file_digest(translator, 'sha256').hexdigest()
        receipt = {'package': package, 'version': version, 'version_code': number,
                   'target_sdk': target_sdk, 'source': source, 'sha256': release.sha256(out),
                   'translator_sha256': translator_sha256,
                   'qualification': 'Signed development build; gameplay qualification is separate.'}
        out.with_suffix('.build.json').write_text(json.dumps(receipt, indent=2) + '\n')
        Path(str(out) + '.sha256').write_text(receipt['sha256'] + '  ' + out.name + '\n')
        if args.install:
            subprocess.run(['adb', '-s', args.install, 'install', '--no-streaming', '-r', '-t', str(out)], check=True)
        print(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    main()
