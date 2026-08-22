import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../services/auth_manager.dart';
import '../theme/colors.dart';

class TargetAuthDialog extends StatefulWidget {
  final String target;

  const TargetAuthDialog({super.key, required this.target});

  @override
  State<TargetAuthDialog> createState() => _TargetAuthDialogState();
}

class _TargetAuthDialogState extends State<TargetAuthDialog> {
  final _noteController = TextEditingController();
  bool _agreed = false;

  @override
  void dispose() {
    _noteController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Row(
        children: [
          Icon(Icons.verified_user, color: AppColors.primary),
          SizedBox(width: 8),
          Text('目标授权'),
        ],
      ),
      content: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: AppColors.primary.withOpacity(0.08),
                borderRadius: BorderRadius.circular(6),
              ),
              child: Row(
                children: [
                  const Icon(Icons.link, size: 16, color: AppColors.primary),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      widget.target,
                      style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 16),
            const Text(
              '请确认您对该目标拥有明确的书面授权，可以进行网络压力测试。未经授权的测试可能违反法律法规。',
              style: TextStyle(fontSize: 13, height: 1.5),
            ),
            const SizedBox(height: 16),
            TextField(
              controller: _noteController,
              decoration: const InputDecoration(
                labelText: '授权备注',
                hintText: '例如：内部测试环境，已获运维团队授权',
              ),
              maxLines: 2,
            ),
            const SizedBox(height: 12),
            CheckboxListTile(
              contentPadding: EdgeInsets.zero,
              title: const Text(
                '我确认对该目标拥有合法授权，并承担全部法律责任',
                style: TextStyle(fontSize: 13),
              ),
              value: _agreed,
              onChanged: (v) => setState(() => _agreed = v ?? false),
              controlAffinity: ListTileControlAffinity.leading,
            ),
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context, false),
          child: const Text('取消'),
        ),
        ElevatedButton.icon(
          onPressed: _agreed
              ? () {
                  context.read<AuthManager>().authorizeTarget(
                        target: widget.target,
                        note: _noteController.text.trim().isEmpty ? '未填写备注' : _noteController.text.trim(),
                      );
                  Navigator.pop(context, true);
                }
              : null,
          icon: const Icon(Icons.check),
          label: const Text('确认授权'),
        ),
      ],
    );
  }
}
