#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../mobile/ios"
if [[ ! -d Python.xcframework ]]; then
  curl --fail --location --retry 3 -o Python-support.tar.gz https://github.com/beeware/Python-Apple-support/releases/download/3.13-b15/Python-3.13-iOS-support.b15.tar.gz
  echo '80175765a31babe43b0910395cf86ba4e8412adf1902b069d55b74d523ecc5d1  Python-support.tar.gz' | shasum -a 256 -c -
  tar xzf Python-support.tar.gz
fi
xcodegen generate
arch="$(uname -m)"
xcodebuild -project PaperAI.xcodeproj -scheme PaperAI -configuration Release -sdk iphonesimulator -destination 'generic/platform=iOS Simulator' -derivedDataPath build/simulator ARCHS="$arch" ONLY_ACTIVE_ARCH=YES CODE_SIGNING_ALLOWED=NO build
xcodebuild -project PaperAI.xcodeproj -scheme PaperAI -configuration Release -sdk iphoneos -destination 'generic/platform=iOS' -archivePath build/PaperAI.xcarchive ARCHS=arm64 CODE_SIGNING_ALLOWED=NO archive
expected_version=$(python3 -c 'import sys;sys.path.insert(0,"../../app");from core import VERSION;print(VERSION)')
python3 -c 'import plistlib,sys;info=plistlib.load(open("build/PaperAI.xcarchive/Products/Applications/PaperAI.app/Info.plist","rb"));assert info["CFBundleShortVersionString"]==sys.argv[1],info;print("Verified iOS bundle version:",info["CFBundleShortVersionString"])' "$expected_version"
mkdir -p ../../dist/ios/Payload
cp -R build/PaperAI.xcarchive/Products/Applications/PaperAI.app ../../dist/ios/Payload/
cd ../../dist/ios
zip -qry PAPER-AI-unsigned.ipa Payload
cp -R ../../mobile/ios/build/simulator/Build/Products/Release-iphonesimulator/PaperAI.app .
zip -qry PAPER-AI-simulator.zip PaperAI.app
