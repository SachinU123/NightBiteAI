import 'package:flutter/material.dart';
import '../../../../core/theme/app_colors.dart';
import '../../models/food_models.dart';

class RiskScoreCard extends StatelessWidget {
  final FoodAnalysisResponse food;

  const RiskScoreCard({super.key, required this.food});

  Color _getRiskColor() {
    switch (food.riskBand.toLowerCase()) {
      case 'low':
        return AppColors.riskLow;
      case 'moderate':
      case 'medium':
        return AppColors.riskMedium;
      case 'high':
        return AppColors.riskHigh;
      case 'critical':
      case 'extreme':
        return AppColors.riskExtreme;
      default:
        return AppColors.textMuted;
    }
  }

  @override
  Widget build(BuildContext context) {
    final riskColor = _getRiskColor();

    return Container(
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(24),
        border: Border.all(color: riskColor.withValues(alpha: 0.3)),
        boxShadow: [
          BoxShadow(
            color: riskColor.withValues(alpha: 0.1),
            blurRadius: 20,
            offset: const Offset(0, 8),
          ),
        ],
      ),
      child: Stack(
        children: [
          // Background icon
          Positioned(
            right: -20,
            bottom: -20,
            child: Icon(
              Icons.warning_amber_rounded,
              size: 140,
              color: riskColor.withValues(alpha: 0.05),
            ),
          ),
          
          Padding(
            padding: const EdgeInsets.all(24.0),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Expanded(
                      child: Text(
                        food.normalizedFoodText ?? food.foodCategory ?? "Unknown Food",
                        style: const TextStyle(
                          fontSize: 22,
                          fontWeight: FontWeight.bold,
                          color: AppColors.textPrimary,
                        ),
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                      decoration: BoxDecoration(
                        color: riskColor.withValues(alpha: 0.2),
                        borderRadius: BorderRadius.circular(20),
                        border: Border.all(color: riskColor.withValues(alpha: 0.5)),
                      ),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Icon(Icons.local_fire_department, color: riskColor, size: 16),
                          const SizedBox(width: 4),
                          Text(
                            food.riskBand.toUpperCase(),
                            style: TextStyle(
                              color: riskColor,
                              fontWeight: FontWeight.bold,
                              fontSize: 12,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
                
                if (food.sourceApp != null) ...[
                  const SizedBox(height: 8),
                  Row(
                    children: [
                      Icon(Icons.phone_android, size: 14, color: AppColors.textMuted),
                      const SizedBox(width: 4),
                      Text(
                        'Detected via ${food.sourceApp}',
                        style: const TextStyle(
                          fontSize: 12,
                          color: AppColors.textMuted,
                        ),
                      ),
                    ],
                  ),
                ],

                const SizedBox(height: 12),
                
                // Show explicit time and Late Night penalty badge
                Builder(
                  builder: (context) {
                    final localTime = food.eventTimestamp.toLocal();
                    final hourStr = localTime.hour > 12 ? '${localTime.hour - 12}' : (localTime.hour == 0 ? '12' : '${localTime.hour}');
                    final minStr = localTime.minute.toString().padLeft(2, '0');
                    final amPm = localTime.hour >= 12 ? 'PM' : 'AM';
                    final isLateNight = localTime.hour >= 22 || localTime.hour <= 4;
                    
                    return Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            const Icon(Icons.access_time, size: 14, color: AppColors.textMuted),
                            const SizedBox(width: 4),
                            Text(
                              'Time Captured: $hourStr:$minStr $amPm',
                              style: const TextStyle(
                                fontSize: 13,
                                color: AppColors.textMuted,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                          ],
                        ),
                        if (isLateNight) ...[
                          const SizedBox(height: 8),
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                            decoration: BoxDecoration(
                              color: AppColors.riskExtreme.withValues(alpha: 0.15),
                              borderRadius: BorderRadius.circular(8),
                            ),
                            child: Row(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                const Icon(Icons.bedtime, size: 13, color: AppColors.riskExtreme),
                                const SizedBox(width: 6),
                                const Flexible(
                                  child: Text(
                                    '🌙 Late Night Penalty: +20% to +60%',
                                    style: TextStyle(
                                      fontSize: 11,
                                      color: AppColors.riskExtreme,
                                      fontWeight: FontWeight.bold,
                                    ),
                                    maxLines: 1,
                                    overflow: TextOverflow.ellipsis,
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ],
                      ],
                    );
                  }
                ),

                const SizedBox(height: 24),
                
                // Risk Score row
                Row(
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: [
                    Text(
                      food.riskScore.toStringAsFixed(1),
                      style: TextStyle(
                        fontSize: 48,
                        height: 1,
                        fontWeight: FontWeight.w900,
                        color: riskColor,
                      ),
                    ),
                    const SizedBox(width: 4),
                    const Padding(
                      padding: EdgeInsets.only(bottom: 8.0),
                      child: Text(
                        '/ 10 Risk Score',
                        style: TextStyle(
                          color: AppColors.textSecondary,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 16),
                
                // Tags
                if (food.riskTags.isNotEmpty)
                  Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: food.riskTags.map((tag) => Container(
                      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                      decoration: BoxDecoration(
                        color: AppColors.surfaceHighlight,
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: Text(
                        '#$tag',
                        style: const TextStyle(
                          color: AppColors.textSecondary,
                          fontSize: 12,
                        ),
                      ),
                    )).toList(),
                  ),

                const SizedBox(height: 24),
                const Divider(color: AppColors.divider),
                const SizedBox(height: 16),
                
                // Nudge
                Container(
                  padding: const EdgeInsets.all(16),
                  decoration: BoxDecoration(
                    color: AppColors.primary.withValues(alpha: 0.1),
                    borderRadius: BorderRadius.circular(16),
                    border: Border.all(color: AppColors.primary.withValues(alpha: 0.3)),
                  ),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Icon(Icons.lightbulb_outline, color: AppColors.primaryLight, size: 24),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Text(
                              'Smart Nudge',
                              style: TextStyle(
                                color: AppColors.primaryLight,
                                fontWeight: FontWeight.bold,
                                fontSize: 14,
                              ),
                            ),
                            const SizedBox(height: 4),
                            Text(
                              food.smartNudge,
                              style: const TextStyle(
                                color: AppColors.textPrimary,
                                height: 1.4,
                                fontSize: 14,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
                
                // Healthier Swap
                if (food.healthierSwap != null && food.healthierSwap!.isNotEmpty) ...[
                  const SizedBox(height: 12),
                  Container(
                    padding: const EdgeInsets.all(16),
                    decoration: BoxDecoration(
                      color: AppColors.riskLow.withValues(alpha: 0.1),
                      borderRadius: BorderRadius.circular(16),
                      border: Border.all(color: AppColors.riskLow.withValues(alpha: 0.3)),
                    ),
                    child: Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Icon(Icons.eco_outlined, color: AppColors.riskLow, size: 24),
                        const SizedBox(width: 12),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              const Text(
                                'Healthier Swap',
                                style: TextStyle(
                                  color: AppColors.riskLow,
                                  fontWeight: FontWeight.bold,
                                  fontSize: 14,
                                ),
                              ),
                              const SizedBox(height: 4),
                              Text(
                                food.healthierSwap!,
                                style: const TextStyle(
                                  color: AppColors.textPrimary,
                                  height: 1.4,
                                  fontSize: 14,
                                ),
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                  ),
                ]
              ],
            ),
          ),
        ],
      ),
    );
  }
}
