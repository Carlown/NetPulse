class AppConstants {
  static const String appName = 'NetPulse';
  static const String appVersion = '1.0.0';
  static const String githubRepo = 'Carlown/NetPulse';
  static const String githubUrl = 'https://github.com/Carlown/NetPulse';

  // Stress test defaults
  static const int defaultQps = 100;
  static const int defaultDuration = 30;
  static const int defaultTimeout = 10000;
  static const int highQpsThreshold = 500;
  static const int maxQps = 10000;

  // Rate limiter
  static const double tokenBucketRefillRate = 100.0;
  static const int tokenBucketCapacity = 200;

  // Monitoring
  static const int monitorIntervalMs = 1000;
  static const int maxChartDataPoints = 60;

  // Collaboration
  static const int defaultCollabPort = 8765;
  static const int collabTimeoutMs = 30000;

  // Storage keys
  static const String keyThemeMode = 'theme_mode';
  static const String keyLocale = 'locale';
  static const String keyDisclaimerAccepted = 'disclaimer_accepted';
  static const String keyAuthorizedTargets = 'authorized_targets';
  static const String keyAuditLogs = 'audit_logs';
  static const String keyDefaultQps = 'default_qps';
  static const String keyDefaultDuration = 'default_duration';

  // Protocols
  static const List<String> supportedProtocols = ['HTTP', 'HTTPS', 'TCP', 'UDP', 'ICMP'];

  // HTTP methods
  static const List<String> httpMethods = ['GET', 'POST', 'PUT', 'DELETE', 'HEAD', 'PATCH'];
}
