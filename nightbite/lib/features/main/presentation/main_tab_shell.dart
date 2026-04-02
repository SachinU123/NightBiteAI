import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/theme/app_colors_extension.dart';
import '../../../core/services/notification_ingestion_service.dart';
import '../providers/chat_provider.dart';
import 'tabs/home_tab.dart';
import 'tabs/history_tab.dart';
import 'tabs/ai_coach_tab.dart';
import 'tabs/profile_tab.dart';

class MainTabShell extends ConsumerStatefulWidget {
  const MainTabShell({super.key});

  @override
  ConsumerState<MainTabShell> createState() => _MainTabShellState();
}

class _MainTabShellState extends ConsumerState<MainTabShell> {
  int _currentIndex = 0;
  NotificationIngestionService? _ingestionService;

  final List<Widget> _tabs = const [
    HomeTab(),
    HistoryTab(),
    AiCoachTab(),
    ProfileTab(),
  ];

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _startNotificationIngestion();
    });
  }

  void _startNotificationIngestion() {
    try {
      _ingestionService = NotificationIngestionService(ref);
      _ingestionService!.startListening();
      debugPrint('[NightBite] Notification ingestion service started.');
    } catch (e) {
      debugPrint('[NightBite] Notification ingestion service unavailable: $e');
    }
  }

  @override
  void dispose() {
    _ingestionService?.stopListening();
    super.dispose();
  }

  /// Called from quick actions to open AI Coach with a prefilled prompt.
  /// Does NOT auto-send — user can edit and submit.
  void navigateToAiCoachWithPrefill(String prompt) {
    setState(() => _currentIndex = 2); // index 2 = AI Coach
    ref.read(chatProvider.notifier).prefillMessage(prompt);
  }

  @override
  Widget build(BuildContext context) {
    final colors = context.appColors;

    // Listen for quick-action navigation requests from HomeTab
    ref.listen(homeNavigationRequestProvider, (_, targetIndex) {
      if (targetIndex != null) {
        setState(() => _currentIndex = targetIndex);
        ref.read(homeNavigationRequestProvider.notifier).consumed();
      }
    });

    // Show snackbar when a real food order is detected from Zomato/Swiggy
    ref.listen(lastIngestionResultProvider, (_, result) {
      if (result != null && result.isOrder && result.isFoodRelated) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Row(
              children: [
                const Icon(Icons.notifications_active, color: Colors.white, size: 18),
                const SizedBox(width: 10),
                Expanded(
                  child: Text(
                    '🍕 ${result.platformName ?? "Food"} order captured! '
                    'Risk score: ${result.riskScore?.toStringAsFixed(1) ?? "N/A"}/10',
                    style: const TextStyle(color: Colors.white, fontSize: 13),
                  ),
                ),
              ],
            ),
            backgroundColor: colors.riskHigh,
            duration: const Duration(seconds: 4),
            behavior: SnackBarBehavior.floating,
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
          ),
        );
      }
    });

    return Scaffold(
      backgroundColor: colors.background,
      body: SafeArea(
        child: IndexedStack(
          index: _currentIndex,
          children: _tabs,
        ),
      ),
      bottomNavigationBar: Container(
        decoration: BoxDecoration(
          color: colors.surface,
          border: Border(top: BorderSide(color: colors.divider, width: 1.0)),
        ),
        child: NavigationBar(
          selectedIndex: _currentIndex,
          onDestinationSelected: (index) {
            setState(() => _currentIndex = index);
          },
          backgroundColor: colors.surface,
          indicatorColor: colors.primary.withValues(alpha: 0.2),
          destinations: [
            NavigationDestination(
              icon: const Icon(Icons.home_outlined),
              selectedIcon: Icon(Icons.home, color: colors.primaryLight),
              label: 'Home',
            ),
            NavigationDestination(
              icon: const Icon(Icons.history_outlined),
              selectedIcon: Icon(Icons.history, color: colors.primaryLight),
              label: 'History',
            ),
            NavigationDestination(
              icon: const Icon(Icons.psychology_outlined),
              selectedIcon: Icon(Icons.psychology, color: colors.primaryLight),
              label: 'AI Coach',
            ),
            NavigationDestination(
              icon: const Icon(Icons.person_outline),
              selectedIcon: Icon(Icons.person, color: colors.primaryLight),
              label: 'Profile',
            ),
          ],
        ),
      ),
    );
  }
}
