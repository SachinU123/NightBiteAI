// NightBite — Notification Ingestion Service
//
// STRICT FILTERING: Only processes notifications from supported food delivery
// apps. All other apps (WhatsApp, Gmail, SMS, etc.) are dropped immediately
// at the device level, before any backend call is made.
//
// Supported apps:
//   - Zomato  (com.application.zomato)
//   - Swiggy  (in.swiggy.android)
//
// Architecture:
//   NotificationListenerService (Android plugin)
//     → Package whitelist check  ← NEW: strict filter
//       → Content-level order keyword check  ← NEW
//         → Backend POST /api/v1/notifications/ingest
//           → Backend returns risk analysis
//
// IMPORTANT: Requires notification access permission in Android settings.
import 'dart:async';
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:notification_listener_service/notification_listener_service.dart';
import 'package:notification_listener_service/notification_event.dart';
import '../network/dio_client.dart';
import '../../features/main/providers/food_provider.dart';

/// State emitted after a notification is ingested
class NotificationIngestionResult {
  final bool success;
  final bool isFoodRelated;
  final bool isOrder;
  final String? platformName;
  final double? riskScore;
  final String? nudge;
  final String explanation;

  const NotificationIngestionResult({
    required this.success,
    required this.isFoodRelated,
    required this.isOrder,
    this.platformName,
    this.riskScore,
    this.nudge,
    required this.explanation,
  });
}

/// Notifier that holds the latest notification ingestion result
class IngestionResultNotifier extends Notifier<NotificationIngestionResult?> {
  @override
  NotificationIngestionResult? build() => null;

  void update(NotificationIngestionResult result) {
    state = result;
  }
}

/// Provider that holds the latest notification ingestion result
final lastIngestionResultProvider =
    NotifierProvider<IngestionResultNotifier, NotificationIngestionResult?>(
        IngestionResultNotifier.new);

/// Service that listens to Android notifications and sends them to backend
class NotificationIngestionService {
  StreamSubscription<ServiceNotificationEvent>? _subscription;
  final WidgetRef _ref;

  NotificationIngestionService(this._ref);

  /// Start listening for notifications. Call once after auth is confirmed.
  void startListening() {
    _subscription?.cancel();

    _subscription = NotificationListenerService.notificationsStream.listen(
      _onNotification,
      onError: (e) => debugPrint('[NightBite/NLS] Stream error: $e'),
      cancelOnError: false,
    );

    debugPrint('[NightBite/NLS] Notification listener stream started');
  }

  /// Stop listening (call on logout or dispose)
  void stopListening() {
    _subscription?.cancel();
    _subscription = null;
    debugPrint('[NightBite/NLS] Notification listener stream stopped');
  }

  /// Strict whitelist — ONLY these packages are processed.
  /// Everything else (WhatsApp, Gmail, SMS, social media) is silently dropped.
  static const _supportedPackages = {
    'com.application.zomato',
    'in.swiggy.android',
  };

  /// Friendly names for supported apps.
  static const _appNames = {
    'com.application.zomato': 'Zomato',
    'in.swiggy.android': 'Swiggy',
  };

  /// Content-level keywords that indicate a real order event (not promo spam).
  static const _orderKeywords = [
    'order', 'ordered', 'delivery', 'arriving', 'delivered',
    'preparing', 'on the way', 'out for delivery', 'restaurant',
    'item', 'items', 'total', 'eta', 'placed', 'accepted',
    'picked up', 'dispatched', 'payment', 'bill', 'invoice',
  ];

  Future<void> _onNotification(ServiceNotificationEvent event) async {
    final package = event.packageName ?? '';
    final title = (event.title ?? '').toLowerCase();
    final content = (event.content ?? '').toLowerCase();
    final combined = '$title $content';

    // ── GATE 1: Package whitelist ─────────────────────────────────────────────
    if (!_supportedPackages.contains(package)) {
      // Silently drop — not from a food delivery app
      return;
    }

    debugPrint('[NightBite/NLS] 📦 Whitelisted package: $package');
    debugPrint('[NightBite/NLS]   Title  : ${event.title}');
    debugPrint('[NightBite/NLS]   Content: ${event.content}');

    // ── GATE 2: Content keyword check ────────────────────────────────────────
    // Reject pure marketing/promotional notifications.
    final hasOrderKeyword = _orderKeywords.any((kw) => combined.contains(kw));
    if (!hasOrderKeyword) {
      debugPrint('[NightBite/NLS] ⛔ Rejected — no order keyword found in content');
      return;
    }

    debugPrint('[NightBite/NLS] ✅ Order keyword matched — forwarding to backend');

    // ── Forward to backend ────────────────────────────────────────────────────
    await _sendToBackend(
      appPackage: package,
      appName: _appNames[package] ?? package,
      title: event.title ?? '',
      text: event.content ?? '',
    );
  }

  Future<void> _sendToBackend({
    required String appPackage,
    required String appName,
    required String title,
    required String text,
  }) async {
    try {
      final dio = _ref.read(dioProvider);
      final response = await dio.post(
        '/notifications/ingest',
        data: {
          'app_package': appPackage,
          'app_name': appName,
          'title': title,
          'text': text,
          'posted_at': DateTime.now().toUtc().toIso8601String(),
        },
      );

      if (response.statusCode == 201 && response.data != null) {
        final data = response.data as Map<String, dynamic>;
        final isFoodRelated = data['is_food_related'] == true;
        final isOrder = data['is_order'] == true;

        debugPrint(
            '[NightBite/NLS] Backend response: food=$isFoodRelated, order=$isOrder');

        final result = NotificationIngestionResult(
          success: true,
          isFoodRelated: isFoodRelated,
          isOrder: isOrder,
          platformName: data['platform_name'],
          riskScore: (data['combined_risk_score'] as num?)?.toDouble(),
          nudge: data['smart_nudge'],
          explanation: data['explanation'] ?? '',
        );

        // Update the notification result state
        _ref.read(lastIngestionResultProvider.notifier).update(result);

        // If it's an actual food order, refresh the home & history providers
        if (isOrder && isFoodRelated) {
          debugPrint(
              '[NightBite/NLS] 🍕 Food order detected! Refreshing providers...');
          _ref.invalidate(latestFoodProvider);
          _ref.invalidate(historyProvider);
          _ref.invalidate(insightsProvider);
        }
      }
    } catch (e) {
      debugPrint('[NightBite/NLS] Backend ingestion failed: $e');
      // Don't rethrow — notification listener should never crash the app
    }
  }
}
