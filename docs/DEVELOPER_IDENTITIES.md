# Developer identity workflow

## Scan with pseudonymous developer IDs

```shell
codescan scan /path/to/repository --output ./scan-output --encrypt-developer-identities
```

CodeScan prompts for a seed twice. Use a long, unique passphrase; it is not accepted as a CLI argument and is not written to disk. The scan includes developer activity grouped by stable `DEV-...` IDs. Names and emails are stored only in the encrypted `developer-identities.enc.json` artifact. Do not email that artifact and its seed together.

## Decrypt for authorized review

```shell
codescan decrypt-identities ./scan-output/developer-identities.enc.json > developers.csv
```

The command prompts for the seed and emits CSV to standard output. Protect the redirected CSV under the same access controls as the original names and emails. Decryption validates the authenticated ciphertext and reports a clear error for an incorrect seed or modified file.

IDs are stable for the same seed and exact author name/email pair. Git aliases are not merged automatically. Commit counts and changed-line counts describe repository activity; they are not measures of productivity, code quality, or employee performance.
