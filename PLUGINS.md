# NetPulse Plugin Development Guide

NetPulse plugins are plain Python files. If you can write Python, you can extend NetPulse — add custom test protocols, new pages, report exporters and more.

> Full working examples live in the [`marketplace/`](marketplace/) folder: `example_hello.py` (UI page + config), `example_dns.py` (custom protocol + target provider), `random_target.py` (simple tool page).

---

## Quick Start

A minimal plugin is ~10 lines. Save this as `my_plugin.py`:

```python
# -*- coding: utf-8 -*-

class Plugin(NetPulsePlugin):
    name = "My First Plugin"          # or ("中文名", "English name")
    version = "1.0"
    author = "you"
    description = "Does something useful"

    def on_load(self, ctx):
        self._ctx = ctx               # host context

    def create_widget(self, parent):
        from PySide6.QtWidgets import QWidget, QVBoxLayout
        from qfluentwidgets import StrongBodyLabel
        w = QWidget(parent)
        QVBoxLayout(w).addWidget(StrongBodyLabel("Hello NetPulse!"))
        return w                       # becomes a page in the main window
```

Drop it into the plugins folder and restart (or reload from the plugin page):

```
%APPDATA%\NetPulse\plugins\my_plugin.py
```

## Plugin Format

| Format | Layout | Plugin ID |
|--------|--------|-----------|
| Single file | `xxx.py` | `xxx` |
| Folder | `xxx/main.py` (+ assets) | `xxx` |

- The plugin ID equals the file/folder name — stable and unique.
- Define a class named `Plugin` inheriting `NetPulsePlugin`. The base class is injected into your module namespace — **no import needed**.
- Either format may optionally define other classes/helpers freely.

## Metadata

Class attributes on `Plugin`:

```python
class Plugin(NetPulsePlugin):
    name        = ("你好插件", "Hello Plugin")   # (中文, English) tuple = bilingual
    version     = "1.2"                          # compared for marketplace updates
    author      = "Your Name"
    description = ("一句话简介", "One-line summary")
    icon        = "SPEED_HIGH"                   # FluentIcon name, or "icon.png" (relative path)
    category    = "tool"                         # tool / protocol / ui / other (optional, auto-detected)
```

- Every `name` / `description` / label field accepts a `(中文, English)` tuple and follows the UI language automatically.
- `icon` may be a built-in [FluentIcon](https://qfluentwidgets.com/pages/icons/) name (e.g. `"SPEED_HIGH"`, `"CLOUD"`) or a relative image path.
- `category` sets the marketplace filter type: `tool` (utilities), `protocol` (custom test protocols), `ui` (pages/widgets) or `other`. If omitted, it is auto-detected from what the plugin registers.

## Lifecycle Hooks

```python
class Plugin(NetPulsePlugin):
    def on_load(self, ctx): ...        # init resources, register extensions
    def on_unload(self): ...           # release resources (registered items auto-cleaned)
    def create_widget(self, parent): ...  # return a QWidget = own nav page (or None)
    def on_test_start(self, configs): ...  # configs: list of target dicts
    def on_test_end(self, report): ...     # report: summary dict
```

## PluginContext (`ctx`)

```python
ctx.plugin_id      # this plugin's ID
ctx.app_version    # host app version
ctx.logger         # shared logger
ctx.tr(zh, en)     # translate at runtime

ctx.get("key")           # plugin-private config (auto-persisted, namespaced by plugin ID)
ctx.set("key", value)
```

## Extension APIs

All registered in `on_load`:

### Custom test protocol

Adds an entry to the protocol dropdown in the stress test page.

```python
def my_handler(config, timeout, state):
    # Runs in worker threads — must be thread-safe & reentrant.
    # config: {"target", "port", "protocol", "packet_size", ...}
    # state:  per-worker dict, reuse it for sockets / connections
    # return: (ok: bool, err: str|None, nbytes_sent: int)
    ...

ctx.register_protocol("MYPROTO", my_handler)
```

### Report exporter

Adds an entry to the "Export report" menu.

```python
def export(report, path):          # main thread; write report dict to path
    ...

ctx.register_exporter(("导出 XML", "Export XML"), export)
```

### Target provider

Adds a "plugin targets" button that fills the target list.

```python
def targets():                     # main thread; return list of address strings
    return ["223.5.5.5", "8.8.8.8"]

ctx.register_target_provider(("常用 DNS", "Common DNS"), targets)
```

### Live metrics subscription

```python
def on_metrics(snapshot):          # main thread, ~every 500ms during a test
    print(snapshot["qps"], snapshot["avg"])

# snapshot fields: running, total, success, fail, qps, avg, tx, active,
#                  progress, last_error, targets (per-target list)
ctx.subscribe_metrics(on_metrics)
```

## Publish to the Marketplace

1. Put your plugin in the local plugins folder and test it.
2. Open **Plugin Marketplace → Publish**, pick your plugin, upload an icon (PNG/JPG, optional).
3. Click publish — the app handles GitHub OAuth in the browser, no manual token. Listings go live automatically (auto-merge workflow, no manual review).
4. Publish a new version by bumping `version` and publishing again — users see an "Update" button.

## Security Notes

- Plugins run in the host process with full privileges. Only install plugins from sources you trust.
- Protocol handlers run in worker threads: keep them thread-safe, avoid Qt GUI calls there.
- Clean up sockets/files in `on_unload()`.

---

# NetPulse 插件开发指南

NetPulse 插件就是普通的 Python 文件。会写 Python 就能扩展 NetPulse —— 自定义测试协议、新页面、报告导出器等等。

> 完整示例在 [`marketplace/`](marketplace/) 目录：`example_hello.py`（界面 + 配置）、`example_dns.py`（自定义协议 + 目标源）、`random_target.py`（简单工具页）。

---

## 快速开始

一个最小插件只要 10 行左右。保存为 `my_plugin.py`：

```python
# -*- coding: utf-8 -*-

class Plugin(NetPulsePlugin):
    name = "我的第一个插件"         # 或 ("中文名", "English name")
    version = "1.0"
    author = "你"
    description = "做点有用的事"

    def on_load(self, ctx):
        self._ctx = ctx               # 宿主上下文

    def create_widget(self, parent):
        from PySide6.QtWidgets import QWidget, QVBoxLayout
        from qfluentwidgets import StrongBodyLabel
        w = QWidget(parent)
        QVBoxLayout(w).addWidget(StrongBodyLabel("你好 NetPulse！"))
        return w                       # 会成为主窗口的一个页面
```

放进插件目录，重启（或在插件页点重载）即可：

```
%APPDATA%\NetPulse\plugins\my_plugin.py
```

## 插件格式

| 格式 | 布局 | 插件 ID |
|------|------|---------|
| 单文件 | `xxx.py` | `xxx` |
| 文件夹 | `xxx/main.py`（可带资源） | `xxx` |

- 插件 ID = 文件名/文件夹名，唯一且稳定。
- 定义一个继承 `NetPulsePlugin` 的 `Plugin` 类。基类已注入模块命名空间，**无需 import**。
- 两种格式都可以自由定义其他类和辅助函数。

## 元数据

`Plugin` 类的属性：

```python
class Plugin(NetPulsePlugin):
    name        = ("你好插件", "Hello Plugin")   # (中文, English) 元组 = 双语
    version     = "1.2"                          # 用于市场更新比较
    author      = "你的名字"
    description = ("一句话简介", "One-line summary")
    icon        = "SPEED_HIGH"                   # FluentIcon 名，或 "icon.png"（相对路径）
    category    = "tool"                         # tool / protocol / ui / other（可选，自动识别）
```

- `name` / `description` / 各处 label 都支持 `(中文, English)` 元组，自动跟随界面语言。
- `icon` 可以是内置 [FluentIcon](https://qfluentwidgets.com/pages/icons/) 名（如 `"SPEED_HIGH"`、`"CLOUD"`）或相对路径的图片。
- `category` 是市场筛选类型：`tool`（工具）、`protocol`（自定义协议）、`ui`（页面/界面）或 `other`（其他）。不填则按插件注册的能力自动识别。

## 生命周期钩子

```python
class Plugin(NetPulsePlugin):
    def on_load(self, ctx): ...        # 初始化资源、注册扩展
    def on_unload(self): ...           # 释放资源（注册项由宿主自动清理）
    def create_widget(self, parent): ...  # 返回 QWidget = 独立导航页（返回 None 则不加页）
    def on_test_start(self, configs): ...  # configs: 目标配置列表
    def on_test_end(self, report): ...     # report: 汇总报告字典
```

## PluginContext（`ctx`）

```python
ctx.plugin_id      # 本插件 ID
ctx.app_version    # 宿主版本号
ctx.logger         # 共享日志器
ctx.tr(zh, en)     # 运行时翻译

ctx.get("key")           # 插件私有配置（自动持久化，按插件 ID 命名空间隔离）
ctx.set("key", value)
```

## 扩展 API

全部在 `on_load` 中注册：

### 自定义测试协议

在压测页协议下拉框中增加一项。

```python
def my_handler(config, timeout, state):
    # 在 worker 线程执行 —— 必须线程安全、可重入。
    # config: {"target", "port", "protocol", "packet_size", ...}
    # state:  每个 worker 一份的字典，可复用 socket / 连接
    # 返回: (成功?, 错误码或None, 发送字节数)
    ...

ctx.register_protocol("MYPROTO", my_handler)
```

### 报告导出器

在"导出报告"菜单中增加一项。

```python
def export(report, path):          # 主线程调用；把报告写到 path
    ...

ctx.register_exporter(("导出 XML", "Export XML"), export)
```

### 目标集提供者

在压测页增加"插件目标"按钮，一键填充目标列表。

```python
def targets():                     # 主线程调用；返回地址字符串列表
    return ["223.5.5.5", "8.8.8.8"]

ctx.register_target_provider(("常用 DNS", "Common DNS"), targets)
```

### 实时指标订阅

```python
def on_metrics(snapshot):          # 主线程，压测期间约 500ms 一次
    print(snapshot["qps"], snapshot["avg"])

# snapshot 字段：running, total, success, fail, qps, avg, tx, active,
#                progress, last_error, targets（分目标明细列表）
ctx.subscribe_metrics(on_metrics)
```

## 发布到插件市场

1. 把插件放进本地插件目录并测试。
2. 打开 **插件市场 → 发布**，选择插件，上传图标（PNG/JPG，可选）。
3. 点击发布 —— 软件自动走浏览器 GitHub OAuth，无需手动生成令牌。发布后自动上架（自动合并工作流，无需人工审核）。
4. 发新版本只需改 `version` 再发布一次 —— 用户会看到"更新"按钮。

## 安全须知

- 插件运行于主程序进程内，拥有同等权限。请只安装可信来源的插件。
- 协议 handler 在 worker 线程执行：保持线程安全，不要在里面碰 Qt 界面。
- 在 `on_unload()` 里清理 socket / 文件。
