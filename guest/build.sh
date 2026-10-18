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
# spikers-science-pal-research-* also matches spikers-science-pal-*, so keep
# the integration package (version starts with a digit) separate.
packages=()
for candidate in "$output"/packages/spikers-science-pal-*.pkg.tar.zst; do
  name=${candidate##*/}
  [[ $name == spikers-science-pal-research-* ]] && continue
  packages+=("$candidate")
done
((${#packages[@]} == 1)) || { echo "guest/build.sh: expected one spikers-science-pal package" >&2; exit 1; }
research=("$output"/packages/spikers-science-pal-research-*.pkg.tar.zst)
((${#research[@]} == 1)) || {
  echo "guest/build.sh: expected one spikers-science-pal-research package in $output/packages" >&2
  exit 1
}
# Both packages are installed into the factory disk. The downloaded VM
# therefore already contains the research workbench; it is not a later pacman step.
"$guest_dir/factory/build-container.sh" --output "$output" \
  --package "${packages[0]}" --package "${research[0]}"
