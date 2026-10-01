#!/usr/bin/env bash
set -euo pipefail
adb install -r mobile/android/app/build/outputs/apk/release/app-release.apk
adb logcat -c
adb shell am start -n io.github.keller52.paperai/.MainActivity --ez smoke_test true
for i in $(seq 1 60); do
  if adb logcat -d -s PAPER_AI:I | grep -q PAPER_AI_UI_READY; then
    mkdir -p dist/android
    adb shell screencap -p /sdcard/paper-ai.png
    adb pull /sdcard/paper-ai.png dist/android/emulator.png
    exit 0
  fi
  sleep 1
done
adb logcat -d > dist/android/startup.log
echo 'Android workspace did not become ready';exit 1
