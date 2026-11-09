# Privacy and data handling

The local inventory scan performs no network requests and does not execute project code. It records relative paths, filename-derived language, byte size, and line counts. It does not include source excerpts, absolute scan paths, credentials, or contributor identities. Review the output bundle before sharing it because filenames and project structure can still be sensitive.

Symlinks are skipped and common generated/vendor directories are excluded. Future network-backed checks will be opt-in and will document metadata transfer before release.
