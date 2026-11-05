# Install Earbud Manager

**Current source version:** `v0.9.3-rc1` (Ubuntu GNOME; CMF Buds 2 test target). The published `v0.9.1-rc2` Debian package is older. A new GitHub Release must be published before its updated installer appears under Releases.

## Install from a release (recommended)

1. Open [GitHub Releases](https://github.com/Mimmmooo/earbud-manager/releases).
2. Download the `.deb` file from the **matching version** (not an older release).
3. From the download directory, run:

```bash
sudo apt install './earbud-manager_0.9.3~rc1-1_all.deb'
```

Alternatively, double-click the package and use Ubuntu's software installer. APT installs missing system packages when available. No `pip` or virtual environment is needed. Run the app from Applications, or type `earbud-manager`.

**Update:** Install the newer `.deb` with APT as above. **Remove:** `sudo apt remove earbud-manager`. Local rename preferences remain.

## Install from source

```bash
git clone https://github.com/Mimmmooo/earbud-manager.git
cd earbud-manager
./install.sh
```

For a preview without installing, run `/usr/bin/python3 src/earbuds_manager.py` after installing the system dependencies listed in README. **Do not mix source installation and the Debian package.** If you already installed from source, run `./uninstall.sh` from the source checkout before installing the `.deb` package.

## Build the matching Debian package

On Ubuntu or Debian with `dpkg-deb` installed, from the repository root:

```bash
bash packaging/build-deb.sh
```

This creates `dist/earbud-manager_0.9.3~rc1-1_all.deb` for the current VERSION. Build checks (including installation layout validation) also run automatically in [GitHub Actions](https://github.com/Mimmmooo/earbud-manager/actions); the successful run provides an artifact ZIP containing the `.deb`.

## Publish a new installer (maintainer)

1. **Merge and verify** the version branch on `main`. Confirm `VERSION` says `0.9.3-rc1` and GitHub Actions is green.
2. On GitHub, open **Releases → Draft a new release**, create a new tag **`v0.9.3-rc1` targeting `main`**, and mark it **Pre-release**. Publish the release without attaching the old `.deb`.
3. The `Publish Debian installer on version tag` workflow builds and attaches the correct `.deb` to that release. Check its workflow status and confirm the asset appears before giving users the link.

**Never overwrite the old `v0.9.1-rc2` release asset with a newer app**. Keep version-specific release history intact.

Windows/macOS installers are not available. The app is unofficial and does not alter GNOME Settings itself.
