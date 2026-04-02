import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../features/auth/providers/auth_provider.dart';

class ApiConfig {
  static const String baseUrl = 'http://192.168.0.101:8000/api/v1';
}

final dioProvider = Provider<Dio>((ref) {
  final dio = Dio(
    BaseOptions(
      baseUrl: ApiConfig.baseUrl,
      connectTimeout: const Duration(seconds: 30),
      receiveTimeout: const Duration(seconds: 30),
      headers: {
        'Content-Type': 'application/json',
      },
    ),
  );

  dio.interceptors.add(
    InterceptorsWrapper(
      onRequest: (options, handler) async {
        // Read the token directly to avoid ref.watch loops in interceptor
        final authState = ref.read(authProvider);
        if (authState.token != null) {
          options.headers['Authorization'] = 'Bearer ${authState.token}';
        }
        return handler.next(options);
      },
      onError: (DioException e, handler) {
        if (e.response?.statusCode == 401) {
          ref.read(authProvider.notifier).logout(); // token expired
        }
        return handler.next(e);
      },
    ),
  );

  return dio;
});
