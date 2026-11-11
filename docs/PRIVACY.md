# Privacy and data handling

The local inventory scan performs no network requests and does not execute project code. It records relative paths, filename-derived language, byte size, and line counts. It does not include source excerpts, absolute scan paths, credentials, or contributor identities. Review the output bundle before sharing it because filenames and project structure can still be sensitive.

Symlinks are skipped and common generated/vendor directories are excluded. Network-backed checks are disabled by default and require explicit selection with documented data-transfer behavior.

Dependency discovery is currently offline and parses supported files as static text/XML/JSON/TOML. It does not run package managers and does not contact vulnerability databases. Package names and versions are included in `results.json` and summarized in the Markdown report.

OSV-Scanner vulnerability scanning is disabled by default. Offline mode reads an existing local advisory database only. Online mode requires the explicit `--vulnerability-scan online` option and sends package names, versions, and ecosystems to OSV.dev; no source code is intentionally transmitted by CodeScan. Package license lookup is a separate `--license-scan` opt-in and sends package metadata to deps.dev through OSV-Scanner. Local license-file detection only records common filenames and makes no legal determination. CodeScan never invokes OSV-Scanner remediation. See [OSV-Scanner integration](OSV_SCANNER.md) for the executable behavior and upstream privacy references.

## Developer identity pseudonymization

Detailed developer activity is opt-in. Run `codescan scan PATH --encrypt-developer-identities`; CodeScan prompts twice for a seed and never accepts it as a command-line argument. The seed derives stable, repository-independent pseudonymous IDs and encrypts a developer ID-to-name/email/activity map using PBKDF2-HMAC-SHA256 and Fernet authenticated encryption. A random salt is stored with the encrypted artifact at `developer-identities.enc.json`; the seed is not stored. The encrypted artifact is created with owner-only permissions where the operating system supports them.

The Markdown and JSON scan reports contain developer IDs and aggregate activity only. They do not contain developer names or email addresses. Keep the seed separately and share it only with authorized reviewers. A weak or reused seed can make identity protection weaker; use a long, unique passphrase and retain it securely. If the seed is lost, the encrypted identity map cannot be recovered. The seed is not an encryption key backup mechanism.

To review identities, run `codescan decrypt-identities PATH/developer-identities.enc.json`. The tool prompts for the seed and writes decrypted CSV to standard output. Redirect that output only to a location approved for sensitive data. A wrong seed or modified artifact is rejected.
