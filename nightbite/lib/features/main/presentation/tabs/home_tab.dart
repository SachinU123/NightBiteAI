import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../../core/theme/app_colors_extension.dart';
import '../../providers/food_provider.dart';
import '../../providers/chat_provider.dart';
import '../widgets/manual_entry_sheet.dart';
import 'package:intl/intl.dart';
import '../../models/food_models.dart';

// Provider to request tab navigation from Home tab (public — consumed by MainTabShell)
class _NavRequestNotifier extends Notifier<int?> {
  @override
  int? build() => null;
  void request(int index) => state = index;
  void consumed() => state = null;
}
final homeNavigationRequestProvider = NotifierProvider<_NavRequestNotifier, int?>(_NavRequestNotifier.new);

class HomeTab extends ConsumerWidget {
  const HomeTab({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final latestFoodAsync = ref.watch(latestFoodProvider);
    final historyAsync = ref.watch(historyProvider);
    final colors = context.appColors;

    return Scaffold(
      backgroundColor: colors.background,
      body: SafeArea(
        child: RefreshIndicator(
          onRefresh: () async {
            ref.invalidate(latestFoodProvider);
            ref.invalidate(historyProvider);
          },
          child: CustomScrollView(
            physics: const BouncingScrollPhysics(),
            slivers: [
              _buildAppBar(context, colors),
              SliverPadding(
                padding: const EdgeInsets.symmetric(horizontal: 20),
                sliver: SliverList(
                  delegate: SliverChildListDelegate([
                    const SizedBox(height: 12),
                    _buildHeroSummary(latestFoodAsync, context, colors),
                    const SizedBox(height: 32),

                    Text("Tonight's Activity", style: _sectionTitleStyle(colors)),
                    const SizedBox(height: 16),
                    _buildTonightActivity(historyAsync, context, colors),
                    const SizedBox(height: 32),

                    Text('Time Pattern: 10 PM – 4 AM', style: _sectionTitleStyle(colors)),
                    const SizedBox(height: 16),
                    _buildTimeWindowVisual(context, colors),
                    const SizedBox(height: 32),

                    Text('Quick Actions', style: _sectionTitleStyle(colors)),
                    const SizedBox(height: 16),
                    _buildQuickActions(context, ref, colors),
                    const SizedBox(height: 32),

                    Text('Micro-Insights', style: _sectionTitleStyle(colors)),
                    const SizedBox(height: 16),
                    _buildMicroInsights(historyAsync, context, colors),
                    const SizedBox(height: 32),
                  ]),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  SliverAppBar _buildAppBar(BuildContext context, NightBiteColors colors) {
    return SliverAppBar(
      backgroundColor: colors.background,
      title: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Late-Night Radar',
            style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold, color: colors.textPrimary),
          ),
          Text(
            'Analyzing your 10 PM - 4 AM choices',
            style: TextStyle(fontSize: 14, color: colors.primaryLight),
          ),
        ],
      ),
      floating: true,
      centerTitle: false,
    );
  }

  TextStyle _sectionTitleStyle(NightBiteColors colors) {
    return TextStyle(
      fontSize: 18,
      fontWeight: FontWeight.bold,
      color: colors.textPrimary,
      letterSpacing: 0.5,
    );
  }

  Widget _buildHeroSummary(AsyncValue<FoodAnalysisResponse?> latestAsync, BuildContext context, NightBiteColors colors) {
    return latestAsync.when(
      data: (food) {
        if (food == null) {
          return _buildEmptyHero(context, colors);
        }
        return _HeroCard(food: food, colors: colors);
      },
      loading: () => const SizedBox(height: 200, child: Center(child: CircularProgressIndicator())),
      error: (e, _) => Container(
        height: 150,
        decoration: BoxDecoration(
          color: colors.riskHigh.withValues(alpha: 0.1),
          borderRadius: BorderRadius.circular(24),
        ),
        child: Center(child: Text('Error loading latest activity', style: TextStyle(color: colors.riskHigh))),
      ),
    );
  }

  Widget _buildEmptyHero(BuildContext context, NightBiteColors colors) {
    return Container(
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        color: colors.surfaceHighlight,
        borderRadius: BorderRadius.circular(24),
        border: Border.all(color: colors.divider),
      ),
      child: Column(
        children: [
          Icon(Icons.shield_outlined, size: 48, color: colors.primary),
          const SizedBox(height: 16),
          Text('No Late-Night Activity', style: TextStyle(color: colors.textPrimary, fontSize: 18, fontWeight: FontWeight.bold)),
          const SizedBox(height: 8),
          Text('You maintained a clean streak tonight.', style: TextStyle(color: colors.textSecondary)),
        ],
      ),
    );
  }

  Widget _buildTonightActivity(AsyncValue<List<HistoryEventItem>> historyAsync, BuildContext context, NightBiteColors colors) {
    return historyAsync.when(
      data: (events) {
        // Just an example logic for "Tonight" (Last 12 hours)
        final tonightEvents = events.where((e) {
          final diff = DateTime.now().difference(e.eventTimestamp.toLocal());
          return diff.inHours <= 12;
        }).take(3).toList();

        if (tonightEvents.isEmpty) {
          return Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: colors.surface,
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: colors.divider),
            ),
            child: Row(
              children: [
                Icon(Icons.bedtime_outlined, color: colors.textMuted),
                const SizedBox(width: 12),
                Text('No orders placed tonight.', style: TextStyle(color: colors.textMuted)),
              ],
            ),
          );
        }

        return Column(
          children: tonightEvents.map((item) {
            final isHighRisk = item.riskBand.toLowerCase() == 'high' || item.riskBand.toLowerCase() == 'extreme';
            final timeStr = DateFormat('h:mm a').format(item.eventTimestamp.toLocal());

            return Container(
              margin: const EdgeInsets.only(bottom: 12),
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: colors.surface,
                borderRadius: BorderRadius.circular(16),
                border: Border.all(
                  color: isHighRisk ? colors.riskHigh.withValues(alpha: 0.3) : colors.divider,
                ),
              ),
              child: Row(
                children: [
                  Container(
                    width: 48,
                    height: 48,
                    decoration: BoxDecoration(
                      color: isHighRisk ? colors.riskHigh.withValues(alpha: 0.1) : colors.primary.withValues(alpha: 0.1),
                      shape: BoxShape.circle,
                    ),
                    child: Icon(
                      isHighRisk ? Icons.warning_rounded : Icons.fastfood,
                      color: isHighRisk ? colors.riskHigh : colors.primaryLight,
                    ),
                  ),
                  const SizedBox(width: 16),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          item.normalizedFoodText ?? item.foodCategory ?? "Unknown Activity",
                          style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: colors.textPrimary),
                        ),
                        const SizedBox(height: 4),
                        Row(
                          children: [
                            Text(timeStr, style: TextStyle(fontSize: 13, color: colors.textSecondary)),
                            const SizedBox(width: 8),
                            Container(
                              padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                              decoration: BoxDecoration(
                                color: colors.surfaceHighlight,
                                borderRadius: BorderRadius.circular(4),
                              ),
                              child: Text(
                                item.sourceApp ?? 'Manual',
                                style: TextStyle(fontSize: 10, color: colors.textMuted),
                              ),
                            )
                          ],
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            );
          }).toList(),
        );
      },
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (e, _) => const Text('Error loading tonight events'),
    );
  }

  Widget _buildTimeWindowVisual(BuildContext context, NightBiteColors colors) {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: colors.surface,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: colors.divider),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text('10 PM', style: TextStyle(color: colors.textSecondary, fontSize: 12)),
              Text('1 AM', style: TextStyle(color: colors.riskMedium, fontSize: 12, fontWeight: FontWeight.bold)),
              Text('4 AM', style: TextStyle(color: colors.riskHigh, fontSize: 12, fontWeight: FontWeight.bold)),
            ],
          ),
          const SizedBox(height: 8),
          Container(
            height: 8,
            width: double.infinity,
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(4),
              gradient: LinearGradient(
                colors: [colors.riskLow, colors.riskMedium, colors.riskHigh],
                stops: const [0.0, 0.5, 1.0],
              ),
            ),
          ),
          const SizedBox(height: 12),
          Text('Your highest risk window is around 1:30 AM based on recent history.', 
               style: TextStyle(color: colors.textMuted, fontSize: 12)),
        ],
      ),
    );
  }

  Widget _buildQuickActions(BuildContext context, WidgetRef ref, NightBiteColors colors) {
    void openAiCoachWithPrefill(String prompt) {
      // Navigate to AI Coach tab (index 2) and prefill the input
      ref.read(chatProvider.notifier).prefillMessage(prompt);
      ref.read(homeNavigationRequestProvider.notifier).request(2);
    }

    return Column(
      children: [
        Row(
          children: [
            Expanded(
              child: _ActionCard(
                title: 'Analyze Pattern',
                icon: Icons.analytics_outlined,
                color: colors.primaryLight,
                colors: colors,
                subtitle: 'Prefills AI Coach',
                onTap: () => openAiCoachWithPrefill(
                  'Analyze my late-night ordering pattern for this month.',
                ),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: _ActionCard(
                title: 'Healthier Swaps',
                icon: Icons.eco_outlined,
                color: colors.riskLow,
                colors: colors,
                subtitle: 'Get AI suggestions',
                onTap: () => openAiCoachWithPrefill(
                  'Suggest healthier swaps based on my recent late-night orders.',
                ),
              ),
            ),
          ],
        ),
        const SizedBox(height: 12),
        // Manual Entry — full width, premium CTA
        _ManualEntryCard(colors: colors),
      ],
    );
  }

  Widget _buildMicroInsights(
    AsyncValue<List<HistoryEventItem>> historyAsync,
    BuildContext context,
    NightBiteColors colors,
  ) {
    return historyAsync.when(
      loading: () => const SizedBox(
        height: 60,
        child: Center(child: CircularProgressIndicator()),
      ),
      error: (_, _) => _InsightRow(
        icon: Icons.info_outline,
        text: 'Could not load order history for insights.',
        colors: colors,
      ),
      data: (events) {
        if (events.isEmpty) {
          return Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: colors.surface,
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: colors.divider),
            ),
            child: Row(
              children: [
                Icon(Icons.bedtime_outlined, color: colors.textMuted),
                const SizedBox(width: 12),
                Text(
                  'Start logging orders to see personalized insights.',
                  style: TextStyle(color: colors.textMuted, fontSize: 13),
                ),
              ],
            ),
          );
        }

        // Compute real insights from history
        final hourCounts = <int, int>{};
        final categoryCounts = <String, int>{};
        for (final e in events) {
          final h = e.eventTimestamp.toLocal().hour;
          hourCounts[h] = (hourCounts[h] ?? 0) + 1;
          final cat = e.foodCategory;
          if (cat != null && cat.isNotEmpty) {
            categoryCounts[cat] = (categoryCounts[cat] ?? 0) + 1;
          }
        }

        String? hourInsight;
        if (hourCounts.isNotEmpty) {
          final topHour = hourCounts.entries.reduce((a, b) => a.value >= b.value ? a : b).key;
          final fmtHour = topHour == 0 ? '12 AM' : topHour > 12 ? '${topHour - 12} PM' : '$topHour ${topHour < 12 ? 'AM' : 'PM'}';
          hourInsight = 'You order most often around $fmtHour based on your history.';
        }

        String? catInsight;
        if (categoryCounts.isNotEmpty) {
          final topCat = categoryCounts.entries.reduce((a, b) => a.value >= b.value ? a : b).key;
          catInsight = 'Your most ordered category is $topCat.';
        }

        return Column(
          children: [
            if (hourInsight != null) ...[  
              _InsightRow(
                icon: Icons.access_time_filled,
                text: hourInsight,
                colors: colors,
              ),
              const SizedBox(height: 12),
            ],
            if (catInsight != null)
              _InsightRow(
                icon: Icons.repeat,
                text: catInsight,
                colors: colors,
              ),
            if (hourInsight == null && catInsight == null)
              _InsightRow(
                icon: Icons.info_outline,
                text: 'More insights will appear as you accumulate order history.',
                colors: colors,
              ),
          ],
        );
      },
    );
  }
}

class _HeroCard extends StatelessWidget {
  final FoodAnalysisResponse food;
  final NightBiteColors colors;

  const _HeroCard({required this.food, required this.colors});

  @override
  Widget build(BuildContext context) {
    final isHighRisk = food.riskBand.toLowerCase() == 'high' || food.riskBand.toLowerCase() == 'extreme';
    final riskColor = isHighRisk ? colors.riskHigh : colors.riskMedium;

    return Container(
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        color: colors.surfaceHighlight,
        borderRadius: BorderRadius.circular(24),
        border: Border.all(color: riskColor.withValues(alpha: 0.5)),
        boxShadow: [
          BoxShadow(
            color: riskColor.withValues(alpha: 0.1),
            blurRadius: 20,
            offset: const Offset(0, 8),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                decoration: BoxDecoration(
                  color: riskColor.withValues(alpha: 0.2),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Text(
                  'LATEST ORDER',
                  style: TextStyle(color: riskColor, fontSize: 10, fontWeight: FontWeight.bold),
                ),
              ),
              const Spacer(),
              Text(
                DateFormat('h:mm a').format(food.eventTimestamp.toLocal()),
                style: TextStyle(color: colors.textSecondary, fontWeight: FontWeight.bold),
              ),
            ],
          ),
          const SizedBox(height: 16),
          Text(
            food.normalizedFoodText ?? food.foodCategory ?? "Late-night meal",
            style: TextStyle(fontSize: 28, fontWeight: FontWeight.w900, color: colors.textPrimary),
          ),
          const SizedBox(height: 8),
          Row(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Text(
                food.riskScore.round().toString(),
                style: TextStyle(fontSize: 48, fontWeight: FontWeight.w900, color: riskColor, height: 1),
              ),
              const SizedBox(width: 8),
              Padding(
                padding: const EdgeInsets.only(bottom: 6.0),
                child: Text(
                  '/ 10 Risk Score',
                  style: TextStyle(color: colors.textSecondary, fontWeight: FontWeight.bold),
                ),
              ),
            ],
          ),
          const SizedBox(height: 20),
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: colors.surface,
              borderRadius: BorderRadius.circular(12),
            ),
            child: Row(
              children: [
                Icon(Icons.auto_awesome, color: colors.primaryLight, size: 20),
                const SizedBox(width: 12),
                Expanded(
                  child: Text(
                    food.smartNudge,
                    style: TextStyle(color: colors.textPrimary, fontSize: 13),
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _ActionCard extends StatelessWidget {
  final String title;
  final String? subtitle;
  final IconData icon;
  final Color color;
  final NightBiteColors colors;
  final VoidCallback onTap;

  const _ActionCard({
    required this.title,
    this.subtitle,
    required this.icon,
    required this.color,
    required this.colors,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(16),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 20),
        decoration: BoxDecoration(
          color: color.withValues(alpha: 0.1),
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: color.withValues(alpha: 0.3)),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(icon, color: color, size: 28),
            const SizedBox(height: 12),
            Text(
              title,
              style: TextStyle(color: color, fontWeight: FontWeight.bold, fontSize: 14),
            ),
            if (subtitle != null) ...[  
              const SizedBox(height: 4),
              Text(subtitle!, style: TextStyle(color: color.withValues(alpha: 0.7), fontSize: 11)),
            ],
          ],
        ),
      ),
    );
  }
}

class _ManualEntryCard extends StatelessWidget {
  final NightBiteColors colors;
  const _ManualEntryCard({required this.colors});

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: () {
        showModalBottomSheet(
          context: context,
          isScrollControlled: true,
          backgroundColor: Colors.transparent,
          builder: (ctx) => const ManualEntrySheet(),
        );
      },
      borderRadius: BorderRadius.circular(16),
      child: Container(
        width: double.infinity,
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
        decoration: BoxDecoration(
          gradient: LinearGradient(
            colors: [colors.primary.withValues(alpha: 0.15), colors.primaryLight.withValues(alpha: 0.08)],
            begin: Alignment.centerLeft,
            end: Alignment.centerRight,
          ),
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: colors.primary.withValues(alpha: 0.3)),
        ),
        child: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(
                color: colors.primary.withValues(alpha: 0.2),
                shape: BoxShape.circle,
              ),
              child: Icon(Icons.add_circle_outline, color: colors.primaryLight, size: 22),
            ),
            const SizedBox(width: 16),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Add Order Manually',
                    style: TextStyle(
                      color: colors.textPrimary,
                      fontWeight: FontWeight.bold,
                      fontSize: 15,
                    ),
                  ),
                  Text(
                    'Log a meal not captured from notifications',
                    style: TextStyle(color: colors.textMuted, fontSize: 12),
                  ),
                ],
              ),
            ),
            Icon(Icons.chevron_right, color: colors.textSecondary),
          ],
        ),
      ),
    );
  }
}

class _InsightRow extends StatelessWidget {
  final IconData icon;
  final String text;
  final NightBiteColors colors;

  const _InsightRow({required this.icon, required this.text, required this.colors});

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Container(
          padding: const EdgeInsets.all(8),
          decoration: BoxDecoration(
            color: colors.surfaceHighlight,
            shape: BoxShape.circle,
          ),
          child: Icon(icon, size: 16, color: colors.primaryLight),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: Text(text, style: TextStyle(color: colors.textSecondary, fontSize: 14)),
        ),
      ],
    );
  }
}
