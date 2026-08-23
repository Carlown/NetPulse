# NetPulse

**Legally-Authorized Network Stress Testing & Performance Monitoring Tool**

**合法授权网络压力测试与性能监控工具**

[![Platform](https://img.shields.io/badge/Platform-Windows-blue)](https://github.com) [![Python](https://img.shields.io/badge/Python-3.10+-green)](https://www.python.org) [![License](https://img.shields.io/badge/License-MIT-orange)](LICENSE)

---

## 🇬🇧 English

### Introduction

NetPulse is a Windows desktop application for network stress testing and performance monitoring, built with **Python + PySide6 + QFluentWidgets** following the **Windows 11 Fluent Design** language. A **legal-compliance framework** is built in: every test target must pass an authorization confirmation first, rate and concurrency are capped by a token bucket, and all operations are written to an audit log.

> ⚠️ **Disclaimer**: This tool is for learning, research, and performance testing **with written authorization only**. Stress-testing unauthorized targets is illegal; the user bears full legal responsibility.

### Features

| Module | Description |
|--------|-------------|
| 📊 **Dashboard** | Real-time CPU / memory / network cards and trend charts |
| 🔥 **Stress Test** | HTTP / HTTPS / TCP / UDP / ICMP protocols; live QPS, latency percentiles (P50/P90/P99), **total sent traffic** (auto-scaled B/KB/MB/GB/TB), classified failure reasons |
| 🤝 **Collaborative Test** | Host / node modes, one-click invite code copy, IPv4+IPv6 dual-stack listening, UPnP automatic port mapping (Internet collaboration supported) |
| 🧩 **Plugin System** | Full plugin platform: local plugin management (enable/disable/reload), **built-in plugin marketplace**, one-click install & update, custom icons, and **one-click publish/unpublish to GitHub** — no manual token required |
| 📈 **Monitoring** | Real-time CPU / memory / network speed curves, smooth wheel zoom, double-click to resume live scrolling |
| ⚙️ **Settings** | Dark / light theme, Chinese-English language selection (restart to fully apply), default parameters, audit log export |

### Security & Compliance

- **First-launch disclaimer**: must read and accept before use
- **Authorized target list**: each target requires separate authorization (with note & timestamp)
- **High-rate double confirmation**: re-confirmation dialog above 500 QPS
- **Token-bucket rate limiting**: shared across threads, never exceeds the configured rate
- **Audit log**: start / stop / authorization events persisted to disk

### Plugin System (New in v1.1.0)

NetPulse v1.1.0 ships with a full plugin platform — extend the app with your own features:

- **Plugin Marketplace**: browse, search, install and update community plugins with one click (integrity-verified via SHA-256)
- **Local Plugin Management**: enable / disable / reload / remove plugins instantly; metadata and icons stay visible when disabled
- **One-click Publish**: publish your own plugins to the marketplace directly from the app via GitHub OAuth device flow — no manual token generation. Publishes go live automatically (auto-merge workflow, no manual review)
- **One-click Unpublish**: plugin authors can remove their own listings at any time
- **Custom Icons**: plugin authors can upload a PNG/JPG icon (also supports built-in Fluent icons); auto-generated colored initial badge as fallback
- **Rich Plugin API**: register custom protocols, exporters, target providers and metrics subscriptions; respond to test lifecycle events
- **Guarded lifecycle**: plugin load/page errors are logged and isolated where possible; plugins still run in-process and must be trusted

Check the built-in `example_hello.py` / `example_dns.py` plugins in the plugin folder for API usage examples. **Want to write your own?** See the [**Plugin Development Guide**](PLUGINS.md) — a minimal plugin is about 10 lines of Python.

### Install (End Users)

1. Go to the [**Releases**](https://github.com/Carlown/NetPulse/releases/latest) page
2. Download the latest `NetPulse-Setup-x.x.x.exe`
3. Run the installer and follow the wizard (desktop shortcut optional)
4. Launch from the Start menu or desktop

### Run from Source (Developers)

```bash
git clone https://github.com/Carlown/NetPulse.git
cd NetPulsePy
pip install -r requirements.txt
python main.py
```

### Build from Source

```bash
# 1. Build single-file exe
pyinstaller --name NetPulse --icon app.ico --windowed --onefile --add-data "app.ico;." main.py

# 2. Create the installer (requires Inno Setup 7)
ISCC.exe installer.iss
# Output: installer/NetPulse-Setup-1.1.7.exe
```

### Tech Stack

- **UI**: PySide6 + QFluentWidgets (Fluent Design)
- **Charts**: PySide6 QtCharts (native real-time curves)
- **System monitoring**: psutil
- **Networking**: requests / socket / icmplib
- **Rate limiting**: custom token-bucket algorithm
- **Storage**: JSON (`%APPDATA%\NetPulse`)
- **Packaging**: PyInstaller + Inno Setup 7

---

## 🇨🇳 中文说明

### 简介

NetPulse 是一款 Windows 桌面端的网络压力测试与性能监控工具，基于 **Python + PySide6 + QFluentWidgets** 构建，采用 **Windows 11 Fluent Design** 设计语言。工具内置**法律合规框架**：所有测试目标必须先通过授权确认，速率与并发受令牌桶限速保护，全部操作写入审计日志。

> ⚠️ **免责声明**：本工具仅供学习研究与获得书面授权的性能测试使用。对未授权目标发起压力测试属于违法行为，使用者需自行承担全部法律责任。

### 功能特性

| 模块 | 说明 |
|------|------|
| 📊 **仪表盘** | CPU / 内存 / 网络实时监控卡片与趋势图 |
| 🔥 **压力测试** | HTTP / HTTPS / TCP / UDP / ICMP 五种协议，实时 QPS、延迟分位数（P50/P90/P99）、**总发送流量统计**（自动换算 B/KB/MB/GB/TB）、失败原因分类统计 |
| 🤝 **协同测试** | 主控邀请 / 节点加入模式，邀请码一键复制，IPv4+IPv6 双栈监听，UPnP 自动端口映射（支持外网协同） |
| 🧩 **插件系统** | 完整插件平台：本地插件管理（启用/禁用/重载）、**内置插件市场**、一键安装与更新、自定义图标、**一键发布/下架到 GitHub** —— 无需手动生成令牌 |
| 📈 **性能监控** | CPU / 内存 / 网速实时曲线，鼠标滚轮平滑缩放，双击恢复实时滚动 |
| ⚙️ **设置** | 深色 / 浅色主题，中英双语选择（重启后完整生效），默认参数配置，审计日志导出 |

### 安全与合规设计

- **首次启动免责声明**：必须阅读并同意方可使用
- **目标授权清单**：每个测试目标需单独确认授权（含备注与时间戳）
- **高速率二次确认**：速率超过 500 QPS 时弹出再次确认
- **令牌桶限速**：多线程共享令牌桶，严格不超设定速率
- **审计日志**：开始 / 停止 / 授权等关键操作全部落盘

### 插件系统（v1.1.0 新增）

NetPulse v1.1.0 内置完整插件平台，可以自由扩展功能：

- **插件市场**：浏览、搜索、一键安装和更新社区插件（SHA-256 完整性校验）
- **本地插件管理**：即时启用 / 禁用 / 重载 / 删除插件；禁用后图标和元数据保持显示
- **一键发布**：通过 GitHub OAuth 设备授权，直接在软件内把你的插件发布到市场 —— 无需手动生成令牌，发布后自动上架（自动合并工作流，无需人工审核）
- **一键下架**：插件作者可随时下架自己发布的插件
- **自定义图标**：发布时可上传 PNG/JPG 图标（也支持内置 Fluent 图标）；未上传时自动生成彩色首字徽章
- **丰富的插件 API**：注册自定义协议、导出器、目标源和指标订阅；响应测试生命周期事件
- **受保护生命周期**：插件加载/页面错误会尽量隔离并记录；插件仍在进程内运行，仅应安装可信插件

插件目录内置 `example_hello.py` / `example_dns.py` 示例插件，可参考其 API 用法。**想自己写一个？** 看 [**插件开发指南**](PLUGINS.md) —— 最小插件只要 10 行 Python。

### 安装（普通用户）

1. 进入 [**Releases**](https://github.com/Carlown/NetPulse/releases/latest) 发布页
2. 下载最新的 `NetPulse-Setup-x.x.x.exe`
3. 双击运行，按向导完成安装（可勾选桌面快捷方式）
4. 安装后从开始菜单或桌面启动

### 从源码运行（开发者）

```bash
git clone https://github.com/Carlown/NetPulse.git
cd NetPulsePy
pip install -r requirements.txt
python main.py
```

### 从源码打包

```bash
# 1. 生成单文件 exe
pyinstaller --name NetPulse --icon app.ico --windowed --onefile --add-data "app.ico;." main.py

# 2. 制作安装程序（需安装 Inno Setup 7）
ISCC.exe installer.iss
# 产物位于 installer/NetPulse-Setup-1.1.7.exe
```

### 技术栈

- **界面**：PySide6 + QFluentWidgets（Fluent Design）
- **图表**：PySide6 QtCharts（原生实时曲线）
- **系统监控**：psutil
- **网络**：requests / socket / icmplib
- **限速**：自研令牌桶算法
- **存储**：JSON（`%APPDATA%\NetPulse`）
- **打包**：PyInstaller + Inno Setup 7

---

## License / 许可证

MIT License
