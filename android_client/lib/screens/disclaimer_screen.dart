import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../services/auth_manager.dart';
import '../theme/colors.dart';
import 'main_screen.dart';

class DisclaimerScreen extends StatelessWidget {
  const DisclaimerScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final isChinese = context.watch<SettingsService>().isChinese;

    return Scaffold(
      backgroundColor: isDark ? AppColors.darkBackground : AppColors.lightBackground,
      appBar: AppBar(
        title: Text(isChinese ? '法律声明' : 'Legal Disclaimer'),
        automaticallyImplyLeading: false,
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: AppColors.danger.withOpacity(0.1),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: AppColors.danger.withOpacity(0.3)),
              ),
              child: Row(
                children: [
                  const Icon(Icons.warning_amber_rounded, color: AppColors.danger, size: 32),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Text(
                      isChinese
                          ? '请仔细阅读以下法律声明，使用本工具即表示您同意所有条款。'
                          : 'Please read the following legal disclaimer carefully. By using this tool, you agree to all terms.',
                      style: const TextStyle(color: AppColors.danger, fontWeight: FontWeight.w600),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 24),
            _buildSection(
              context,
              isChinese ? '1. 合法使用' : '1. Lawful Use',
              isChinese
                  ? '本工具仅允许对您拥有明确书面授权的目标系统执行网络压力测试。未经授权对第三方系统进行压力测试可能违反《中华人民共和国网络安全法》、《刑法》第二百八十六条等相关法律法规，构成破坏计算机信息系统罪。'
                  : 'This tool may only be used to perform network stress testing on target systems for which you have explicit written authorization. Unauthorized stress testing of third-party systems may violate cybersecurity laws and constitute computer-related crimes.',
            ),
            const SizedBox(height: 16),
            _buildSection(
              context,
              isChinese ? '2. 责任声明' : '2. Liability Disclaimer',
              isChinese
                  ? '本工具按"现状"提供，作者不对因使用本工具造成的任何直接或间接损失承担责任。使用者需自行承担使用本工具的全部风险和法律责任。'
                  : 'This tool is provided "as is". The authors shall not be liable for any direct or indirect damages arising from the use of this tool. Users assume all risks and legal responsibilities associated with using this tool.',
            ),
            const SizedBox(height: 16),
            _buildSection(
              context,
              isChinese ? '3. 合规框架' : '3. Compliance Framework',
              isChinese
                  ? '本工具内置目标授权管理、QPS 限速、审计日志等合规功能。这些功能仅为辅助提醒，不能替代您的法律判断。您有责任确保所有测试活动符合当地法律法规。'
                  : 'This tool includes built-in compliance features such as target authorization, QPS rate limiting, and audit logging. These features are auxiliary reminders only and do not replace your legal judgment. You are responsible for ensuring all testing activities comply with local laws.',
            ),
            const SizedBox(height: 16),
            _buildSection(
              context,
              isChinese ? '4. 开源协议' : '4. Open Source License',
              isChinese
                  ? '本项目采用 MIT 开源协议。您可以自由使用、修改和分发，但需保留原始版权声明和许可声明。'
                  : 'This project is licensed under the MIT License. You may freely use, modify, and distribute it, provided you retain the original copyright and license notices.',
            ),
            const SizedBox(height: 32),
            SizedBox(
              width: double.infinity,
              child: ElevatedButton.icon(
                onPressed: () {
                  context.read<AuthManager>().acceptDisclaimer();
                  Navigator.of(context).pushReplacement(
                    MaterialPageRoute(builder: (_) => const MainScreen()),
                  );
                },
                icon: const Icon(Icons.check_circle_outline),
                label: Text(isChinese ? '我已阅读并同意上述声明' : 'I have read and agree to the above'),
                style: ElevatedButton.styleFrom(
                  padding: const EdgeInsets.symmetric(vertical: 16),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildSection(BuildContext context, String title, String content) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          title,
          style: Theme.of(context).textTheme.titleMedium?.copyWith(
                fontWeight: FontWeight.bold,
                color: AppColors.textPrimary(context),
              ),
        ),
        const SizedBox(height: 8),
        Text(
          content,
          style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                color: AppColors.textSecondary(context),
                height: 1.6,
              ),
        ),
      ],
    );
  }
}
