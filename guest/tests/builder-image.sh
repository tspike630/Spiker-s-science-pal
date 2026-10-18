#!/bin/bash
#
# Loads the guest builder image (guest/factory/Containerfile) from ARCHIVE, a
# zstd-compressed `docker save` that CI keeps in its cache, or builds it and
# writes ARCHIVE for the cache to keep.
#
#   guest/tests/builder-image.sh ARCHIVE
#
# The image is spikers-science-pal-guest-builder, for GUEST_BUILDER_IMAGE.

set -euo pipefail
archive=${1:?usage: builder-image.sh ARCHIVE}
repo_dir=$(cd "$(dirname "$0")/../.." && pwd)
if [[ -f $archive ]]; then
  zstd -dc "$archive" | docker load --quiet
else
  docker build --quiet --platform linux/arm64 -f "$repo_dir/guest/factory/Containerfile" -t spikers-science-pal-guest-builder "$repo_dir"
  docker save spikers-science-pal-guest-builder | zstd -T0 -3 -q -o "$archive"
fi
