import 'package:flutter/material.dart';
import '../models/test_result.dart';
import '../theme/colors.dart';

class ProtocolSelector extends StatelessWidget {
  final TestProtocol selectedProtocol;
  final ValueChanged<TestProtocol> onProtocolChanged;

  const ProtocolSelector({
    super.key,
    required this.selectedProtocol,
    required this.onProtocolChanged,
  });

  @override
  Widget build(BuildContext context) {
    final protocols = TestProtocol.values;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          '协议',
          style: TextStyle(
            fontSize: 12,
            color: AppColors.textSecondary(context),
            fontWeight: FontWeight.w500,
          ),
        ),
        const SizedBox(height: 8),
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: protocols.map((protocol) {
            final isSelected = protocol == selectedProtocol;
            return GestureDetector(
              onTap: () => onProtocolChanged(protocol),
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                decoration: BoxDecoration(
                  color: isSelected ? AppColors.primary : Colors.transparent,
                  borderRadius: BorderRadius.circular(6),
                  border: Border.all(
                    color: isSelected ? AppColors.primary : AppColors.borderColor(context),
                  ),
                ),
                child: Text(
                  protocol.name,
                  style: TextStyle(
                    color: isSelected ? Colors.white : AppColors.textPrimary(context),
                    fontWeight: isSelected ? FontWeight.w600 : FontWeight.normal,
                    fontSize: 13,
                  ),
                ),
              ),
            );
          }).toList(),
        ),
      ],
    );
  }
}
