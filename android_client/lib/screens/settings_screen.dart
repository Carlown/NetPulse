import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:package_info_plus/package_info_plus.dart';
import '../services/settings_service.dart';
import '../services/auth_manager.dart';
import '../theme/colors.dart';
import '../utils/constants.dart';

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  String _appVersion = '1.0.0';

  @override
  void initState() {
    super.initState();
    _loadVersion();
  }

  Future<void> _loadVersion() async {
    try {
      final info = await PackageInfo.fromPlatform();
      setState(() => _appVersion = info.version);
    } catch (_) {}
  }

  @override
  Widget build(BuildContext context) {
    final isChinese = context.watch<SettingsService>().isChinese;
    final settings = context.watch<SettingsService>();
    final authManager = context.watch<AuthManager>();

    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        _buildSection(
          context,
          isChinese ? '外观' : 'Appearance',
          [
            ListTile(
              leading: const Icon(Icons.brightness_6),
              title: Text(isChinese ? '主题模式' : 'Theme Mode'),
              subtitle: Text(settings.themeName),
              trailing: DropdownButton<ThemeMode>(
                value: settings.themeMode,
                underline: const SizedBox(),
                items: [
                  DropdownMenuItem(value: ThemeMode.system, child: Text(isChinese ? '跟随系统' : 'System')),
                  DropdownMenuItem(value: ThemeMode.light, child: Text(isChinese ? '浅色' : 'Light')),
                  DropdownMenuItem(value: ThemeMode.dark, child: Text(isChinese ? '深色' : 'Dark')),
                ],
                onChanged: (v) => settings.setThemeMode(v ?? ThemeMode.system),
              ),
            ),
            ListTile(
              leading: const Icon(Icons.language),
              title: Text(isChinese ? '语言' : 'Language'),
              subtitle: Text(settings.languageName),
              trailing: DropdownButton<Locale>(
                value: settings.locale,
                underline: const SizedBox(),
                items: const [
                  DropdownMenuItem(value: Locale('zh', 'CN'), child: Text('简体中文')),
                  DropdownMenuItem(value: Locale('en', 'US'), child: Text('English')),
                ],
                onChanged: (v) => settings.setLocale(v ?? const Locale('zh', 'CN')),
              ),
            ),
          ],
        ),
        const SizedBox(height: 16),
        _buildSection(
          context,
          isChinese ? '压测默认值' : 'Stress Test Defaults',
          [
            ListTile(
              leading: const Icon(Icons.speed),
              title: Text(isChinese ? '默认 QPS' : 'Default QPS'),
              subtitle: Text('${settings.defaultQps} /s'),
              trailing: SizedBox(
                width: 100,
                child: Slider(
                  value: settings.defaultQps.toDouble(),
                  min: 10,
                  max: 1000,
                  divisions: 99,
                  label: '${settings.defaultQps}',
                  onChanged: (v) => settings.setDefaultQps(v.toInt()),
                ),
              ),
            ),
            ListTile(
              leading: const Icon(Icons.timer),
              title: Text(isChinese ? '默认持续时间' : 'Default Duration'),
              subtitle: Text('${settings.defaultDuration} ${isChinese ? '秒' : 's'}'),
              trailing: SizedBox(
                width: 100,
                child: Slider(
                  value: settings.defaultDuration.toDouble(),
                  min: 5,
                  max: 300,
                  divisions: 59,
                  label: '${settings.defaultDuration}',
                  onChanged: (v) => settings.setDefaultDuration(v.toInt()),
                ),
              ),
            ),
            SwitchListTile(
              secondary: const Icon(Icons.shield),
              title: Text(isChinese ? '启用限速' : 'Enable Rate Limiter'),
              subtitle: Text(isChinese ? '令牌桶全局限速' : 'Token bucket global rate limit'),
              value: settings.rateLimiterEnabled,
              onChanged: (v) => settings.setRateLimiterEnabled(v),
            ),
            SwitchListTile(
              secondary: const Icon(Icons.screen_lock_portrait),
              title: Text(isChinese ? '测试时保持亮屏' : 'Keep Screen Awake'),
              value: settings.wakelockEnabled,
              onChanged: (v) => settings.setWakelockEnabled(v),
            ),
          ],
        ),
        const SizedBox(height: 16),
        _buildSection(
          context,
          isChinese ? '合规与审计' : 'Compliance & Audit',
          [
            SwitchListTile(
              secondary: const Icon(Icons.assignment),
              title: Text(isChinese ? '启用审计日志' : 'Enable Audit Logging'),
              value: settings.auditLoggingEnabled,
              onChanged: (v) => settings.setAuditLoggingEnabled(v),
            ),
            ListTile(
              leading: const Icon(Icons.verified_user),
              title: Text(isChinese ? '已授权目标' : 'Authorized Targets'),
              subtitle: Text('${authManager.authorizedTargets.length} ${isChinese ? '个' : 'targets'}'),
              trailing: const Icon(Icons.chevron_right),
              onTap: () => _showAuthorizedTargets(context, isChinese, authManager),
            ),
            ListTile(
              leading: const Icon(Icons.history),
              title: Text(isChinese ? '审计日志' : 'Audit Logs'),
              subtitle: Text('${authManager.auditLogs.length} ${isChinese ? '条记录' : 'entries'}'),
              trailing: const Icon(Icons.chevron_right),
              onTap: () => _showAuditLogs(context, isChinese, authManager),
            ),
          ],
        ),
        const SizedBox(height: 16),
        _buildSection(
          context,
          isChinese ? '关于' : 'About',
          [
            ListTile(
              leading: const Icon(Icons.info_outline),
              title: const Text('NetPulse'),
              subtitle: Text('${isChinese ? '版本' : 'Version'} $_appVersion'),
            ),
            ListTile(
              leading: const Icon(Icons.code),
              title: Text(isChinese ? '开源协议' : 'License'),
              subtitle: const Text('MIT License'),
            ),
            ListTile(
              leading: const Icon(Icons.link),
              title: Text(isChinese ? '项目地址' : 'Project URL'),
              subtitle: const Text('github.com/Carlown/NetPulse'),
              onTap: () {},
            ),
            ListTile(
              leading: const Icon(Icons.description),
              title: Text(isChinese ? '法律声明' : 'Legal Disclaimer'),
              trailing: const Icon(Icons.chevron_right),
              onTap: () => _showDisclaimer(context, isChinese),
            ),
          ],
        ),
        const SizedBox(height: 24),
        Center(
          child: Text(
            '${isChinese ? '基于 Flutter 构建' : 'Built with Flutter'}  |  MIT License',
            style: TextStyle(color: AppColors.textSecondary(context), fontSize: 12),
          ),
        ),
      ],
    );
  }

  Widget _buildSection(BuildContext context, String title, List<Widget> children) {
    return Container(
      decoration: BoxDecoration(
        color: AppColors.cardBackground(context),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: AppColors.borderColor(context)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 12, 16, 4),
            child: Text(
              title,
              style: Theme.of(context).textTheme.titleSmall?.copyWith(
                    color: AppColors.primary,
                    fontWeight: FontWeight.w600,
                  ),
            ),
          ),
          ...children,
        ],
      ),
    );
  }

  void _showAuthorizedTargets(BuildContext context, bool isChinese, AuthManager authManager) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      builder: (context) => DraggableScrollableSheet(
        initialChildSize: 0.6,
        minChildSize: 0.3,
        maxChildSize: 0.9,
        expand: false,
        builder: (context, scrollController) => Column(
          children: [
            Padding(
              padding: const EdgeInsets.all(16),
              child: Text(
                isChinese ? '已授权目标' : 'Authorized Targets',
                style: Theme.of(context).textTheme.titleLarge,
              ),
            ),
            Expanded(
              child: authManager.authorizedTargets.isEmpty
                  ? Center(child: Text(isChinese ? '暂无授权目标' : 'No authorized targets'))
                  : ListView.builder(
                      controller: scrollController,
                      itemCount: authManager.authorizedTargets.length,
                      itemBuilder: (context, index) {
                        final auth = authManager.authorizedTargets[index];
                        return ListTile(
                          leading: const Icon(Icons.verified, color: AppColors.success),
                          title: Text(auth.target),
                          subtitle: Text('${auth.note}\n${auth.authorizedAt.toLocal()}'),
                          isThreeLine: true,
                          trailing: IconButton(
                            icon: const Icon(Icons.delete_outline, color: AppColors.danger),
                            onPressed: () {
                              authManager.revokeAuthorization(auth.target);
                              Navigator.pop(context);
                            },
                          ),
                        );
                      },
                    ),
            ),
          ],
        ),
      ),
    );
  }

  void _showAuditLogs(BuildContext context, bool isChinese, AuthManager authManager) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      builder: (context) => DraggableScrollableSheet(
        initialChildSize: 0.7,
        minChildSize: 0.3,
        maxChildSize: 0.95,
        expand: false,
        builder: (context, scrollController) => Column(
          children: [
            Padding(
              padding: const EdgeInsets.all(16),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(isChinese ? '审计日志' : 'Audit Logs', style: Theme.of(context).textTheme.titleLarge),
                  TextButton.icon(
                    onPressed: () => authManager.clearAuditLogs(),
                    icon: const Icon(Icons.delete_sweep, size: 18),
                    label: Text(isChinese ? '清空' : 'Clear'),
                  ),
                ],
              ),
            ),
            Expanded(
              child: authManager.auditLogs.isEmpty
                  ? Center(child: Text(isChinese ? '暂无日志' : 'No logs'))
                  : ListView.builder(
                      controller: scrollController,
                      itemCount: authManager.auditLogs.length,
                      itemBuilder: (context, index) {
                        final log = authManager.auditLogs[index];
                        return ListTile(
                          leading: const Icon(Icons.receipt_long, size: 20),
                          title: Text(log.action, style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w600)),
                          subtitle: Text('${log.target}\n${log.details}', style: const TextStyle(fontSize: 12)),
                          isThreeLine: true,
                          trailing: Text(
                            '${log.timestamp.hour.toString().padLeft(2, '0')}:${log.timestamp.minute.toString().padLeft(2, '0')}',
                            style: const TextStyle(fontSize: 11),
                          ),
                        );
                      },
                    ),
            ),
          ],
        ),
      ),
    );
  }

  void _showDisclaimer(BuildContext context, bool isChinese) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(isChinese ? '法律声明' : 'Legal Disclaimer'),
        content: SingleChildScrollView(
          child: Text(
            isChinese
                ? '本工具仅允许对拥有明确书面授权的目标系统执行网络压力测试。未经授权对第三方系统进行压力测试可能违反相关法律法规。使用者需自行承担全部风险和法律责任。'
                : 'This tool may only be used to perform network stress testing on target systems for which you have explicit written authorization. Unauthorized testing may violate applicable laws. Users assume all risks and legal responsibilities.',
            style: const TextStyle(height: 1.6),
          ),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context), child: Text(isChinese ? '关闭' : 'Close')),
        ],
      ),
    );
  }
}
