#!/bin/bash
# Double-click installer for the research VM disk (spikers-science-pal-research 0.4.8-1).
#
# macOS 15, Apple Silicon. The user never types a command: this file is
# Contents/MacOS/install inside 安装科研虚拟机 0.4.8.app. It downloads the
# published disk, checks the checksum, and installs it into an existing
# Spiker's Science Pal app. It does not build a QEMU app and it does not
# replace a VM disk that is already in use.
set -euo pipefail

version=0.4.8
disk_sha=33caf5836b86a86aba300b2ea1242515f8b7ec406dfd3c55cc18cafd75a0992e
disk_bytes=21474836480
compressed_sha=9f9a4b474e05f1bf8ccef8de7222c647eae844eab485cc5f0acdab530222383e
compressed_bytes=4080778367
base_url="https://github.com/tspike630/Spiker-s-science-pal/releases/download/factory-2026-10-19-research-0.4.8"
# One public file, when a host without GitHub's 2 GiB asset limit has it.
# Empty means the installer downloads the parts below and joins them.
single_url=""

part_names=(
  spikers-aarch64-edge.img.zst.001
  spikers-aarch64-edge.img.zst.002
  spikers-aarch64-edge.img.zst.003
  spikers-aarch64-edge.img.zst.004
)
part_bytes=(1073741824 1073741824 1073741824 859552895)
part_shas=(
  eba87976cb123d4dbf0b46e9487d13bf3f22dd50d163c0370d8ac39ec96e55d5
  efc4b326579f68109554362a1301881f5889858ca880629fd72f4a38eaa5b76f
  28ebcf4dcde0315c7a579d10c17446b5a142f96625040b74f5056205e4914869
  376135eac8a2ea2fd9eaa8311d6573e8f16941eb380589ff7cbf5f0daa4ffbb9
)

PLUTIL=${SPIKERS_PLUTIL:-/usr/bin/plutil}
OSASCRIPT=${SPIKERS_OSASCRIPT:-/usr/bin/osascript}
CODESIGN=${SPIKERS_CODESIGN:-/usr/bin/codesign}

hash_file() {
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$1" | awk '{print $1}'
  else
    /usr/bin/shasum -a 256 "$1" | awk '{print $1}'
  fi
}

ui_notify() {
  if [[ ${SPIKERS_INSTALLER_TEST:-0} == 1 ]]; then
    printf 'NOTIFY %s\n' "$1"
    return 0
  fi
  "$OSASCRIPT" - "$1" <<'APPLESCRIPT' >/dev/null 2>&1 || true
on run argv
  display notification (item 1 of argv) with title "Spiker's Science Pal"
end run
APPLESCRIPT
}

ui_alert() {
  if [[ ${SPIKERS_INSTALLER_TEST:-0} == 1 ]]; then
    printf 'ALERT %s\n' "$1"
    return 0
  fi
  "$OSASCRIPT" - "$1" <<'APPLESCRIPT' >/dev/null || true
on run argv
  display dialog (item 1 of argv) buttons {"好"} default button "好" with title "Spiker's Science Pal"
end run
APPLESCRIPT
}

ui_confirm() {
  local answer
  if [[ ${SPIKERS_INSTALLER_TEST:-0} == 1 ]]; then
    printf 'CONFIRM %s\n' "$1"
    return 0
  fi
  if ! answer=$("$OSASCRIPT" - "$1" <<'APPLESCRIPT'
on run argv
  set answer to button returned of (display dialog (item 1 of argv) buttons {"取消", "开始安装"} default button "开始安装" with title "Spiker's Science Pal")
  return answer
end run
APPLESCRIPT
  ); then
    return 1
  fi
  [[ $answer == "开始安装" ]]
}

print_manifest() {
  local index
  printf '{\n'
  printf '  "version": "%s",\n' "$version"
  printf '  "disk_sha256": "%s",\n' "$disk_sha"
  printf '  "disk_bytes": %s,\n' "$disk_bytes"
  printf '  "compressed_sha256": "%s",\n' "$compressed_sha"
  printf '  "compressed_bytes": %s,\n' "$compressed_bytes"
  printf '  "base_url": "%s",\n' "$base_url"
  printf '  "single_url": "%s",\n' "$single_url"
  printf '  "parts": [\n'
  for index in 0 1 2 3; do
    local comma=","
    [[ $index -eq 3 ]] && comma=""
    printf '    {"name": "%s", "bytes": %s, "sha256": "%s"}%s\n' \
      "${part_names[$index]}" "${part_bytes[$index]}" "${part_shas[$index]}" "$comma"
  done
  printf '  ]\n}\n'
}

apply_test_overrides() {
  [[ ${SPIKERS_INSTALLER_TEST:-0} == 1 ]] || return 0
  if [[ -n ${SPIKERS_INSTALLER_DISK_SHA:-} ]]; then
    disk_sha=$SPIKERS_INSTALLER_DISK_SHA
  fi
  if [[ -n ${SPIKERS_INSTALLER_COMPRESSED_SHA:-} ]]; then
    compressed_sha=$SPIKERS_INSTALLER_COMPRESSED_SHA
  fi
  if [[ -n ${SPIKERS_INSTALLER_COMPRESSED_BYTES:-} ]]; then
    compressed_bytes=$SPIKERS_INSTALLER_COMPRESSED_BYTES
  fi
  if [[ -n ${SPIKERS_INSTALLER_BASE_URL:-} ]]; then
    base_url=$SPIKERS_INSTALLER_BASE_URL
  fi
}

require_mac() {
  [[ ${SPIKERS_INSTALLER_TEST:-0} == 1 ]] && return 0
  if [[ $(uname -s) != Darwin || $(uname -m) != arm64 ]]; then
    ui_alert "这个安装器只能在 Apple 芯片的 Mac（macOS 15 或更新）上打开。"
    exit 1
  fi
  local major
  major=$(sw_vers -productVersion | cut -d. -f1)
  if [[ ! $major =~ ^[0-9]+$ ]] || ((major < 15)); then
    ui_alert "需要 macOS 15 或更新的系统。当前系统不能安装这份科研虚拟机。"
    exit 1
  fi
}

require_space() {
  [[ ${SPIKERS_INSTALLER_TEST:-0} == 1 ]] && return 0
  local avail need=6291456
  avail=$(df -k "$HOME" | awk 'NR==2 { print $4 }')
  if [[ ! $avail =~ ^[0-9]+$ ]] || ((avail < need)); then
    ui_alert "磁盘剩余空间不够。下载并装入科研包 0.4.8 大约需要 6 GB 空闲空间。"
    exit 1
  fi
}

download_image() {
  local dest=$1
  mkdir -p "$(dirname "$dest")"
  if [[ -f $dest ]] && [[ $(hash_file "$dest") == "$compressed_sha" ]]; then
    return 0
  fi
  if [[ ${SPIKERS_INSTALLER_TEST:-0} == 1 && -n ${SPIKERS_INSTALLER_FIXTURE_DIR:-} ]]; then
    cp "$SPIKERS_INSTALLER_FIXTURE_DIR/image.zst" "$dest"
  elif [[ -n $single_url ]]; then
    ui_notify "正在下载科研虚拟机 ${version}。"
    rm -f "$dest.partial"
    if curl -fL --retry 5 --retry-delay 2 -o "$dest.partial" "$single_url"; then
      mv "$dest.partial" "$dest"
    else
      rm -f "$dest.partial"
      download_parts "$dest" || return 1
    fi
    else
    download_parts "$dest" || return 1
  fi
  if [[ $(hash_file "$dest") != "$compressed_sha" ]]; then
    rm -f "$dest"
    return 1
  fi
}

download_parts() {
  local dest=$1
  local dir index name part actual
  dir=$(dirname "$dest")
  mkdir -p "$dir/parts"
  for index in 0 1 2 3; do
    name=${part_names[$index]}
    ui_notify "正在下载科研虚拟机 ${version}，第 $((index + 1)) 段，共 4 段。"
    part="$dir/parts/$name"
    if [[ ! -f $part ]] || [[ $(hash_file "$part") != "${part_shas[$index]}" ]]; then
      rm -f "$part.partial"
      curl -fL --retry 5 --retry-delay 2 -o "$part.partial" "$base_url/$name"
      mv "$part.partial" "$part"
    fi
    actual=$(hash_file "$part")
    if [[ $actual != "${part_shas[$index]}" ]]; then
      rm -f "$part"
      return 1
    fi
    if [[ $(wc -c <"$part" | tr -d ' ') != "${part_bytes[$index]}" ]]; then
      rm -f "$part"
      return 1
    fi
  done
  cat "$dir/parts/${part_names[0]}" "$dir/parts/${part_names[1]}" \
    "$dir/parts/${part_names[2]}" "$dir/parts/${part_names[3]}" >"$dest.partial"
  mv "$dest.partial" "$dest"
}

write_download_json() {
  local dest=$1
  cat >"$dest" <<EOF
{
  "format": 1,
  "kind": "spikers-science-pal-factory-download",
  "identity": "$disk_sha",
  "image": {"bytes": $compressed_bytes, "sha256": "$compressed_sha"},
  "parts": [
    {"url": "$base_url/${part_names[0]}", "bytes": ${part_bytes[0]}, "sha256": "${part_shas[0]}"},
    {"url": "$base_url/${part_names[1]}", "bytes": ${part_bytes[1]}, "sha256": "${part_shas[1]}"},
    {"url": "$base_url/${part_names[2]}", "bytes": ${part_bytes[2]}, "sha256": "${part_shas[2]}"},
    {"url": "$base_url/${part_names[3]}", "bytes": ${part_bytes[3]}, "sha256": "${part_shas[3]}"}
  ]
}
EOF
}

update_sums() {
  local guest=$1
  local image_name=$2
  local sums="$guest/SHA256SUMS"
  [[ -f $sums && ! -L $sums ]] || return 0
  local image_hash factory_hash tmp line hash file
  image_hash=$(hash_file "$guest/$image_name")
  factory_hash=$(hash_file "$guest/factory.json")
  tmp=$(mktemp)
  while IFS= read -r line || [[ -n $line ]]; do
    hash=${line%% *}
    file=${line#* }
    file=${file# }
    case $file in
      "$image_name") printf '%s  %s\n' "$image_hash" "$file" ;;
      factory.json) printf '%s  %s\n' "$factory_hash" "$file" ;;
      *) printf '%s\n' "$line" ;;
    esac
  done <"$sums" >"$tmp"
  mv "$tmp" "$sums"
  chmod 644 "$sums" || true
}

resign_app() {
  local app=$1
  if [[ ${SPIKERS_INSTALLER_TEST:-0} != 1 ]]; then
    /usr/bin/xattr -cr "$app" 2>/dev/null || true
    if "$CODESIGN" --force --sign - --preserve-metadata=identifier,entitlements,flags,runtime "$app"; then
      return 0
    fi
    "$CODESIGN" --force --sign - --preserve-metadata=identifier,entitlements "$app"
    return
  fi
  "$CODESIGN" --force --sign - --preserve-metadata=identifier,entitlements,flags,runtime "$app"
}

restore_app() {
  local app=$1 backup=$2 image=$3
  local guest="$app/Contents/Resources/guest"
  if [[ -f $backup/image ]]; then
    mv -f "$backup/image" "$image"
  else
    rm -f "$image"
  fi
  if [[ -f $backup/factory.json ]]; then
    mv -f "$backup/factory.json" "$guest/factory.json"
  fi
  if [[ -f $backup/download.json ]]; then
    mv -f "$backup/download.json" "$guest/download.json"
  elif [[ -f $guest/download.json ]]; then
    rm -f "$guest/download.json"
  fi
  if [[ -f $backup/SHA256SUMS ]]; then
    mv -f "$backup/SHA256SUMS" "$guest/SHA256SUMS"
  fi
}

copy_image() {
  local source=$1 dest=$2
  rm -f "$dest"
  if ! cp -c "$source" "$dest" 2>/dev/null; then
    cp "$source" "$dest"
  fi
}

install_one() {
  local app=$1
  local cache_file=$2
  local guest="$app/Contents/Resources/guest"
  local factory="$guest/factory.json"
  local name image backup
  [[ -d $app && ! -L $app ]] || return 1
  [[ -f $factory && ! -L $factory ]] || return 2
  name=$("$PLUTIL" -extract compressed.path raw -o - "$factory") || return 3
  [[ $name =~ ^[A-Za-z0-9._-]+\.img\.zst$ ]] || return 3
  image="$guest/$name"
  backup="$(dirname "$cache_file")/backup-$(basename "$app")"
  rm -rf "$backup"
  mkdir -p "$backup"
  cp -p "$factory" "$backup/factory.json"
  if [[ -f $guest/download.json && ! -L $guest/download.json ]]; then
    cp -p "$guest/download.json" "$backup/download.json"
  fi
  if [[ -f $guest/SHA256SUMS && ! -L $guest/SHA256SUMS ]]; then
    cp -p "$guest/SHA256SUMS" "$backup/SHA256SUMS"
  fi
  if [[ -f $image && ! -L $image ]]; then
    mv "$image" "$backup/image"
  fi
  if ! copy_image "$cache_file" "$image"; then
    restore_app "$app" "$backup" "$image"
    return 1
  fi
  chmod 644 "$image" || true
  if ! "$PLUTIL" -replace compressed.sha256 -string "$compressed_sha" "$factory" \
    || ! "$PLUTIL" -replace disk.sha256 -string "$disk_sha" "$factory" \
    || ! "$PLUTIL" -replace disk.bytes -integer "$disk_bytes" "$factory"; then
    restore_app "$app" "$backup" "$image"
    return 1
  fi
  write_download_json "$guest/download.json"
  chmod 644 "$guest/download.json" || true
  update_sums "$guest" "$name" || true
  if ! resign_app "$app"; then
    restore_app "$app" "$backup" "$image"
    return 1
  fi
  rm -rf "$backup"
}

elevate_install() {
  local app=$1
  local cache_file=$2
  [[ ${SPIKERS_INSTALLER_TEST:-0} == 1 ]] && return 1
  "$OSASCRIPT" - "$0" "$app" "$cache_file" <<'APPLESCRIPT'
on run argv
  set scriptPath to item 1 of argv
  set appPath to item 2 of argv
  set cachePath to item 3 of argv
  do shell script quoted form of scriptPath & " --install-one " & quoted form of appPath & " " & quoted form of cachePath with administrator privileges
end run
APPLESCRIPT
}

find_apps() {
  local roots=("/Applications" "$HOME/Applications" "$HOME/Desktop")
  local names=("Spiker's Science Pal.app" "Spiker's Science Pal Dev.app")
  local root name candidate
  for root in "${roots[@]}"; do
    for name in "${names[@]}"; do
      candidate="$root/$name"
      if [[ -d $candidate && ! -L $candidate && -f $candidate/Contents/Resources/guest/factory.json ]]; then
        printf '%s\n' "$candidate"
      fi
    done
  done
}

existing_disks() {
  local root="$HOME/Library/Application Support/Spiker's Science Pal"
  [[ -d $root ]] || return 0
  find "$root" -maxdepth 5 -type f -path '*/shell/disk.img' 2>/dev/null || true
}

short_path() {
  local path=$1
  case $path in
    "$HOME"/*) printf '~/%s\n' "${path#"$HOME"/}" ;;
    *) printf '%s\n' "$path" ;;
  esac
}

place_factory_cache() {
  local cache_file=$1
  local directory="$HOME/Library/Application Support/Spiker's Science Pal/VM/v1/shell-factory"
  local target
  [[ -d $directory && ! -L $directory ]] || return 0
  target="$directory/$disk_sha.img.zst"
  if [[ -f $target ]] && [[ $(hash_file "$target") == "$compressed_sha" ]]; then
    return 0
  fi
  copy_image "$cache_file" "$target"
  chmod 600 "$target" || true
}

save_without_app() {
  local cache_file=$1
  local dest="$HOME/Desktop/SpikersSciencePal-vm"
  mkdir -p "$dest"
  copy_image "$cache_file" "$dest/spikers-aarch64-edge.img.zst"
  chmod 644 "$dest/spikers-aarch64-edge.img.zst" || true
  printf '%s  %s\n' "$compressed_sha" "spikers-aarch64-edge.img.zst" >"$dest/SHA256SUMS"
  cat >"$dest/说明.txt" <<EOF
这是科研虚拟机磁盘的压缩包，版本 ${version}（spikers-science-pal-research ${version}-1）。
启动虚拟机需要你已经用仓库编译好的 Spiker's Science Pal Mac App。
这个文件夹里没有能开机的 App。
EOF
}

main() {
  local cache_file apps_text app failed existing message line
  apply_test_overrides
  if [[ ${1:-} == --print-manifest ]]; then
    print_manifest
    exit 0
  fi
  if [[ ${1:-} == --install-one ]]; then
    [[ $# -eq 3 ]] || exit 2
    install_one "$2" "$3"
    exit
  fi
  require_mac
  if ! ui_confirm "将下载科研虚拟机磁盘 ${version}（大约 4 GB），并装进这台 Mac 上已经安装的 Spiker's Science Pal。不用输入命令。已经有的虚拟机磁盘不会被覆盖。"; then
    exit 0
  fi
  require_space
  cache_file="$HOME/Library/Caches/Spiker's Science Pal/research-${version}/spikers-aarch64-edge.img.zst"
  ui_notify "正在下载科研虚拟机 ${version}。"
  if ! download_image "$cache_file"; then
    ui_alert "下载没有通过校验，科研包 ${version} 没有安装。请检查网络后再打开一次这个安装器。"
    exit 1
  fi
  apps_text=$(find_apps || true)
  if [[ -z $apps_text ]]; then
    save_without_app "$cache_file"
    ui_alert "磁盘已经放在桌面的 SpikersSciencePal-vm 文件夹里，版本是 ${version}。这台 Mac 上没有找到 Spiker's Science Pal。启动虚拟机需要你已经用仓库编译好的 Mac App。这里不能另外做一个能开机的 App。"
    exit 0
  fi
  failed=""
  while IFS= read -r app; do
    [[ -n $app ]] || continue
    if ! install_one "$app" "$cache_file"; then
      if ! elevate_install "$app" "$cache_file"; then
        failed="${failed}$(short_path "$app")
"
      fi
    fi
  done <<<"$apps_text"
  place_factory_cache "$cache_file" || true
  message="安装完成。科研包版本是 ${version}。"
  if [[ -n $failed ]]; then
    message="${message} 这些 App 没有装上：${failed}"
  fi
  existing=$(existing_disks || true)
  if [[ -n $existing ]]; then
    message="${message} 已经有的虚拟机仍用旧磁盘，这次没有改它。"
    while IFS= read -r line; do
      [[ -n $line ]] || continue
      message="${message} $(short_path "$line")"
    done <<<"$existing"
    message="${message} 在 App 里重置，或换一个新的数据文件夹之后，新的虚拟机会使用 ${version}。"
  else
    message="${message} 下次新建虚拟机会使用这份磁盘。"
  fi
  ui_alert "$message"
  if [[ -n $failed ]]; then
    exit 1
  fi
}

main "$@"
