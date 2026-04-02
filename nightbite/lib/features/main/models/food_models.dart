class FoodAnalysisResponse {
  final int eventId;
  final String sourceType;
  final String? sourceApp;
  final String? normalizedFoodText;
  final String? foodCategory;
  final List<String> riskTags;
  final double riskScore;
  final String riskBand;
  final String smartNudge;
  final String? healthierSwap;
  final DateTime eventTimestamp;

  FoodAnalysisResponse({
    required this.eventId,
    required this.sourceType,
    this.sourceApp,
    this.normalizedFoodText,
    this.foodCategory,
    required this.riskTags,
    required this.riskScore,
    required this.riskBand,
    required this.smartNudge,
    this.healthierSwap,
    required this.eventTimestamp,
  });

  factory FoodAnalysisResponse.fromJson(Map<String, dynamic> json) {
    return FoodAnalysisResponse(
      eventId: json['event_id'],
      sourceType: json['source_type'],
      sourceApp: json['source_app'],
      normalizedFoodText: json['normalized_food_text'],
      foodCategory: json['food_category'],
      riskTags: List<String>.from(json['risk_tags'] ?? []),
      riskScore: (json['risk_score'] as num).toDouble(),
      riskBand: json['risk_band'],
      smartNudge: json['smart_nudge'],
      healthierSwap: json['healthier_swap'],
      eventTimestamp: DateTime.parse(json['event_timestamp']),
    );
  }
}

class HistoryEventItem {
  final int eventId;
  final String sourceType;
  final String? sourceApp;
  final String? normalizedFoodText;
  final double riskScore;
  final String riskBand;
  final DateTime eventTimestamp;
  final String? foodCategory;

  HistoryEventItem({
    required this.eventId,
    required this.sourceType,
    this.sourceApp,
    this.normalizedFoodText,
    required this.riskScore,
    required this.riskBand,
    required this.eventTimestamp,
    this.foodCategory,
  });

  factory HistoryEventItem.fromJson(Map<String, dynamic> json) {
    return HistoryEventItem(
      eventId: json['event_id'],
      sourceType: json['source_type'],
      sourceApp: json['source_app'],
      normalizedFoodText: json['normalized_food_text'],
      riskScore: (json['risk_score'] as num).toDouble(),
      riskBand: json['risk_band'],
      eventTimestamp: DateTime.parse(json['event_timestamp']),
      foodCategory: json['food_category'],
    );
  }
}

class UserInsightsResponse {
  final double? weeklyAvgRisk;
  final int highRiskCountThisWeek;
  final int totalEventsThisWeek;
  final String? commonFoodCategory;
  final String riskTrend;

  UserInsightsResponse({
    this.weeklyAvgRisk,
    required this.highRiskCountThisWeek,
    required this.totalEventsThisWeek,
    this.commonFoodCategory,
    required this.riskTrend,
  });

  factory UserInsightsResponse.fromJson(Map<String, dynamic> json) {
    return UserInsightsResponse(
      weeklyAvgRisk: json['weekly_avg_risk'] != null 
          ? (json['weekly_avg_risk'] as num).toDouble() 
          : null,
      highRiskCountThisWeek: json['high_risk_count_this_week'],
      totalEventsThisWeek: json['total_events_this_week'],
      commonFoodCategory: json['common_food_category'],
      riskTrend: json['risk_trend'],
    );
  }
}
