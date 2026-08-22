# NetPulse Android Client

NetPulse 的 Android 移动端客户端，使用 Flutter 构建，UI 风格参照原 Windows 桌面版的 Fluent Design 设计语言。

## 功能特性

- **仪表盘**：实时监控设备 CPU、内存、网络流量
- **压力测试**：支持 HTTP/HTTPS、TCP、UDP、ICMP 四种协议压测
- **协同测试**：分布式多节点协同压测，支持 Host/Node 模式
- **合规框架**：目标授权管理、QPS 限速、审计日志
- **Fluent Design UI**：明暗主题、卡片式布局、流畅动画
- **中英文双语**：界面语言切换

## 技术栈

- **框架**：Flutter 3.x / Dart 3.x
- **UI 库**：fluent_ui（Fluent Design 风格）
- **状态管理**：Provider
- **图表**：fl_chart
- **网络**：dio、http、web_socket_channel
- **本地存储**：shared_preferences

## 项目结构

```
lib/
├── main.dart                 # 应用入口
├── app.dart                  # 应用根组件
├── theme/                    # 主题配置
│   ├── app_theme.dart
│   └── colors.dart
├── models/                   # 数据模型
│   ├── test_result.dart
│   ├── target_auth.dart
│   └── system_stats.dart
├── services/                 # 业务服务
│   ├── stress_tester.dart
│   ├── system_monitor.dart
│   ├── auth_manager.dart
│   ├── collaboration_service.dart
│   └── settings_service.dart
├── screens/                  # 页面
│   ├── splash_screen.dart
│   ├── disclaimer_screen.dart
│   ├── dashboard_screen.dart
│   ├── stress_test_screen.dart
│   ├── collaboration_screen.dart
│   └── settings_screen.dart
├── widgets/                  # 复用组件
│   ├── stat_card.dart
│   ├── metric_chart.dart
│   ├── protocol_selector.dart
│   ├── target_auth_dialog.dart
│   └── busy_overlay.dart
└── utils/                    # 工具类
    ├── constants.dart
    └── formatters.dart
```

## 构建说明

### 环境要求
- Flutter SDK >= 3.10.0
- Android SDK (API level 21+)
- Android Studio / VS Code

### 构建步骤

```bash
cd android_client
flutter pub get
flutter build apk --release
```

构建产物位于 `build/app/outputs/flutter-apk/app-release.apk`

### 调试运行

```bash
flutter run
```

## 法律声明

本工具仅允许对拥有书面授权的目标执行网络压力测试。未授权压测属于违法行为，使用者承担全部法律责任。

## License

MIT License - 与原项目保持一致
