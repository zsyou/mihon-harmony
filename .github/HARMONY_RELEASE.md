# Harmony release automation

The `Harmony Release` workflow checks the latest stable Mihon release every day and publishes the
corresponding `vX.Y.Z-harmony.1` release when it does not already exist. It can also be run manually
with an explicit upstream tag and patch number.

The job builds that upstream tag. It does not build this fork's default branch, and it does not call
upstream `release.yml` (that workflow only runs for `mihonapp/mihon`). Harmony-only changes are
applied from `.github/patches/` before Gradle starts.

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

The workflow decodes `SIGNING_KEY` to a temporary keystore and passes it to Gradle as `storeFile`.
It also passes `storeFileBase64` so older Mihon tags that still decode the keystore inside Gradle
keep working. `MIHON_GITHUB_RELEASE=true` selects that signing path. When the variable is unset,
Gradle leaves the path untouched and does not throw. When it is `true` but a password, alias, or
keystore is missing, configuration fails with the names of the missing values instead of
`getenv(...) must not be null`.

## Publishing

- Scheduled runs use the latest non-draft, non-prerelease release reported by GitHub and patch
  number `1`.
- To publish another fork revision for the same Mihon version, manually run the workflow with the
  same upstream tag and the next patch number, for example `2`.
- Manual runs can set `dry_run` to apply the patches and print the version bump without signing,
  building, tagging, or publishing. Dry run does not check the signing secrets.
- Existing GitHub releases are skipped. A dry run still validates the patches.
- A patch conflict, missing signing secret, failed `spotlessCheck`, failed unit test, or failed
  build stops the workflow before a tag or release is created.

`versionCode` becomes `upstreamVersionCode * 100 + patchNumber`. `versionName` becomes
`X.Y.Z-harmony.N`.

## What the patches change

`.github/patches/series` lists the patches in apply order:

1. `harmony.patch` — fork notice in `README.md`, `UniFile.renameToOrCopy`, its unit test, and the
   `Downloader.kt` call sites. Rename is still tried first. Copy-and-delete is only the fallback
   for SAF providers that do not support `renameDocument`, which is what keeps chapter downloads
   from remaining as `.tmp` files on HarmonyOS / ZhuoyiTong.
2. `signing.patch` — null-safe release signing in `app/build.gradle.kts`.

`.github/patches/BASE_TAG` records the Mihon tag those patches were last refreshed against.

Check the series locally before relying on the scheduled run:

```shell
python3 .github/scripts/test_prepare_harmony_tree.py
python3 .github/scripts/prepare_harmony_tree.py --check --upstream-tag v0.21.2 --patch-number 1
```

`--check` fetches the tag, applies every patch in a temporary worktree, checks the Harmony rename
fallbacks and the signing block, and rewrites `versionCode` / `versionName`. It does not change the
current branch. Use `--apply` only in GitHub Actions; it detaches the checkout onto the upstream tag.

## Refreshing the patches

Refresh when `--check` reports that a patch does not apply, or when the patched tree fails
`spotlessCheck` or `testDebugUnitTest` because upstream moved the download or signing code.

1. Fetch the tag you want to follow, for example `v0.21.2`:

   ```shell
   git fetch --no-tags https://github.com/mihonapp/mihon.git tag v0.21.2
   git worktree add --detach /tmp/mihon-harmony-refresh FETCH_HEAD
   cd /tmp/mihon-harmony-refresh
   ```

2. Port the Harmony behavior onto that tree:
   - Keep the bilingual fork notice at the top of `README.md`.
   - Keep `UniFile.renameToOrCopy` in
     `core/common/src/main/kotlin/tachiyomi/core/common/storage/UniFileExtensions.kt`.
     It must return the renamed file, or the copied file when rename is unsupported, and it must
     not overwrite an existing target.
   - Keep the unit test next to it. Call MockK `any()` inside `every` / `verify`.
     Do not add `import io.mockk.any`: MockK 1.14 only declares `any` on `MockKMatcherScope`,
     and that import fails `:core:common:compileDebugUnitTestKotlin`.
   - In `Downloader.kt`, final names for the chapter directory, page image, cached image, and CBZ
     archive must go through `renameToOrCopy`. Create `.nomedia` on the directory returned for a
     non-CBZ chapter, because a copy fallback returns a different file from the temporary directory.
   - Replace the `MIHON_GITHUB_RELEASE` signing block with the null-safe block already in
     `signing.patch` (either `storeFile` or `storeFileBase64`, and `error(...)` when the flag is set
     but a value is blank). Do not call `file(System.getenv(...))` or `.toBoolean()` on `getenv`.

3. From the worktree, regenerate the patches. Do this before the version bump; version numbers are
   applied later by `prepare_harmony_tree.py`.

   ```shell
   git add -A
   git diff --cached -- \
     README.md \
     app/src/main/java/eu/kanade/tachiyomi/data/download/Downloader.kt \
     core/common/src/main/kotlin/tachiyomi/core/common/storage/UniFileExtensions.kt \
     core/common/src/test/java/tachiyomi/core/common/storage/UniFileExtensionsTest.kt \
     > /path/to/mihon-harmony/.github/patches/harmony.patch
   git diff --cached -- app/build.gradle.kts \
     > /path/to/mihon-harmony/.github/patches/signing.patch
   ```

4. Write the tag into `.github/patches/BASE_TAG`, run the `--check` command against that tag, and
   commit only the patch files, `BASE_TAG`, and any script or workflow updates. Do not commit the
   upstream worktree. Remove it with `git worktree remove --force /tmp/mihon-harmony-refresh`.

If upstream adds another signing environment variable, extend the null-safe block and the workflow
environment together, then refresh `signing.patch`.
