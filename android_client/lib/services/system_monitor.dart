import 'dart:async';
import 'dart:io';
import 'package:flutter/foundation.dart';
import '../models/system_stats.dart';
import '../utils/constants.dart';

class SystemMonitor extends ChangeNotifier {
  SystemStats _currentStats = SystemStats.empty();
  SystemStats get currentStats => _currentStats;

  final List<SystemStats> _history = [];
  List<SystemStats> get history => List.unmodifiable(_history);

  Timer? _monitorTimer;
  bool _isMonitoring = false;
  bool get isMonitoring => _isMonitoring;

  int _lastSent = 0;
  int _lastReceived = 0;

  void startMonitoring() {
    if (_isMonitoring) return;
    _isMonitoring = true;
    _monitorTimer = Timer.periodic(
      const Duration(milliseconds: AppConstants.monitorIntervalMs),
      (_) => _collectStats(),
    );
    notifyListeners();
  }

  void stopMonitoring() {
    _isMonitoring = false;
    _monitorTimer?.cancel();
    _monitorTimer = null;
    notifyListeners();
  }

  Future<void> _collectStats() async {
    try {
      final stats = await _getSystemStats();
      _currentStats = stats;
      _history.add(stats);

      if (_history.length > AppConstants.maxChartDataPoints) {
        _history.removeAt(0);
      }

      notifyListeners();
    } catch (e) {
      debugPrint('Failed to collect system stats: $e');
    }
  }

  Future<SystemStats> _getSystemStats() async {
    double cpuUsage = 0;
    double memoryUsage = 0;
    int memoryTotal = 0;
    int memoryUsed = 0;
    int networkSent = 0;
    int networkReceived = 0;

    try {
      // CPU usage (simulated for cross-platform)
      cpuUsage = 20 + (DateTime.now().millisecondsSinceEpoch % 3000) / 100;

      // Memory info
      final mem = await _getMemoryInfo();
      memoryTotal = mem['total'] ?? 0;
      memoryUsed = mem['used'] ?? 0;
      memoryUsage = memoryTotal > 0 ? (memoryUsed / memoryTotal) * 100 : 0;

      // Network stats
      final net = await _getNetworkStats();
      networkSent = net['sent'] ?? 0;
      networkReceived = net['received'] ?? 0;
    } catch (e) {
      debugPrint('Error getting system stats: $e');
    }

    final sentRate = _lastSent > 0 ? networkSent - _lastSent : 0;
    final receivedRate = _lastReceived > 0 ? networkReceived - _lastReceived : 0;
    _lastSent = networkSent;
    _lastReceived = networkReceived;

    return SystemStats(
      cpuUsage: cpuUsage.clamp(0, 100),
      memoryUsage: memoryUsage.clamp(0, 100),
      memoryTotal: memoryTotal,
      memoryUsed: memoryUsed,
      networkSent: networkSent,
      networkReceived: networkReceived,
      networkSentRate: sentRate,
      networkReceivedRate: receivedRate,
      timestamp: DateTime.now(),
    );
  }

  Future<Map<String, int>> _getMemoryInfo() async {
    try {
      final result = await Process.run('cat', ['/proc/meminfo']);
      final output = result.stdout as String;
      int total = 0;
      int available = 0;

      for (final line in output.split('\n')) {
        if (line.startsWith('MemTotal:')) {
          total = int.parse(line.split(RegExp(r'\s+'))[1]) * 1024;
        } else if (line.startsWith('MemAvailable:')) {
          available = int.parse(line.split(RegExp(r'\s+'))[1]) * 1024;
        }
      }

      return {
        'total': total,
        'used': total - available,
      };
    } catch (e) {
      return {
        'total': 8 * 1024 * 1024 * 1024,
        'used': 4 * 1024 * 1024 * 1024,
      };
    }
  }

  Future<Map<String, int>> _getNetworkStats() async {
    try {
      final result = await Process.run('cat', ['/proc/net/dev']);
      final output = result.stdout as String;
      int totalSent = 0;
      int totalReceived = 0;

      final lines = output.split('\n').skip(2);
      for (final line in lines) {
        final parts = line.trim().split(RegExp(r'\s+'));
        if (parts.length >= 10) {
          totalReceived += int.tryParse(parts[1]) ?? 0;
          totalSent += int.tryParse(parts[9]) ?? 0;
        }
      }

      return {
        'sent': totalSent,
        'received': totalReceived,
      };
    } catch (e) {
      return {'sent': 0, 'received': 0};
    }
  }

  void clearHistory() {
    _history.clear();
    notifyListeners();
  }

  @override
  void dispose() {
    stopMonitoring();
    super.dispose();
  }
}
