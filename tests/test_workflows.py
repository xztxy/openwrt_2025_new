from pathlib import Path
import re
import unittest

import yaml


ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"
BUILD_WRAPPERS = (
    "immortalwrt-x86-23.05.yml",
    "immortalwrt-x86-24.10.yml",
    "immortalwrt-x86-docker-24.10.yml",
    "lede-x86-Openwrt.yml",
)
SHELL_SCRIPTS = (
    ROOT / "scripts" / "immortalwrt_23.05_x86.sh",
    ROOT / "scripts" / "immortalwrt_24.10_x86.sh",
    ROOT / "scripts" / "lede_x86",
    ROOT / "scripts" / "sh" / "immortalwrt_diy-part1.sh",
    ROOT / "scripts" / "sh" / "lede_diy-part1",
)


class WorkflowContractTests(unittest.TestCase):
    def test_all_workflows_are_valid_yaml(self):
        for path in sorted(WORKFLOWS.glob("*.yml")):
            with self.subTest(path=path.name):
                yaml.safe_load(path.read_text(encoding="utf-8"))

    def test_builds_use_one_reusable_ubuntu_2404_workflow(self):
        reusable = WORKFLOWS / "_build-openwrt.yml"
        self.assertTrue(reusable.is_file())
        reusable_text = reusable.read_text(encoding="utf-8")
        self.assertIn("runs-on: ubuntu-24.04", reusable_text)
        self.assertNotIn("full-upgrade", reusable_text)
        self.assertIn("depends_ubuntu_2404", reusable_text)

        for name in BUILD_WRAPPERS:
            with self.subTest(workflow=name):
                text = (WORKFLOWS / name).read_text(encoding="utf-8")
                self.assertIn("uses: ./.github/workflows/_build-openwrt.yml", text)
                self.assertNotIn("runs-on: ubuntu-22.04", text)
    def test_build_wrappers_pass_explicit_target_metadata(self):
        for name in BUILD_WRAPPERS:
            with self.subTest(workflow=name):
                text = (WORKFLOWS / name).read_text(encoding="utf-8")
                self.assertIn("target_board: x86", text)
                self.assertIn("target_subtarget: '64'", text)


    def test_workflows_do_not_track_mutable_action_branches(self):
        mutable_ref = re.compile(r"uses:\s+[^\s]+@(main|master)(?:\s|$)", re.MULTILINE)
        for path in sorted(WORKFLOWS.glob("*.yml")):
            with self.subTest(path=path.name):
                text = path.read_text(encoding="utf-8")
                self.assertIsNone(mutable_ref.search(text))

    def test_workflows_use_scoped_permissions_and_builtin_token(self):
        for path in sorted(WORKFLOWS.glob("*.yml")):
            with self.subTest(path=path.name):
                text = path.read_text(encoding="utf-8")
                self.assertIn("permissions:", text)
                self.assertNotIn("secrets.MY_GITHUB_TOKEN", text)

    def test_ubuntu_2404_dependency_manifest_replaces_2204_manifest(self):
        new_manifest = ROOT / "depends_ubuntu_2404"
        self.assertTrue(new_manifest.is_file())
        self.assertFalse((ROOT / "depends_ubuntu_2204").exists())
        packages = set(new_manifest.read_text(encoding="utf-8").split())
        for package in ("clang", "lld", "llvm", "libncurses-dev", "zstd"):
            self.assertIn(package, packages)

    def test_customization_scripts_fail_fast(self):
        for path in SHELL_SCRIPTS:
            with self.subTest(path=path.relative_to(ROOT).as_posix()):
                lines = path.read_text(encoding="utf-8").splitlines()
                self.assertEqual(lines[0], "#!/usr/bin/env bash")
                self.assertIn("set -Eeuo pipefail", lines[:5])
    def test_customization_scripts_reference_live_plugin_sources(self):
        scripts = "\n".join(path.read_text(encoding="utf-8") for path in SHELL_SCRIPTS)
        self.assertNotIn(
            "-b main https://github.com/sirpdboy/luci-theme-kucat", scripts
        )
        self.assertNotIn(
            "-b main https://github.com/sirpdboy/luci-app-kucat-config", scripts
        )
        self.assertNotIn(
            "-b master https://github.com/sirpdboy/luci-app-netdata", scripts
        )
        self.assertNotIn("github.com/xiaorouji/openwrt-passwall", scripts)
        self.assertIn(
            "github.com/Openwrt-Passwall/openwrt-passwall-packages", scripts
        )
        self.assertIn("github.com/Openwrt-Passwall/openwrt-passwall", scripts)


    def test_naiveproxy_remains_enabled_with_modern_toolchain(self):
        config = (ROOT / "configs" / "immortalwrt_24.10_x86.config").read_text(
            encoding="utf-8"
        )
        self.assertIn("CONFIG_PACKAGE_naiveproxy=y", config)


if __name__ == "__main__":
    unittest.main()
