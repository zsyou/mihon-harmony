#!/usr/bin/env python3
"""Unit tests for the Harmony tree preparer. Run from the repository root."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / ".github" / "scripts" / "prepare_harmony_tree.py"


def load_prepare():
    spec = importlib.util.spec_from_file_location("prepare_harmony_tree", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


prepare = load_prepare()


class RewriteVersionsTest(unittest.TestCase):
    def test_replaces_first_assignments_only(self) -> None:
        source = '\n'.join(
            [
                "android {",
                "    defaultConfig {",
                '        versionCode = 38',
                '        versionName = "0.21.2"',
                "    }",
                "}",
                'val versionName = output.versionName.get()',
                '        versionName = "untouched"',
                "",
            ],
        )
        bump = prepare.rewrite_versions(source, "v0.21.2", 1)
        self.assertEqual(3801, bump.version_code)
        self.assertEqual("0.21.2-harmony.1", bump.version_name)
        self.assertEqual(38, bump.previous_code)
        self.assertIn('versionName = "0.21.2-harmony.1"', bump.text)
        self.assertIn('versionName = "untouched"', bump.text)
        self.assertNotIn('versionName = "0.21.2"\n', bump.text)
        self.assertEqual(1, bump.text.count("versionCode = 3801"))

    def test_missing_version_mentions_the_script(self) -> None:
        with self.assertRaises(prepare.PrepareError) as caught:
            prepare.rewrite_versions("no versions here\n", "v0.21.2", 1)
        self.assertIn("versionCode", str(caught.exception))
        self.assertIn("prepare_harmony_tree.py", str(caught.exception))

    def test_patch_number_is_base_ten(self) -> None:
        source = 'versionCode = 8\nversionName = "0.1.0"\n'
        bump = prepare.rewrite_versions(source, "v0.1.0", 8)
        self.assertEqual(808, bump.version_code)
        self.assertEqual("0.1.0-harmony.8", bump.version_name)


class PatchContractTest(unittest.TestCase):
    def test_series_and_base_tag_exist(self) -> None:
        patches = prepare.load_patches(REPO)
        names = [name for name, _data in patches]
        self.assertEqual(["harmony.patch", "signing.patch"], names)
        self.assertEqual("v0.21.2", prepare.read_base_tag(REPO))

    def test_signing_patch_does_not_reintroduce_unsafe_getenv(self) -> None:
        _name, data = prepare.load_patches(REPO)[1]
        added = "\n".join(
            line[1:]
            for line in data.decode().splitlines()
            if line.startswith("+") and not line.startswith("+++")
        )
        self.assertNotIn("file(System.getenv(", added)
        self.assertNotIn('.toBoolean()', added)
        self.assertNotIn(".let(Base64::decode)", added)
        self.assertIn('System.getenv("MIHON_GITHUB_RELEASE") == "true"', added)

    def test_download_patch_keeps_rename_fallback(self) -> None:
        _name, data = prepare.load_patches(REPO)[0]
        text = data.decode()
        self.assertIn("fun UniFile.renameToOrCopy", text)
        self.assertIn("tmpDir.renameToOrCopy(chapterDirname)", text)
        self.assertIn('file.renameToOrCopy("$filename.$extension")', text)
        self.assertIn("import io.mockk.any", text)


class ApplyFailureTest(unittest.TestCase):
    def test_failed_apply_names_the_patch_and_refresh_doc(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            subprocess.check_call(["git", "init", "-b", "main"], cwd=repo)
            subprocess.check_call(["git", "config", "user.email", "test@example.com"], cwd=repo)
            subprocess.check_call(["git", "config", "user.name", "test"], cwd=repo)
            gradle = repo / "app"
            gradle.mkdir()
            (gradle / "build.gradle.kts").write_text("versionCode = 1\n")
            subprocess.check_call(["git", "add", "app/build.gradle.kts"], cwd=repo)
            subprocess.check_call(["git", "commit", "-m", "init"], cwd=repo)
            bad = """diff --git a/app/build.gradle.kts b/app/build.gradle.kts
--- a/app/build.gradle.kts
+++ b/app/build.gradle.kts
@@ -1 +1 @@
-versionCode = 99
+versionCode = 100
"""
            with self.assertRaises(prepare.PrepareError) as caught:
                prepare.apply_patch_bytes(repo, "signing.patch", bad.encode(), "v9.9.9", "v0.21.2")
            message = str(caught.exception)
            self.assertIn("signing.patch", message)
            self.assertIn("v9.9.9", message)
            self.assertIn("v0.21.2", message)
            self.assertIn(".github/HARMONY_RELEASE.md", message)


class ValidationTest(unittest.TestCase):
    def test_rejects_bad_tag_and_patch_number(self) -> None:
        with self.assertRaises(prepare.PrepareError):
            prepare.validate_tag("v0.21")
        with self.assertRaises(prepare.PrepareError):
            prepare.validate_tag("0.21.2")
        with self.assertRaises(prepare.PrepareError):
            prepare.validate_patch_number(0)
        with self.assertRaises(prepare.PrepareError):
            prepare.validate_patch_number(100)

    def test_refuses_keystore_paths(self) -> None:
        with self.assertRaises(prepare.PrepareError):
            prepare.refuse_signing_material("?? secrets/mihon-harmony.jks\n")
        with self.assertRaises(prepare.PrepareError):
            prepare.refuse_signing_material("A  keystore.properties\n")


if __name__ == "__main__":
    unittest.main()
