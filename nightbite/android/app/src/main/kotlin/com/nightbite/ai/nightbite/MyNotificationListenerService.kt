package com.nightbite.ai.nightbite

import android.service.notification.NotificationListenerService
import android.service.notification.StatusBarNotification
import android.util.Log

/**
 * NightBite Custom Notification Listener — INACTIVE / REFERENCE ONLY
 *
 * This class is NOT registered in AndroidManifest.xml. The Flutter plugin
 * `notification_listener_service` handles notification listening via its own
 * registered service and bridges events to Dart.
 *
 * This file is kept as a reference implementation that is:
 *   - In the correct package (com.nightbite.ai.nightbite)
 *   - Null-safe and crash-proof
 *   - Uses Android Log instead of println()
 *
 * If you ever need to reactivate this as the primary listener:
 *   1. Remove the notification_listener_service plugin from pubspec.yaml
 *   2. Add this service to AndroidManifest.xml with the correct name:
 *      android:name=".MyNotificationListenerService"
 *   3. Set up a MethodChannel to bridge events to Flutter
 */
class MyNotificationListenerService : NotificationListenerService() {

    companion object {
        private const val TAG = "NightBite/NLS"
        private val FOOD_PACKAGES = setOf(
            "in.swiggy.android",
            "com.application.zomato",
            "com.zomato.order",
        )
    }

    override fun onListenerConnected() {
        super.onListenerConnected()
        Log.i(TAG, "Notification listener connected")
    }

    override fun onListenerDisconnected() {
        super.onListenerDisconnected()
        Log.w(TAG, "Notification listener disconnected")
    }

    override fun onNotificationPosted(sbn: StatusBarNotification?) {
        if (sbn == null) return

        try {
            val packageName = sbn.packageName ?: return

            // Only process food delivery apps — ignore all others
            if (packageName !in FOOD_PACKAGES) return

            val notification = sbn.notification ?: return
            val extras = notification.extras ?: return

            val title = extras.getString("android.title") ?: "(no title)"
            val text = extras.getCharSequence("android.text")?.toString() ?: "(no text)"

            Log.d(TAG, "Food notification from: $packageName")
            Log.d(TAG, "  Title: $title")
            Log.d(TAG, "  Text : $text")

            // TODO: Forward to Flutter via MethodChannel when this service is activated
            // bridgeToFlutter(packageName, title, text)

        } catch (e: Exception) {
            Log.e(TAG, "Error processing notification — ignored safely", e)
        }
    }

    override fun onNotificationRemoved(sbn: StatusBarNotification?) {
        // No-op: we don't track removals
    }
}