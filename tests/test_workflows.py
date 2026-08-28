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

    def test_immortalwrt_dockerd_cross_compile_skips_host_binary_copy(self):
        script = (ROOT / "scripts" / "immortalwrt_24.10_x86.sh").read_text(
            encoding="utf-8"
        )
        self.assertIn("999-cross-compile-no-host-binaries.patch", script)
        self.assertIn('"${CC:-}" == *openwrt*', script)
        self.assertNotIn('TARGET_GOOS="${GOOS:-$(go env GOOS)}"', script)

    def test_autoupdate_build_contract_uses_owned_zzz_api_channel(self):
        reusable_text = (WORKFLOWS / "_build-openwrt.yml").read_text(
            encoding="utf-8"
        )
        for required_input in (
            "autoupdate_source:",
            "autoupdate_edition:",
            "autoupdate_tag:",
            "autoupdate_profile:",
        ):
            self.assertIn(required_input, reusable_text)

        for required_behavior in (
            "/etc/openwrt_update",
            'GITHUB_LINK="https://github.com/$GITHUB_REPOSITORY"',
            'RELEASE_DOWNLOAD="https://github.com/$GITHUB_REPOSITORY/releases/download/$AUTOUPDATE_TAG"',
            'FIRMWARE_VERSION="$current_firmware"',
            'TARGET_BOARD="x86"',
            'DEVICE_MODEL="$target_profile"',
            "Publish zzz_api update channel",
            'gh api "repos/$GITHUB_REPOSITORY/releases/tags/$AUTOUPDATE_TAG" | python3 -m json.tool',
        ):
            self.assertIn(required_behavior, reusable_text)

        self.assertNotIn("/etc/openwrt_autoupdate", reusable_text)
        self.assertLess(
            reusable_text.index('gh api "repos/$GITHUB_REPOSITORY/releases/tags/$AUTOUPDATE_TAG"'),
            reusable_text.index('gh release upload "$AUTOUPDATE_TAG" "$AUTOUPDATE_DIR/zzz_api"'),
        )
        self.assertIn("group: ${{ inputs.autoupdate_tag }}", reusable_text)
        docker_wrapper = (WORKFLOWS / "immortalwrt-x86-docker-24.10.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("autoupdate_profile: x86-64-docker", docker_wrapper)

        expected_channels = {
            "immortalwrt-x86-23.05.yml": ("Immortalwrt", "23.05", "Update-immortalwrt-23.05-x86"),
            "immortalwrt-x86-24.10.yml": ("Immortalwrt", "24.10", "Update-immortalwrt-24.10-x86"),
            "immortalwrt-x86-docker-24.10.yml": ("Immortalwrt", "24.10", "Update-immortalwrt-24.10-docker-x86"),
            "lede-x86-Openwrt.yml": ("Lede", "23.05", "Update-lede-x86"),
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
        self.assertIn('GITHUB_LINK="https://github.com/$GITHUB_REPOSITORY"', combined)

        for config_name in (
            "immortalwrt_23.05_x86.config",
            "immortalwrt_24.10_x86.config",
            "immortalwrt_24.10_docker_x86.config",
            "lede_x86.config",
        ):
            config = (ROOT / "configs" / config_name).read_text(encoding="utf-8")
            self.assertIn("CONFIG_PACKAGE_luci-app-autoupdate=y", config)

    def test_upstream_checkers_track_source_and_plugin_fingerprints(self):
        reusable = (WORKFLOWS / "_check-upstreams.yml").read_text(
            encoding="utf-8"
        )
        for required in (
            "primary_ref:",
            "MINIMUM_BUILD_INTERVAL_MINUTES",
            "latest_success_epoch",
            "Skipping rebuild during cooldown",
            "upstream_refs:",
            "build_targets:",
            "configuration_paths:",
            "fingerprint=",
            "releases/tags/",
            "build-state-",
            "client_payload[source_commit]",
            "client_payload[fingerprint]",
            "client_payload[target]",
        ):
            self.assertIn(required, reusable)
        self.assertNotIn("actions/cache", reusable)
        self.assertIn("display_title", reusable)
        self.assertIn("queued", reusable)
        self.assertIn("in_progress", reusable)
        self.assertIn("pending", reusable)
        self.assertIn("waiting", reusable)
        self.assertIn("requested", reusable)
        self.assertNotIn("git tag", reusable)
        self.assertNotIn('"$GITHUB_SHA" > "$state_file"', reusable)

        expected = {
            "Update Checker_lede.yml": (
                ("coolsnowwolf/lede:master", "fw876/helloworld:master"),
                ("lede-x86|lede-updated|Update-lede-x86|lede-x86-Openwrt.yml",),
                ("configs/lede_x86.config", "scripts/lede_x86"),
            ),
            "Update Checker_immortalwrt.yml": (
                (
                    "immortalwrt/immortalwrt:openwrt-24.10",
                    "Openwrt-Passwall/openwrt-passwall:main",
                ),
                (
                    "immortalwrt-24.10-x86|immortalwrt-updated|Update-immortalwrt-24.10-x86|immortalwrt-x86-24.10.yml",
                    "immortalwrt-24.10-docker-x86|immortalwrt-docker-updated|Update-immortalwrt-24.10-docker-x86|immortalwrt-x86-docker-24.10.yml",
                ),
                (
                    "configs/immortalwrt_24.10_x86.config",
                    "configs/immortalwrt_24.10_docker_x86.config",
                ),
            ),
        }
        for workflow_name, (tracked_refs, targets, configuration_paths) in expected.items():
            with self.subTest(workflow=workflow_name):
                text = (WORKFLOWS / workflow_name).read_text(encoding="utf-8")
                self.assertIn("uses: ./.github/workflows/_check-upstreams.yml", text)
                for tracked_ref in tracked_refs:
                    self.assertIn(tracked_ref, text)
                for target in targets:
                    self.assertIn(target, text)
                for configuration_path in configuration_paths:
                    self.assertIn(configuration_path, text)

    def test_builds_checkout_detected_commit_and_record_success(self):
        reusable_text = (WORKFLOWS / "_build-openwrt.yml").read_text(
            encoding="utf-8"
        )
        for required in (
            "source_commit:",
            "build_fingerprint:",
            'git fetch --depth 1 origin "$SOURCE_COMMIT"',
            'git checkout --detach "$SOURCE_COMMIT"',
            "Record successful upstream build",
            "build-state-",
            'gh release upload "$AUTOUPDATE_TAG" "$state_file" --clobber',
        ):
            self.assertIn(required, reusable_text)

        self.assertLess(
            reusable_text.index("Publish zzz_api update channel"),
            reusable_text.index("Record successful upstream build"),
        )

    def test_only_supported_targets_receive_automatic_dispatches(self):
        lede = (WORKFLOWS / "lede-x86-Openwrt.yml").read_text(encoding="utf-8")
        standard = (WORKFLOWS / "immortalwrt-x86-24.10.yml").read_text(
            encoding="utf-8"
        )
        docker = (WORKFLOWS / "immortalwrt-x86-docker-24.10.yml").read_text(
            encoding="utf-8"
        )
        legacy = (WORKFLOWS / "immortalwrt-x86-23.05.yml").read_text(
            encoding="utf-8"
        )

        self.assertIn("repository_dispatch", lede)
        self.assertIn("github.event.client_payload.target == 'lede-x86'", lede)
        self.assertIn("repository_dispatch", standard)
        self.assertIn(
            "github.event.client_payload.target == 'immortalwrt-24.10-x86'",
            standard,
        )
        self.assertIn("repository_dispatch", docker)
        self.assertIn(
            "github.event.client_payload.target == 'immortalwrt-24.10-docker-x86'",
            docker,
        )
        self.assertNotIn("repository_dispatch", legacy)

        for text in (lede, standard, docker):
            self.assertIn("source_commit: ${{ github.event.client_payload.source_commit }}", text)
            self.assertIn(
                "build_fingerprint: ${{ github.event.client_payload.fingerprint }}",
                text,
            )
            self.assertIn(
                "${{ github.event.client_payload.fingerprint || github.run_id }}",
                text,
            )

    def test_lede_preserves_local_router_function_packages(self):
        config = (ROOT / "configs" / "lede_x86.config").read_text(
            encoding="utf-8"
        )
        required_packages = (
            "6rd",
            "6to4",
            "btrfs-progs",
            "kmod-fs-btrfs",
            "luci-app-filemanager",
            "luci-i18n-filemanager-zh-cn",
            "mihomo-meta",
            "openssh-sftp-server",
            "snmpd",
        )
        for package in required_packages:
            with self.subTest(package=package):
                self.assertIn(f"CONFIG_PACKAGE_{package}=y", config)

        self.assertNotIn("CONFIG_PACKAGE_auto-scripts=y", config)

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
