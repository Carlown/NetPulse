enum TestProtocol { http, https, tcp, udp, icmp }

extension TestProtocolExtension on TestProtocol {
  String get name {
    switch (this) {
      case TestProtocol.http:
        return 'HTTP';
      case TestProtocol.https:
        return 'HTTPS';
      case TestProtocol.tcp:
        return 'TCP';
      case TestProtocol.udp:
        return 'UDP';
      case TestProtocol.icmp:
        return 'ICMP';
    }
  }

  static TestProtocol fromName(String name) {
    return TestProtocol.values.firstWhere(
      (p) => p.name == name.toUpperCase(),
      orElse: () => TestProtocol.http,
    );
  }
}

class LatencyStats {
  final int p50;
  final int p90;
  final int p99;
  final int min;
  final int max;
  final double avg;

  const LatencyStats({
    required this.p50,
    required this.p90,
    required this.p99,
    required this.min,
    required this.max,
    required this.avg,
  });

  factory LatencyStats.empty() => const LatencyStats(
        p50: 0,
        p90: 0,
        p99: 0,
        min: 0,
        max: 0,
        avg: 0,
      );

  Map<String, dynamic> toJson() => {
        'p50': p50,
        'p90': p90,
        'p99': p99,
        'min': min,
        'max': max,
        'avg': avg,
      };

  factory LatencyStats.fromJson(Map<String, dynamic> json) => LatencyStats(
        p50: json['p50'] ?? 0,
        p90: json['p90'] ?? 0,
        p99: json['p99'] ?? 0,
        min: json['min'] ?? 0,
        max: json['max'] ?? 0,
        avg: (json['avg'] ?? 0).toDouble(),
      );
}

class ErrorStats {
  final int total;
  final Map<String, int> byType;

  const ErrorStats({
    required this.total,
    required this.byType,
  });

  factory ErrorStats.empty() => const ErrorStats(total: 0, byType: {});

  double get errorRate {
    return 0;
  }

  Map<String, dynamic> toJson() => {
        'total': total,
        'byType': byType,
      };

  factory ErrorStats.fromJson(Map<String, dynamic> json) => ErrorStats(
        total: json['total'] ?? 0,
        byType: Map<String, int>.from(json['byType'] ?? {}),
      );
}

class TestResult {
  final String id;
  final String target;
  final TestProtocol protocol;
  final DateTime startTime;
  final DateTime? endTime;
  final int totalRequests;
  final int successCount;
  final int failedCount;
  final double currentQps;
  final double avgQps;
  final int totalBytesSent;
  final int totalBytesReceived;
  final LatencyStats latency;
  final ErrorStats errors;
  final bool isRunning;

  const TestResult({
    required this.id,
    required this.target,
    required this.protocol,
    required this.startTime,
    this.endTime,
    this.totalRequests = 0,
    this.successCount = 0,
    this.failedCount = 0,
    this.currentQps = 0,
    this.avgQps = 0,
    this.totalBytesSent = 0,
    this.totalBytesReceived = 0,
    this.latency = const LatencyStats.empty(),
    this.errors = const ErrorStats.empty(),
    this.isRunning = false,
  });

  Duration get elapsed {
    final end = endTime ?? DateTime.now();
    return end.difference(startTime);
  }

  double get successRate {
    if (totalRequests == 0) return 0;
    return (successCount / totalRequests) * 100;
  }

  double get errorRate {
    if (totalRequests == 0) return 0;
    return (failedCount / totalRequests) * 100;
  }

  TestResult copyWith({
    String? id,
    String? target,
    TestProtocol? protocol,
    DateTime? startTime,
    DateTime? endTime,
    int? totalRequests,
    int? successCount,
    int? failedCount,
    double? currentQps,
    double? avgQps,
    int? totalBytesSent,
    int? totalBytesReceived,
    LatencyStats? latency,
    ErrorStats? errors,
    bool? isRunning,
  }) {
    return TestResult(
      id: id ?? this.id,
      target: target ?? this.target,
      protocol: protocol ?? this.protocol,
      startTime: startTime ?? this.startTime,
      endTime: endTime ?? this.endTime,
      totalRequests: totalRequests ?? this.totalRequests,
      successCount: successCount ?? this.successCount,
      failedCount: failedCount ?? this.failedCount,
      currentQps: currentQps ?? this.currentQps,
      avgQps: avgQps ?? this.avgQps,
      totalBytesSent: totalBytesSent ?? this.totalBytesSent,
      totalBytesReceived: totalBytesReceived ?? this.totalBytesReceived,
      latency: latency ?? this.latency,
      errors: errors ?? this.errors,
      isRunning: isRunning ?? this.isRunning,
    );
  }

  Map<String, dynamic> toJson() => {
        'id': id,
        'target': target,
        'protocol': protocol.name,
        'startTime': startTime.toIso8601String(),
        'endTime': endTime?.toIso8601String(),
        'totalRequests': totalRequests,
        'successCount': successCount,
        'failedCount': failedCount,
        'currentQps': currentQps,
        'avgQps': avgQps,
        'totalBytesSent': totalBytesSent,
        'totalBytesReceived': totalBytesReceived,
        'latency': latency.toJson(),
        'errors': errors.toJson(),
        'isRunning': isRunning,
      };

  factory TestResult.fromJson(Map<String, dynamic> json) => TestResult(
        id: json['id'] ?? '',
        target: json['target'] ?? '',
        protocol: TestProtocolExtension.fromName(json['protocol'] ?? 'HTTP'),
        startTime: DateTime.parse(json['startTime'] ?? DateTime.now().toIso8601String()),
        endTime: json['endTime'] != null ? DateTime.parse(json['endTime']) : null,
        totalRequests: json['totalRequests'] ?? 0,
        successCount: json['successCount'] ?? 0,
        failedCount: json['failedCount'] ?? 0,
        currentQps: (json['currentQps'] ?? 0).toDouble(),
        avgQps: (json['avgQps'] ?? 0).toDouble(),
        totalBytesSent: json['totalBytesSent'] ?? 0,
        totalBytesReceived: json['totalBytesReceived'] ?? 0,
        latency: LatencyStats.fromJson(json['latency'] ?? {}),
        errors: ErrorStats.fromJson(json['errors'] ?? {}),
        isRunning: json['isRunning'] ?? false,
      );
}
