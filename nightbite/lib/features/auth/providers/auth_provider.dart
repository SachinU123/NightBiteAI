import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../../../core/network/dio_client.dart';

class AuthState {
  final bool isAuthenticated;
  final bool isLoading;
  final String? error;
  final String? token;
  final bool registrationSuccess; // true after successful registration → show success, go to login

  const AuthState({
    this.isAuthenticated = false,
    this.isLoading = true,
    this.error,
    this.token,
    this.registrationSuccess = false,
  });

  AuthState copyWith({
    bool? isAuthenticated,
    bool? isLoading,
    String? error,
    bool clearError = false,
    String? token,
    bool? registrationSuccess,
  }) {
    return AuthState(
      isAuthenticated: isAuthenticated ?? this.isAuthenticated,
      isLoading: isLoading ?? this.isLoading,
      error: clearError ? null : (error ?? this.error),
      token: token ?? this.token,
      registrationSuccess: registrationSuccess ?? this.registrationSuccess,
    );
  }
}

class AuthNotifier extends Notifier<AuthState> {
  static const _tokenKey = 'nightbite_auth_token';

  @override
  AuthState build() {
    _checkInitialAuth();
    return const AuthState(isLoading: true);
  }

  Future<void> _checkInitialAuth() async {
    final prefs = await SharedPreferences.getInstance();
    final token = prefs.getString(_tokenKey);
    if (token != null && token.isNotEmpty) {
      state = state.copyWith(isLoading: false, isAuthenticated: true, token: token);
    } else {
      state = state.copyWith(isLoading: false, isAuthenticated: false);
    }
  }

  Future<void> login(String email, String password) async {
    state = state.copyWith(isLoading: true, clearError: true);
    try {
      final dio = ref.read(dioProvider);
      final response = await dio.post('/auth/login', data: {
        'email': email,
        'password': password,
      });

      final token = response.data['access_token'];
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString(_tokenKey, token);

      state = state.copyWith(
        isLoading: false,
        isAuthenticated: true,
        token: token,
        registrationSuccess: false,
      );
    } on DioException catch (e) {
      final msg = e.response?.data['detail'] ?? 'Login failed. Please check credentials.';
      state = state.copyWith(isLoading: false, error: msg.toString());
    } catch (e) {
      state = state.copyWith(isLoading: false, error: 'An unexpected error occurred.');
    }
  }

  /// Register creates an account but does NOT log in.
  /// On success, sets registrationSuccess=true and navigates to login.
  Future<void> register(String name, String email, String password) async {
    state = state.copyWith(isLoading: true, clearError: true);
    try {
      final dio = ref.read(dioProvider);
      await dio.post('/auth/register', data: {
        'name': name,
        'email': email,
        'password': password,
      });

      // ✅ Registration successful — do NOT auto-login.
      // Set registrationSuccess=true so the UI shows success and navigates to login.
      state = state.copyWith(
        isLoading: false,
        isAuthenticated: false, // explicitly stay logged out
        registrationSuccess: true,
      );
    } on DioException catch (e) {
      final msg = e.response?.data['detail'] ?? 'Registration failed. Please try again.';
      state = state.copyWith(isLoading: false, error: msg.toString());
    } catch (e) {
      state = state.copyWith(isLoading: false, error: 'An unexpected error occurred.');
    }
  }

  void clearRegistrationSuccess() {
    state = state.copyWith(registrationSuccess: false);
  }

  Future<void> logout() async {
    state = state.copyWith(isLoading: true);
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_tokenKey);
    state = const AuthState(isAuthenticated: false, isLoading: false);
  }
}

final authProvider = NotifierProvider<AuthNotifier, AuthState>(() {
  return AuthNotifier();
});
