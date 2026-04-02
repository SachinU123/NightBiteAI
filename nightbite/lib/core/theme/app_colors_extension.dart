import 'package:flutter/material.dart';

class NightBiteColors extends ThemeExtension<NightBiteColors> {
  final Color background;
  final Color surface;
  final Color surfaceHighlight;
  final Color primary;
  final Color primaryLight;
  final Color secondary;
  final Color textPrimary;
  final Color textSecondary;
  final Color textMuted;
  final Color riskLow;
  final Color riskMedium;
  final Color riskHigh;
  final Color riskExtreme;
  final Color divider;
  final Color success;
  final Color warning;

  const NightBiteColors({
    required this.background,
    required this.surface,
    required this.surfaceHighlight,
    required this.primary,
    required this.primaryLight,
    required this.secondary,
    required this.textPrimary,
    required this.textSecondary,
    required this.textMuted,
    required this.riskLow,
    required this.riskMedium,
    required this.riskHigh,
    required this.riskExtreme,
    required this.divider,
    required this.success,
    required this.warning,
  });

  @override
  NightBiteColors copyWith({
    Color? background,
    Color? surface,
    Color? surfaceHighlight,
    Color? primary,
    Color? primaryLight,
    Color? secondary,
    Color? textPrimary,
    Color? textSecondary,
    Color? textMuted,
    Color? riskLow,
    Color? riskMedium,
    Color? riskHigh,
    Color? riskExtreme,
    Color? divider,
    Color? success,
    Color? warning,
  }) {
    return NightBiteColors(
      background: background ?? this.background,
      surface: surface ?? this.surface,
      surfaceHighlight: surfaceHighlight ?? this.surfaceHighlight,
      primary: primary ?? this.primary,
      primaryLight: primaryLight ?? this.primaryLight,
      secondary: secondary ?? this.secondary,
      textPrimary: textPrimary ?? this.textPrimary,
      textSecondary: textSecondary ?? this.textSecondary,
      textMuted: textMuted ?? this.textMuted,
      riskLow: riskLow ?? this.riskLow,
      riskMedium: riskMedium ?? this.riskMedium,
      riskHigh: riskHigh ?? this.riskHigh,
      riskExtreme: riskExtreme ?? this.riskExtreme,
      divider: divider ?? this.divider,
      success: success ?? this.success,
      warning: warning ?? this.warning,
    );
  }

  @override
  NightBiteColors lerp(ThemeExtension<NightBiteColors>? other, double t) {
    if (other is! NightBiteColors) return this;
    return NightBiteColors(
      background: Color.lerp(background, other.background, t)!,
      surface: Color.lerp(surface, other.surface, t)!,
      surfaceHighlight: Color.lerp(surfaceHighlight, other.surfaceHighlight, t)!,
      primary: Color.lerp(primary, other.primary, t)!,
      primaryLight: Color.lerp(primaryLight, other.primaryLight, t)!,
      secondary: Color.lerp(secondary, other.secondary, t)!,
      textPrimary: Color.lerp(textPrimary, other.textPrimary, t)!,
      textSecondary: Color.lerp(textSecondary, other.textSecondary, t)!,
      textMuted: Color.lerp(textMuted, other.textMuted, t)!,
      riskLow: Color.lerp(riskLow, other.riskLow, t)!,
      riskMedium: Color.lerp(riskMedium, other.riskMedium, t)!,
      riskHigh: Color.lerp(riskHigh, other.riskHigh, t)!,
      riskExtreme: Color.lerp(riskExtreme, other.riskExtreme, t)!,
      divider: Color.lerp(divider, other.divider, t)!,
      success: Color.lerp(success, other.success, t)!,
      warning: Color.lerp(warning, other.warning, t)!,
    );
  }

  static const dark = NightBiteColors(
    background: Color(0xFF0B101D),
    surface: Color(0xFF161E30),
    surfaceHighlight: Color(0xFF1E2840),
    primary: Color(0xFF7C3AED),
    primaryLight: Color(0xFF9F6BEE),
    secondary: Color(0xFFFACC15),
    textPrimary: Color(0xFFF8FAFC),
    textSecondary: Color(0xFF94A3B8),
    textMuted: Color(0xFF64748B),
    riskLow: Color(0xFF10B981),
    riskMedium: Color(0xFFF59E0B),
    riskHigh: Color(0xFFEF4444),
    riskExtreme: Color(0xFF7F1D1D),
    divider: Color(0xFF334155),
    success: Color(0xFF10B981),
    warning: Color(0xFFF59E0B),
  );

  static const light = NightBiteColors(
    background: Color(0xFFF8FAFC),
    surface: Color(0xFFFFFFFF),
    surfaceHighlight: Color(0xFFF1F5F9),
    primary: Color(0xFF7C3AED),
    primaryLight: Color(0xFF9F6BEE),
    secondary: Color(0xFFFACC15),
    textPrimary: Color(0xFF0F172A),
    textSecondary: Color(0xFF475569),
    textMuted: Color(0xFF94A3B8),
    riskLow: Color(0xFF10B981),
    riskMedium: Color(0xFFF59E0B),
    riskHigh: Color(0xFFEF4444),
    riskExtreme: Color(0xFFB91C1C),
    divider: Color(0xFFE2E8F0),
    success: Color(0xFF10B981),
    warning: Color(0xFFF59E0B),
  );
}

extension NightBiteThemeExt on BuildContext {
  NightBiteColors get appColors => Theme.of(this).extension<NightBiteColors>()!;
}
