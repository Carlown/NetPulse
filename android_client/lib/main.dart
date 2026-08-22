import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'app.dart';
import 'services/settings_service.dart';
import 'services/auth_manager.dart';
import 'services/system_monitor.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  final settingsService = SettingsService();
  await settingsService.load();

  final authManager = AuthManager();
  await authManager.load();

  final systemMonitor = SystemMonitor();

  runApp(
    MultiProvider(
      providers: [
        ChangeNotifierProvider(create: (_) => settingsService),
        ChangeNotifierProvider(create: (_) => authManager),
        ChangeNotifierProvider(create: (_) => systemMonitor),
      ],
      child: const NetPulseApp(),
    ),
  );
}
