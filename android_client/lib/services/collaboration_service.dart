import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'package:flutter/foundation.dart';
import 'package:web_socket_channel/web_socket_channel.dart';
import '../utils/constants.dart';

enum CollabRole { host, node }

enum CollabStatus { disconnected, connecting, connected, testing }

class CollabNode {
  final String id;
  final String name;
  final String address;
  final int port;
  final bool isOnline;
  final double cpuUsage;
  final int currentQps;

  const CollabNode({
    required this.id,
    required this.name,
    required this.address,
    required this.port,
    this.isOnline = false,
    this.cpuUsage = 0,
    this.currentQps = 0,
  });

  CollabNode copyWith({
    String? id,
    String? name,
    String? address,
    int? port,
    bool? isOnline,
    double? cpuUsage,
    int? currentQps,
  }) {
    return CollabNode(
      id: id ?? this.id,
      name: name ?? this.name,
      address: address ?? this.address,
      port: port ?? this.port,
      isOnline: isOnline ?? this.isOnline,
      cpuUsage: cpuUsage ?? this.cpuUsage,
      currentQps: currentQps ?? this.currentQps,
    );
  }
}

class CollaborationService extends ChangeNotifier {
  CollabRole _role = CollabRole.host;
  CollabRole get role => _role;

  CollabStatus _status = CollabStatus.disconnected;
  CollabStatus get status => _status;

  final List<CollabNode> _nodes = [];
  List<CollabNode> get nodes => List.unmodifiable(_nodes);

  String? _inviteCode;
  String? get inviteCode => _inviteCode;

  String? _hostAddress;
  String? get hostAddress => _hostAddress;

  WebSocketChannel? _channel;
  ServerSocket? _serverSocket;
  Timer? _heartbeatTimer;

  int _totalDistributedQps = 0;
  int get totalDistributedQps => _totalDistributedQps;

  Future<void> startHost({int port = AppConstants.defaultCollabPort}) async {
    try {
      _role = CollabRole.host;
      _status = CollabStatus.connecting;
      notifyListeners();

      _serverSocket = await ServerSocket.bind(InternetAddress.anyIPv4, port);
      _inviteCode = _generateInviteCode();
      _status = CollabStatus.connected;

      _serverSocket!.listen((socket) {
        _handleNodeConnection(socket);
      });

      _startHeartbeat();
      notifyListeners();
    } catch (e) {
      _status = CollabStatus.disconnected;
      notifyListeners();
      rethrow;
    }
  }

  Future<void> connectToHost({
    required String address,
    int port = AppConstants.defaultCollabPort,
    required String inviteCode,
  }) async {
    try {
      _role = CollabRole.node;
      _hostAddress = address;
      _status = CollabStatus.connecting;
      notifyListeners();

      final uri = Uri.parse('ws://$address:$port');
      _channel = WebSocketChannel.connect(uri);

      _channel!.stream.listen(
        (data) => _handleHostMessage(data),
        onDone: () => _onDisconnected(),
        onError: (_) => _onDisconnected(),
      );

      // Send join message with invite code
      _channel!.sink.add(jsonEncode({
        'type': 'join',
        'inviteCode': inviteCode,
        'name': Platform.localHostname,
      }));

      _status = CollabStatus.connected;
      _startHeartbeat();
      notifyListeners();
    } catch (e) {
      _status = CollabStatus.disconnected;
      notifyListeners();
      rethrow;
    }
  }

  void _handleNodeConnection(Socket socket) {
    socket.listen(
      (data) {
        final message = jsonDecode(utf8.decode(data));
        _handleNodeMessage(socket, message);
      },
      onDone: () {
        // Node disconnected
      },
    );
  }

  void _handleNodeMessage(Socket socket, Map<String, dynamic> message) {
    switch (message['type']) {
      case 'join':
        final node = CollabNode(
          id: DateTime.now().millisecondsSinceEpoch.toString(),
          name: message['name'] ?? 'Unknown',
          address: socket.remoteAddress.address,
          port: socket.remotePort,
          isOnline: true,
        );
        _nodes.add(node);
        notifyListeners();
        break;
      case 'stats':
        final nodeId = message['nodeId'];
        final index = _nodes.indexWhere((n) => n.id == nodeId);
        if (index >= 0) {
          _nodes[index] = _nodes[index].copyWith(
            cpuUsage: (message['cpuUsage'] ?? 0).toDouble(),
            currentQps: message['qps'] ?? 0,
          );
          _totalDistributedQps = _nodes.fold(0, (sum, n) => sum + n.currentQps);
          notifyListeners();
        }
        break;
    }
  }

  void _handleHostMessage(dynamic data) {
    final message = jsonDecode(data);
    switch (message['type']) {
      case 'test_config':
        // Host sent test configuration
        break;
      case 'start_test':
        _status = CollabStatus.testing;
        notifyListeners();
        break;
      case 'stop_test':
        _status = CollabStatus.connected;
        notifyListeners();
        break;
    }
  }

  void broadcastTestConfig(Map<String, dynamic> config) {
    if (_role == CollabRole.host) {
      // Broadcast to all connected nodes
      _status = CollabStatus.testing;
      notifyListeners();
    }
  }

  void stopDistributedTest() {
    _status = CollabStatus.connected;
    _totalDistributedQps = 0;
    notifyListeners();
  }

  void _startHeartbeat() {
    _heartbeatTimer = Timer.periodic(const Duration(seconds: 5), (_) {
      if (_channel != null) {
        _channel!.sink.add(jsonEncode({'type': 'ping'}));
      }
    });
  }

  void _onDisconnected() {
    _status = CollabStatus.disconnected;
    _heartbeatTimer?.cancel();
    notifyListeners();
  }

  Future<void> disconnect() async {
    _heartbeatTimer?.cancel();
    _channel?.sink.close();
    _channel = null;
    _serverSocket?.close();
    _serverSocket = null;
    _nodes.clear();
    _inviteCode = null;
    _hostAddress = null;
    _totalDistributedQps = 0;
    _status = CollabStatus.disconnected;
    notifyListeners();
  }

  String _generateInviteCode() {
    final random = DateTime.now().millisecondsSinceEpoch;
    return (random % 1000000).toString().padLeft(6, '0');
  }

  @override
  void dispose() {
    disconnect();
    super.dispose();
  }
}
