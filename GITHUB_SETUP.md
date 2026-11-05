# GitHub publishing checklist

1. Sign in to the **owner's** GitHub account, create a PUBLIC repository named `earbud-manager`.
2. Select **README: Off**, **.gitignore: None**, **License: None** because all three already exist in this source tree.
3. Upload all repository files, including `.github/` and `.gitignore`; do **not** upload diagnostic logs, private configs or personal test results.
4. Before committing from a terminal, choose a safe author identity. The owner's email/name may appear publicly. GitHub's noreply address is recommended for privacy.
5. The owner can invite a contributor using repository **Settings → Collaborators / Access → Add people**, and assign an appropriate role. For the contributor's personal GitHub account, use a separate branch and pull requests; do not share passwords or access tokens.
6. Under Releases → Draft a new release, create a **pre-release** tag `v0.9.1-rc2` and attach `earbud-manager_0.9.1~rc2-1_all.deb` and the source ZIP. Mark as pre-release until hardware testing is complete.
7. Description: `Unofficial GNOME earbuds configuration app. Ubuntu/Linux preview available; Windows/macOS planned.`

## License warning

A `LICENSE` file containing the MIT license is bundled. Review provenance and third-party licenses before publicly declaring all source to be original or fully MIT-compatible. GitHub's license chooser should remain **None** because a LICENSE file is already present.

## Privacy warning

Git commits publish author name/email. Bluetooth device names and MAC addresses may appear in logs and issue screenshots. Remove them before posting. `.gitignore` does not retroactively remove files already committed.
