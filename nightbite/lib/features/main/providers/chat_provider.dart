import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../../core/network/dio_client.dart';

// ─────────────────────────────────────────────────────────────────────────────
// Models
// ─────────────────────────────────────────────────────────────────────────────

class ChatMessage {
  final String text;
  final bool isUser;
  final bool isError;

  const ChatMessage({
    required this.text,
    required this.isUser,
    this.isError = false,
  });
}

class ChatState {
  final List<ChatMessage> messages;
  final bool isLoading;
  final String? pendingPrefill; // prefill text from quick actions

  const ChatState({
    required this.messages,
    this.isLoading = false,
    this.pendingPrefill,
  });

  ChatState copyWith({
    List<ChatMessage>? messages,
    bool? isLoading,
    String? pendingPrefill,
    bool clearPrefill = false,
  }) =>
      ChatState(
        messages: messages ?? this.messages,
        isLoading: isLoading ?? this.isLoading,
        pendingPrefill: clearPrefill ? null : (pendingPrefill ?? this.pendingPrefill),
      );
}

// ─────────────────────────────────────────────────────────────────────────────
// Notifier
// ─────────────────────────────────────────────────────────────────────────────

class ChatNotifier extends Notifier<ChatState> {
  static const _welcomeMsg = ChatMessage(
    text:
        "Hi! I'm your NightBite AI Coach 🌙\nAsk me anything about your late-night eating habits, get healthier swaps, or let me analyze your patterns!",
    isUser: false,
  );

  @override
  ChatState build() => const ChatState(messages: [_welcomeMsg]);

  /// Set a prefilled prompt (from quick action buttons) — does NOT auto-send.
  void prefillMessage(String text) {
    state = state.copyWith(pendingPrefill: text);
  }

  /// Clears the pending prefill after the UI consumes it.
  void clearPrefill() {
    state = state.copyWith(clearPrefill: true);
  }

  Future<void> sendMessage(String text) async {
    final trimmed = text.trim();
    if (trimmed.isEmpty || state.isLoading) return;

    // Add user bubble immediately
    state = state.copyWith(
      messages: [...state.messages, ChatMessage(text: trimmed, isUser: true)],
      isLoading: true,
      clearPrefill: true,
    );

    // --- Strategy 1: Backend /chat (authenticated, uses Claude + user history) ---
    String? reply = await _callBackendAuth(trimmed);

    // Check if auth backend returned a structured error
    if (reply != null && reply.startsWith('__error__:')) {
      _addError(reply.substring('__error__:'.length));
      return;
    }

    // --- Strategy 2: Backend /chat/public fallback (no history context) ---
    if (reply == null) {
      debugPrint('[ChatBot] Auth endpoint failed, trying /chat/public');
      reply = await _callBackendPublic(trimmed);
    }

    // If both backends returned null — surface a real error (do NOT fake AI)
    if (reply == null || reply.isEmpty) {
      _addError(
        'AI Coach is unavailable right now. Please check your connection or ensure the backend server is running.'
      );
      return;
    }

    state = state.copyWith(
      messages: [...state.messages, ChatMessage(text: reply, isUser: false)],
      isLoading: false,
    );
  }

  /// Call the authenticated backend Claude endpoint (includes user history context)
  Future<String?> _callBackendAuth(String message) async {
    try {
      debugPrint('[ChatBot] Calling backend /chat with auth...');
      final dio = ref.read(dioProvider);
      final response = await dio
          .post(
            '/chat',
            data: {'message': message},
            options: Options(
              sendTimeout: const Duration(seconds: 10),
              receiveTimeout: const Duration(seconds: 45),
            ),
          )
          .timeout(const Duration(seconds: 50));

      final reply = response.data?['reply'] as String?;
      if (reply != null && reply.trim().isNotEmpty) {
        debugPrint('[ChatBot] ✅ Backend /chat replied');
        return reply.trim();
      }
      return null;
    } on DioException catch (e) {
      final statusCode = e.response?.statusCode;
      final detail = e.response?.data?['detail'] as String?;
      debugPrint(
          '[ChatBot] Backend /chat DioError: ${e.type} | $statusCode | $detail');
      // Surface backend error detail (e.g., Claude 503) as the reply error
      if (detail != null && detail.isNotEmpty) {
        // Return as a special error marker so caller can show it
        return '__error__:$detail';
      }
      return null;
    } catch (e) {
      debugPrint('[ChatBot] Backend /chat error: $e');
      return null;
    }
  }

  /// Call backend public endpoint (no auth, no history — general guidance)
  Future<String?> _callBackendPublic(String message) async {
    try {
      debugPrint('[ChatBot] Calling backend /chat/public...');
      final dio = ref.read(dioProvider);
      final response = await dio
          .post(
            '/chat/public',
            data: {'message': message},
            options: Options(
              sendTimeout: const Duration(seconds: 10),
              receiveTimeout: const Duration(seconds: 30),
            ),
          )
          .timeout(const Duration(seconds: 35));

      final reply = response.data?['reply'] as String?;
      if (reply != null && reply.trim().isNotEmpty) return reply.trim();
      return null;
    } catch (e) {
      debugPrint('[ChatBot] Backend /chat/public error: $e');
      return null;
    }
  }

  void _addError(String msg) {
    state = state.copyWith(
      messages: [
        ...state.messages,
        ChatMessage(text: msg, isUser: false, isError: true)
      ],
      isLoading: false,
    );
  }

  void clearChat() {
    state = const ChatState(messages: [_welcomeMsg]);
  }
}

final chatProvider =
    NotifierProvider<ChatNotifier, ChatState>(ChatNotifier.new);
