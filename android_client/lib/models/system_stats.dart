class SystemStats {
  final double cpuUsage;
  final double memoryUsage;
  final int memoryTotal;
  final int memoryUsed;
  final int networkSent;
  final int networkReceived;
  final int networkSentRate;
  final int networkReceivedRate;
  final DateTime timestamp;

  const SystemStats({
    this.cpuUsage = 0,
    this.memoryUsage = 0,
    this.memoryTotal = 0,
    this.memoryUsed = 0,
    this.networkSent = 0,
    this.networkReceived = 0,
    this.networkSentRate = 0,
    this.networkReceivedRate = 0,
    required this.timestamp,
  });

  factory SystemStats.empty() => SystemStats(
        timestamp: DateTime.now(),
      );

  SystemStats copyWith({
    double? cpuUsage,
    double? memoryUsage,
    int? memoryTotal,
    int? memoryUsed,
    int? networkSent,
    int? networkReceived,
    int? networkSentRate,
    int? networkReceivedRate,
    DateTime? timestamp,
  }) {
    return SystemStats(
      cpuUsage: cpuUsage ?? this.cpuUsage,
      memoryUsage: memoryUsage ?? this.memoryUsage,
      memoryTotal: memoryTotal ?? this.memoryTotal,
      memoryUsed: memoryUsed ?? this.memoryUsed,
      networkSent: networkSent ?? this.networkSent,
      networkReceived: networkReceived ?? this.networkReceived,
      networkSentRate: networkSentRate ?? this.networkSentRate,
      networkReceivedRate: networkReceivedRate ?? this.networkReceivedRate,
      timestamp: timestamp ?? this.timestamp,
    );
  }

  Map<String, dynamic> toJson() => {
        'cpuUsage': cpuUsage,
        'memoryUsage': memoryUsage,
        'memoryTotal': memoryTotal,
        'memoryUsed': memoryUsed,
        'networkSent': networkSent,
        'networkReceived': networkReceived,
        'networkSentRate': networkSentRate,
        'networkReceivedRate': networkReceivedRate,
        'timestamp': timestamp.toIso8601String(),
      };

  factory SystemStats.fromJson(Map<String, dynamic> json) => SystemStats(
        cpuUsage: (json['cpuUsage'] ?? 0).toDouble(),
        memoryUsage: (json['memoryUsage'] ?? 0).toDouble(),
        memoryTotal: json['memoryTotal'] ?? 0,
        memoryUsed: json['memoryUsed'] ?? 0,
        networkSent: json['networkSent'] ?? 0,
        networkReceived: json['networkReceived'] ?? 0,
        networkSentRate: json['networkSentRate'] ?? 0,
        networkReceivedRate: json['networkReceivedRate'] ?? 0,
        timestamp: DateTime.parse(json['timestamp'] ?? DateTime.now().toIso8601String()),
      );
}
