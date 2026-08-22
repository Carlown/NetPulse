import 'dart:async';
import 'dart:math';
import 'package:flutter/foundation.dart';
import 'package:uuid/uuid.dart';
import '../models/test_result.dart';
import '../utils/constants.dart';

class StressTester extends ChangeNotifier {
  TestResult? _currentResult;
  TestResult? get currentResult => _currentResult;

  bool _isRunning = false;
  bool get isRunning => _isRunning;

  Timer? _statsTimer;
  Timer? _requestTimer;
  final List<int> _latencySamples = [];
  int _requestCount = 0;
  int _successCount = 0;
  int _failedCount = 0;
  int _bytesSent = 0;
  int _bytesReceived = 0;
  int _lastSecondRequests = 0;
  double _currentQps = 0;

  // Token bucket rate limiter
  double _tokens = 0;
  double _maxTokens = 0;
  double _refillRate = 0;
  DateTime _lastRefill = DateTime.now();

  final _uuid = const Uuid();

  Future<void> startTest({
    required String target,
    required TestProtocol protocol,
    int qps = AppConstants.defaultQps,
    int duration = AppConstants.defaultDuration,
    int timeout = AppConstants.defaultTimeout,
    String httpMethod = 'GET',
    Map<String, String>? headers,
    String? body,
  }) async {
    if (_isRunning) return;

    _isRunning = true;
    _requestCount = 0;
    _successCount = 0;
    _failedCount = 0;
    _bytesSent = 0;
    _bytesReceived = 0;
    _latencySamples.clear();
    _currentQps = 0;
    _lastSecondRequests = 0;

    // Initialize token bucket
    _maxTokens = qps.toDouble();
    _refillRate = qps.toDouble();
    _tokens = _maxTokens;
    _lastRefill = DateTime.now();

    _currentResult = TestResult(
      id: _uuid.v4(),
      target: target,
      protocol: protocol,
      startTime: DateTime.now(),
      isRunning: true,
    );

    notifyListeners();

    // Start stats update timer
    _statsTimer = Timer.periodic(const Duration(seconds: 1), (_) {
      _updateStats();
    });

    // Start request generation
    _requestTimer = Timer.periodic(const Duration(milliseconds: 10), (_) {
      _refillTokens();
      while (_tokens >= 1 && _isRunning) {
        _tokens -= 1;
        _executeRequest(target, protocol, httpMethod, headers, body, timeout);
      }
    });

    // Auto stop after duration
    if (duration > 0) {
      Timer(Duration(seconds: duration), () {
        if (_isRunning) stopTest();
      });
    }
  }

  void _refillTokens() {
    final now = DateTime.now();
    final elapsed = now.difference(_lastRefill).inMilliseconds / 1000.0;
    _tokens = min(_maxTokens, _tokens + _refillRate * elapsed);
    _lastRefill = now;
  }

  Future<void> _executeRequest(
    String target,
    TestProtocol protocol,
    String httpMethod,
    Map<String, String>? headers,
    String? body,
    int timeout,
  ) async {
    final startTime = DateTime.now();
    _requestCount++;
    _lastSecondRequests++;

    try {
      // Simulated request execution - in real implementation would use
      // http/dio for HTTP, RawSocket for TCP, RawDatagramSocket for UDP
      await Future.delayed(Duration(milliseconds: Random().nextInt(100) + 10));

      final latency = DateTime.now().difference(startTime).inMilliseconds;
      _latencySamples.add(latency);
      _successCount++;
      _bytesSent += 100 + (body?.length ?? 0);
      _bytesReceived += Random().nextInt(5000) + 200;
    } catch (e) {
      _failedCount++;
    }
  }

  void _updateStats() {
    if (_currentResult == null) return;

    _currentQps = _lastSecondRequests.toDouble();
    _lastSecondRequests = 0;

    // Calculate latency percentiles
    final latencies = List<int>.from(_latencySamples)..sort();
    int p50 = 0, p90 = 0, p99 = 0, min = 0, max = 0;
    double avg = 0;

    if (latencies.isNotEmpty) {
      p50 = _percentile(latencies, 50);
      p90 = _percentile(latencies, 90);
      p99 = _percentile(latencies, 99);
      min = latencies.first;
      max = latencies.last;
      avg = latencies.reduce((a, b) => a + b) / latencies.length;
    }

    _currentResult = _currentResult!.copyWith(
      totalRequests: _requestCount,
      successCount: _successCount,
      failedCount: _failedCount,
      currentQps: _currentQps,
      avgQps: _requestCount / max(1, DateTime.now().difference(_currentResult!.startTime).inSeconds),
      totalBytesSent: _bytesSent,
      totalBytesReceived: _bytesReceived,
      latency: LatencyStats(
        p50: p50,
        p90: p90,
        p99: p99,
        min: min,
        max: max,
        avg: avg,
      ),
    );

    notifyListeners();
  }

  int _percentile(List<int> sortedData, int percentile) {
    if (sortedData.isEmpty) return 0;
    final index = (percentile / 100 * (sortedData.length - 1)).round();
    return sortedData[index];
  }

  void stopTest() {
    if (!_isRunning) return;

    _isRunning = false;
    _statsTimer?.cancel();
    _requestTimer?.cancel();
    _statsTimer = null;
    _requestTimer = null;

    if (_currentResult != null) {
      _currentResult = _currentResult!.copyWith(
        endTime: DateTime.now(),
        isRunning: false,
      );
    }

    notifyListeners();
  }

  void reset() {
    stopTest();
    _currentResult = null;
    _latencySamples.clear();
    _requestCount = 0;
    _successCount = 0;
    _failedCount = 0;
    _bytesSent = 0;
    _bytesReceived = 0;
    notifyListeners();
  }

  @override
  void dispose() {
    _statsTimer?.cancel();
    _requestTimer?.cancel();
    super.dispose();
  }
}
