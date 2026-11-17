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

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'games/totk/android'), str(ROOT / 'games/totk/android/apk')]
import build_release as release
import build_apk
import audit_apk


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
        libs = release.build_native(work, ndk, logs, release=False, jobs=args.jobs)
        libs = release.strip_debug(libs, work, ndk, logs)
        translator = release.release_translator(args.translator, work, ndk, logs)
        dex = release.build_classes(sdk, work / 'classes.dex', logs)
        assets = release.stage_assets(work / 'apk-stage/assets', release.licence_texts(work, ndk),
                                      commit=release.source_commit())
        driver = work / 'libtotk_turnip.so'
        driver.write_bytes(release.check_turnip(args.turnip).read_bytes())
        arguments = ['--dex', str(dex), '--ondevice-xlate', str(translator), '--assets', str(assets),
                     '--launcher-mipmaps', str(ROOT / 'games/totk/android/apk/launcher'),
                     '--out', str(out), '--key', str(key), '--make-key',
                     '--package', 'com.gtomasel.totk.dev', '--label', 'TotK Test',
                     '--version-name', version, '--version-code', str(number),
                     '--min-sdk', '33', '--target-sdk', '36']
        for lib in [*libs, driver]:
            arguments += ['--lib', str(lib)]
        build_apk.main(arguments)
        release.verify_signatures(out, logs, sdk)
        problems = audit_apk.audit(out)
        if problems:
            out.unlink()
            raise RuntimeError('APK audit failed: ' + '; '.join(problems))
        receipt = {'package': 'com.gtomasel.totk.dev', 'version': version, 'version_code': number,
                   'target_sdk': 36, 'source': release.source_commit(),
                   'sha256': hashlib.sha256(out.read_bytes()).hexdigest(),
                   'translator_sha256': hashlib.sha256(translator.read_bytes()).hexdigest(),
                   'qualification': 'Signed development build; gameplay qualification is separate.'}
        out.with_suffix('.build.json').write_text(json.dumps(receipt, indent=2) + '\n')
        Path(str(out) + '.sha256').write_text(receipt['sha256'] + '  ' + out.name + '\n')
        if args.install:
            subprocess.run(['adb', '-s', args.install, 'install', '--no-streaming', '-r', '-t', str(out)], check=True)
        print(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    main()
