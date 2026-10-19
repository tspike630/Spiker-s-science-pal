#!/bin/sh
# One installer for the factory VM. It downloads the disk, checks it, and
# writes spikers-aarch64-edge.img. The research package is already installed.
#
#   sh scripts/install-factory-vm.sh [output-directory]
#
set -eu

base="https://github.com/tspike630/Spiker-s-science-pal/releases/download/factory-2026-10-19"
whole_sha="74dd98f2f3c0f7fc47d052bc437b58361119d0f87880e91589874103ca7ad25c"
out=${1:-$PWD/spikers-science-pal-vm}

check() {
  file=$1
  sum=$2
  if command -v sha256sum >/dev/null 2>&1; then
    printf '%s  %s\n' "$sum" "$file" | sha256sum -c -
  else
    printf '%s  %s\n' "$sum" "$file" | shasum -a 256 -c -
  fi
}

fetch() {
  name=$1
  sum=$2
  if [ -f "$name" ] && check "$name" "$sum"; then
    return
  fi
  echo "下载 $name"
  curl -fL --retry 5 --retry-delay 2 -o "$name.partial" "$base/$name"
  mv "$name.partial" "$name"
  check "$name" "$sum"
}

mkdir -p "$out"
cd "$out"

fetch spikers-aarch64-edge.img.zst.001 9f33f77c6326e1f3f1e83279e20efd4dcf4055d163126386aac6734c08db5287
fetch spikers-aarch64-edge.img.zst.002 5169e99f71a041f07e485b7c006ebec58113d7f40cd43c78190880165cc9ef9b
fetch spikers-aarch64-edge.img.zst.003 ef25c7e9983295130d6babe1ab6a66cc841982e5e169fb5f56989b6924eee074
fetch spikers-aarch64-edge.img.zst.004 cd794107bb1211dc31a31310ebb5f4b877a47668768c5a7f8ff525dc4de707b1

echo "拼成一个压缩包"
cat \
  spikers-aarch64-edge.img.zst.001 \
  spikers-aarch64-edge.img.zst.002 \
  spikers-aarch64-edge.img.zst.003 \
  spikers-aarch64-edge.img.zst.004 \
  > spikers-aarch64-edge.img.zst
check spikers-aarch64-edge.img.zst "$whole_sha"

if command -v zstd >/dev/null 2>&1; then
  echo "解压虚拟机磁盘"
  zstd -d -f spikers-aarch64-edge.img.zst
  echo "完成：$out/spikers-aarch64-edge.img"
  echo "这是 20 GiB 的虚拟机磁盘，里面已经装有 spikers-science-pal-research 0.4.0-1。"
else
  echo "压缩包已校验：$out/spikers-aarch64-edge.img.zst"
  echo "本机没有 zstd。安装后执行：zstd -d spikers-aarch64-edge.img.zst"
fi
