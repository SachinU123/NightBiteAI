import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'app_colors_extension.dart';

class AppTheme {
  static ThemeData get darkTheme {
    return ThemeData(
      useMaterial3: true,
      brightness: Brightness.dark,
      scaffoldBackgroundColor: NightBiteColors.dark.background,
      colorScheme: ColorScheme.dark(
        primary: NightBiteColors.dark.primary,
        secondary: NightBiteColors.dark.secondary,
        surface: NightBiteColors.dark.surface,
        error: NightBiteColors.dark.riskHigh,
      ),
      extensions: const [
        NightBiteColors.dark,
      ],
      textTheme: GoogleFonts.outfitTextTheme().apply(
        bodyColor: NightBiteColors.dark.textPrimary,
        displayColor: NightBiteColors.dark.textPrimary,
      ),
      appBarTheme: AppBarTheme(
        backgroundColor: Colors.transparent,
        elevation: 0,
        centerTitle: false,
        iconTheme: IconThemeData(color: NightBiteColors.dark.textPrimary),
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: NightBiteColors.dark.primary,
          foregroundColor: Colors.white,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(16),
          ),
          padding: const EdgeInsets.symmetric(vertical: 16, horizontal: 24),
          textStyle: GoogleFonts.outfit(
            fontWeight: FontWeight.w600,
            fontSize: 16,
          ),
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: NightBiteColors.dark.surfaceHighlight,
        contentPadding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(16),
          borderSide: BorderSide.none,
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(16),
          borderSide: BorderSide.none,
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(16),
          borderSide: BorderSide(color: NightBiteColors.dark.primary, width: 2),
        ),
        hintStyle: TextStyle(color: NightBiteColors.dark.textMuted),
      ),
      cardTheme: CardThemeData(
        color: NightBiteColors.dark.surface,
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(20),
        ),
        margin: const EdgeInsets.symmetric(vertical: 8),
      ),
    );
  }

  static ThemeData get lightTheme {
    return ThemeData(
      useMaterial3: true,
      brightness: Brightness.light,
      scaffoldBackgroundColor: NightBiteColors.light.background,
      colorScheme: ColorScheme.light(
        primary: NightBiteColors.light.primary,
        secondary: NightBiteColors.light.secondary,
        surface: NightBiteColors.light.surface,
        error: NightBiteColors.light.riskHigh,
      ),
      extensions: const [
        NightBiteColors.light,
      ],
      textTheme: GoogleFonts.outfitTextTheme().apply(
        bodyColor: NightBiteColors.light.textPrimary,
        displayColor: NightBiteColors.light.textPrimary,
      ),
      appBarTheme: AppBarTheme(
        backgroundColor: Colors.transparent,
        elevation: 0,
        centerTitle: false,
        iconTheme: IconThemeData(color: NightBiteColors.light.textPrimary),
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: NightBiteColors.light.primary,
          foregroundColor: Colors.white,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(16),
          ),
          padding: const EdgeInsets.symmetric(vertical: 16, horizontal: 24),
          textStyle: GoogleFonts.outfit(
            fontWeight: FontWeight.w600,
            fontSize: 16,
          ),
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: NightBiteColors.light.surfaceHighlight,
        contentPadding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(16),
          borderSide: BorderSide.none,
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(16),
          borderSide: BorderSide.none,
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(16),
          borderSide: BorderSide(color: NightBiteColors.light.primary, width: 2),
        ),
        hintStyle: TextStyle(color: NightBiteColors.light.textMuted),
      ),
      cardTheme: CardThemeData(
        color: NightBiteColors.light.surface,
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(20),
        ),
        margin: const EdgeInsets.symmetric(vertical: 8),
      ),
    );
  }
}
