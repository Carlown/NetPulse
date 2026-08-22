import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../utils/constants.dart';

class SettingsService extends ChangeNotifier {
  ThemeMode _themeMode = ThemeMode.system;
  ThemeMode get themeMode => _themeMode;

  Locale _locale = const Locale('zh', 'CN');
  Locale get locale => _locale;

  int _defaultQps = AppConstants.defaultQps;
  int get defaultQps => _defaultQps;

  int _defaultDuration = AppConstants.defaultDuration;
  int get defaultDuration => _defaultDuration;

  bool _rateLimiterEnabled = true;
  bool get rateLimiterEnabled => _rateLimiterEnabled;

  bool _auditLoggingEnabled = true;
  bool get auditLoggingEnabled => _auditLoggingEnabled;

  bool _wakelockEnabled = true;
  bool get wakelockEnabled => _wakelockEnabled;

  Future<void> load() async {
    final prefs = await SharedPreferences.getInstance();

    final themeIndex = prefs.getInt(AppConstants.keyThemeMode);
    if (themeIndex != null && themeIndex >= 0 && themeIndex < ThemeMode.values.length) {
      _themeMode = ThemeMode.values[themeIndex];
    }

    final localeCode = prefs.getString(AppConstants.keyLocale);
    if (localeCode != null) {
      if (localeCode == 'en') {
        _locale = const Locale('en', 'US');
      } else {
        _locale = const Locale('zh', 'CN');
      }
    }

    _defaultQps = prefs.getInt(AppConstants.keyDefaultQps) ?? AppConstants.defaultQps;
    _defaultDuration = prefs.getInt(AppConstants.keyDefaultDuration) ?? AppConstants.defaultDuration;

    notifyListeners();
  }

  Future<void> setThemeMode(ThemeMode mode) async {
    _themeMode = mode;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setInt(AppConstants.keyThemeMode, mode.index);
    notifyListeners();
  }

  Future<void> setLocale(Locale locale) async {
    _locale = locale;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(AppConstants.keyLocale, locale.languageCode);
    notifyListeners();
  }

  Future<void> setDefaultQps(int qps) async {
    _defaultQps = qps;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setInt(AppConstants.keyDefaultQps, qps);
    notifyListeners();
  }

  Future<void> setDefaultDuration(int duration) async {
    _defaultDuration = duration;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setInt(AppConstants.keyDefaultDuration, duration);
    notifyListeners();
  }

  Future<void> setRateLimiterEnabled(bool enabled) async {
    _rateLimiterEnabled = enabled;
    notifyListeners();
  }

  Future<void> setAuditLoggingEnabled(bool enabled) async {
    _auditLoggingEnabled = enabled;
    notifyListeners();
  }

  Future<void> setWakelockEnabled(bool enabled) async {
    _wakelockEnabled = enabled;
    notifyListeners();
  }

  bool get isChinese => _locale.languageCode == 'zh';

  String get languageName => isChinese ? '简体中文' : 'English';

  String get themeName {
    switch (_themeMode) {
      case ThemeMode.light:
        return isChinese ? '浅色' : 'Light';
      case ThemeMode.dark:
        return isChinese ? '深色' : 'Dark';
      case ThemeMode.system:
        return isChinese ? '跟随系统' : 'System';
    }
  }
}
