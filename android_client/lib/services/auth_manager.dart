import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:uuid/uuid.dart';
import '../models/target_auth.dart';
import '../utils/constants.dart';

class AuthManager extends ChangeNotifier {
  final List<TargetAuthorization> _authorizedTargets = [];
  List<TargetAuthorization> get authorizedTargets => List.unmodifiable(_authorizedTargets);

  final List<AuditLogEntry> _auditLogs = [];
  List<AuditLogEntry> get auditLogs => List.unmodifiable(_auditLogs);

  bool _disclaimerAccepted = false;
  bool get disclaimerAccepted => _disclaimerAccepted;

  final _uuid = const Uuid();

  Future<void> load() async {
    final prefs = await SharedPreferences.getInstance();

    _disclaimerAccepted = prefs.getBool(AppConstants.keyDisclaimerAccepted) ?? false;

    final targetsJson = prefs.getString(AppConstants.keyAuthorizedTargets);
    if (targetsJson != null) {
      final List<dynamic> decoded = jsonDecode(targetsJson);
      _authorizedTargets.clear();
      _authorizedTargets.addAll(
        decoded.map((e) => TargetAuthorization.fromJson(e as Map<String, dynamic>)),
      );
    }

    final logsJson = prefs.getString(AppConstants.keyAuditLogs);
    if (logsJson != null) {
      final List<dynamic> decoded = jsonDecode(logsJson);
      _auditLogs.clear();
      _auditLogs.addAll(
        decoded.map((e) => AuditLogEntry.fromJson(e as Map<String, dynamic>)),
      );
    }

    notifyListeners();
  }

  Future<void> acceptDisclaimer() async {
    _disclaimerAccepted = true;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(AppConstants.keyDisclaimerAccepted, true);
    _addAuditLog(action: 'disclaimer_accepted', target: 'system', details: 'User accepted legal disclaimer');
    notifyListeners();
  }

  bool isTargetAuthorized(String target) {
    return _authorizedTargets.any(
      (t) => t.target == target && t.isActive && !t.isExpired,
    );
  }

  TargetAuthorization? getAuthorization(String target) {
    try {
      return _authorizedTargets.firstWhere(
        (t) => t.target == target,
      );
    } catch (_) {
      return null;
    }
  }

  Future<void> authorizeTarget({
    required String target,
    required String note,
    String authorizedBy = 'local_user',
  }) async {
    final auth = TargetAuthorization(
      target: target,
      note: note,
      authorizedAt: DateTime.now(),
      authorizedBy: authorizedBy,
    );

    final existingIndex = _authorizedTargets.indexWhere((t) => t.target == target);
    if (existingIndex >= 0) {
      _authorizedTargets[existingIndex] = auth;
    } else {
      _authorizedTargets.add(auth);
    }

    await _saveTargets();
    _addAuditLog(
      action: 'target_authorized',
      target: target,
      details: 'Target authorized with note: $note',
    );
    notifyListeners();
  }

  Future<void> revokeAuthorization(String target) async {
    _authorizedTargets.removeWhere((t) => t.target == target);
    await _saveTargets();
    _addAuditLog(
      action: 'target_revoked',
      target: target,
      details: 'Target authorization revoked',
    );
    notifyListeners();
  }

  Future<void> _saveTargets() async {
    final prefs = await SharedPreferences.getInstance();
    final json = jsonEncode(_authorizedTargets.map((e) => e.toJson()).toList());
    await prefs.setString(AppConstants.keyAuthorizedTargets, json);
  }

  void _addAuditLog({
    required String action,
    required String target,
    required String details,
    String? result,
  }) {
    final entry = AuditLogEntry(
      id: _uuid.v4(),
      timestamp: DateTime.now(),
      action: action,
      target: target,
      details: details,
      result: result,
    );
    _auditLogs.insert(0, entry);

    if (_auditLogs.length > 500) {
      _auditLogs.removeLast();
    }

    _saveLogs();
  }

  Future<void> _saveLogs() async {
    final prefs = await SharedPreferences.getInstance();
    final json = jsonEncode(_auditLogs.map((e) => e.toJson()).toList());
    await prefs.setString(AppConstants.keyAuditLogs, json);
  }

  Future<void> clearAuditLogs() async {
    _auditLogs.clear();
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(AppConstants.keyAuditLogs);
    notifyListeners();
  }

  String exportAuditLogs() {
    return jsonEncode(_auditLogs.map((e) => e.toJson()).toList());
  }

  void logTestStart(String target, String protocol) {
    _addAuditLog(
      action: 'test_started',
      target: target,
      details: 'Stress test started with protocol: $protocol',
    );
  }

  void logTestStop(String target, String result) {
    _addAuditLog(
      action: 'test_stopped',
      target: target,
      details: 'Stress test stopped',
      result: result,
    );
  }
}
