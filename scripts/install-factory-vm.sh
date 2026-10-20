#!/bin/sh
# Fallback installer for the factory VM. Mac users should open the app instead:
#
#   https://github.com/tspike630/Spiker-s-science-pal/releases/download/factory-2026-10-19-research-0.4.8/SpikersSciencePal.dmg
#
# This script downloads the same disk, checks it, and writes
# spikers-aarch64-edge.img. The research package 0.4.8-1 is already installed.
#
#   sh scripts/install-factory-vm.sh [output-directory]
#
set -eu

base="https://github.com/tspike630/Spiker-s-science-pal/releases/download/factory-2026-10-19-research-0.4.8"
whole_sha="9f9a4b474e05f1bf8ccef8de7222c647eae844eab485cc5f0acdab530222383e"
out=${1:-$PWD/spikers-science-pal-vm}

echo "Mac 上请下载并打开这个应用，不用输入命令："
echo "https://github.com/tspike630/Spiker-s-science-pal/releases/download/factory-2026-10-19-research-0.4.8/SpikersSciencePal.dmg"
echo "下面继续用脚本下载同一份磁盘。科研包版本是 0.4.8-1。"

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

fetch spikers-aarch64-edge.img.zst.001 eba87976cb123d4dbf0b46e9487d13bf3f22dd50d163c0370d8ac39ec96e55d5
fetch spikers-aarch64-edge.img.zst.002 efc4b326579f68109554362a1301881f5889858ca880629fd72f4a38eaa5b76f
fetch spikers-aarch64-edge.img.zst.003 28ebcf4dcde0315c7a579d10c17446b5a142f96625040b74f5056205e4914869
fetch spikers-aarch64-edge.img.zst.004 376135eac8a2ea2fd9eaa8311d6573e8f16941eb380589ff7cbf5f0daa4ffbb9

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
  echo "这是 20 GiB 的虚拟机磁盘，里面已经装有 spikers-science-pal-research 0.4.8-1。"
else
  echo "压缩包已校验：$out/spikers-aarch64-edge.img.zst"
  echo "本机没有 zstd。安装后执行：zstd -d spikers-aarch64-edge.img.zst"
fi
