import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../models/test_result.dart';
import '../services/stress_tester.dart';
import '../services/auth_manager.dart';
import '../services/settings_service.dart';
import '../theme/colors.dart';
import '../utils/constants.dart';
import '../utils/formatters.dart';
import '../widgets/protocol_selector.dart';
import '../widgets/target_auth_dialog.dart';
import '../widgets/busy_overlay.dart';

class StressTestScreen extends StatefulWidget {
  const StressTestScreen({super.key});

  @override
  State<StressTestScreen> createState() => _StressTestScreenState();
}

class _StressTestScreenState extends State<StressTestScreen> {
  final _targetController = TextEditingController();
  final _qpsController = TextEditingController(text: '${AppConstants.defaultQps}');
  final _durationController = TextEditingController(text: '${AppConstants.defaultDuration}');
  final _headersController = TextEditingController();
  final _bodyController = TextEditingController();

  TestProtocol _selectedProtocol = TestProtocol.http;
  String _selectedMethod = 'GET';

  @override
  void dispose() {
    _targetController.dispose();
    _qpsController.dispose();
    _durationController.dispose();
    _headersController.dispose();
    _bodyController.dispose();
    super.dispose();
  }

  Future<void> _startTest() async {
    final target = _targetController.text.trim();
    if (target.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('请输入目标地址')),
      );
      return;
    }

    final authManager = context.read<AuthManager>();
    if (!authManager.isTargetAuthorized(target)) {
      final result = await showDialog<bool>(
        context: context,
        builder: (_) => TargetAuthDialog(target: target),
      );
      if (result != true) return;
    }

    final qps = int.tryParse(_qpsController.text) ?? AppConstants.defaultQps;
    if (qps > AppConstants.highQpsThreshold) {
      final confirm = await showDialog<bool>(
        context: context,
        builder: (context) => AlertDialog(
          title: const Text('高 QPS 确认'),
          content: Text('您设置的 QPS 为 $qps，超过 ${AppConstants.highQpsThreshold} 的安全阈值。确认要继续吗？'),
          actions: [
            TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('取消')),
            ElevatedButton(onPressed: () => Navigator.pop(context, true), child: const Text('确认')),
          ],
        ),
      );
      if (confirm != true) return;
    }

    final duration = int.tryParse(_durationController.text) ?? AppConstants.defaultDuration;
    authManager.logTestStart(target, _selectedProtocol.name);

    await context.read<StressTester>().startTest(
          target: target,
          protocol: _selectedProtocol,
          qps: qps,
          duration: duration,
          httpMethod: _selectedMethod,
          headers: _parseHeaders(),
          body: _bodyController.text.isEmpty ? null : _bodyController.text,
        );
  }

  Map<String, String>? _parseHeaders() {
    final text = _headersController.text.trim();
    if (text.isEmpty) return null;
    final headers = <String, String>{};
    for (final line in text.split('\n')) {
      final parts = line.split(':');
      if (parts.length >= 2) {
        headers[parts[0].trim()] = parts.sublist(1).join(':').trim();
      }
    }
    return headers.isEmpty ? null : headers;
  }

  void _stopTest() {
    final tester = context.read<StressTester>();
    final result = tester.currentResult;
    tester.stopTest();
    if (result != null) {
      context.read<AuthManager>().logTestStop(
            result.target,
            'Total: ${result.totalRequests}, Success: ${result.successCount}, Failed: ${result.failedCount}',
          );
    }
  }

  @override
  Widget build(BuildContext context) {
    final isChinese = context.watch<SettingsService>().isChinese;
    final tester = context.watch<StressTester>();
    final result = tester.currentResult;

    return Stack(
      children: [
        ListView(
          padding: const EdgeInsets.all(16),
          children: [
            _buildConfigSection(context, isChinese),
            const SizedBox(height: 16),
            if (result != null) _buildResultSection(context, isChinese, result),
          ],
        ),
        if (tester.isRunning) const BusyOverlay(message: '压力测试进行中...'),
      ],
    );
  }

  Widget _buildConfigSection(BuildContext context, bool isChinese) {
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
            isChinese ? '测试配置' : 'Test Configuration',
            style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w600),
          ),
          const SizedBox(height: 16),
          TextField(
            controller: _targetController,
            decoration: InputDecoration(
              labelText: isChinese ? '目标地址' : 'Target URL',
              hintText: 'https://example.com/api',
              prefixIcon: const Icon(Icons.link),
            ),
          ),
          const SizedBox(height: 12),
          ProtocolSelector(
            selectedProtocol: _selectedProtocol,
            onProtocolChanged: (protocol) {
              setState(() => _selectedProtocol = protocol);
            },
          ),
          if (_selectedProtocol == TestProtocol.http || _selectedProtocol == TestProtocol.https) ...[
            const SizedBox(height: 12),
            DropdownButtonFormField<String>(
              value: _selectedMethod,
              decoration: InputDecoration(
                labelText: isChinese ? 'HTTP 方法' : 'HTTP Method',
              ),
              items: AppConstants.httpMethods.map((m) => DropdownMenuItem(value: m, child: Text(m))).toList(),
              onChanged: (v) => setState(() => _selectedMethod = v ?? 'GET'),
            ),
          ],
          const SizedBox(height: 12),
          Row(
            children: [
              Expanded(
                child: TextField(
                  controller: _qpsController,
                  decoration: InputDecoration(
                    labelText: isChinese ? 'QPS' : 'QPS',
                    suffixText: '/s',
                  ),
                  keyboardType: TextInputType.number,
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: TextField(
                  controller: _durationController,
                  decoration: InputDecoration(
                    labelText: isChinese ? '持续时间' : 'Duration',
                    suffixText: isChinese ? '秒' : 's',
                  ),
                  keyboardType: TextInputType.number,
                ),
              ),
            ],
          ),
          if (_selectedProtocol == TestProtocol.http || _selectedProtocol == TestProtocol.https) ...[
            const SizedBox(height: 12),
            TextField(
              controller: _headersController,
              decoration: InputDecoration(
                labelText: isChinese ? '请求头 (每行一个)' : 'Headers (one per line)',
                hintText: 'Content-Type: application/json',
              ),
              maxLines: 3,
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _bodyController,
              decoration: InputDecoration(
                labelText: isChinese ? '请求体' : 'Request Body',
              ),
              maxLines: 3,
            ),
          ],
          const SizedBox(height: 20),
          SizedBox(
            width: double.infinity,
            child: context.watch<StressTester>().isRunning
                ? ElevatedButton.icon(
                    onPressed: _stopTest,
                    icon: const Icon(Icons.stop),
                    label: Text(isChinese ? '停止测试' : 'Stop Test'),
                    style: ElevatedButton.styleFrom(backgroundColor: AppColors.danger),
                  )
                : ElevatedButton.icon(
                    onPressed: _startTest,
                    icon: const Icon(Icons.play_arrow),
                    label: Text(isChinese ? '开始测试' : 'Start Test'),
                  ),
          ),
        ],
      ),
    );
  }

  Widget _buildResultSection(BuildContext context, bool isChinese, TestResult result) {
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
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                isChinese ? '测试结果' : 'Test Results',
                style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w600),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(
                  color: result.isRunning ? AppColors.success.withOpacity(0.15) : AppColors.textSecondary(context).withOpacity(0.1),
                  borderRadius: BorderRadius.circular(4),
                ),
                child: Text(
                  result.isRunning ? (isChinese ? '运行中' : 'Running') : (isChinese ? '已完成' : 'Completed'),
                  style: TextStyle(
                    color: result.isRunning ? AppColors.success : AppColors.textSecondary(context),
                    fontSize: 12,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          _buildResultGrid(context, result),
          const SizedBox(height: 16),
          _buildLatencySection(context, isChinese, result),
        ],
      ),
    );
  }

  Widget _buildResultGrid(BuildContext context, TestResult result) {
    return GridView.count(
      crossAxisCount: 2,
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      childAspectRatio: 1.8,
      crossAxisSpacing: 12,
      mainAxisSpacing: 12,
      children: [
        _buildMetricTile('QPS', Formatters.formatQps(result.currentQps), AppColors.primary),
        _buildMetricTile('总请求', Formatters.formatNumber(result.totalRequests), AppColors.accent),
        _buildMetricTile('成功', '${result.successCount} (${Formatters.formatPercent(result.successRate)}%)', AppColors.success),
        _buildMetricTile('失败', '${result.failedCount} (${Formatters.formatPercent(result.errorRate)}%)', AppColors.danger),
        _buildMetricTile('已用时', Formatters.formatDuration(result.elapsed), AppColors.warning),
        _buildMetricTile('总流量', Formatters.formatBytes(result.totalBytesSent + result.totalBytesReceived), AppColors.primaryDark),
      ],
    );
  }

  Widget _buildMetricTile(String label, String value, Color color) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: color.withOpacity(0.08),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: color.withOpacity(0.2)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Text(label, style: TextStyle(fontSize: 12, color: AppColors.textSecondary(context))),
          const SizedBox(height: 4),
          Text(value, style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: color)),
        ],
      ),
    );
  }

  Widget _buildLatencySection(BuildContext context, bool isChinese, TestResult result) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          isChinese ? '延迟统计' : 'Latency Statistics',
          style: Theme.of(context).textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w600),
        ),
        const SizedBox(height: 12),
        Row(
          children: [
            Expanded(child: _buildLatencyTile('P50', result.latency.p50)),
            const SizedBox(width: 8),
            Expanded(child: _buildLatencyTile('P90', result.latency.p90)),
            const SizedBox(width: 8),
            Expanded(child: _buildLatencyTile('P99', result.latency.p99)),
          ],
        ),
        const SizedBox(height: 8),
        Row(
          children: [
            Expanded(child: _buildLatencyTile(isChinese ? '最小' : 'Min', result.latency.min)),
            const SizedBox(width: 8),
            Expanded(child: _buildLatencyTile(isChinese ? '平均' : 'Avg', result.latency.avg.toInt())),
            const SizedBox(width: 8),
            Expanded(child: _buildLatencyTile(isChinese ? '最大' : 'Max', result.latency.max)),
          ],
        ),
      ],
    );
  }

  Widget _buildLatencyTile(String label, int value) {
    return Container(
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: AppColors.cardBackground(context),
        borderRadius: BorderRadius.circular(6),
        border: Border.all(color: AppColors.borderColor(context)),
      ),
      child: Column(
        children: [
          Text(label, style: TextStyle(fontSize: 11, color: AppColors.textSecondary(context))),
          const SizedBox(height: 2),
          Text(Formatters.formatLatency(value), style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w600)),
        ],
      ),
    );
  }
}
