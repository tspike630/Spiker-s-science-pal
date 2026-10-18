#!/bin/bash
#
# Builds the guest: the spikers-science-pal integration package, the
# spikers-science-pal-research workbench package, then the factory disk with
# both installed. Both run in the privileged ARM64 builder.
# --factory-only builds the disk with the packages already in DIR/packages
# (make guest builds the packages as their own cached step).
#
#   guest/build.sh [--factory-only] [--output DIR]
#
# Output defaults to dist/guest: the factory files plus packages/.

set -euo pipefail

guest_dir=$(cd "$(dirname "$0")" && pwd)
output="$guest_dir/../dist/guest"
factory_only=0
while (($#)); do
  case $1 in
    --factory-only) factory_only=1; shift ;;
    --output) output=${2:?}; shift 2 ;;
    *) echo "Usage: guest/build.sh [--factory-only] [--output DIR]" >&2; exit 64 ;;
  esac
done

mkdir -p "$output"
output=$(cd "$output" && pwd)
if ((!factory_only)); then
  rm -rf "$output/packages"
  "$guest_dir/package/build.sh" --output "$output/packages"
  "$guest_dir/package/build-research.sh" --output "$output/packages"
fi
shopt -s nullglob
packages=("$output"/packages/spikers-science-pal-*.pkg.tar.zst)
((${#packages[@]} == 1)) || { echo "guest/build.sh: expected one spikers-science-pal package" >&2; exit 1; }
research=("$output"/packages/spikers-science-pal-research-*.pkg.tar.zst)
if ((${#research[@]} == 0)) && ((factory_only)); then
  echo "guest/build.sh: spikers-science-pal-research package missing in $output/packages (run guest/package/build-research.sh first)" >&2
  exit 1
fi
((${#research[@]} <= 1)) || echo "guest/build.sh: warning: multiple spikers-science-pal-research packages; using ${research[0]##*/}" >&2
build_args=(--package "${packages[0]}")
if ((${#research[@]})); then
  build_args+=(--package "${research[0]}")
fi
"$guest_dir/factory/build-container.sh" --output "$output" "${build_args[@]}"
