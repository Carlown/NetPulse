import 'package:flutter/material.dart';

class AppColors {
  // Primary brand colors - Fluent Design blue
  static const Color primary = Color(0xFF0078D4);
  static const Color primaryLight = Color(0xFF40A0FF);
  static const Color primaryDark = Color(0xFF005A9E);

  // Accent colors
  static const Color accent = Color(0xFF00B7C3);
  static const Color success = Color(0xFF107C10);
  static const Color warning = Color(0xFFB45309);
  static const Color danger = Color(0xFFD13438);

  // Light theme
  static const Color lightBackground = Color(0xFFF3F3F3);
  static const Color lightCard = Color(0xFFFFFFFF);
  static const Color lightBorder = Color(0xFFE5E5E5);
  static const Color lightText = Color(0xFF1A1A1A);
  static const Color lightTextSecondary = Color(0xFF616161);
  static const Color lightTextTertiary = Color(0xFFA0A0A0);

  // Dark theme
  static const Color darkBackground = Color(0xFF202020);
  static const Color darkCard = Color(0xFF2D2D2D);
  static const Color darkBorder = Color(0xFF3D3D3D);
  static const Color darkText = Color(0xFFF3F3F3);
  static const Color darkTextSecondary = Color(0xFFB0B0B0);
  static const Color darkTextTertiary = Color(0xFF707070);

  // Chart colors
  static const List<Color> chartPalette = [
    primary,
    accent,
    success,
    warning,
    danger,
    Color(0xFF8764B8),
    Color(0xFFC239B3),
    Color(0xFFE3008C),
  ];

  static Color textPrimary(BuildContext context) {
    return Theme.of(context).brightness == Brightness.dark
        ? darkText
        : lightText;
  }

  static Color textSecondary(BuildContext context) {
    return Theme.of(context).brightness == Brightness.dark
        ? darkTextSecondary
        : lightTextSecondary;
  }

  static Color cardBackground(BuildContext context) {
    return Theme.of(context).brightness == Brightness.dark
        ? darkCard
        : lightCard;
  }

  static Color borderColor(BuildContext context) {
    return Theme.of(context).brightness == Brightness.dark
        ? darkBorder
        : lightBorder;
  }
}
