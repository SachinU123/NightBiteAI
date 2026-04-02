import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../../core/theme/app_colors_extension.dart';
import '../../providers/food_provider.dart';
import 'package:intl/intl.dart';
import '../../models/food_models.dart';
import 'package:collection/collection.dart';
import '../widgets/chat_sheet.dart';

class HistoryTab extends ConsumerStatefulWidget {
  const HistoryTab({super.key});

  @override
  ConsumerState<HistoryTab> createState() => _HistoryTabState();
}

class _HistoryTabState extends ConsumerState<HistoryTab> {
  final TextEditingController _searchController = TextEditingController();
  String _searchQuery = '';
  String _sortBy = 'recent'; // 'recent', 'frequency', 'risk'

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final historyAsync = ref.watch(historyProvider);
    final colors = context.appColors;

    return Scaffold(
      backgroundColor: colors.background,
      appBar: AppBar(
        title: Text('Food History', style: TextStyle(fontWeight: FontWeight.bold, color: colors.textPrimary)),
        backgroundColor: colors.surface,
        elevation: 0,
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(130),
          child: Container(
            color: colors.surface,
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
            child: Column(
              children: [
                _buildSearchBar(colors),
                const SizedBox(height: 12),
                _buildSortChips(colors),
                const SizedBox(height: 8),
              ],
            ),
          ),
        ),
      ),
      body: historyAsync.when(
        data: (events) {
          if (events.isEmpty) {
            return _buildEmptyState(colors);
          }

          // Process events
          var filteredEvents = events.where((e) {
            if (_searchQuery.isEmpty) return true;
            final name = (e.normalizedFoodText ?? e.foodCategory ?? '').toLowerCase();
            return name.contains(_searchQuery.toLowerCase());
          }).toList();

          // Group by name
          final grouped = groupBy(filteredEvents, (HistoryEventItem e) => e.normalizedFoodText ?? e.foodCategory ?? 'Unknown');

          // Convert to list of groups
          var groupedList = grouped.entries.map((entry) {
            final items = entry.value;
            items.sort((a, b) => b.eventTimestamp.compareTo(a.eventTimestamp));
            final latest = items.first;
            final avgRisk = items.map((e) => e.riskScore).average;
            return _GroupedHistory(
              name: entry.key,
              count: items.length,
              latestEvent: latest,
              avgRisk: avgRisk,
              allEvents: items,
            );
          }).toList();

          // Sort
          if (_sortBy == 'recent') {
            groupedList.sort((a, b) => b.latestEvent.eventTimestamp.compareTo(a.latestEvent.eventTimestamp));
          } else if (_sortBy == 'frequency') {
            groupedList.sort((a, b) => b.count.compareTo(a.count));
          } else if (_sortBy == 'risk') {
            groupedList.sort((a, b) => b.avgRisk.compareTo(a.avgRisk));
          }

          if (groupedList.isEmpty) {
            return Center(child: Text('No matching late-night orders found.', style: TextStyle(color: colors.textSecondary)));
          }

          return RefreshIndicator(
            onRefresh: () async => ref.invalidate(historyProvider),
            child: ListView.separated(
              physics: const AlwaysScrollableScrollPhysics(),
              padding: const EdgeInsets.all(16),
              itemCount: groupedList.length,
              separatorBuilder: (_, _) => const SizedBox(height: 12),
              itemBuilder: (context, index) {
                return _GroupedHistoryCard(group: groupedList[index], colors: colors);
              },
            ),
          );
        },
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (err, stack) => Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(Icons.error_outline, color: colors.riskHigh, size: 48),
              const SizedBox(height: 16),
              Text('Failed to load history', style: TextStyle(color: colors.textPrimary)),
              TextButton(
                onPressed: () => ref.invalidate(historyProvider),
                child: const Text('Retry'),
              )
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildSearchBar(NightBiteColors colors) {
    return TextField(
      controller: _searchController,
      onChanged: (val) => setState(() => _searchQuery = val),
      style: TextStyle(color: colors.textPrimary),
      decoration: InputDecoration(
        hintText: 'Search pizza, Swiggy, Biryani...',
        hintStyle: TextStyle(color: colors.textMuted),
        prefixIcon: Icon(Icons.search, color: colors.textMuted),
        suffixIcon: _searchQuery.isNotEmpty 
            ? IconButton(
                icon: Icon(Icons.clear, color: colors.textMuted),
                onPressed: () {
                  _searchController.clear();
                  setState(() => _searchQuery = '');
                },
              )
            : null,
      ),
    );
  }

  Widget _buildSortChips(NightBiteColors colors) {
    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      child: Row(
        children: [
          _buildChip('Most Recent', 'recent', colors),
          const SizedBox(width: 8),
          _buildChip('Most Ordered', 'frequency', colors),
          const SizedBox(width: 8),
          _buildChip('Highest Risk', 'risk', colors),
        ],
      ),
    );
  }

  Widget _buildChip(String label, String value, NightBiteColors colors) {
    final isSelected = _sortBy == value;
    return ChoiceChip(
      label: Text(label),
      selected: isSelected,
      onSelected: (selected) {
        if (selected) setState(() => _sortBy = value);
      },
      backgroundColor: colors.surfaceHighlight,
      selectedColor: colors.primary.withValues(alpha: 0.2),
      labelStyle: TextStyle(
        color: isSelected ? colors.primaryLight : colors.textSecondary,
        fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
      ),
      side: BorderSide(
        color: isSelected ? colors.primary.withValues(alpha: 0.5) : Colors.transparent,
      ),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
    );
  }

  Widget _buildEmptyState(NightBiteColors colors) {
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(Icons.history, size: 64, color: colors.textMuted.withValues(alpha: 0.5)),
          const SizedBox(height: 16),
          Text(
            'No late-night history yet.',
            style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: colors.textSecondary),
          ),
          const SizedBox(height: 8),
          Text(
            'Your captured orders will group here.',
            style: TextStyle(color: colors.textMuted),
          ),
        ],
      ),
    );
  }
}

class _GroupedHistory {
  final String name;
  final int count;
  final HistoryEventItem latestEvent;
  final double avgRisk;
  final List<HistoryEventItem> allEvents;

  _GroupedHistory({
    required this.name,
    required this.count,
    required this.latestEvent,
    required this.avgRisk,
    required this.allEvents,
  });
}

class _GroupedHistoryCard extends StatelessWidget {
  final _GroupedHistory group;
  final NightBiteColors colors;

  const _GroupedHistoryCard({required this.group, required this.colors});

  @override
  Widget build(BuildContext context) {
    final isHighRisk = group.avgRisk >= 7.0; // Simple threshold
    final dateStr = DateFormat('MMM d, h:mm a').format(group.latestEvent.eventTimestamp.toLocal());

    return InkWell(
      onTap: () {
        // Show Drill Down Bottom Sheet or Dialog
        _showItemDetails(context, group, colors);
      },
      borderRadius: BorderRadius.circular(16),
      child: Container(
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
              width: 52,
              height: 52,
              alignment: Alignment.center,
              decoration: BoxDecoration(
                color: isHighRisk ? colors.riskHigh.withValues(alpha: 0.1) : colors.primary.withValues(alpha: 0.1),
                shape: BoxShape.circle,
              ),
              child: Text(
                '${group.count}x',
                style: TextStyle(
                  color: isHighRisk ? colors.riskHigh : colors.primaryLight,
                  fontWeight: FontWeight.bold,
                  fontSize: 16,
                ),
              ),
            ),
            const SizedBox(width: 16),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    group.name,
                    style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: colors.textPrimary),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                  const SizedBox(height: 4),
                  Row(
                    children: [
                      Icon(Icons.history, size: 14, color: colors.textMuted),
                      const SizedBox(width: 4),
                      Expanded(
                        child: Text(
                          'Last: $dateStr',
                          style: TextStyle(fontSize: 12, color: colors.textSecondary),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
            const SizedBox(width: 8),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
              decoration: BoxDecoration(
                color: colors.surfaceHighlight,
                borderRadius: BorderRadius.circular(12),
              ),
              child: Row(
                children: [
                  Icon(Icons.local_fire_department, size: 14, color: isHighRisk ? colors.riskHigh : colors.riskMedium),
                  const SizedBox(width: 4),
                  Text(
                    group.avgRisk.toStringAsFixed(1),
                    style: TextStyle(
                      color: isHighRisk ? colors.riskHigh : colors.textPrimary,
                      fontWeight: FontWeight.bold,
                    ),
                  )
                ],
              ),
            )
          ],
        ),
      ),
    );
  }

  void _showItemDetails(BuildContext context, _GroupedHistory group, NightBiteColors colors) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (ctx) => Container(
        height: MediaQuery.of(context).size.height * 0.85,
        decoration: BoxDecoration(
          color: colors.background,
          borderRadius: const BorderRadius.vertical(top: Radius.circular(24)),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Center(
              child: Container(
                margin: const EdgeInsets.only(top: 12, bottom: 24),
                width: 40,
                height: 4,
                decoration: BoxDecoration(
                  color: colors.divider,
                  borderRadius: BorderRadius.circular(2),
                ),
              ),
            ),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 24),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(group.name, style: TextStyle(fontSize: 28, fontWeight: FontWeight.bold, color: colors.textPrimary)),
                  const SizedBox(height: 8),
                  Text('Ordered ${group.count} times late-night', style: TextStyle(fontSize: 16, color: colors.textSecondary)),
                ],
              ),
            ),
            const SizedBox(height: 24),
            Expanded(
              child: ListView(
                padding: const EdgeInsets.symmetric(horizontal: 24),
                children: [
                  Container(
                    padding: const EdgeInsets.all(20),
                    decoration: BoxDecoration(
                      color: colors.surface,
                      borderRadius: BorderRadius.circular(20),
                      border: Border.all(color: colors.divider),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text('Order History', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: colors.textPrimary)),
                        const SizedBox(height: 16),
                        ...group.allEvents.map((e) {
                          return Padding(
                            padding: const EdgeInsets.only(bottom: 12),
                            child: Row(
                              children: [
                                Container(
                                  width: 8,
                                  height: 8,
                                  decoration: BoxDecoration(
                                    color: colors.primary,
                                    shape: BoxShape.circle,
                                  ),
                                ),
                                const SizedBox(width: 12),
                                Expanded(
                                  child: Text(
                                    DateFormat('MMM d, yyyy').format(e.eventTimestamp.toLocal()),
                                    style: TextStyle(color: colors.textPrimary),
                                  ),
                                ),
                                Text(
                                  DateFormat('h:mm a').format(e.eventTimestamp.toLocal()),
                                  style: TextStyle(color: colors.textSecondary, fontWeight: FontWeight.bold),
                                ),
                              ],
                            ),
                          );
                        }),
                      ],
                    ),
                  ),
                  const SizedBox(height: 24),
                  ElevatedButton.icon(
                    onPressed: () {
                      Navigator.pop(context);
                      showModalBottomSheet(
                        context: context,
                        isScrollControlled: true,
                        backgroundColor: Colors.transparent,
                        builder: (ctx) => AiCoachChatSheet(initialPrompt: 'Why is my recurring late-night habit of ordering ${group.name} risky?'),
                      );
                    },
                    icon: const Icon(Icons.psychology),
                    label: const Text('Ask AI about this habit'),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: colors.primary,
                      foregroundColor: Colors.white,
                      minimumSize: const Size(double.infinity, 56),
                    ),
                  ),
                  const SizedBox(height: 48),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
