# Contributing

Contributions are welcome, especially verified support for additional earbuds.

- Open an issue describing the model, firmware (if known), Linux version, expected behavior, and actual behavior.
- **Never post raw Bluetooth logs or screenshots containing personal details.** Remove MAC addresses, paired device names, usernames, system paths, account information and location data before publishing.
- Keep Bluetooth write commands allowlisted. Document the exact request, response and read-back validation before enabling a new control.
- Preserve the compact original GNOME Adwaita UI and existing 15-second Find My Earbuds behavior.
- Run the offline tests before proposing a change: `python3 -m unittest discover -s tests -v`.
- A feature is considered hardware-tested only after it has been verified on the specified earbuds model. Do not describe UI mockups as working controls.
- Avoid adding remote network access or telemetry without an explicit technical discussion and a privacy review.
