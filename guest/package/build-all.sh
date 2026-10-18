#!/bin/bash
#
# Builds both guest packages into one directory. make guest-package runs this
# so the factory disk and the downloaded VM always have a research package to
# install beside the integration package.
#
#   guest/package/build-all.sh [--output DIR]

set -euo pipefail

package_dir=$(cd "$(dirname "$0")" && pwd)
output=""
while (($#)); do
  case $1 in
    --output) output=${2:?}; shift 2 ;;
    -h | --help) sed -n '2,7p' "$0"; exit 0 ;;
    *) echo "spikers-science-pal-packages: unknown option: $1" >&2; exit 1 ;;
  esac
done

if [[ -z $output ]]; then
  echo "spikers-science-pal-packages: --output is required" >&2
  exit 1
fi

"$package_dir/build.sh" --output "$output"
"$package_dir/build-research.sh" --output "$output"
