# Integration updates

Three pieces update on their own schedules:

| Piece | Ships through | Who triggers it |
| --- | --- | --- |
| Mac app | DMG ([app updates](app-updates.md)) | The user installs the app |
| `spikers-science-pal` guest package | Bundled in the app, offered on every boot | Automatic, before login |
| `spikers-science-pal-research` | Installed in the factory disk a new VM downloads | Already present after the download |
| Spiker's Science Pal, its Hyprland stack and kernel | Spiker's Science Pal's repositories | `spikers update` in the guest |

Replacing the app never touches a VM's disk. The guest updates itself.

See [runtime validation](runtime-validation.md) for the tested boot, upgrade,
graphics and host-integration paths, plus the remaining interactive checks.

## The guest package

Every Mac integration in the guest is the `spikers-science-pal` pacman package
([guest/package](../guest/package/README.md)). The app bundles the package it
was built with, in `Contents/Resources/guest-packages/`.

On every boot the launcher:

1. names that archive in the systemd credential `spikerssciencepal.package`, and
2. shares it on a read-only virtio-9p share tagged `spikerssciencepal-packages`.

Before any login, `spikers-science-pal-package-install.service` compares the offered
version with the installed one (`vercmp`). It installs the archive with
`pacman -U` only when it is newer. A guest that already has the same version,
or a newer one installed in the guest, keeps it. Package
installation uses pacman and the package's own install hooks; there is no
host-side file journal, consent catalog or migration runner.

The result goes to `/var/lib/spikers-science-pal/package-install.json`
(`installed`, `current` or `failed`, with a message). The status reporter
sends it to the app with the next report.

Developers can turn the offer off with `SPIKERS_SHELL_INSTALL_PACKAGE=` (an
empty value) or name another archive with
`SPIKERS_SHELL_INSTALL_PACKAGE=/path/to/spikers-science-pal-<version>-aarch64.pkg.tar.zst`.
`make guest-package` rebuilds only the package; the next `make app` bundles
it.

## Status

`spikers-science-pal-guest-status.service` sends one JSON line every 10 seconds on
`dev.spikerssciencepal.guest` (protocol 1):

```json
{"channel":"edge","kernel":{"installed":"7.2.8-11","running":"7.2.8-11-omarchy"},
 "spikers":"4.0.0.r7024.g246f33a-1","package":"0.1.0-1","protocol":1}
```

The app keeps the last report in `<VM storage>/shell/guest-status.json`. The
start menu's **Spiker's Science Pal** row shows the Spiker's Science Pal version and channel on one
line and the integration package on the other:

- **Current**: the guest has the bundled package or a newer one.
- **Update pending**: the guest reported an older package. It shows
  `Integrations <installed> → <bundled> next launch`.
- A failed installation shows its message.

Before the first report the row says that versions appear after Spiker's Science Pal
starts. Reports are advisory: they decide only what the start menu shows.

## Spiker's Science Pal itself

Spiker's Science Pal, the kernel and every other package update through `spikers update`
inside the guest. It takes a Snapper snapshot first; the snapshot appears in
Limine's boot menu for rollback. `omarchy-channel-set` switches channels the
platform has a template for. On ARM, Spiker's Science Pal publishes only to `edge` for now.

## Compatibility

Every virtio port keeps its protocol. A guest ignores ports it does not know,
and the app reads only the report fields it knows, so either the app or the
guest can be updated first. A guest updated before the app may carry a package
newer than the app's; the app then leaves it alone.

VMs created by earlier direct-boot versions of the app are not launched or
migrated by this version. Their disks stay in the storage folder untouched.
The launcher attaches `disks/current/rootfs.ext4` (or another `disks/*/`
root) to the persistent VM as a read-only virtio disk with serial
`spikers-previous`, and the package's `spikers-science-pal-import-previous` copies the
user's files and lists or installs their packages from it. See the
[README](../README.md#existing-vm-data).

## Where the installer is

`make guest` builds both guest archives and the factory disk. `guest/build.sh`
passes `spikers-science-pal-*.pkg.tar.zst` and
`spikers-science-pal-research-*.pkg.tar.zst` to the factory, and
`guest/factory/build-image.sh` installs those local packages with `pacstrap -U`.
A disk built from `main2` at `623d584` or later already contains
`spikers-science-pal-research`. Opening that VM does not need `pacman -U`.

On 2026-10-18 `make guest-package` completed in the ARM64 builder. The same
archives are committed under `guest/prebuilt/` so they can be downloaded:

- [spikers-science-pal-0.1.0-23-aarch64.pkg.tar.zst](https://github.com/tspike630/Spiker-s-science-pal/raw/cursor/research-preinstall-receipt-b758/guest/prebuilt/spikers-science-pal-0.1.0-23-aarch64.pkg.tar.zst)
- [spikers-science-pal-research-0.4.0-1-any.pkg.tar.zst](https://github.com/tspike630/Spiker-s-science-pal/raw/cursor/research-preinstall-receipt-b758/guest/prebuilt/spikers-science-pal-research-0.4.0-1-any.pkg.tar.zst)

The research archive is `arch = any`, `pkgver = 0.4.0-1`. On an existing VM,
`sudo pacman -U` of the integration archive first, then the research archive,
installs the workbench. A factory disk built from `main2` at `623d584` or later
installs both during `pacstrap` and does not need that manual step.

The factory disk built on 2026-10-19 already contains both packages.
`packages.txt` in the release lists `spikers-science-pal-research 0.4.0-1`.
The compressed disk is 3.9 GiB. GitHub stores files only up to 2 GiB, so the
release keeps four parts and one installer script that downloads them, checks
them, and writes the single disk:

https://github.com/tspike630/Spiker-s-science-pal/releases/download/factory-2026-10-19/install-factory-vm.sh

```
sh install-factory-vm.sh
```

The script writes `spikers-aarch64-edge.img`, the 20 GiB VM disk. Its
uncompressed sha256 is
`e35304268b2fb8ae2695643ab682e4a75725f63a4c2d0f2ec4fee7a1c8603208`. The Mac DMG
is still produced by `make release` on Apple Silicon.

科研包已构建并预装。一个安装包的入口是 `install-factory-vm.sh`，跑完得到已经装好科研包的虚拟机磁盘。那份磁盘里的版本是 `spikers-science-pal-research` 0.4.0-1。

0.4.1 adds the 科研 column (one field, one window). It is a separate archive on `cursor/research-menu-apps-b758`, and the 2026-10-19 factory disk stays on 0.4.0-1:

https://github.com/tspike630/Spiker-s-science-pal/raw/cursor/research-menu-apps-b758/guest/prebuilt/spikers-science-pal-research-0.4.1-1-any.pkg.tar.zst

On a VM that is already running:

```
sudo pacman -U https://github.com/tspike630/Spiker-s-science-pal/raw/cursor/research-menu-apps-b758/guest/prebuilt/spikers-science-pal-research-0.4.1-1-any.pkg.tar.zst
/usr/lib/spikers-science-pal-research/menu-entries
/usr/lib/spikers-science-pal-research/desktop-entries
```

The menu watches the jsonc those two commands write. Logging in again runs the same scripts from the session unit.

0.4.5 adds the general handoff. The connected Omarchy agent decides the procedure for the goal. It may use the shell, open SciencePal, and run the nine-step calculator only when the goal is a table to screen. The 2026-10-19 factory disk stays on 0.4.0-1. On a VM that is already running:

```
sudo pacman -U https://github.com/tspike630/Spiker-s-science-pal/raw/cursor/research-engine-apps-b758/guest/prebuilt/spikers-science-pal-research-0.4.5-1-any.pkg.tar.zst
/usr/lib/spikers-science-pal-research/menu-entries
/usr/lib/spikers-science-pal-research/desktop-entries
```

`sciencepal-file-upload.sql` in that package is the grant for `scrub_nested_message_unicode`. It has to be run by the database owner in the Supabase SQL editor. Installing the package does not change sciencepal.ai.
