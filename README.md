# OpenWrt x86_64 固件自动编译

本仓库使用 GitHub Actions 编译自用 x86_64 固件。所有构建统一复用 `.github/workflows/_build-openwrt.yml`，运行环境为 Ubuntu 24.04，并检查 Clang 主版本不低于 18。

## 构建任务

| 固件 | 上游分支 | 触发方式 | Release tag |
| --- | --- | --- | --- |
| ImmortalWrt 24.10 | `immortalwrt/immortalwrt:openwrt-24.10` | 每日更新检测、手动 | `immortalwrt-24.10-x86` |
| ImmortalWrt 24.10 Docker | `immortalwrt/immortalwrt:openwrt-24.10` | 手动 | `immortalwrt-24.10-docker-x86` |
| ImmortalWrt 23.05 | `immortalwrt/immortalwrt:openwrt-23.05` | 手动 | `immortalwrt-23.05-x86` |
| LEDE | `coolsnowwolf/lede:master` | 每日更新检测、手动 | `lede-x86` |

每次成功构建都会：

- 上传 GitHub Actions Artifact；
- 发布日期前缀的 `squashfs-combined-efi.img.gz`；
- 生成并发布 `SHA256SUMS`；
- 更新对应的固定 Release tag；
- 为 ImmortalWrt 24.10 非 Docker 和 LEDE 发送企业微信、Telegram 通知。

## 固件默认设置

- 管理地址：`192.168.15.1`
- 主机名：`Momo`
- 发行标识：`OpenWrt`

## 手动编译

可在 GitHub Actions 页面运行对应 Workflow，也可使用 GitHub CLI：

```bash
gh workflow run immortalwrt-x86-24.10.yml
gh workflow run immortalwrt-x86-docker-24.10.yml
gh workflow run immortalwrt-x86-23.05.yml
gh workflow run lede-x86-Openwrt.yml
```

## 自动更新

- ImmortalWrt 24.10：每天 `12:00 UTC` 检查上游提交；
- LEDE：每天 `02:00 UTC` 检查上游提交；
- 上游提交变化后，通过 `repository_dispatch` 启动对应固件编译；
- 检测流程也可手动运行，并将 `force_build` 设为 `true` 强制触发。

自动触发使用最小权限的 `${{ github.token }}`，不需要个人访问令牌。

## 通知 Secrets

如需发送通知，在仓库 Actions secrets 中配置：

- `WECHAT_WORK_URL`
- `WECHAT_WORK_TOKEN`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

通知失败不会使已经成功生成和发布的固件被标记为编译失败。

## 维护与校验

`Maintenance Cleanup` 每月 1 日运行：每个 Workflow 至少保留最近 3 次运行，仅删除超过 90 天的额外运行，不删除 Release。

本地校验命令：

```bash
python -m unittest discover -s tests -v
go run github.com/rhysd/actionlint/cmd/actionlint@v1.7.12
sh -n scripts/*.sh scripts/sh/* scripts/lede_x86
```
