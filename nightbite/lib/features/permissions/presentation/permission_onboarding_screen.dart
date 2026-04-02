import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:notification_listener_service/notification_listener_service.dart';
import '../../../core/theme/app_colors.dart';

class PermissionOnboardingScreen extends StatefulWidget {
  const PermissionOnboardingScreen({super.key});

  @override
  State<PermissionOnboardingScreen> createState() =>
      _PermissionOnboardingScreenState();
}

class _PermissionOnboardingScreenState
    extends State<PermissionOnboardingScreen> {
  bool _isPermissionGranted = false;
  bool _isLoading = false;
  String? _errorMessage;

  @override
  void initState() {
    super.initState();
    _checkPermission();
  }

  Future<void> _checkPermission() async {
    if (!mounted) return;
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });
    try {
      final isGranted =
          await NotificationListenerService.isPermissionGranted();
      if (!mounted) return;
      setState(() {
        _isPermissionGranted = isGranted;
        _isLoading = false;
      });
      debugPrint('[NightBite] Notification permission granted: $isGranted');
    } catch (e) {
      debugPrint('[NightBite] Error checking notification permission: $e');
      if (!mounted) return;
      setState(() {
        _isPermissionGranted = false;
        _isLoading = false;
        // Non-fatal: user can still proceed to manual entry
      });
    }
  }

  Future<void> _requestPermission() async {
    try {
      debugPrint('[NightBite] Requesting notification listener permission...');
      final acted = await NotificationListenerService.requestPermission();
      debugPrint('[NightBite] Permission request result: $acted');
      // After returning from system settings, re-check the actual state
      await _checkPermission();
    } catch (e) {
      debugPrint('[NightBite] Error requesting notification permission: $e');
      if (!mounted) return;
      setState(() {
        _errorMessage =
            'Could not open permission settings. Please enable manually in Settings → Apps → NightBite → Notification Access.';
      });
    }
  }

  void _continue() {
    debugPrint(
        '[NightBite] Continuing to main — permission: $_isPermissionGranted');
    context.go('/main');
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(24.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const Spacer(),
              const Icon(
                Icons.notifications_active_outlined,
                size: 80,
                color: AppColors.primary,
              ),
              const SizedBox(height: 32),
              const Text(
                'Auto-detect Food Orders',
                textAlign: TextAlign.center,
                style: TextStyle(
                  fontSize: 28,
                  fontWeight: FontWeight.bold,
                  color: AppColors.textPrimary,
                ),
              ),
              const SizedBox(height: 16),
              const Text(
                'NightBite AI uses your notifications to instantly analyze food orders from apps like Swiggy and Zomato.\n\nWithout this, you can still enter food manually.',
                textAlign: TextAlign.center,
                style: TextStyle(
                  fontSize: 16,
                  color: AppColors.textSecondary,
                  height: 1.5,
                ),
              ),
              const Spacer(),

              // Error message (non-fatal)
              if (_errorMessage != null) ...[
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: AppColors.riskHigh.withValues(alpha: 0.1),
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(
                        color: AppColors.riskHigh.withValues(alpha: 0.4)),
                  ),
                  child: Text(
                    _errorMessage!,
                    textAlign: TextAlign.center,
                    style: const TextStyle(
                      color: AppColors.riskHigh,
                      fontSize: 13,
                    ),
                  ),
                ),
                const SizedBox(height: 16),
              ],

              // Permission status
              if (_isLoading)
                const Center(child: CircularProgressIndicator())
              else if (_isPermissionGranted)
                Container(
                  padding: const EdgeInsets.all(16),
                  decoration: BoxDecoration(
                    color: AppColors.riskLow.withValues(alpha: 0.1),
                    borderRadius: BorderRadius.circular(16),
                    border: Border.all(
                        color: AppColors.riskLow.withValues(alpha: 0.5)),
                  ),
                  child: const Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(Icons.check_circle, color: AppColors.riskLow),
                      SizedBox(width: 8),
                      Text(
                        'Permission Granted!',
                        style: TextStyle(
                          color: AppColors.riskLow,
                          fontWeight: FontWeight.bold,
                          fontSize: 16,
                        ),
                      ),
                    ],
                  ),
                ),

              const SizedBox(height: 32),

              if (!_isPermissionGranted && !_isLoading)
                ElevatedButton(
                  onPressed: _requestPermission,
                  child: const Text('Enable Notification Access'),
                ),
              const SizedBox(height: 16),
              TextButton(
                onPressed: _continue,
                child: Text(
                  _isPermissionGranted ? 'Continue' : 'Skip & Enter Manually',
                  style: TextStyle(
                    color: _isPermissionGranted
                        ? AppColors.primaryLight
                        : AppColors.textMuted,
                    fontSize: 16,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
              const SizedBox(height: 16),
            ],
          ),
        ),
      ),
    );
  }
}
