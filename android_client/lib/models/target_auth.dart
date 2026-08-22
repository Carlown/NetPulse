class TargetAuthorization {
  final String target;
  final String note;
  final DateTime authorizedAt;
  final String authorizedBy;
  final bool isActive;

  const TargetAuthorization({
    required this.target,
    required this.note,
    required this.authorizedAt,
    required this.authorizedBy,
    this.isActive = true,
  });

  bool get isExpired {
    final now = DateTime.now();
    final expiry = authorizedAt.add(const Duration(days: 30));
    return now.isAfter(expiry);
  }

  TargetAuthorization copyWith({
    String? target,
    String? note,
    DateTime? authorizedAt,
    String? authorizedBy,
    bool? isActive,
  }) {
    return TargetAuthorization(
      target: target ?? this.target,
      note: note ?? this.note,
      authorizedAt: authorizedAt ?? this.authorizedAt,
      authorizedBy: authorizedBy ?? this.authorizedBy,
      isActive: isActive ?? this.isActive,
    );
  }

  Map<String, dynamic> toJson() => {
        'target': target,
        'note': note,
        'authorizedAt': authorizedAt.toIso8601String(),
        'authorizedBy': authorizedBy,
        'isActive': isActive,
      };

  factory TargetAuthorization.fromJson(Map<String, dynamic> json) => TargetAuthorization(
        target: json['target'] ?? '',
        note: json['note'] ?? '',
        authorizedAt: DateTime.parse(json['authorizedAt'] ?? DateTime.now().toIso8601String()),
        authorizedBy: json['authorizedBy'] ?? '',
        isActive: json['isActive'] ?? true,
      );
}

class AuditLogEntry {
  final String id;
  final DateTime timestamp;
  final String action;
  final String target;
  final String details;
  final String? result;

  const AuditLogEntry({
    required this.id,
    required this.timestamp,
    required this.action,
    required this.target,
    required this.details,
    this.result,
  });

  Map<String, dynamic> toJson() => {
        'id': id,
        'timestamp': timestamp.toIso8601String(),
        'action': action,
        'target': target,
        'details': details,
        'result': result,
      };

  factory AuditLogEntry.fromJson(Map<String, dynamic> json) => AuditLogEntry(
        id: json['id'] ?? '',
        timestamp: DateTime.parse(json['timestamp'] ?? DateTime.now().toIso8601String()),
        action: json['action'] ?? '',
        target: json['target'] ?? '',
        details: json['details'] ?? '',
        result: json['result'],
      );
}
