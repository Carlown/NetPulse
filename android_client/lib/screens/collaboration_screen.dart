import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';
import '../services/collaboration_service.dart';
import '../services/settings_service.dart';
import '../theme/colors.dart';
import '../utils/constants.dart';

class CollaborationScreen extends StatefulWidget {
  const CollaborationScreen({super.key});

  @override
  State<CollaborationScreen> createState() => _CollaborationScreenState();
}

class _CollaborationScreenState extends State<CollaborationScreen> with SingleTickerProviderStateMixin {
  late TabController _tabController;
  final _hostAddressController = TextEditingController();
  final _inviteCodeController = TextEditingController();
  final _portController = TextEditingController(text: '${AppConstants.defaultCollabPort}');

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 2, vsync: this);
  }

  @override
  void dispose() {
    _tabController.dispose();
    _hostAddressController.dispose();
    _inviteCodeController.dispose();
    _portController.dispose();
    super.dispose();
  }

  Future<void> _startHost() async {
    final port = int.tryParse(_portController.text) ?? AppConstants.defaultCollabPort;
    try {
      await context.read<CollaborationService>().startHost(port: port);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('主机已启动，分享邀请码给节点')),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('启动失败: $e')),
        );
      }
    }
  }

  Future<void> _connectToHost() async {
    final address = _hostAddressController.text.trim();
    final inviteCode = _inviteCodeController.text.trim();
    final port = int.tryParse(_portController.text) ?? AppConstants.defaultCollabPort;

    if (address.isEmpty || inviteCode.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('请输入主机地址和邀请码')),
      );
      return;
    }

    try {
      await context.read<CollaborationService>().connectToHost(
            address: address,
            port: port,
            inviteCode: inviteCode,
          );
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('已连接到主机')),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('连接失败: $e')),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final isChinese = context.watch<SettingsService>().isChinese;
    final collab = context.watch<CollaborationService>();

    return Column(
      children: [
        Container(
          color: AppColors.cardBackground(context),
          child: TabBar(
            controller: _tabController,
            labelColor: AppColors.primary,
            unselectedLabelColor: AppColors.textSecondary(context),
            indicatorColor: AppColors.primary,
            tabs: [
              Tab(text: isChinese ? '创建主机' : 'Host'),
              Tab(text: isChinese ? '加入主机' : 'Join'),
            ],
          ),
        ),
        Expanded(
          child: TabBarView(
            controller: _tabController,
            children: [
              _buildHostTab(context, isChinese, collab),
              _buildJoinTab(context, isChinese, collab),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildHostTab(BuildContext context, bool isChinese, CollaborationService collab) {
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        if (collab.status == CollabStatus.connected || collab.status == CollabStatus.testing)
          _buildHostSessionCard(context, isChinese, collab)
        else
          _buildHostConfigCard(context, isChinese),
        const SizedBox(height: 16),
        if (collab.nodes.isNotEmpty) _buildNodesList(context, isChinese, collab),
      ],
    );
  }

  Widget _buildHostConfigCard(BuildContext context, bool isChinese) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.cardBackground(context),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: AppColors.borderColor(context)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            isChinese ? '主机配置' : 'Host Configuration',
            style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w600),
          ),
          const SizedBox(height: 16),
          TextField(
            controller: _portController,
            decoration: InputDecoration(
              labelText: isChinese ? '监听端口' : 'Listen Port',
            ),
            keyboardType: TextInputType.number,
          ),
          const SizedBox(height: 20),
          SizedBox(
            width: double.infinity,
            child: ElevatedButton.icon(
              onPressed: _startHost,
              icon: const Icon(Icons.router),
              label: Text(isChinese ? '启动主机' : 'Start Host'),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildHostSessionCard(BuildContext context, bool isChinese, CollaborationService collab) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.success.withOpacity(0.08),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: AppColors.success.withOpacity(0.3)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.check_circle, color: AppColors.success),
              const SizedBox(width: 8),
              Text(
                isChinese ? '主机运行中' : 'Host Running',
                style: const TextStyle(color: AppColors.success, fontWeight: FontWeight.w600),
              ),
            ],
          ),
          const SizedBox(height: 16),
          if (collab.inviteCode != null) ...[
            Text(isChinese ? '邀请码' : 'Invite Code', style: TextStyle(color: AppColors.textSecondary(context))),
            const SizedBox(height: 8),
            Row(
              children: [
                Expanded(
                  child: Container(
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: AppColors.cardBackground(context),
                      borderRadius: BorderRadius.circular(6),
                    ),
                    child: Text(
                      collab.inviteCode!,
                      style: const TextStyle(fontSize: 24, fontWeight: FontWeight.bold, letterSpacing: 4),
                      textAlign: TextAlign.center,
                    ),
                  ),
                ),
                IconButton(
                  icon: const Icon(Icons.copy),
                  onPressed: () {
                    Clipboard.setData(ClipboardData(text: collab.inviteCode!));
                    ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(content: Text('邀请码已复制')),
                    );
                  },
                ),
              ],
            ),
            const SizedBox(height: 12),
          ],
          Text('${isChinese ? '已连接节点' : 'Connected Nodes'}: ${collab.nodes.length}'),
          const SizedBox(height: 12),
          Text('${isChinese ? '总分布式 QPS' : 'Total Distributed QPS'}: ${collab.totalDistributedQps}'),
          const SizedBox(height: 16),
          Row(
            children: [
              Expanded(
                child: OutlinedButton.icon(
                  onPressed: () => collab.disconnect(),
                  icon: const Icon(Icons.stop),
                  label: Text(isChinese ? '停止主机' : 'Stop Host'),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildNodesList(BuildContext context, bool isChinese, CollaborationService collab) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.cardBackground(context),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: AppColors.borderColor(context)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            isChinese ? '节点列表' : 'Node List',
            style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w600),
          ),
          const SizedBox(height: 12),
          ...collab.nodes.map((node) => ListTile(
                leading: CircleAvatar(
                  backgroundColor: node.isOnline ? AppColors.success : AppColors.textSecondary(context),
                  child: Text(node.name.isNotEmpty ? node.name[0].toUpperCase() : '?'),
                ),
                title: Text(node.name),
                subtitle: Text('${node.address}:${node.port}'),
                trailing: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: [
                    Text('QPS: ${node.currentQps}', style: const TextStyle(fontWeight: FontWeight.w600)),
                    Text('CPU: ${node.cpuUsage.toStringAsFixed(1)}%', style: TextStyle(fontSize: 12, color: AppColors.textSecondary(context))),
                  ],
                ),
              )),
        ],
      ),
    );
  }

  Widget _buildJoinTab(BuildContext context, bool isChinese, CollaborationService collab) {
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        if (collab.status == CollabStatus.connected || collab.status == CollabStatus.testing)
          _buildJoinSessionCard(context, isChinese, collab)
        else
          _buildJoinConfigCard(context, isChinese),
      ],
    );
  }

  Widget _buildJoinConfigCard(BuildContext context, bool isChinese) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.cardBackground(context),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: AppColors.borderColor(context)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            isChinese ? '加入主机' : 'Join Host',
            style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w600),
          ),
          const SizedBox(height: 16),
          TextField(
            controller: _hostAddressController,
            decoration: InputDecoration(
              labelText: isChinese ? '主机地址' : 'Host Address',
              hintText: '192.168.1.100',
              prefixIcon: const Icon(Icons.dns),
            ),
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _inviteCodeController,
            decoration: InputDecoration(
              labelText: isChinese ? '邀请码' : 'Invite Code',
              prefixIcon: const Icon(Icons.vpn_key),
            ),
            keyboardType: TextInputType.number,
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _portController,
            decoration: InputDecoration(
              labelText: isChinese ? '端口' : 'Port',
            ),
            keyboardType: TextInputType.number,
          ),
          const SizedBox(height: 20),
          SizedBox(
            width: double.infinity,
            child: ElevatedButton.icon(
              onPressed: _connectToHost,
              icon: const Icon(Icons.login),
              label: Text(isChinese ? '连接主机' : 'Connect'),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildJoinSessionCard(BuildContext context, bool isChinese, CollaborationService collab) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.success.withOpacity(0.08),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: AppColors.success.withOpacity(0.3)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.check_circle, color: AppColors.success),
              const SizedBox(width: 8),
              Text(
                isChinese ? '已连接到主机' : 'Connected to Host',
                style: const TextStyle(color: AppColors.success, fontWeight: FontWeight.w600),
              ),
            ],
          ),
          const SizedBox(height: 12),
          if (collab.hostAddress != null) Text('${isChinese ? '主机' : 'Host'}: ${collab.hostAddress}'),
          const SizedBox(height: 16),
          SizedBox(
            width: double.infinity,
            child: OutlinedButton.icon(
              onPressed: () => collab.disconnect(),
              icon: const Icon(Icons.logout),
              label: Text(isChinese ? '断开连接' : 'Disconnect'),
            ),
          ),
        ],
      ),
    );
  }
}
