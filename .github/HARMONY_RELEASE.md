# Harmony release automation

The `Harmony Release` workflow checks the latest stable Mihon release every day and publishes the
corresponding `vX.Y.Z-harmony.1` release when it does not already exist. It can also be run manually
with an explicit upstream tag and patch number.

## One-time signing setup

Create a dedicated release key and keep multiple secure backups. Losing this key prevents future
versions from updating existing installations.

```shell
keytool -genkeypair -v \
  -keystore mihon-harmony.jks \
  -alias mihon-harmony \
  -keyalg RSA \
  -keysize 4096 \
  -validity 10000
```

Add these repository Actions secrets under **Settings > Secrets and variables > Actions**:

- `SIGNING_KEY`: Base64-encoded contents of `mihon-harmony.jks`.
- `KEY_STORE_PASSWORD`: Keystore password.
- `ALIAS`: Key alias, such as `mihon-harmony`.
- `KEY_PASSWORD`: Key password.

On macOS, copy the encoded keystore with:

```shell
base64 -i mihon-harmony.jks | pbcopy
```

Never commit the keystore or its passwords to this repository.

## Publishing

- Scheduled runs use the latest non-draft, non-prerelease release reported by GitHub and patch
  number `1`.
- To publish another fork revision for the same Mihon version, manually run the workflow with the
  same upstream tag and the next patch number, for example `2`.
- Existing GitHub releases are skipped.
- A cherry-pick conflict, failed check, failed test, or failed build stops the workflow before a tag
  or release is created.

Harmony-only changes must be committed on `main`, then their commit IDs added in order to
`.github/harmony-patches.txt`. Keep those commits focused so they can be cherry-picked cleanly onto
future Mihon stable tags.
