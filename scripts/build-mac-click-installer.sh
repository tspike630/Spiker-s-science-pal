#!/bin/bash
# Build the double-click macOS installer zip. The zip holds a tiny app.
# The app downloads the factory disk when it is opened.
set -euo pipefail

root=$(cd "$(dirname "$0")/.." && pwd)
source_script="$root/scripts/mac-click-install-research-vm.sh"
[[ -f $source_script ]] || {
  echo "build-mac-click-installer: missing $source_script" >&2
  exit 1
}
stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT
app_name="安装科研虚拟机 0.4.8.app"
app="$stage/$app_name"
mkdir -p "$app/Contents/MacOS" "$app/Contents/Resources"
cp "$source_script" "$app/Contents/MacOS/install"
chmod 755 "$app/Contents/MacOS/install"
cat >"$app/Contents/Info.plist" <<'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleDevelopmentRegion</key>
  <string>zh-Hans</string>
  <key>CFBundleDisplayName</key>
  <string>安装科研虚拟机 0.4.8</string>
  <key>CFBundleExecutable</key>
  <string>install</string>
  <key>CFBundleIdentifier</key>
  <string>dev.spikerssciencepal.research-vm-installer</string>
  <key>CFBundleInfoDictionaryVersion</key>
  <string>6.0</string>
  <key>CFBundleName</key>
  <string>安装科研虚拟机 0.4.8</string>
  <key>CFBundlePackageType</key>
  <string>APPL</string>
  <key>CFBundleShortVersionString</key>
  <string>0.4.8</string>
  <key>CFBundleVersion</key>
  <string>0.4.8</string>
  <key>CFBundleSupportedPlatforms</key>
  <array>
    <string>MacOSX</string>
  </array>
  <key>LSArchitecturePriority</key>
  <array>
    <string>arm64</string>
  </array>
  <key>LSMinimumSystemVersion</key>
  <string>15.0</string>
  <key>NSHighResolutionCapable</key>
  <true/>
</dict>
</plist>
EOF
cat >"$stage/请先看我.txt" <<'EOF'
打开「安装科研虚拟机 0.4.8」。不用输入命令。

如果 macOS 提示无法打开：按住 Control，点这个 App，再选「打开」。

它会自己下载科研包 0.4.8 的虚拟机磁盘，核对校验和，并装进已经安装的 Spiker's Science Pal。
已经有的虚拟机磁盘不会被盖掉。新的虚拟机，或者在 App 里重置之后，才会用 0.4.8。
EOF
output=${1:-"$root/dist/SpikersSciencePal-Research-0.4.8-Mac.zip"}
mkdir -p "$(dirname "$output")"
rm -f "$output"
(
  cd "$stage"
  zip -r -X "$output" "$app_name" "请先看我.txt"
)
echo "$output"
