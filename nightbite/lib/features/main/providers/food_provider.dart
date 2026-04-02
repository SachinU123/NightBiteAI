import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/network/dio_client.dart';
import '../models/food_models.dart';

// Provides the latest food event
final latestFoodProvider = FutureProvider.autoDispose<FoodAnalysisResponse?>((ref) async {
  final dio = ref.watch(dioProvider);
  try {
    final response = await dio.get('/food-events/latest');
    if (response.statusCode == 200 && response.data != null) {
      if (response.data is Map<String, dynamic>) {
        return FoodAnalysisResponse.fromJson(response.data);
      }
    }
    return null;
  } on DioException catch (e) {
    if (e.response?.statusCode == 404) return null;
    rethrow;
  }
});

// Provides history
final historyProvider = FutureProvider.autoDispose<List<HistoryEventItem>>((ref) async {
  final dio = ref.watch(dioProvider);
  final response = await dio.get('/food-events/history');
  
  if (response.statusCode == 200) {
    final data = response.data;
    if (data['events'] != null) {
      return (data['events'] as List)
          .map((item) => HistoryEventItem.fromJson(item))
          .toList();
    }
  }
  return [];
});

// Provides insights
final insightsProvider = FutureProvider.autoDispose<UserInsightsResponse?>((ref) async {
  final dio = ref.watch(dioProvider);
  try {
    final response = await dio.get('/user-insights');
    if (response.statusCode == 200) {
      return UserInsightsResponse.fromJson(response.data);
    }
    return null;
  } catch (e) {
    return null;
  }
});

class FoodNotifier extends Notifier<AsyncValue<void>> {
  @override
  AsyncValue<void> build() {
    return const AsyncData(null);
  }

  Future<void> manualEntry(String text) async {
    state = const AsyncLoading();
    try {
      final dio = ref.read(dioProvider);
      await dio.post('/food-events/manual-entry', data: {
        'food_text': text,
      });
      state = const AsyncData(null);
      
      // Refresh providers after entry
      ref.invalidate(latestFoodProvider);
      ref.invalidate(historyProvider);
      ref.invalidate(insightsProvider);
      
    } catch (e, stack) {
      state = AsyncError(e, stack);
    }
  }
}

final foodActionProvider = NotifierProvider<FoodNotifier, AsyncValue<void>>(() {
  return FoodNotifier();
});
