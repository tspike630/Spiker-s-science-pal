#!/bin/bash
#
# Builds the spikers-science-pal-research pacman package with makepkg in the
# upstream builder image (guest/factory/Containerfile).
#
#   guest/package/build-research.sh [--output DIR]
#
# Output defaults to dist/guest/packages. The archive name is
# spikers-science-pal-research-<version>-1-any.pkg.tar.zst, which does not
# replace the integration package beside it.

set -euo pipefail

fail() {
  echo "spikers-science-pal-research-package: $*" >&2
  exit 1
}

package_dir=$(cd "$(dirname "$0")" && pwd)
repo_dir=$(cd "$package_dir/../.." && pwd)
output="$repo_dir/dist/guest/packages"

while (($#)); do
  case $1 in
    --output) output=${2:?}; shift 2 ;;
    -h | --help) sed -n '2,10p' "$0"; exit 0 ;;
    *) fail "unknown option: $1" ;;
  esac
done

command -v docker >/dev/null || fail "docker is required"
command -v git >/dev/null || fail "git is required"
mkdir -p "$output"
output=$(cd "$output" && pwd)
builder_image=${GUEST_BUILDER_IMAGE:-spikers-science-pal-guest-builder}
[[ -n ${GUEST_BUILDER_IMAGE:-} ]] ||
  docker build --quiet --platform linux/arm64 -f "$repo_dir/guest/factory/Containerfile" -t "$builder_image" "$repo_dir" >/dev/null

tar_flags=(--no-xattrs)
tar --version 2>/dev/null | grep -q 'GNU tar' || tar_flags+=(--no-mac-metadata)
recipe=$(mktemp -d "${TMPDIR:-/tmp}/spikers-science-pal-research-package.XXXXXX")
trap 'rm -rf "$recipe"' EXIT
(
  cd "$package_dir/spikers-science-pal-research"
  git ls-files -z --cached --others --exclude-standard -- . |
    while IFS= read -r -d '' file; do if [[ -e $file ]]; then printf '%s\0' "$file"; fi; done |
    COPYFILE_DISABLE=1 tar -c "${tar_flags[@]}" --null -T - -f "$recipe/recipe.tar"
)
COPYFILE_DISABLE=1 tar -r "${tar_flags[@]}" -f "$recipe/recipe.tar" -C "$repo_dir" LICENSE

docker run --rm -i --platform linux/arm64 --entrypoint /bin/bash \
  -v "$output:/output" "$builder_image" -c '
    set -euo pipefail
    useradd -m builder
    install -d -o builder /build/spikers-science-pal-research
    tar -x -C /build/spikers-science-pal-research --no-same-owner
    chown -R builder /build
    cd /build/spikers-science-pal-research
    runuser -u builder -- env PKGEXT=.pkg.tar.zst makepkg --nodeps --force --noconfirm 2>&1 | grep -v "libfakeroot internal error" >&2
    rm -f /output/spikers-science-pal-research-*.pkg.tar.zst
    install -m 0644 spikers-science-pal-research-*.pkg.tar.zst /output/
    ls spikers-science-pal-research-*.pkg.tar.zst
  ' <"$recipe/recipe.tar"
