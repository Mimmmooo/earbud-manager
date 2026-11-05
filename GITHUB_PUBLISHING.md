# Publishing this repository on GitHub

This file is for project maintainers. It contains **no personal account information**.

## Recommended repository settings

- **Repository name:** `earbud-manager`
- **Visibility:** Public (only after privacy review and local testing)
- **Description:** `Unofficial GNOME earbud manager for Linux: CMF Buds 2 ANC, battery, low latency, multipoint, and Find My Earbuds.`
- **Topics:** `linux`, `ubuntu`, `gnome`, `bluetooth`, `earbuds`, `gtk4`, `libadwaita`, `python`, `cmf`, `nothing-tech`
- **Homepage:** Optional; leave empty unless a real project website exists.
- **License:** MIT (already included)

## Publish commands

Create a **new empty GitHub repository** first. Do not initialize it with an extra README or license, because the project already contains those files.

```bash
cd earbud-manager
/usr/bin/python3 -m unittest discover -s tests -v
bash -n install.sh uninstall.sh
git init
git add .
git status --short
# Review the entire staged diff for privacy BEFORE committing:
git diff --cached --stat
git diff --cached

git commit -m "Initial public test release v0.9.1-rc2"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/earbud-manager.git
git push -u origin main
```

Replace `YOUR_USERNAME` locally. You can alternatively use a GitHub SSH remote if configured. GitHub authentication is required for the push; **never put credentials in files or commit them**.

## Create a GitHub release

On the repository page, go to **Releases → Draft a new release**.

- **Tag:** `v0.9.1-rc2`
- **Title:** `v0.9.1-rc2 — Faster controls and stable Adwaita UI`
- Check **Set as a pre-release** (hardware validation is ongoing).
- Attach the release ZIP if desired.

**Release note (copy and paste):**

> Public test build for Ubuntu GNOME. Maintains the original Adwaita interface and supported CMF Buds 2 controls. Speeds up UI responsiveness by updating widgets in place and separating Bluetooth work from discovery and telemetry queues. Includes permanent installation under `/opt`, local device naming, dual connection, and a read-only paired-device list. Direct device switching and GNOME Settings Power-panel modifications are not included. Please redact Bluetooth device names and addresses in issue reports.

## Before publishing

- [ ] Run app with a real connected device on Ubuntu.
- [ ] Verify ANC, Low Latency, Dual Connection, battery and 15-second Find My Earbuds.
- [ ] Confirm local rename persists across app restarts.
- [ ] Confirm launch works from application menu after `./install.sh`.
- [ ] Confirm `./uninstall.sh` removes only app files.
- [ ] Verify Git author name/email in commits are what you intentionally want public (`git config user.name` and `git config user.email`).
- [ ] Review `git diff --cached` for private data and secrets; `.gitignore` alone is not a guarantee.

**Platform honesty:** Ubuntu/GNOME is the only runnable variant. Windows/macOS folders describe future implementations, not releases.
