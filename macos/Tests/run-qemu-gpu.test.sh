#!/bin/bash
#
# Contract test for run-qemu-gpu.sh: a fake app bundle with shimmed QEMU,
# helper and zstd, driven mostly through the dry-run path. Checks the UEFI
# boot, the host-settings credential, the integration package offer, storage
# layout, resets, disposable VMs, input validation and the progress lines the
# app reads. Runs no VM.

set -euo pipefail
# An unexpected failure (such as a launch whose error output is captured)
# would otherwise end the test without a word.
trap 'printf "run-qemu-gpu.test: unexpected failure at line %s\n" "$LINENO" >&2' ERR

test_dir=$(cd "$(dirname "$0")" && pwd -P)
macos_dir=$(cd "$test_dir/.." && pwd -P)

fail() {
  printf 'run-qemu-gpu.test: %s\n' "$*" >&2
  exit 1
}

assert_contains() {
  [[ $1 == *"$2"* ]] || fail "expected output to contain [$2], got [$1]"
}

assert_not_contains() {
  [[ $1 != *"$2"* ]] || fail "expected output not to contain [$2]"
}

test_root=$(mktemp -d '/private/tmp/spikers-qemu-test.XXXXXX')
stale_runs=()
trap '/bin/rm -rf "$test_root" ${stale_runs[@]+"${stale_runs[@]}"}' EXIT HUP INT TERM

app="$test_root/Spiker's Science Pal.app"
resources="$app/Contents/Resources"
shims="$test_root/bin"
mkdir -p "$app/Contents/MacOS" "$resources/guest" "$resources/guest-packages" "$resources/firmware" \
  "$resources/runtime/bin" "$resources/scripts" "$shims"
cp "$macos_dir/run-qemu-gpu.sh" "$macos_dir/qemu-port-forwarding.sh" "$macos_dir/qemu-networking.sh" \
  "$macos_dir/network-identity.py" "$resources/scripts/"
chmod 755 "$resources/scripts/run-qemu-gpu.sh"

cat >"$app/Contents/MacOS/spikers-vm-helper" <<'SH'
#!/bin/bash
case $1 in
  --host-keyboard-geometry) echo jis ;;
  --host-timezone) echo America/Sao_Paulo ;;
  --sparsify) exit 0 ;;
  *) exit 1 ;;
esac
SH
# The fake QEMU carries the project's patch markers, answers -device help and
# records every other invocation. It never starts: a real launch fails with
# "QEMU exited before it was ready" after the storage work is done.
write_qemu() { # extra-marker
  cat >"$resources/runtime/bin/Spiker's Science Pal" <<SH
#!/bin/bash
# SpikersSciencePal.icns SPIKERS_SDL_AUDIO_CONTROL_DIRECTORY guest_owner_uid $1
if [[ "\$*" == "-device help" ]]; then
  for device in hda-micro intel-hda virtconsole virtserialport virtio-balloon-pci virtio-9p-pci \\
    virtio-blk-pci virtio-gpu-gl-pci virtio-keyboard-pci virtio-net-pci virtio-rng-pci \\
    virtio-serial-pci virtio-tablet-pci virtio-pinch-pci qemu-xhci usb-host; do
    printf 'name "%s", bus PCI\n' "\$device"
  done
  exit 0
fi
# The nested-virtualization probe fails, as on M1/M2 Macs.
[[ "\$*" == *"-qmp stdio"* ]] && exit 1
printf '%s\n' "\$*" >>"$test_root/qemu-invocations"
exit 1
SH
  chmod 755 "$resources/runtime/bin/Spiker's Science Pal"
}
write_qemu 'exact bus 0 matching'
# The fake factory is stored uncompressed; "decompressing" copies it.
cat >"$resources/runtime/bin/zstd" <<'SH'
#!/bin/bash
while (($#)); do
  case $1 in
    -o) out=$2; shift 2 ;;
    -*) shift ;;
    *) in=$1; shift ;;
  esac
done
if [[ -n ${FAKE_ZSTD_FAIL:-} ]]; then
  printf 'partial' >"$out"
  exit 1
fi
cp "$in" "$out"
SH
printf '#!/bin/sh\nexit 0\n' >"$shims/codesign"
# The launcher sizes the VM from the host. Report a 10-core, 16 GiB Mac, so
# the result does not depend on the machine running the test (GitHub's
# Apple Silicon runners have three CPUs, below the guest's minimum of four).
cat >"$shims/sysctl" <<'SH'
#!/bin/bash
case $* in
  "-n hw.logicalcpu") echo 10 ;;
  "-n hw.memsize") echo 17179869184 ;;
  *) exec /usr/sbin/sysctl "$@" ;;
esac
SH
chmod 755 "$app/Contents/MacOS/spikers-vm-helper" "$resources/runtime/bin/zstd" "$shims/codesign" "$shims/sysctl"

dd if=/dev/zero of="$resources/guest/spikers-aarch64-edge.img.zst" bs=1048576 count=4 2>/dev/null
sha=$(shasum -a 256 "$resources/guest/spikers-aarch64-edge.img.zst" | cut -d' ' -f1)
cat >"$resources/guest/factory.json" <<JSON
{"format":1,"kind":"upstream-shell-factory","boot":"uefi-limine",
 "disk":{"path":"spikers-aarch64-edge.img","bytes":4194304,"sha256":"$sha"},
 "compressed":{"path":"spikers-aarch64-edge.img.zst","sha256":"$sha"}}
JSON
printf 'firmware' >"$resources/firmware/edk2-aarch64-code.fd"
printf 'package' >"$resources/guest-packages/spikers-science-pal-0.2.0-1-aarch64.pkg.tar.zst"

state="$test_root/state"
launch_env=()
launch() { # args...
  env PATH="$shims:$PATH" SPIKERS_QEMU_GPU_STATE_ROOT="$state" SPIKERS_QEMU_GPU_DRY_RUN=1 \
    SPIKERS_QEMU_GPU_CPUS=4 SPIKERS_QEMU_GPU_MEMORY_MIB=2048 ${launch_env[@]+"${launch_env[@]}"} \
    "$resources/scripts/run-qemu-gpu.sh" "$@" 2>&1 | sed 's/\\//g'
  return "${PIPESTATUS[0]}"
}
qemu_ran() {
  [[ -s $test_root/qemu-invocations ]]
}

# Inspect-only reports the factory identity and size for build-app.sh.
record=$(env SPIKERS_QEMU_GPU_INSPECT_ONLY=1 "$resources/scripts/run-qemu-gpu.sh")
[[ $record == "$sha"$'\t'4194304 ]] || fail "unexpected inspect record: $record"

# --- a first persistent launch creates the VM from the factory -----------------
launch_env=(SPIKERS_QEMU_GPU_PORT_FORWARDS=tcp:2222:22 SPIKERS_QEMU_GPU_LOCALE=ja_JP.UTF-8 SPIKERS_QEMU_GPU_DISK_GIB=1)
output=$(launch)
assert_contains "$output" "[qemu-gpu] Launch phase: checking"
assert_contains "$output" "[qemu-gpu] Launch phase: preparing"
assert_contains "$output" "[qemu-gpu] Launch phase: finishing"
assert_contains "$output" "if=pflash,format=raw,readonly=on,file=$resources/firmware/edk2-aarch64-code.fd"
assert_contains "$output" "if=pflash,format=raw,file=$state/shell/efi-vars.fd"
assert_not_contains "$output" " -kernel "
assert_not_contains "$output" " -append "
host_settings='spikers.qemu_virgl=1 spikers.virgl_dual_source=1 spikerssciencepal.ssh_access=1 spikerssciencepal.keyboard=jis spikerssciencepal.locale=ja_JP.UTF-8 spikerssciencepal.timezone=America/Sao_Paulo'
assert_contains "$output" "host settings: $host_settings"
assert_contains "$output" "io.systemd.credential.binary:spikerssciencepal.host=$(printf '%s' "$host_settings" | base64 | tr -d '\n')"
package=$(printf '%s' spikers-science-pal-0.2.0-1-aarch64.pkg.tar.zst | base64 | tr -d '\n')
assert_contains "$output" "io.systemd.credential.binary:spikerssciencepal.package=$package"
assert_contains "$output" "mount_tag=spikerssciencepal-packages"
assert_contains "$output" "hostfwd=tcp:127.0.0.1:2222-:22"
assert_contains "$output" "Nested virtualization is off"
assert_not_contains "$output" "virtualization=on"
assert_contains "$output" "-add-fd fd=9,set=77,opaque=spikers-persistent-lock"
# The app accepts only this QMP path shape (QEMUGPULauncher.qmpSocketPath).
[[ $output =~ unix:/tmp/spikers-qemu-gpu\.[A-Za-z0-9]{6}/qmp\.sock, ]] || fail "the QMP socket path is not one the app accepts"
for port in 'nr=0,chardev=spikers-hvc0' 'nr=1,chardev=spikers-audio-bridge,name=dev.spikerssciencepal.audio' \
  'nr=2,chardev=spikers-clipboard-bridge,name=dev.spikerssciencepal.clipboard' \
  'nr=3,chardev=spikers-authentication-bridge,name=dev.spikerssciencepal.authentication' \
  'nr=4,chardev=spikers-camera-bridge,name=dev.spikerssciencepal.camera' 'nr=5,chardev=spikers-guest-status,name=dev.spikerssciencepal.guest' \
  'nr=6,chardev=spikers-settings-bridge,name=dev.spikerssciencepal.settings' 'nr=7,chardev=spikers-battery-bridge,name=dev.spikerssciencepal.battery' \
  'nr=8,chardev=spikers-timezone-bridge,name=dev.spikerssciencepal.timezone'; do
  assert_contains "$output" "$port"
done
[[ -f $state/shell/disk.img && -f $state/shell/efi-vars.fd && -f $state/shell/vm.json && -f $state/shell-factory/$sha.img ]] ||
  fail "the persistent VM was not created"
# A dry run never grows the disk.
[[ $(stat -f %z "$state/shell/disk.img") == 4194304 ]] || fail "a dry run grew the disk"
[[ $(stat -f %z "$state/shell/efi-vars.fd") == 67108864 ]] || fail "the variable store is not 64 MiB"
[[ $(stat -f %Lp "$state/shell/disk.img") == 600 && $(stat -f %Lp "$state") == 700 ]] || fail "the VM is not private"
[[ $(<"$state/.spikers-qemu-storage") == spikers-qemu-storage-root-v1 ]] || fail "no storage-root marker"
qemu_ran && fail "a dry run started QEMU"

# Opting in probes EL2 on macOS 26 or newer and falls back when the probe fails.
cat >"$shims/sw_vers" <<'SH'
#!/bin/bash
echo 26.6.2
SH
chmod 755 "$shims/sw_vers"
launch_env=(SPIKERS_QEMU_GPU_NESTED_VIRT=1)
output=$(launch)
assert_contains "$output" "Nested virtualization is unavailable"
assert_not_contains "$output" "virtualization=on"
rm "$shims/sw_vers"
launch_env=()

# QEMU's reboot, shutdown and monitor policy: one QMP controller, no debugger.
[[ $(grep -o -- "-action reboot=reset,shutdown=poweroff" <<<"$output" | wc -l | tr -d ' ') == 1 ]] ||
  fail "QEMU must reset on reboot and power off on shutdown"
[[ $(grep -o -- " -qmp " <<<"$output" | wc -l | tr -d ' ') == 1 ]] || fail "QEMU must expose exactly one QMP socket"
assert_contains "$output" "-monitor none"
for forbidden in -no-reboot -no-shutdown ' -gdb ' ' -s '; do
  assert_not_contains "$output" "$forbidden"
done
assert_not_contains "$output" "qemu-xhci"

# --- the VM persists; the package offer can be turned off --------------------------
printf 'guest data' | dd of="$state/shell/disk.img" conv=notrunc 2>/dev/null
launch_env=(SPIKERS_SHELL_INSTALL_PACKAGE=)
output=$(launch)
[[ $(head -c 10 "$state/shell/disk.img") == 'guest data' ]] || fail "the persistent disk was replaced"
assert_not_contains "$output" "spikerssciencepal.package"
assert_not_contains "$output" "spikerssciencepal.ssh_access"
assert_not_contains "$output" "Launch phase: preparing"

# --- a VM from an earlier direct-boot version is attached read-only ----------------
assert_not_contains "$output" "spikers-previous"
mkdir -p "$state/disks/current"
printf 'old vm' >"$state/disks/current/rootfs.ext4"
launch_env=()
output=$(launch)
assert_contains "$output" "id=spikers-previous,file=$state/disks/current/rootfs.ext4,format=raw,media=disk,readonly=on"
assert_contains "$output" "virtio-blk-pci,drive=spikers-previous,serial=spikers-previous"
[[ $(<"$state/disks/current/rootfs.ext4") == 'old vm' ]] || fail "the previous VM's disk changed"
assert_not_contains "$(launch --ephemeral)" "spikers-previous"
rm -rf "$state/disks"

# --- a real launch grows the disk, keeps the lock and cleans up --------------------
# One run directory belongs to a launcher that is gone, the other to this shell.
dead=$(mktemp -d '/private/tmp/spikers-qemu-gpu.XXXXXX')
alive=$(mktemp -d '/private/tmp/spikers-qemu-gpu.XXXXXX')
stale_runs=("$dead" "$alive")
printf 'run-qemu-gpu:v2:999999\n' >"$dead/.run-qemu-gpu.owner"
printf 'run-qemu-gpu:v2:%s\n' "$$" >"$alive/.run-qemu-gpu.owner"
launch_env=(SPIKERS_QEMU_GPU_DRY_RUN=0 SPIKERS_QEMU_GPU_DISK_GIB=1)
output=$(launch) && fail "the fake QEMU launch succeeded"
assert_contains "$output" "run-qemu-gpu: QEMU exited before it was ready"
[[ $(stat -f %z "$state/shell/disk.img") == 1073741824 ]] || fail "the disk was not grown to 1 GiB"
[[ ! -e $dead ]] || fail "a stale run directory was kept"
[[ -d $alive ]] || fail "a live run directory was removed"
work=$(sed -n 's/.*unix:\/tmp\/\(spikers-qemu-gpu\.[A-Za-z0-9]*\)\/qmp.sock.*/\1/p' "$test_root/qemu-invocations" | head -1)
[[ -n $work && ! -e /private/tmp/$work ]] || fail "the run directory was not removed"
# A smaller size never shrinks the disk.
launch_env=(SPIKERS_QEMU_GPU_DRY_RUN=0 SPIKERS_QEMU_GPU_DISK_GIB=1)
launch >/dev/null && fail "the fake QEMU launch succeeded"
[[ $(stat -f %z "$state/shell/disk.img") == 1073741824 ]] || fail "the disk changed size"
: >"$test_root/qemu-invocations"

# The lock refuses a second launch of the same VM.
exec 8>>"$state/shell/lock"
/usr/bin/lockf -s -t 0 8 || fail "could not take the test lock"
launch_env=()
output=$(launch) && fail "a locked VM launched"
assert_contains "$output" "run-qemu-gpu: this VM is already open"
exec 8>&-

# --- disposable VMs -------------------------------------------------------------------
# A disposable VM clones the storage folder's factory and leaves the VM alone.
output=$(launch --ephemeral)
assert_not_contains "$output" "Launch phase: preparing"
assert_not_contains "$output" "-add-fd"
assert_contains "$output" "file=/private/tmp/spikers-qemu-gpu."
[[ $(head -c 10 "$state/shell/disk.img") == 'guest data' ]] || fail "an ephemeral launch touched the persistent disk"
# A session-only storage folder clones from SPIKERS_QEMU_GPU_FACTORY_CACHE.
launch_env=(SPIKERS_QEMU_GPU_STATE_ROOT="$test_root/session" SPIKERS_QEMU_GPU_FACTORY_CACHE="$state/shell-factory")
output=$(launch)
assert_not_contains "$output" "Launch phase: preparing"
[[ -f $test_root/session/shell/disk.img ]] || fail "the session VM was not created"

# --- resets ------------------------------------------------------------------------------
launch_env=()
output=$(launch --reset-storage-only)
assert_contains "$output" "[qemu-gpu] Reset phase: checking"
assert_contains "$output" "[qemu-gpu] Reset phase: deleting"
assert_contains "$output" "[qemu-gpu] Reset phase: finishing"
assert_contains "$output" "Reset complete"
assert_not_contains "$output" "Launch phase"
[[ ! -e $state/shell/disk.img && ! -e $state/shell/efi-vars.fd ]] || fail "reset kept the VM"
[[ -f $state/shell-factory/$sha.img ]] || fail "reset removed the factory cache"
qemu_ran && fail "a reset started QEMU"
output=$(launch --reset-storage)
[[ -f $state/shell/disk.img ]] || fail "reset-and-launch did not create a new VM"

# --- USB passthrough ------------------------------------------------------------------
# The app's exact-port form (USBPassthrough.swift).
launch_env=(SPIKERS_QEMU_GPU_USB_HOST=vendorid=0x05ac,productid=0x12a8,hostbus=1,hostport=2.1)
output=$(launch)
assert_contains "$output" "-device qemu-xhci,id=spikers-usb,streams=off"
assert_contains "$output" "-device usb-host,bus=spikers-usb.0,id=spikers-usb-host,vendorid=0x05ac,productid=0x12a8,hostbus=1,hostport=2.1"
write_qemu ''
output=$(launch) && fail "a QEMU without exact USB bus matching was accepted"
assert_contains "$output" "exact USB bus matching"
write_qemu 'exact bus 0 matching'

# --- shared folder --------------------------------------------------------------------
mkdir -p "$test_root/My Work"
launch_env=(SPIKERS_QEMU_GPU_SHARED_FOLDER="$test_root/My Work")
output=$(launch)
assert_contains "$output" "path=$test_root/My Work,security_model=none,multidevs=remap,guest_owner_uid=1000,guest_owner_gid=1000"
assert_contains "$output" "mount_tag=mac"
assert_contains "$output" "spikers.shared_folder_name=TXkgV29yaw"
for refused in "$HOME" "$HOME/Library" /Applications; do
  launch_env=(SPIKERS_QEMU_GPU_SHARED_FOLDER="$refused")
  output=$(launch) && fail "sharing $refused was accepted"
  [[ $output == *"run-qemu-gpu: refusing to share"* || $output == *"run-qemu-gpu: shared folder must be owned"* ]] ||
    fail "sharing $refused failed for another reason: $output"
done

# --- bridged networking ------------------------------------------------------------------
# A dry run never starts the network helper (this bundle has none) and the
# persistent VM gets its saved address.
launch_env=(SPIKERS_NETWORK_MODE=bridged SPIKERS_NETWORK_INTERFACE=en0 SPIKERS_NETWORK_BRIDGED_SSH=1
  SPIKERS_QEMU_GPU_PORT_FORWARDS=tcp:2222:22)
output=$(launch)
assert_contains "$output" "addr.path=/private/tmp/bridge-dry-run/network.sock"
assert_contains "$output" "spikerssciencepal.ssh_access=1 spikerssciencepal.ssh_from=any"
assert_not_contains "$output" "hostfwd="
mac=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["mac"])' "$state/network-identities/current.json")
assert_contains "$output" "mac=$mac,"
output=$(launch)
assert_contains "$output" "mac=$mac,"

# --- invalid inputs are refused before storage is touched ----------------------------------
untouched="$test_root/untouched"
for setting in SPIKERS_QEMU_GPU_CPUS=2 SPIKERS_QEMU_GPU_MEMORY_MIB=1024 SPIKERS_QEMU_GPU_MEMORY_MIB=lots \
  SPIKERS_QEMU_GPU_DISK_GIB=0 SPIKERS_QEMU_GPU_DISK_GIB=9000 SPIKERS_QEMU_GPU_LOCALE=xx_XX.UTF-8 \
  'SPIKERS_QEMU_GPU_USB_HOST=vendorid=0x05ac,romfile=/etc/hosts' 'SPIKERS_QEMU_GPU_USB_HOST=vendorid=0x05ac -s' \
  SPIKERS_QEMU_GPU_HVF_TRACE_LOG=relative.log SPIKERS_QEMU_GPU_IMMERSIVE=2 SPIKERS_QEMU_GPU_DRY_RUN=2 \
  SPIKERS_QEMU_GPU_NESTED_VIRT=yes \
  SPIKERS_QEMU_GPU_SHARED_FOLDER=/etc,x SPIKERS_SHELL_INSTALL_PACKAGE=/etc/hosts SPIKERS_NETWORK_MODE=vmnet \
  SPIKERS_QEMU_GPU_PORT_FORWARDS=tcp:22:22:22; do
  launch_env=("$setting" SPIKERS_QEMU_GPU_STATE_ROOT="$untouched")
  output=$(launch) && fail "$setting was accepted"
  [[ $output == *run-qemu-gpu:* || $output == *'Network mode'* || $output == *forward* ]] ||
    fail "$setting failed without a launcher error: $output"
  [[ ! -e $untouched ]] || fail "$setting touched storage"
done

# --- a release app's downloaded factory ---------------------------------------------------
# A release app carries no image. An existing VM still launches; a new one
# needs the app's verified download (FactoryImageDownload.swift).
downloaded="$test_root/downloaded.img.zst"
mv "$resources/guest/spikers-aarch64-edge.img.zst" "$downloaded"
rm -f "$state/shell-factory/$sha.img"
launch_env=()
output=$(launch)
assert_not_contains "$output" "Launch phase: preparing"
fresh="$test_root/fresh"
launch_env=(SPIKERS_QEMU_GPU_STATE_ROOT="$fresh")
output=$(launch) && fail "a new VM was created without the factory image"
assert_contains "$output" "run-qemu-gpu: the Spiker's Science Pal image has not been downloaded"
launch_env=(SPIKERS_QEMU_GPU_STATE_ROOT="$fresh" SPIKERS_QEMU_GPU_FACTORY_IMAGE=relative.img.zst)
output=$(launch) && fail "a relative factory image was accepted"
assert_contains "$output" "SPIKERS_QEMU_GPU_FACTORY_IMAGE must be an absolute path"
# A failed decompression (a full disk) leaves no partial disk behind.
launch_env=(SPIKERS_QEMU_GPU_STATE_ROOT="$fresh" SPIKERS_QEMU_GPU_FACTORY_IMAGE="$downloaded" FAKE_ZSTD_FAIL=1)
output=$(launch) && fail "a failed decompression was accepted"
assert_contains "$output" "run-qemu-gpu: could not decompress the factory disk"
[[ ! -e $fresh/shell-factory/$sha.img.partial && ! -e $fresh/shell/disk.img ]] ||
  fail "a failed decompression left files behind"
launch_env=(SPIKERS_QEMU_GPU_STATE_ROOT="$fresh" SPIKERS_QEMU_GPU_FACTORY_IMAGE="$downloaded")
output=$(launch)
assert_contains "$output" "Launch phase: preparing"
[[ -f $fresh/shell/disk.img && -f $fresh/shell-factory/$sha.img ]] || fail "the downloaded factory did not create a VM"
printf 'damaged' >"$test_root/damaged.img.zst"
launch_env=(SPIKERS_QEMU_GPU_STATE_ROOT="$test_root/damaged" SPIKERS_QEMU_GPU_FACTORY_IMAGE="$test_root/damaged.img.zst")
output=$(launch) && fail "a damaged factory image was accepted"
assert_contains "$output" "run-qemu-gpu: the Spiker's Science Pal factory image is damaged"
# The bundled image wins over a download.
launch_env=(SPIKERS_QEMU_GPU_STATE_ROOT="$test_root/bundled" SPIKERS_QEMU_GPU_FACTORY_IMAGE="$test_root/damaged.img.zst")
mv "$downloaded" "$resources/guest/spikers-aarch64-edge.img.zst"
output=$(launch)
[[ -f $test_root/bundled/shell/disk.img ]] || fail "the bundled factory did not win over a download"

# --- storage location checks -------------------------------------------------------------
launch_env=(SPIKERS_QEMU_GPU_TEST_FS_TYPE=exfat)
output=$(launch) && fail "a non-APFS storage folder was accepted"
assert_contains "$output" "requires an APFS volume"
for broad in /tmp /Users relative/path; do
  launch_env=(SPIKERS_QEMU_GPU_STATE_ROOT="$broad")
  output=$(launch) && fail "storage folder $broad was accepted"
  assert_contains "$output" "run-qemu-gpu:"
done
rm -f "$state/shell-factory/$sha.img"
launch_env=(SPIKERS_QEMU_GPU_TEST_FREE_BYTES=1024 SPIKERS_QEMU_GPU_STATE_ROOT="$test_root/full")
output=$(launch) && fail "a launch without free space was accepted"
assert_contains "$output" "not enough free space"
[[ ! -e $test_root/full/shell/disk.img ]] || fail "a VM was created without free space"

# --- the app's error mapping and the Cocoa keyboard env -------------------------------------
grep -q '^export SPIKERSSCIENCEPAL_KEYBOARD=\$keyboard$' "$resources/scripts/run-qemu-gpu.sh" ||
  fail "the Cocoa display must get the same keyboard geometry as the guest"
grep -q '^  echo "run-qemu-gpu: \$\*" >&2$' "$resources/scripts/run-qemu-gpu.sh" ||
  fail "errors must keep the run-qemu-gpu: prefix the app maps"
qemu_ran && fail "QEMU was started outside the real-launch case"

echo "run-qemu-gpu.test: ok"
