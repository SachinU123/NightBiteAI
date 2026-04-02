import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/theme/app_colors.dart';

class SplashScreen extends ConsumerWidget {
  const SplashScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return const Scaffold(
      backgroundColor: AppColors.background,
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.nightlight_round, size: 80, color: AppColors.primary),
            SizedBox(height: 24),
            Text(
              'NightBite AI',
              style: TextStyle(
                fontSize: 32,
                fontWeight: FontWeight.bold,
                color: AppColors.textPrimary,
              ),
            ),
            SizedBox(height: 16),
            CircularProgressIndicator(color: AppColors.primary),
          ],
        ),
      ),
    );
  }
}
