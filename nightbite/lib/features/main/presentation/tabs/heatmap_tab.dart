import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../../core/network/dio_client.dart';
import '../../../../core/theme/app_colors_extension.dart';

// ── Models ────────────────────────────────────────────────────────────────────

class HeatmapCell {
  final String locationKey;
  final String? timeBucket; // "10p","11p","12a","1a","2a","3a","4a","day"
  final String? dayOfWeek;  // "Mon","Tue",...
  final int orderCount;
  final double avgRisk;
  final int highRiskCount;
  final double hotspotIntensity;

  const HeatmapCell({
    required this.locationKey,
    this.timeBucket,
    this.dayOfWeek,
    required this.orderCount,
    required this.avgRisk,
    required this.highRiskCount,
    required this.hotspotIntensity,
  });

  factory HeatmapCell.fromJson(Map<String, dynamic> j) => HeatmapCell(
        locationKey: j['location_key'] as String,
        timeBucket: j['time_bucket'] as String?,
        dayOfWeek: j['day_of_week'] as String?,
        orderCount: (j['order_count'] as num).toInt(),
        avgRisk: (j['avg_risk'] as num).toDouble(),
        highRiskCount: (j['high_risk_count'] as num).toInt(),
        hotspotIntensity: (j['hotspot_intensity'] as num).toDouble(),
      );
}

// ── Provider ──────────────────────────────────────────────────────────────────

final heatmapProvider =
    FutureProvider.autoDispose.family<List<HeatmapCell>, int>((ref, days) async {
  final dio = ref.watch(dioProvider);
  final response =
      await dio.get('/analytics/heatmap', queryParameters: {'days': days});
  if (response.statusCode == 200) {
    final cells = response.data['cells'] as List;
    return cells.map((c) => HeatmapCell.fromJson(c as Map<String, dynamic>)).toList();
  }
  return [];
});

// ── Constants ─────────────────────────────────────────────────────────────────

const _timeSlots = ['10p', '11p', '12a', '1a', '2a', '3a', '4a'];
const _timeLabels = ['10PM', '11PM', '12AM', '1AM', '2AM', '3AM', '4AM'];
const _dayOrder = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

// ── Heatmap Tab ───────────────────────────────────────────────────────────────

class HeatmapTab extends ConsumerStatefulWidget {
  const HeatmapTab({super.key});

  @override
  ConsumerState<HeatmapTab> createState() => _HeatmapTabState();
}

class _HeatmapTabState extends ConsumerState<HeatmapTab> {
  int _selectedDays = 7;

  @override
  Widget build(BuildContext context) {
    final heatmapAsync = ref.watch(heatmapProvider(_selectedDays));
    final colors = context.appColors;

    return Scaffold(
      backgroundColor: colors.background,
      appBar: AppBar(
        title: Text('🧪 Lab & Analytics',
            style: TextStyle(fontWeight: FontWeight.bold, color: colors.textPrimary)),
        backgroundColor: colors.surface,
        elevation: 0,
        actions: [
          Padding(
            padding: const EdgeInsets.only(right: 12),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [7, 14, 30].map((d) {
                final selected = _selectedDays == d;
                return GestureDetector(
                  onTap: () => setState(() => _selectedDays = d),
                  child: AnimatedContainer(
                    duration: const Duration(milliseconds: 200),
                    margin: const EdgeInsets.only(left: 6),
                    padding: const EdgeInsets.symmetric(
                        horizontal: 10, vertical: 4),
                    decoration: BoxDecoration(
                      color: selected
                          ? colors.primary
                          : colors.surfaceHighlight,
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Text(
                      '${d}d',
                      style: TextStyle(
                        color: selected
                            ? Colors.white
                            : colors.textSecondary,
                        fontSize: 12,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),
                );
              }).toList(),
            ),
          ),
        ],
      ),
      body: heatmapAsync.when(
        data: (cells) {
          if (cells.isEmpty) return _buildEmptyState(colors);
          return RefreshIndicator(
            onRefresh: () async =>
                ref.invalidate(heatmapProvider(_selectedDays)),
            child: ListView(
              padding: const EdgeInsets.fromLTRB(16, 16, 16, 24),
              children: [
                _buildSummaryBanner(cells, colors),
                const SizedBox(height: 24),
                _buildSectionHeader(colors),
                const SizedBox(height: 12),
                _buildGrid(cells, colors),
                const SizedBox(height: 16),
                _buildLegend(colors),
                const SizedBox(height: 16),
                _buildInfoBox(colors),
              ],
            ),
          );
        },
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (err, _) => Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(Icons.map_outlined, color: colors.textMuted, size: 64),
              const SizedBox(height: 12),
              Text('Could not load heatmap', style: TextStyle(color: colors.textPrimary)),
              const SizedBox(height: 8),
              Text(err.toString(), style: TextStyle(color: colors.textMuted, fontSize: 11)),
              const SizedBox(height: 16),
              TextButton(
                onPressed: () => ref.invalidate(heatmapProvider(_selectedDays)),
                child: const Text('Retry'),
              ),
            ],
          ),
        ),
      ),
    );
  }

  // ── Summary Banner ─────────────────────────────────────────────────────────

  Widget _buildSummaryBanner(List<HeatmapCell> cells, NightBiteColors colors) {
    final totalOrders = cells.fold(0, (s, c) => s + c.orderCount);
    final totalHighRisk = cells.fold(0, (s, c) => s + c.highRiskCount);
    final locs = cells.map((c) => c.locationKey).toSet().length;
    final avgRisk = cells.isEmpty
        ? 0.0
        : cells.fold(0.0, (s, c) => s + c.avgRisk) / cells.length;

    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [
            colors.riskHigh.withValues(alpha: 0.15),
            colors.riskExtreme.withValues(alpha: 0.08),
          ],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: colors.riskHigh.withValues(alpha: 0.2)),
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceAround,
        children: [
          _stat('Zones', '$locs', colors.primaryLight, colors),
          _vLine(colors),
          _stat('Orders', '$totalOrders', colors.textPrimary, colors),
          _vLine(colors),
          _stat('High Risk', '$totalHighRisk', colors.riskHigh, colors),
          _vLine(colors),
          _stat('Avg Risk', avgRisk.toStringAsFixed(1), colors.riskMedium, colors),
        ],
      ),
    );
  }

  Widget _stat(String label, String value, Color color, NightBiteColors colors) => Column(
        children: [
          Text(value,
              style: TextStyle(
                  fontSize: 22,
                  fontWeight: FontWeight.w900,
                  color: color)),
          const SizedBox(height: 2),
          Text(label,
              style: TextStyle(
                  fontSize: 11, color: colors.textMuted)),
        ],
      );

  Widget _vLine(NightBiteColors colors) => Container(
      height: 36, width: 1, color: colors.divider);

  // ── Section Header ─────────────────────────────────────────────────────────

  Widget _buildSectionHeader(NightBiteColors colors) => Row(
        children: [
          Text(
            'Temporal Hotspots',
            style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.bold,
                color: colors.textPrimary),
          ),
          const SizedBox(width: 8),
          Text('Late-night intensity',
              style: TextStyle(
                  color: colors.textMuted, fontSize: 12)),
        ],
      );

  // ── Main Grid ──────────────────────────────────────────────────────────────

  Widget _buildGrid(List<HeatmapCell> cells, NightBiteColors colors) {
    // Get active days from data
    final activeDays = cells
        .where((c) => c.dayOfWeek != null)
        .map((c) => c.dayOfWeek!)
        .toSet();
    final days = _dayOrder.where((d) => activeDays.contains(d)).toList();

    // Build lookup: day+slot -> intensity
    final Map<String, double> lookup = {};
    final Map<String, int> orderLookup = {};
    for (final cell in cells) {
      if (cell.dayOfWeek == null || cell.timeBucket == null) continue;
      final key = '${cell.dayOfWeek}|${cell.timeBucket}';
      lookup[key] = (lookup[key] ?? 0) + cell.hotspotIntensity;
      orderLookup[key] = (orderLookup[key] ?? 0) + cell.orderCount;
    }

    // Max intensity for scaling
    final maxVal = lookup.values.isEmpty
        ? 1.0
        : lookup.values.reduce((a, b) => a > b ? a : b).clamp(0.1, 10.0);

    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: colors.surface,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: colors.divider),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // ── Column headers (time slots) ──────────────────────────────
          Row(
            children: [
              // Y-axis label space
              const SizedBox(width: 36),
              ...List.generate(_timeSlots.length, (i) {
                return Expanded(
                  child: Text(
                    _timeLabels[i],
                    textAlign: TextAlign.center,
                    style: TextStyle(
                      fontSize: 9,
                      color: colors.textMuted,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                );
              }),
            ],
          ),
          const SizedBox(height: 8),
          // ── Rows (one per day) ────────────────────────────────────────
          ...(days.isEmpty ? _dayOrder : days).map((day) {
            return Padding(
              padding: const EdgeInsets.only(bottom: 6),
              child: Row(
                children: [
                  // Day label
                  SizedBox(
                    width: 36,
                    child: Text(
                      day,
                      style: TextStyle(
                        fontSize: 11,
                        color: colors.textSecondary,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ),
                  // Time slot cells
                  ...List.generate(_timeSlots.length, (i) {
                    final slot = _timeSlots[i];
                    final key = '$day|$slot';
                    final intensity = lookup[key] ?? 0.0;
                    final orders = orderLookup[key] ?? 0;
                    return Expanded(
                      child: _HeatCell(
                        intensity: intensity,
                        maxIntensity: maxVal,
                        orderCount: orders,
                        colors: colors,
                      ),
                    );
                  }),
                ],
              ),
            );
          }),
        ],
      ),
    );
  }

  // ── Legend ─────────────────────────────────────────────────────────────────

  Widget _buildLegend(NightBiteColors colors) => Row(
        children: [
          Text('Low',
              style:
                  TextStyle(color: colors.textMuted, fontSize: 11)),
          const SizedBox(width: 8),
          Expanded(
            child: Container(
              height: 10,
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(4),
                gradient: LinearGradient(
                  colors: [
                    Colors.green.withValues(alpha: 0.3),
                    Colors.orange.withValues(alpha: 0.6),
                    Colors.deepOrange,
                    Colors.purple,
                  ],
                ),
              ),
            ),
          ),
          const SizedBox(width: 8),
          Text('Critical',
              style:
                  TextStyle(color: colors.textMuted, fontSize: 11)),
        ],
      );

  // ── Info Box ───────────────────────────────────────────────────────────────

  Widget _buildInfoBox(NightBiteColors colors) => Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: colors.surfaceHighlight,
          borderRadius: BorderRadius.circular(14),
        ),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(Icons.info_outline, color: colors.primaryLight, size: 16),
            const SizedBox(width: 10),
            Expanded(
              child: Text(
                'Each cell shows the late-night order intensity for that day × time combination. '
                'Darker cells = higher risk ordering patterns. Columns are IST time slots from 10 PM to 4 AM.',
                style: TextStyle(
                    color: colors.textMuted,
                    fontSize: 12,
                    height: 1.5),
              ),
            ),
          ],
        ),
      );

  // ── Empty State ────────────────────────────────────────────────────────────

  Widget _buildEmptyState(NightBiteColors colors) => Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.grid_view_rounded,
                size: 80,
                color: colors.textMuted.withValues(alpha: 0.4)),
            const SizedBox(height: 16),
            Text(
              'No hotspot data yet',
              style: TextStyle(
                  fontSize: 20,
                  fontWeight: FontWeight.bold,
                  color: colors.textSecondary),
            ),
            const SizedBox(height: 8),
            Text(
              'Log some late-night food events to build\nyour personal risk heatmap.',
              textAlign: TextAlign.center,
              style: TextStyle(color: colors.textMuted),
            ),
          ],
        ),
      );
}

// ── Heat Cell Widget ──────────────────────────────────────────────────────────

class _HeatCell extends StatelessWidget {
  final double intensity;
  final double maxIntensity;
  final int orderCount;
  final NightBiteColors colors;

  const _HeatCell({
    required this.intensity,
    required this.maxIntensity,
    required this.orderCount,
    required this.colors,
  });

  Color _cellColor() {
    if (orderCount == 0 || intensity == 0) {
      return colors.surfaceHighlight;
    }
    final ratio = (intensity / maxIntensity).clamp(0.0, 1.0);
    if (ratio < 0.25) return const Color(0xFF2D5A27).withValues(alpha: 0.7 + ratio);
    if (ratio < 0.5) return const Color(0xFF8B6914).withValues(alpha: 0.7 + ratio * 0.5);
    if (ratio < 0.75) return const Color(0xFFB84D00).withValues(alpha: 0.8);
    return const Color(0xFF7B2FBE); // deep purple = critical
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 2),
      height: 32,
      decoration: BoxDecoration(
        color: _cellColor(),
        borderRadius: BorderRadius.circular(5),
      ),
    );
  }
}
