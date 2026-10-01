#!/usr/bin/env bash
set -euo pipefail
device=$(xcrun simctl list devices available -j | python3 -c 'import json,sys;d=json.load(sys.stdin);print(next(v["udid"] for k,vs in d["devices"].items() if "iOS" in k for v in vs if v["name"].startswith("iPhone")))')
xcrun simctl boot "$device"
xcrun simctl bootstatus "$device" -b
xcrun simctl install "$device" mobile/ios/build/simulator/Build/Products/Release-iphonesimulator/PaperAI.app
xcrun simctl launch "$device" io.github.keller52.paperai --smoke-test
container=$(xcrun simctl get_app_container "$device" io.github.keller52.paperai data)
for i in $(seq 1 40); do
  if [[ -f "$container/Documents/native-smoke.txt" ]]; then
    grep -q PAPER_AI_UI_READY "$container/Documents/native-smoke.txt"
    xcrun simctl io "$device" screenshot dist/ios/simulator.png
    exit 0
  fi
  sleep 1
done
xcrun simctl spawn "$device" log show --last 2m --predicate 'process == "PaperAI"' > dist/ios/startup.log
echo 'iOS workspace did not become ready';exit 1
