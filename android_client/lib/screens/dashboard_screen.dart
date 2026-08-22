import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:fl_chart/fl_chart.dart';
import '../services/system_monitor.dart';
import '../services/settings_service.dart';
import '../theme/colors.dart';
import '../utils/formatters.dart';
import '../widgets/stat_card.dart';

class DashboardScreen extends StatefulWidget {
  const DashboardScreen({super.key});

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<SystemMonitor>().startMonitoring();
    });
  }

  @override
  Widget build(BuildContext context) {
    final isChinese = context.watch<SettingsService>().isChinese;
    final monitor = context.watch<SystemMonitor>();
    final stats = monitor.currentStats;

    return RefreshIndicator(
      onRefresh: () async {
        context.read<SystemMonitor>().clearHistory();
      },
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Text(
            isChinese ? '系统资源监控' : 'System Resource Monitor',
            style: Theme.of(context).textTheme.titleLarge?.copyWith(
                  fontWeight: FontWeight.bold,
                ),
          ),
          const SizedBox(height: 16),
          Row(
            children: [
              Expanded(
                child: StatCard(
                  title: isChinese ? 'CPU 使用率' : 'CPU Usage',
                  value: Formatters.formatPercent(stats.cpuUsage),
                  icon: Icons.memory,
                  color: AppColors.primary,
                  progress: stats.cpuUsage / 100,
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: StatCard(
                  title: isChinese ? '内存使用率' : 'Memory Usage',
                  value: Formatters.formatPercent(stats.memoryUsage),
                  icon: Icons.storage,
                  color: AppColors.accent,
                  progress: stats.memoryUsage / 100,
                  subtitle: '${Formatters.formatBytes(stats.memoryUsed)} / ${Formatters.formatBytes(stats.memoryTotal)}',
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Row(
            children: [
              Expanded(
                child: StatCard(
                  title: isChinese ? '上传速率' : 'Upload Rate',
                  value: Formatters.formatBytesPerSecond(stats.networkSentRate),
                  icon: Icons.arrow_upward,
                  color: AppColors.success,
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: StatCard(
                  title: isChinese ? '下载速率' : 'Download Rate',
                  value: Formatters.formatBytesPerSecond(stats.networkReceivedRate),
                  icon: Icons.arrow_downward,
                  color: AppColors.warning,
                ),
              ),
            ],
          ),
          const SizedBox(height: 24),
          _buildChartCard(
            context,
            isChinese ? 'CPU & 内存趋势' : 'CPU & Memory Trend',
            _buildCpuMemoryChart(monitor.history),
          ),
          const SizedBox(height: 16),
          _buildChartCard(
            context,
            isChinese ? '网络流量趋势' : 'Network Traffic Trend',
            _buildNetworkChart(monitor.history),
          ),
          const SizedBox(height: 16),
          _buildNetworkInfoCard(context, isChinese, stats),
        ],
      ),
    );
  }

  Widget _buildChartCard(BuildContext context, String title, Widget chart) {
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
            title,
            style: Theme.of(context).textTheme.titleMedium?.copyWith(
                  fontWeight: FontWeight.w600,
                ),
          ),
          const SizedBox(height: 16),
          SizedBox(height: 180, child: chart),
        ],
      ),
    );
  }

  Widget _buildCpuMemoryChart(List history) {
    if (history.length < 2) {
      return const Center(child: CircularProgressIndicator());
    }

    final cpuSpots = <FlSpot>[];
    final memSpots = <FlSpot>[];

    for (int i = 0; i < history.length; i++) {
      cpuSpots.add(FlSpot(i.toDouble(), history[i].cpuUsage));
      memSpots.add(FlSpot(i.toDouble(), history[i].memoryUsage));
    }

    return LineChart(
      LineChartData(
        gridData: const FlGridData(show: true, drawVerticalLine: false),
        titlesData: const FlTitlesData(show: false),
        borderData: FlBorderData(show: false),
        minY: 0,
        maxY: 100,
        lineBarsData: [
          LineChartBarData(
            spots: cpuSpots,
            isCurved: true,
            color: AppColors.primary,
            barWidth: 2,
            dotData: const FlDotData(show: false),
            belowBarData: BarAreaData(
              show: true,
              color: AppColors.primary.withOpacity(0.1),
            ),
          ),
          LineChartBarData(
            spots: memSpots,
            isCurved: true,
            color: AppColors.accent,
            barWidth: 2,
            dotData: const FlDotData(show: false),
            belowBarData: BarAreaData(
              show: true,
              color: AppColors.accent.withOpacity(0.1),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildNetworkChart(List history) {
    if (history.length < 2) {
      return const Center(child: CircularProgressIndicator());
    }

    final upSpots = <FlSpot>[];
    final downSpots = <FlSpot>[];

    for (int i = 0; i < history.length; i++) {
      upSpots.add(FlSpot(i.toDouble(), (history[i].networkSentRate / 1024).toDouble()));
      downSpots.add(FlSpot(i.toDouble(), (history[i].networkReceivedRate / 1024).toDouble()));
    }

    return LineChart(
      LineChartData(
        gridData: const FlGridData(show: true, drawVerticalLine: false),
        titlesData: const FlTitlesData(show: false),
        borderData: FlBorderData(show: false),
        minY: 0,
        lineBarsData: [
          LineChartBarData(
            spots: upSpots,
            isCurved: true,
            color: AppColors.success,
            barWidth: 2,
            dotData: const FlDotData(show: false),
          ),
          LineChartBarData(
            spots: downSpots,
            isCurved: true,
            color: AppColors.warning,
            barWidth: 2,
            dotData: const FlDotData(show: false),
          ),
        ],
      ),
    );
  }

  Widget _buildNetworkInfoCard(BuildContext context, bool isChinese, dynamic stats) {
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
            isChinese ? '网络统计' : 'Network Statistics',
            style: Theme.of(context).textTheme.titleMedium?.copyWith(
                  fontWeight: FontWeight.w600,
                ),
          ),
          const SizedBox(height: 12),
          _buildInfoRow(isChinese ? '总上传' : 'Total Upload', Formatters.formatBytes(stats.networkSent)),
          _buildInfoRow(isChinese ? '总下载' : 'Total Download', Formatters.formatBytes(stats.networkReceived)),
          _buildInfoRow(isChinese ? '监控状态' : 'Monitor Status', context.watch<SystemMonitor>().isMonitoring ? (isChinese ? '运行中' : 'Running') : (isChinese ? '已停止' : 'Stopped')),
        ],
      ),
    );
  }

  Widget _buildInfoRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label, style: TextStyle(color: AppColors.textSecondary(context))),
          Text(value, style: const TextStyle(fontWeight: FontWeight.w600)),
        ],
      ),
    );
  }
}
