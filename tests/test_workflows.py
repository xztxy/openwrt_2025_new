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


    def test_validation_runs_for_every_build_input(self):
        validate_text = (WORKFLOWS / "validate.yml").read_text(encoding="utf-8")
        for path in (
            ".github/workflows/**",
            "scripts/**",
            "configs/**",
            "depends_ubuntu_2404",
            "tests/**",
        ):
            with self.subTest(path=path):
                self.assertEqual(validate_text.count(f"- '{path}'"), 2)


    def test_workflows_do_not_track_mutable_action_branches(self):
        mutable_ref = re.compile(r"uses:\s+[^\s]+@(main|master)(?:\s|$)", re.MULTILINE)
        for path in sorted(WORKFLOWS.glob("*.yml")):
            with self.subTest(path=path.name):
                text = path.read_text(encoding="utf-8")
                self.assertIsNone(mutable_ref.search(text))

    def test_external_actions_are_pinned_to_commits(self):
        action_ref = re.compile(r"uses:\s+([^\s]+)@([^\s#]+)")
        for path in sorted(WORKFLOWS.glob("*.yml")):
            text = path.read_text(encoding="utf-8")
            for action, ref in action_ref.findall(text):
                with self.subTest(path=path.name, action=action):
                    self.assertRegex(ref, r"^[0-9a-f]{40}$")

    def test_build_does_not_depend_on_external_openwrt_cache_action(self):
        reusable_text = (WORKFLOWS / "_build-openwrt.yml").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("HiGarfield/cachewrtbuild", reusable_text)

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


        active_script_lines = "\n".join(
            line
            for line in scripts.splitlines()
            if not line.lstrip().startswith("#")
        )
        self.assertNotIn("luci-app-bypass", active_script_lines)
        self.assertNotIn("lua-maxminddb", active_script_lines)

    def test_autoupdate_build_contract_uses_owned_zzz_api_channel(self):
        reusable_text = (WORKFLOWS / "_build-openwrt.yml").read_text(
            encoding="utf-8"
        )
        for required_input in (
            "autoupdate_source:",
            "autoupdate_edition:",
            "autoupdate_tag:",
        ):
            self.assertIn(required_input, reusable_text)

        for required_behavior in (
            "/etc/openwrt_autoupdate",
            "GITHUB_API=\"zzz_api\"",
            "CURRENT_FIRMWARE=",
            "COMPILE_DATE=",
            "Publish zzz_api update channel",
            'gh api "repos/$GITHUB_REPOSITORY/releases/tags/$AUTOUPDATE_TAG"',
        ):
            self.assertIn(required_behavior, reusable_text)

        expected_channels = {
            "immortalwrt-x86-23.05.yml": ("Immortalwrt", "23.05", "Update-x86"),
            "immortalwrt-x86-24.10.yml": ("Immortalwrt", "24.10", "Update-x86"),
            "immortalwrt-x86-docker-24.10.yml": ("Immortalwrt", "24.10", "Update-x86"),
            "lede-x86-Openwrt.yml": ("Lede", "23.05", "Update-x86"),
        }
        for name, (source, edition, tag) in expected_channels.items():
            with self.subTest(workflow=name):
                text = (WORKFLOWS / name).read_text(encoding="utf-8")
                self.assertIn(f"autoupdate_source: {source}", text)
                self.assertIn(f"autoupdate_edition: '{edition}'", text)
                self.assertIn(f"autoupdate_tag: {tag}", text)

    def test_autoupdate_dependencies_are_owned_and_not_numeric_upstream(self):
        relevant_files = [
            WORKFLOWS / "_build-openwrt.yml",
            ROOT / "scripts" / "immortalwrt_23.05_x86.sh",
            ROOT / "scripts" / "immortalwrt_24.10_x86.sh",
            ROOT / "scripts" / "lede_x86",
        ]
        combined = "\n".join(path.read_text(encoding="utf-8") for path in relevant_files)

        self.assertNotIn("github.com/281677160/", combined)
        self.assertNotIn("github.com/libntdll/luci-app-autoupdate", combined)
        self.assertIn("github.com/xztxy/luci-app-autoupdate", combined)
        self.assertIn("91894e1a82d7cf226fff429a6b880812ad79e03d", combined)
        self.assertIn('GITHUB_REPOSITORY_URL="https://github.com/$GITHUB_REPOSITORY"', combined)

        for config_name in (
            "immortalwrt_23.05_x86.config",
            "immortalwrt_24.10_x86.config",
            "immortalwrt_24.10_docker_x86.config",
            "lede_x86.config",
        ):
            config = (ROOT / "configs" / config_name).read_text(encoding="utf-8")
            self.assertIn("CONFIG_PACKAGE_luci-app-autoupdate=y", config)

    def test_notifications_are_best_effort_and_accept_full_wecom_urls(self):
        reusable_text = (WORKFLOWS / "_build-openwrt.yml").read_text(
            encoding="utf-8"
        )
        self.assertNotIn('"http://${WECHAT_WORK_URL}/push"', reusable_text)

        workflow = yaml.safe_load(reusable_text)
        notification_steps = {
            step["name"]: step
            for step in workflow["jobs"]["build"]["steps"]
            if step.get("name", "").startswith("Notify ")
        }
        self.assertTrue(notification_steps["Notify WeCom"]["continue-on-error"])
        self.assertTrue(notification_steps["Notify Telegram"]["continue-on-error"])

    def test_immortalwrt_2305_avoids_fileassistant_package_conflict(self):
        config = (ROOT / "configs" / "immortalwrt_23.05_x86.config").read_text(
            encoding="utf-8"
        )
        self.assertIn("CONFIG_PACKAGE_luci-app-advanced=y", config)
        self.assertNotIn("CONFIG_PACKAGE_luci-app-fileassistant=y", config)


    def test_lede_disables_autosamba_when_using_samba4(self):
        config = (ROOT / "configs" / "lede_x86.config").read_text(
            encoding="utf-8"
        )
        self.assertIn("CONFIG_PACKAGE_luci-app-samba4=y", config)
        self.assertIn("# CONFIG_PACKAGE_autosamba is not set", config)


    def test_naiveproxy_remains_enabled_with_modern_toolchain(self):
        config = (ROOT / "configs" / "immortalwrt_24.10_x86.config").read_text(
            encoding="utf-8"
        )
        self.assertIn("CONFIG_PACKAGE_naiveproxy=y", config)


if __name__ == "__main__":
    unittest.main()
