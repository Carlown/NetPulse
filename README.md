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
| 📈 **Monitoring** | Real-time CPU / memory / network speed curves, smooth wheel zoom, double-click to resume live scrolling |
| ⚙️ **Settings** | Dark / light theme, instant Chinese-English switching, default parameters, audit log export |

### Security & Compliance

- **First-launch disclaimer**: must read and accept before use
- **Authorized target list**: each target requires separate authorization (with note & timestamp)
- **High-rate double confirmation**: re-confirmation dialog above 500 QPS
- **Token-bucket rate limiting**: shared across threads, never exceeds the configured rate
- **Audit log**: start / stop / authorization events persisted to disk

### Install (End Users)

1. Go to the [**Releases**](https://github.com/Carlown/NetPulse/releases/tag/v1.0.0) page
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
# Output: installer/NetPulse-Setup-1.0.0.exe
```

### Tech Stack

- **UI**: PySide6 + QFluentWidgets (Fluent Design)
- **Charts**: pyqtgraph (high-performance real-time curves)
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
| 📈 **性能监控** | CPU / 内存 / 网速实时曲线，鼠标滚轮平滑缩放，双击恢复实时滚动 |
| ⚙️ **设置** | 深色 / 浅色主题，中英双语即时切换，默认参数配置，审计日志导出 |

### 安全与合规设计

- **首次启动免责声明**：必须阅读并同意方可使用
- **目标授权清单**：每个测试目标需单独确认授权（含备注与时间戳）
- **高速率二次确认**：速率超过 500 QPS 时弹出再次确认
- **令牌桶限速**：多线程共享令牌桶，严格不超设定速率
- **审计日志**：开始 / 停止 / 授权等关键操作全部落盘

### 安装（普通用户）

1. 进入 [**Releases**](https://github.com/Carlown/NetPulse/releases/tag/v1.0.0) 发布页
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
# 产物位于 installer/NetPulse-Setup-1.0.0.exe
```

### 技术栈

- **界面**：PySide6 + QFluentWidgets（Fluent Design）
- **图表**：pyqtgraph（实时高性能曲线）
- **系统监控**：psutil
- **网络**：requests / socket / icmplib
- **限速**：自研令牌桶算法
- **存储**：JSON（`%APPDATA%\NetPulse`）
- **打包**：PyInstaller + Inno Setup 7

---

## License / 许可证

MIT License
