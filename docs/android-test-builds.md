# Repeatable Android development installs

The test app is `com.gtomasel.totk.dev` (`TotK Test`). It is separate from the upstream
app, targets API36, and uses a stable developer signing key. On the connected S23+
(Android16), the first target36 install and successive `adb install -r -t` updates
succeeded without another installer dialog or fingerprint. A private data marker
survived updates. This is device evidence, not a guarantee for every OEM policy.
The older upstream target33 installer still required the owner's initial biometric
approval. No Play Protect, verifier, lock-screen or biometric setting was disabled.

Build from the current working tree:

```sh
python3 tools/build_android_test_apk.py \
  --ndk /path/to/android-ndk \
  --android-sdk /path/to/android-sdk \
  --turnip /path/to/pinned/driver.so \
  --out .scratch/android-test/TotK-Test.apk \
  --install DEVICE_SERIAL
```

The translator is built with .NET10 by default; `--translator` accepts a previously
source-built Android translator. See `build_release.py` for pinned dependencies and
toolchain requirements. Python needs the repository's `games/totk/requirements.txt`.
The script checks the pinned driver, builds native libraries and Java, includes
licenses, signs the APK, verifies its signature, and runs the APK content audit
before installing. The APK contains no game data or console keys.

Keep `~/.local/share/totk-android-fork/` between builds. Its private signing key and
increasing version counter are outside build caches; a file lock serializes builds.
Do not commit, publish or replace the key. Losing it prevents updating that installed
identity with the same signature. `--state-dir` can select a persistent alternative.
The key is generated only if absent, with restrictive permissions. Build receipts
and SHA256 files sit beside the APK; they never contain the key.

`--install` updates only the named, already-authorized ADB device and preserves app
data. It does not uninstall, clear data, grant USB authorization or dismiss a device
owner authentication prompt. The owner may still need to authorize a first install
on a different phone. The test build is debuggable and intended for local diagnosis;
a signed APK is not a claim of store certification or completed gameplay QA.

Shared game data can be selected in both apps, but run only one game/setup writer at
a time. Each identity has its own private saves and settings. The normal save-import
flow backs up the destination save set before replacement.

## Public fork beta

The signed release build uses application ID `com.gtomasel.totk` and launcher label
**TotK Fork**. It installs alongside both upstream and the development app. To move
saves between identities, use the export and import screens. Download beta updates
from the [fork's GitHub releases](https://github.com/GTomasel/totk-android-fork/releases).

Build from the tagged source with the fork's persistent release signing key. The first
beta used version code 10022. The 1.1.1 beta uses 10101 so Android can update the existing
installation. The pre-release suffix does not change the derived version code.

```sh
python3 games/totk/android/build_release.py \
  --ndk /path/to/android-ndk \
  --android-sdk /path/to/android-sdk \
  --turnip /path/to/pinned/driver.so \
  --key /private/path/to/fork-release-signing.pem \
  --package com.gtomasel.totk --label 'TotK Fork' --target-sdk 36 \
  --version-name 1.1.1-beta.1 --version-code 10101 \
  --out .scratch/android-release/TotK-Fork-1.1.1-beta.1.apk
```

The release build targets API 36 and supports Android 13 and later on ARM64, subject to
device and Vulkan compatibility. It is non-debuggable. Keep the release signing key
separate from the development key. GitHub receives the audited APK and its SHA-256 checksum.
