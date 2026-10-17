#!/usr/bin/env python3
"""Apply Harmony patches onto an upstream Mihon tag and set the fork version.

The release workflow builds an upstream stable tag, not this fork's default
branch. Harmony-only changes therefore live in `.github/patches/` and are
applied here before Gradle runs.

  python3 .github/scripts/prepare_harmony_tree.py --check --upstream-tag v0.21.2
  python3 .github/scripts/prepare_harmony_tree.py --apply --upstream-tag v0.21.2 --patch-number 1
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

UPSTREAM_URL = "https://github.com/mihonapp/mihon.git"
TAG_PATTERN_HELP = "vX.Y.Z"

UNSAFE_FILE_GETENV = 'file(System.getenv('
UNSAFE_RELEASE_FLAG = 'System.getenv("MIHON_GITHUB_RELEASE").toBoolean()'
UNSAFE_BASE64_LET = ".let(Base64::decode)"


class PrepareError(Exception):
    """The Harmony tree cannot be prepared. The message is safe to print in CI."""


@dataclass(frozen=True)
class VersionBump:
    text: str
    previous_code: int
    previous_name: str
    version_code: int
    version_name: str


@dataclass(frozen=True)
class PrepareResult:
    upstream_tag: str
    base_tag: str
    version_code: int
    version_name: str
    previous_code: int
    previous_name: str
    mode: str


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--check",
        action="store_true",
        help="Apply the patches in a temporary worktree and stop before committing",
    )
    mode.add_argument(
        "--apply",
        action="store_true",
        help="Detach the current checkout onto the upstream tag, apply the patches, and commit",
    )
    parser.add_argument("--upstream-tag", required=True, help=f"Official Mihon tag ({TAG_PATTERN_HELP})")
    parser.add_argument("--patch-number", type=int, default=1, help="Harmony patch number from 1 to 99")
    parser.add_argument("--repo", type=Path, default=Path("."), help="Fork checkout that contains .github/patches")
    parser.add_argument(
        "--allow-detach",
        action="store_true",
        help="Allow --apply outside GitHub Actions",
    )
    return parser.parse_args(argv)


def validate_tag(tag: str) -> None:
    parts = tag[1:].split(".") if tag.startswith("v") else []
    if len(parts) != 3 or not all(part.isdigit() for part in parts):
        raise PrepareError(
            f"Unsupported upstream tag: {tag}. Expected a stable Mihon tag such as v0.21.2.",
        )


def validate_patch_number(patch_number: int) -> None:
    if not 1 <= patch_number <= 99:
        raise PrepareError("Patch number must be between 1 and 99.")


def git_env() -> dict[str, str]:
    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"
    return env


def run_git(
    repo: Path,
    args: list[str],
    *,
    check: bool = True,
    capture: bool = False,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        check=check,
        capture_output=capture,
        text=True,
        env=git_env(),
    )


def patches_dir(repo: Path) -> Path:
    return repo / ".github" / "patches"


def read_base_tag(repo: Path) -> str:
    path = patches_dir(repo) / "BASE_TAG"
    if not path.is_file():
        raise PrepareError(
            "Missing .github/patches/BASE_TAG. Record the Mihon tag the patches were refreshed against.",
        )
    tag = path.read_text().strip()
    validate_tag(tag)
    return tag


def load_patches(repo: Path) -> list[tuple[str, bytes]]:
    series = patches_dir(repo) / "series"
    if not series.is_file():
        raise PrepareError(
            "Missing .github/patches/series. List patch filenames in apply order, one per line.",
        )
    names = [line.strip() for line in series.read_text().splitlines() if line.strip() and not line.startswith("#")]
    if not names:
        raise PrepareError(".github/patches/series does not list any patches.")
    loaded: list[tuple[str, bytes]] = []
    for name in names:
        if "/" in name or name.startswith("."):
            raise PrepareError(f"Invalid patch name in series: {name}")
        path = patches_dir(repo) / name
        if not path.is_file():
            raise PrepareError(f"Series lists {name}, but {path} does not exist.")
        loaded.append((name, path.read_bytes()))
    return loaded


def rewrite_versions(gradle_text: str, upstream_tag: str, patch_number: int) -> VersionBump:
    code_marker = "versionCode = "
    name_marker = 'versionName = "'
    code_at = find_assignment(gradle_text, code_marker, "versionCode")
    name_at = find_assignment(gradle_text, name_marker, "versionName")

    code_line_end = gradle_text.find("\n", code_at)
    if code_line_end < 0:
        code_line_end = len(gradle_text)
    code_line = gradle_text[code_at:code_line_end]
    code_value = code_line[len(code_marker):].strip()
    if not code_value.isdigit():
        raise PrepareError(f"Unable to read upstream versionCode from: {code_line.strip()}")
    previous_code = int(code_value)

    name_end = gradle_text.find('"', name_at + len(name_marker))
    if name_end < 0:
        raise PrepareError("Unable to read upstream versionName from app/build.gradle.kts.")
    previous_name = gradle_text[name_at + len(name_marker):name_end]
    version_code = previous_code * 100 + patch_number
    version_name = f"{upstream_tag[1:]}-harmony.{patch_number}"

    # Replace the first assignment only. Later occurrences belong to other build logic.
    updated = gradle_text[:code_at] + f"versionCode = {version_code}" + gradle_text[code_line_end:]
    name_shift = len(f"versionCode = {version_code}") - len(code_line)
    if name_at > code_at:
        name_at += name_shift
        name_end += name_shift
    updated = updated[:name_at] + f'versionName = "{version_name}"' + updated[name_end + 1:]
    return VersionBump(updated, previous_code, previous_name, version_code, version_name)


def find_assignment(text: str, marker: str, label: str) -> int:
    cursor = 0
    while True:
        at = text.find(marker, cursor)
        if at < 0:
            raise PrepareError(
                f"Unable to read upstream {label} from app/build.gradle.kts. "
                "The upstream layout changed; update the version bump in prepare_harmony_tree.py.",
            )
        line_start = text.rfind("\n", 0, at) + 1
        prefix = text[line_start:at]
        if prefix.strip() == "":
            return at
        cursor = at + len(marker)


def apply_patch_bytes(repo: Path, name: str, data: bytes, upstream_tag: str, base_tag: str) -> None:
    with tempfile.NamedTemporaryFile(prefix=f"{name}.", suffix=".patch", delete=False) as handle:
        handle.write(data)
        patch_path = Path(handle.name)
    try:
        checked = run_git(
            repo,
            ["apply", "--check", "--whitespace=nowarn", str(patch_path)],
            check=False,
            capture=True,
        )
        if checked.returncode != 0:
            verbose = run_git(
                repo,
                ["apply", "--check", "--verbose", "--whitespace=nowarn", str(patch_path)],
                check=False,
                capture=True,
            )
            detail = (verbose.stderr or verbose.stdout or checked.stderr or checked.stdout).strip()
            raise PrepareError(
                "\n".join(
                    [
                        f"Patch {name} does not apply onto {upstream_tag}.",
                        f"The patches were last refreshed against {base_tag}.",
                        "Refresh them with the procedure in .github/HARMONY_RELEASE.md, then re-run.",
                        "git apply output:",
                        detail or "(no output)",
                        "",
                        failure_context(repo),
                    ],
                ),
            )
        applied = run_git(
            repo,
            ["apply", "--whitespace=nowarn", str(patch_path)],
            check=False,
            capture=True,
        )
        if applied.returncode != 0:
            detail = (applied.stderr or applied.stdout).strip()
            raise PrepareError(f"git apply failed for {name} after a successful check.\n{detail}")
    finally:
        patch_path.unlink(missing_ok=True)


def failure_context(repo: Path) -> str:
    sections: list[str] = []
    gradle = repo / "app" / "build.gradle.kts"
    if gradle.is_file():
        interesting = relevant_lines(
            gradle,
            ("getenv", "signingConfigs", "MIHON_GITHUB_RELEASE", "versionCode", "versionName"),
        )
        sections.append("Current signing and version lines in app/build.gradle.kts:\n" + interesting)
    downloader = repo / "app/src/main/java/eu/kanade/tachiyomi/data/download/Downloader.kt"
    if downloader.is_file():
        interesting = relevant_lines(downloader, ("renameTo", "createNoMediaFile"))
        sections.append("Current rename lines in Downloader.kt:\n" + interesting)
    return "\n\n".join(sections)


def relevant_lines(path: Path, needles: tuple[str, ...]) -> str:
    lines = []
    for number, line in enumerate(path.read_text().splitlines(), start=1):
        if any(needle in line for needle in needles):
            lines.append(f"  {number}: {line}")
    return "\n".join(lines[:40]) or "  (no matching lines)"


def assert_harmony_tree(repo: Path) -> None:
    readme = repo / "README.md"
    downloader = repo / "app/src/main/java/eu/kanade/tachiyomi/data/download/Downloader.kt"
    extensions = repo / "core/common/src/main/kotlin/tachiyomi/core/common/storage/UniFileExtensions.kt"
    test = repo / "core/common/src/test/java/tachiyomi/core/common/storage/UniFileExtensionsTest.kt"
    gradle = repo / "app" / "build.gradle.kts"
    missing = [str(path.relative_to(repo)) for path in (readme, downloader, extensions, test, gradle) if not path.is_file()]
    if missing:
        raise PrepareError("Harmony tree is missing expected files: " + ", ".join(missing))

    readme_text = readme.read_text()
    if "Mihon Harmony" not in readme_text:
        raise PrepareError("README.md is missing the Harmony fork notice.")

    if "fun UniFile.renameToOrCopy" not in extensions.read_text():
        raise PrepareError("UniFileExtensions.kt does not define renameToOrCopy.")

    downloader_text = downloader.read_text()
    required_calls = (
        "tmpDir.renameToOrCopy(chapterDirname)",
        'file.renameToOrCopy("$filename.$extension")',
        'tmpFile.renameToOrCopy("$filename.${extension.extension}")',
        'zip.renameToOrCopy("$dirname.cbz")',
    )
    missing_calls = [call for call in required_calls if call not in downloader_text]
    if missing_calls:
        raise PrepareError(
            "Downloader.kt is missing Harmony rename fallbacks: " + ", ".join(missing_calls),
        )
    if "import io.mockk.any" not in test.read_text():
        raise PrepareError("UniFileExtensionsTest.kt must import io.mockk.any.")

    gradle_text = gradle.read_text()
    if UNSAFE_FILE_GETENV in gradle_text or UNSAFE_RELEASE_FLAG in gradle_text or UNSAFE_BASE64_LET in gradle_text:
        raise PrepareError(
            "app/build.gradle.kts still evaluates System.getenv() in a way that throws when a variable is unset. "
            "The signing patch did not take effect.",
        )
    if 'System.getenv("MIHON_GITHUB_RELEASE") == "true"' not in gradle_text:
        raise PrepareError("app/build.gradle.kts is missing the null-safe MIHON_GITHUB_RELEASE check.")


def apply_patches(repo: Path, patches: list[tuple[str, bytes]], upstream_tag: str, base_tag: str) -> None:
    for name, data in patches:
        print(f"Applying {name} onto {upstream_tag}", flush=True)
        apply_patch_bytes(repo, name, data, upstream_tag, base_tag)
    assert_harmony_tree(repo)


def bump_version(repo: Path, upstream_tag: str, patch_number: int) -> VersionBump:
    gradle_path = repo / "app" / "build.gradle.kts"
    bump = rewrite_versions(gradle_path.read_text(), upstream_tag, patch_number)
    gradle_path.write_text(bump.text)
    assert_harmony_tree(repo)
    return bump


def ensure_upstream_remote(repo: Path) -> None:
    remotes = run_git(repo, ["remote"], capture=True).stdout.split()
    if "upstream" not in remotes:
        run_git(repo, ["remote", "add", "upstream", UPSTREAM_URL])


def fetch_tag(repo: Path, tag: str) -> None:
    fetched = run_git(
        repo,
        ["fetch", "--no-tags", "upstream", f"refs/tags/{tag}"],
        check=False,
        capture=True,
    )
    if fetched.returncode != 0:
        detail = (fetched.stderr or fetched.stdout).strip()
        raise PrepareError(
            f"Could not fetch {tag} from {UPSTREAM_URL}.\n"
            "Pass an existing stable Mihon tag.\n"
            f"{detail}",
        )


def configure_git_identity(repo: Path) -> None:
    run_git(repo, ["config", "user.name", "github-actions[bot]"])
    run_git(repo, ["config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com"])


def commit_all(repo: Path, message: str) -> None:
    status = run_git(repo, ["status", "--porcelain"], capture=True).stdout
    if not status.strip():
        raise PrepareError(f"Nothing to commit for: {message}")
    refuse_signing_material(status)
    run_git(repo, ["add", "-A"])
    run_git(repo, ["commit", "-m", message])


def refuse_signing_material(status: str) -> None:
    for line in status.splitlines():
        path = line[3:].strip().strip('"')
        if " -> " in path:
            path = path.split(" -> ", 1)[1].strip().strip('"')
        lowered = path.lower()
        if lowered.endswith((".jks", ".keystore")) or lowered.endswith("keystore.properties"):
            raise PrepareError(f"Refusing to commit signing material: {path}")


def prepare_check(repo: Path, patches: list[tuple[str, bytes]], upstream_tag: str, base_tag: str, patch_number: int) -> PrepareResult:
    ensure_upstream_remote(repo)
    fetch_tag(repo, upstream_tag)
    worktree = Path(tempfile.mkdtemp(prefix="harmony-check-"))
    worktree.rmdir()
    try:
        added = run_git(
            repo,
            ["worktree", "add", "--detach", str(worktree), "FETCH_HEAD"],
            check=False,
            capture=True,
        )
        if added.returncode != 0:
            detail = (added.stderr or added.stdout).strip()
            raise PrepareError(f"Could not create a worktree for {upstream_tag}.\n{detail}")
        apply_patches(worktree, patches, upstream_tag, base_tag)
        bump = bump_version(worktree, upstream_tag, patch_number)
        return PrepareResult(
            upstream_tag,
            base_tag,
            bump.version_code,
            bump.version_name,
            bump.previous_code,
            bump.previous_name,
            "check",
        )
    finally:
        run_git(repo, ["worktree", "remove", "--force", str(worktree)], check=False, capture=True)
        shutil.rmtree(worktree, ignore_errors=True)


def remove_script_bytecode(repo: Path) -> None:
    """Unit tests import this module and can leave bytecode next to the script.

    --apply detaches onto upstream and then stages every working-tree change, so
    those files must be gone before the clean-tree check.
    """
    shutil.rmtree(repo / ".github" / "scripts" / "__pycache__", ignore_errors=True)


def prepare_apply(repo: Path, patches: list[tuple[str, bytes]], upstream_tag: str, base_tag: str, patch_number: int) -> PrepareResult:
    remove_script_bytecode(repo)
    status = run_git(repo, ["status", "--porcelain"], capture=True).stdout
    if status.strip():
        raise PrepareError(
            "The working tree is dirty. --apply detaches onto the upstream tag and needs a clean checkout. "
            "Use --check to validate patches without modifying this checkout.",
        )
    ensure_upstream_remote(repo)
    fetch_tag(repo, upstream_tag)
    run_git(repo, ["checkout", "--detach", "FETCH_HEAD"])
    configure_git_identity(repo)
    apply_patches(repo, patches, upstream_tag, base_tag)
    commit_all(repo, "Apply Harmony compatibility patches")
    bump = bump_version(repo, upstream_tag, patch_number)
    commit_all(repo, f"build: set {bump.version_name} version")
    return PrepareResult(
        upstream_tag,
        base_tag,
        bump.version_code,
        bump.version_name,
        bump.previous_code,
        bump.previous_name,
        "apply",
    )


def format_result(result: PrepareResult) -> str:
    lines = [
        f"Harmony {result.mode} succeeded for {result.upstream_tag}.",
        f"Patches were last refreshed against {result.base_tag}.",
        f"versionCode {result.previous_code} -> {result.version_code}",
        f"versionName {result.previous_name} -> {result.version_name}",
    ]
    if result.previous_name != result.upstream_tag[1:]:
        lines.append(
            f"Note: upstream versionName was {result.previous_name}; the release name follows the tag.",
        )
    if result.base_tag != result.upstream_tag:
        lines.append(
            "The requested tag differs from the patch base tag, and the patches still applied.",
        )
    return "\n".join(lines)


def execute(args: argparse.Namespace) -> PrepareResult:
    validate_tag(args.upstream_tag)
    validate_patch_number(args.patch_number)
    repo = args.repo.resolve()
    if not (repo / ".git").exists() and not (repo / ".git").is_file():
        raise PrepareError(f"{repo} is not a git checkout.")
    # Read the fork's patches before --apply replaces the working tree with upstream.
    base_tag = read_base_tag(repo)
    patches = load_patches(repo)
    if args.check:
        return prepare_check(repo, patches, args.upstream_tag, base_tag, args.patch_number)
    in_actions = os.environ.get("GITHUB_ACTIONS") == "true"
    if not in_actions and not args.allow_detach:
        raise PrepareError(
            "--apply detaches the current checkout onto the upstream tag and is for GitHub Actions. "
            "Use --check locally, or pass --allow-detach.",
        )
    return prepare_apply(repo, patches, args.upstream_tag, base_tag, args.patch_number)


def main(argv: list[str] | None = None) -> None:
    try:
        result = execute(parse_args(argv))
    except PrepareError as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)
    print(format_result(result))


if __name__ == "__main__":
    main()
