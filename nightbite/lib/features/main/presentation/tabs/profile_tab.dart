import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../../core/theme/app_colors_extension.dart';
import '../../../auth/providers/auth_provider.dart';
import '../../providers/food_provider.dart';
import '../tabs/heatmap_tab.dart';

// Period filter options for trends
enum TrendPeriod { thisWeek, thisMonth, last3Months, thisYear }

class ProfileTab extends ConsumerStatefulWidget {
  const ProfileTab({super.key});

  @override
  ConsumerState<ProfileTab> createState() => _ProfileTabState();
}

class _ProfileTabState extends ConsumerState<ProfileTab> {
  TrendPeriod _selectedPeriod = TrendPeriod.thisMonth;
  bool _showHeatmap = false;
  bool _darkMode = true; // reflected in current theme

  static const _periodLabels = {
    TrendPeriod.thisWeek: 'This Week',
    TrendPeriod.thisMonth: 'This Month',
    TrendPeriod.last3Months: 'Last 3 Months',
    TrendPeriod.thisYear: 'This Year',
  };

  @override
  Widget build(BuildContext context) {
    final insightsAsync = ref.watch(insightsProvider);
    final historyAsync = ref.watch(historyProvider);
    final colors = context.appColors;

    return Scaffold(
      backgroundColor: colors.background,
      body: CustomScrollView(
        slivers: [
          // ── App bar ──────────────────────────────────────────────────────
          SliverAppBar(
            backgroundColor: colors.surface,
            pinned: true,
            expandedHeight: 0,
            title: Text(
              'Profile',
              style: TextStyle(fontWeight: FontWeight.bold, color: colors.textPrimary),
            ),
          ),

          SliverToBoxAdapter(
            child: Column(
              children: [
                // ── Profile Header ─────────────────────────────────────────
                _ProfileHeader(colors: colors),
                const SizedBox(height: 8),

                // ── Account Block ─────────────────────────────────────────
                _SectionHeader(title: 'Account', colors: colors),
                _AccountBlock(colors: colors, ref: ref),
                const SizedBox(height: 8),

                // ── App Settings ──────────────────────────────────────────
                _SectionHeader(title: 'App Settings', colors: colors),
                _SettingsBlock(
                  colors: colors,
                  darkMode: _darkMode,
                  showHeatmap: _showHeatmap,
                  onDarkModeChanged: (v) => setState(() => _darkMode = v),
                  onHeatmapChanged: (v) => setState(() => _showHeatmap = v),
                ),
                const SizedBox(height: 8),

                // ── Your Trends ───────────────────────────────────────────
                _SectionHeader(title: 'Your Trends', colors: colors),

                // Period filter chips
                SingleChildScrollView(
                  scrollDirection: Axis.horizontal,
                  padding: const EdgeInsets.fromLTRB(16, 8, 16, 12),
                  child: Row(
                    children: TrendPeriod.values.map((p) {
                      final selected = _selectedPeriod == p;
                      return Padding(
                        padding: const EdgeInsets.only(right: 8),
                        child: FilterChip(
                          label: Text(_periodLabels[p]!),
                          selected: selected,
                          onSelected: (_) => setState(() => _selectedPeriod = p),
                          selectedColor: colors.primary.withValues(alpha: 0.2),
                          backgroundColor: colors.surface,
                          labelStyle: TextStyle(
                            color: selected ? colors.primaryLight : colors.textSecondary,
                            fontWeight: selected ? FontWeight.bold : FontWeight.normal,
                            fontSize: 13,
                          ),
                          side: BorderSide(
                            color: selected ? colors.primary.withValues(alpha: 0.5) : Colors.transparent,
                          ),
                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
                        ),
                      );
                    }).toList(),
                  ),
                ),

                // Trends content
                insightsAsync.when(
                  data: (insights) => _TrendsContent(
                    insights: insights,
                    history: historyAsync.asData?.value ?? [],
                    period: _selectedPeriod,
                    colors: colors,
                  ),
                  loading: () => Padding(
                    padding: const EdgeInsets.all(48),
                    child: Center(
                      child: CircularProgressIndicator(color: colors.primaryLight),
                    ),
                  ),
                  error: (e, _) => _TrendsContent(
                    insights: null,
                    history: [],
                    period: _selectedPeriod,
                    colors: colors,
                  ),
                ),

                const SizedBox(height: 8),

                // ── Heatmap Section ───────────────────────────────────────
                if (_showHeatmap) ...[
                  _SectionHeader(title: 'Order Heatmap', colors: colors),
                  Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 16),
                    child: Container(
                      height: 380,
                      decoration: BoxDecoration(
                        color: colors.surface,
                        borderRadius: BorderRadius.circular(20),
                        border: Border.all(color: colors.divider),
                      ),
                      child: ClipRRect(
                        borderRadius: BorderRadius.circular(20),
                        child: const HeatmapTab(),
                      ),
                    ),
                  ),
                ],

                const SizedBox(height: 32),

                // ── Logout ────────────────────────────────────────────────
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 16),
                  child: _LogoutButton(colors: colors, ref: ref),
                ),
                const SizedBox(height: 32),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

// ── Profile Header ────────────────────────────────────────────────────────────

class _ProfileHeader extends StatelessWidget {
  final NightBiteColors colors;
  const _ProfileHeader({required this.colors});

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(24),
      margin: const EdgeInsets.fromLTRB(16, 16, 16, 0),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [
            colors.primary.withValues(alpha: 0.2),
            colors.primaryLight.withValues(alpha: 0.08),
          ],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: colors.primary.withValues(alpha: 0.25)),
      ),
      child: Row(
        children: [
          // Avatar
          Container(
            width: 72,
            height: 72,
            decoration: BoxDecoration(
              color: colors.primary.withValues(alpha: 0.1),
              shape: BoxShape.circle,
              border: Border.all(color: colors.primary.withValues(alpha: 0.3), width: 2),
            ),
            child: const Center(
              child: Text('🌙', style: TextStyle(fontSize: 32)),
            ),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'NightBite User',
                  style: TextStyle(
                    fontSize: 20,
                    fontWeight: FontWeight.bold,
                    color: colors.textPrimary,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  'Late-Night Habit Tracker',
                  style: TextStyle(fontSize: 13, color: colors.textSecondary),
                ),
                const SizedBox(height: 8),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                  decoration: BoxDecoration(
                    color: colors.primary.withValues(alpha: 0.2),
                    borderRadius: BorderRadius.circular(20),
                  ),
                  child: Text(
                    '🔒 Zomato + Swiggy monitoring',
                    style: TextStyle(fontSize: 11, color: colors.primaryLight, fontWeight: FontWeight.w600),
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

// ── Section Header ────────────────────────────────────────────────────────────

class _SectionHeader extends StatelessWidget {
  final String title;
  final NightBiteColors colors;
  const _SectionHeader({required this.title, required this.colors});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 16, 20, 8),
      child: Text(
        title.toUpperCase(),
        style: TextStyle(
          fontSize: 11,
          fontWeight: FontWeight.bold,
          color: colors.textMuted,
          letterSpacing: 1.2,
        ),
      ),
    );
  }
}

// ── Account Block ─────────────────────────────────────────────────────────────

class _AccountBlock extends StatelessWidget {
  final NightBiteColors colors;
  final WidgetRef ref;
  const _AccountBlock({required this.colors, required this.ref});

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 16),
      decoration: BoxDecoration(
        color: colors.surface,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: colors.divider),
      ),
      child: Column(
        children: [
          _ItemTile(
            icon: Icons.person_outline,
            title: 'Display Name',
            subtitle: 'NightBite User',
            colors: colors,
          ),
          Divider(color: colors.divider, height: 1, indent: 56),
          _ItemTile(
            icon: Icons.notifications_none,
            title: 'Monitored Apps',
            subtitle: 'Zomato, Swiggy',
            colors: colors,
          ),
        ],
      ),
    );
  }
}

// ── Settings Block ────────────────────────────────────────────────────────────

class _SettingsBlock extends StatelessWidget {
  final NightBiteColors colors;
  final bool darkMode;
  final bool showHeatmap;
  final ValueChanged<bool> onDarkModeChanged;
  final ValueChanged<bool> onHeatmapChanged;

  const _SettingsBlock({
    required this.colors,
    required this.darkMode,
    required this.showHeatmap,
    required this.onDarkModeChanged,
    required this.onHeatmapChanged,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 16),
      decoration: BoxDecoration(
        color: colors.surface,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: colors.divider),
      ),
      child: Column(
        children: [
          _SwitchTile(
            icon: Icons.dark_mode_outlined,
            title: 'Notification Interception',
            subtitle: 'Active & Listening',
            value: true,
            colors: colors,
            onChanged: (v) {},
          ),
          Divider(color: colors.divider, height: 1, indent: 56),
          _SwitchTile(
            icon: Icons.psychology_outlined,
            title: 'Smart Nudges',
            subtitle: 'Receive healthier alternatives',
            value: true,
            colors: colors,
            onChanged: (v) {},
          ),
          Divider(color: colors.divider, height: 1, indent: 56),
          _SwitchTile(
            icon: Icons.grid_view_rounded,
            title: 'Show Heatmap',
            subtitle: showHeatmap ? 'Visible in Profile' : 'Hidden',
            value: showHeatmap,
            colors: colors,
            onChanged: onHeatmapChanged,
          ),
        ],
      ),
    );
  }
}

// ── Trends Content ────────────────────────────────────────────────────────────

class _TrendsContent extends StatelessWidget {
  final dynamic insights;
  final List<dynamic> history;
  final TrendPeriod period;
  final NightBiteColors colors;

  const _TrendsContent({
    required this.insights,
    required this.history,
    required this.period,
    required this.colors,
  });

  @override
  Widget build(BuildContext context) {
    if (insights == null && history.isEmpty) {
      return _NoDataState(colors: colors);
    }

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16),
      child: Column(
        children: [
          // Quick metric row
          if (insights != null) ...[
            Row(
              children: [
                Expanded(child: _MetricCard(
                  label: 'Avg Risk / 10',
                  value: insights.weeklyAvgRisk?.toStringAsFixed(1) ?? '--',
                  icon: Icons.monitor_heart_outlined,
                  color: _riskColor(insights.weeklyAvgRisk, colors),
                  colors: colors,
                )),
                const SizedBox(width: 12),
                Expanded(child: _MetricCard(
                  label: 'High-Risk Orders',
                  value: insights.highRiskCountThisWeek.toString(),
                  icon: Icons.warning_amber_rounded,
                  color: colors.riskHigh,
                  colors: colors,
                )),
              ],
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(child: _MetricCard(
                  label: 'Total Logged',
                  value: insights.totalEventsThisWeek.toString(),
                  icon: Icons.fastfood_outlined,
                  color: colors.primaryLight,
                  colors: colors,
                )),
                const SizedBox(width: 12),
                Expanded(child: _MetricCard(
                  label: 'Risk Trend',
                  value: insights.riskTrend.toUpperCase(),
                  icon: Icons.trending_up_rounded,
                  color: insights.riskTrend == 'improving' ? colors.success : colors.warning,
                  colors: colors,
                )),
              ],
            ),
            const SizedBox(height: 12),

            if (insights.commonFoodCategory != null)
              _TopCategoryBanner(category: insights.commonFoodCategory!, colors: colors),
          ],

          const SizedBox(height: 12),

          // Time pattern insight card
          _InsightCard(
            icon: Icons.access_time_filled,
            title: 'Late-Night Window',
            body: 'Your monitored window is 10 PM – 4 AM. '
                  'Orders during this time have elevated NCD risk due to slowed metabolism.',
            accentColor: colors.primaryLight,
            colors: colors,
          ),
          const SizedBox(height: 8),
          _InsightCard(
            icon: Icons.info_outline,
            title: 'What drives your risk score?',
            body: 'Each order is scored on: food category base risk × time-of-night multiplier × '
                  'repeat-behavior multiplier. Late night + fried + repeated = highest risk.',
            accentColor: colors.warning,
            colors: colors,
          ),
        ],
      ),
    );
  }

  Color _riskColor(double? risk, NightBiteColors colors) {
    if (risk == null) return colors.textMuted;
    if (risk < 4) return colors.riskLow;
    if (risk < 7) return colors.riskMedium;
    return colors.riskHigh;
  }
}

// ── Smaller sub-widgets ───────────────────────────────────────────────────────

class _MetricCard extends StatelessWidget {
  final String label;
  final String value;
  final IconData icon;
  final Color color;
  final NightBiteColors colors;

  const _MetricCard({
    required this.label,
    required this.value,
    required this.icon,
    required this.color,
    required this.colors,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: color.withValues(alpha: 0.25)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, color: color, size: 22),
          const SizedBox(height: 10),
          Text(
            value,
            style: TextStyle(
              fontSize: 22,
              fontWeight: FontWeight.w900,
              color: color,
            ),
          ),
          const SizedBox(height: 4),
          Text(label, style: TextStyle(color: colors.textSecondary, fontSize: 11)),
        ],
      ),
    );
  }
}

class _TopCategoryBanner extends StatelessWidget {
  final String category;
  final NightBiteColors colors;
  const _TopCategoryBanner({required this.category, required this.colors});

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: colors.surfaceHighlight,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: colors.divider),
      ),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(
              color: colors.primary.withValues(alpha: 0.1),
              shape: BoxShape.circle,
            ),
            child: Icon(Icons.star_rounded, color: colors.primaryLight, size: 22),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('Most Common Category', style: TextStyle(color: colors.textMuted, fontSize: 11)),
                Text(
                  category,
                  style: TextStyle(color: colors.textPrimary, fontSize: 16, fontWeight: FontWeight.bold),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _InsightCard extends StatelessWidget {
  final IconData icon;
  final String title;
  final String body;
  final Color accentColor;
  final NightBiteColors colors;

  const _InsightCard({
    required this.icon,
    required this.title,
    required this.body,
    required this.accentColor,
    required this.colors,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: colors.surface,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: colors.divider),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            padding: const EdgeInsets.all(8),
            decoration: BoxDecoration(
              color: accentColor.withValues(alpha: 0.1),
              shape: BoxShape.circle,
            ),
            child: Icon(icon, color: accentColor, size: 18),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title, style: TextStyle(color: colors.textPrimary, fontWeight: FontWeight.bold, fontSize: 13)),
                const SizedBox(height: 6),
                Text(body, style: TextStyle(color: colors.textSecondary, fontSize: 12, height: 1.5)),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _NoDataState extends StatelessWidget {
  final NightBiteColors colors;
  const _NoDataState({required this.colors});

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 16),
      padding: const EdgeInsets.all(32),
      decoration: BoxDecoration(
        color: colors.surface,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: colors.divider),
      ),
      child: Column(
        children: [
          Text('🌙', style: const TextStyle(fontSize: 48)),
          const SizedBox(height: 16),
          Text(
            'No data yet',
            style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: colors.textPrimary),
          ),
          const SizedBox(height: 8),
          Text(
            'Order trends will appear here once you start logging late-night meals.',
            textAlign: TextAlign.center,
            style: TextStyle(color: colors.textSecondary, fontSize: 13),
          ),
        ],
      ),
    );
  }
}

class _ItemTile extends StatelessWidget {
  final IconData icon;
  final String title;
  final String subtitle;
  final NightBiteColors colors;

  const _ItemTile({
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.colors,
  });

  @override
  Widget build(BuildContext context) {
    return ListTile(
      leading: Icon(icon, color: colors.textSecondary, size: 22),
      title: Text(title, style: TextStyle(color: colors.textPrimary, fontSize: 14)),
      subtitle: Text(subtitle, style: TextStyle(color: colors.textMuted, fontSize: 12)),
    );
  }
}

class _SwitchTile extends StatelessWidget {
  final IconData icon;
  final String title;
  final String subtitle;
  final bool value;
  final NightBiteColors colors;
  final ValueChanged<bool> onChanged;

  const _SwitchTile({
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.value,
    required this.colors,
    required this.onChanged,
  });

  @override
  Widget build(BuildContext context) {
    return ListTile(
      leading: Icon(icon, color: colors.textSecondary, size: 22),
      title: Text(title, style: TextStyle(color: colors.textPrimary, fontSize: 14)),
      subtitle: Text(subtitle, style: TextStyle(color: colors.textMuted, fontSize: 12)),
      trailing: Switch(
        value: value,
        onChanged: onChanged,
        thumbColor: WidgetStateProperty.all(colors.primary),
      ),
    );
  }
}

class _LogoutButton extends StatelessWidget {
  final NightBiteColors colors;
  final WidgetRef ref;
  const _LogoutButton({required this.colors, required this.ref});

  @override
  Widget build(BuildContext context) {
    return OutlinedButton.icon(
      onPressed: () => ref.read(authProvider.notifier).logout(),
      icon: Icon(Icons.logout, color: colors.riskHigh, size: 18),
      label: Text('Sign Out', style: TextStyle(color: colors.riskHigh, fontWeight: FontWeight.bold)),
      style: OutlinedButton.styleFrom(
        padding: const EdgeInsets.symmetric(vertical: 14),
        side: BorderSide(color: colors.riskHigh.withValues(alpha: 0.4)),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        minimumSize: const Size(double.infinity, 0),
      ),
    );
  }
}
