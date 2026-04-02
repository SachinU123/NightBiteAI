import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../../core/theme/app_colors_extension.dart';
import '../../providers/food_provider.dart';

/// Premium manual food order entry bottom sheet.
/// Submits through the SAME backend pipeline as notification captures.
/// Source is marked as 'manual_entry'.
class ManualEntrySheet extends ConsumerStatefulWidget {
  const ManualEntrySheet({super.key});

  @override
  ConsumerState<ManualEntrySheet> createState() => _ManualEntrySheetState();
}

class _ManualEntrySheetState extends ConsumerState<ManualEntrySheet> {
  final _formKey = GlobalKey<FormState>();
  final _foodController = TextEditingController();
  final _restaurantController = TextEditingController();
  final _notesController = TextEditingController();

  String _selectedSource = 'Manual';
  String? _selectedCategory;
  DateTime _selectedTime = DateTime.now();
  bool _submitted = false;

  static const _sources = ['Manual', 'Zomato', 'Swiggy', 'Other'];
  static const _categories = [
    'Fried Fast Food',
    'Pizza',
    'Biryani / Rice',
    'Noodles / Pasta',
    'Burger',
    'Dessert / Sweet',
    'Beverages',
    'Healthy / Salad',
    'Street Food',
    'Other',
  ];

  @override
  void dispose() {
    _foodController.dispose();
    _restaurantController.dispose();
    _notesController.dispose();
    super.dispose();
  }

  Future<void> _pickTime() async {
    final picked = await showTimePicker(
      context: context,
      initialTime: TimeOfDay.fromDateTime(_selectedTime),
    );
    if (picked != null) {
      setState(() {
        _selectedTime = DateTime(
          _selectedTime.year,
          _selectedTime.month,
          _selectedTime.day,
          picked.hour,
          picked.minute,
        );
      });
    }
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;

    final food = _foodController.text.trim();
    final restaurant = _restaurantController.text.trim();
    final notes = _notesController.text.trim();

    // Build the food text that backend NLP will process
    final foodText = [
      food,
      if (restaurant.isNotEmpty) 'from $restaurant',
      if (_selectedCategory != null) '($_selectedCategory)',
      if (notes.isNotEmpty) '- $notes',
    ].join(' ');

    await ref.read(foodActionProvider.notifier).manualEntry(foodText);
    setState(() => _submitted = true);

    await Future.delayed(const Duration(milliseconds: 1500));
    if (mounted) Navigator.of(context).pop();
  }

  @override
  Widget build(BuildContext context) {
    final colors = context.appColors;
    final actionState = ref.watch(foodActionProvider);
    final isLoading = actionState is AsyncLoading;

    return Container(
      height: MediaQuery.of(context).size.height * 0.92,
      decoration: BoxDecoration(
        color: colors.background,
        borderRadius: const BorderRadius.vertical(top: Radius.circular(24)),
      ),
      child: Column(
        children: [
          // Handle
          Container(
            width: 40,
            height: 4,
            margin: const EdgeInsets.symmetric(vertical: 12),
            decoration: BoxDecoration(
              color: colors.divider,
              borderRadius: BorderRadius.circular(2),
            ),
          ),

          // Header
          Padding(
            padding: const EdgeInsets.fromLTRB(20, 0, 20, 16),
            child: Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(10),
                  decoration: BoxDecoration(
                    color: colors.primary.withValues(alpha: 0.15),
                    shape: BoxShape.circle,
                  ),
                  child: Icon(Icons.add_circle_outline, color: colors.primaryLight, size: 22),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Log Order Manually',
                        style: TextStyle(
                          fontSize: 18,
                          fontWeight: FontWeight.bold,
                          color: colors.textPrimary,
                        ),
                      ),
                      Text(
                        'Goes through the same AI risk pipeline',
                        style: TextStyle(fontSize: 11, color: colors.textMuted),
                      ),
                    ],
                  ),
                ),
                IconButton(
                  icon: Icon(Icons.close, color: colors.textSecondary),
                  onPressed: () => Navigator.of(context).pop(),
                ),
              ],
            ),
          ),

          Divider(color: colors.divider, height: 1),

          // Form
          Expanded(
            child: _submitted
                ? _SuccessState(colors: colors)
                : SingleChildScrollView(
                    padding: EdgeInsets.only(
                      left: 20,
                      right: 20,
                      top: 20,
                      bottom: MediaQuery.of(context).viewInsets.bottom + 20,
                    ),
                    child: Form(
                      key: _formKey,
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          // Error state
                          if (actionState is AsyncError)
                            Container(
                              margin: const EdgeInsets.only(bottom: 16),
                              padding: const EdgeInsets.all(12),
                              decoration: BoxDecoration(
                                color: colors.riskHigh.withValues(alpha: 0.1),
                                borderRadius: BorderRadius.circular(12),
                                border: Border.all(color: colors.riskHigh.withValues(alpha: 0.3)),
                              ),
                              child: Text(
                                'Failed to save: ${actionState.error}',
                                style: TextStyle(color: colors.riskHigh, fontSize: 13),
                              ),
                            ),

                          // Food Item
                          _FieldLabel('What did you eat? *', colors),
                          const SizedBox(height: 8),
                          TextFormField(
                            controller: _foodController,
                            style: TextStyle(color: colors.textPrimary),
                            textCapitalization: TextCapitalization.sentences,
                            decoration: _inputDeco(
                              hint: 'e.g. Butter Chicken with Naan, Maggi...',
                              icon: Icons.restaurant_menu,
                              colors: colors,
                            ),
                            validator: (v) {
                              if (v == null || v.trim().isEmpty) return 'Please enter what you ate';
                              if (v.trim().length < 3) return 'Be a bit more specific';
                              return null;
                            },
                          ),
                          const SizedBox(height: 20),

                          // Restaurant / Source App
                          _FieldLabel('Restaurant / Platform', colors),
                          const SizedBox(height: 8),
                          Row(
                            children: [
                              Expanded(
                                child: TextFormField(
                                  controller: _restaurantController,
                                  style: TextStyle(color: colors.textPrimary),
                                  textCapitalization: TextCapitalization.words,
                                  decoration: _inputDeco(
                                    hint: 'Restaurant name (optional)',
                                    icon: Icons.store_outlined,
                                    colors: colors,
                                  ),
                                ),
                              ),
                              const SizedBox(width: 12),
                              // Source dropdown
                              Container(
                                padding: const EdgeInsets.symmetric(horizontal: 12),
                                decoration: BoxDecoration(
                                  color: colors.surface,
                                  borderRadius: BorderRadius.circular(12),
                                  border: Border.all(color: colors.divider),
                                ),
                                child: DropdownButtonHideUnderline(
                                  child: DropdownButton<String>(
                                    value: _selectedSource,
                                    dropdownColor: colors.surface,
                                    style: TextStyle(color: colors.textPrimary, fontSize: 14),
                                    items: _sources
                                        .map((s) => DropdownMenuItem(value: s, child: Text(s)))
                                        .toList(),
                                    onChanged: (v) => setState(() => _selectedSource = v!),
                                  ),
                                ),
                              ),
                            ],
                          ),
                          const SizedBox(height: 20),

                          // Category
                          _FieldLabel('Food Category (optional)', colors),
                          const SizedBox(height: 8),
                          Container(
                            width: double.infinity,
                            padding: const EdgeInsets.symmetric(horizontal: 12),
                            decoration: BoxDecoration(
                              color: colors.surface,
                              borderRadius: BorderRadius.circular(12),
                              border: Border.all(color: colors.divider),
                            ),
                            child: DropdownButtonHideUnderline(
                              child: DropdownButton<String?>(
                                value: _selectedCategory,
                                isExpanded: true,
                                dropdownColor: colors.surface,
                                hint: Text('Select category', style: TextStyle(color: colors.textMuted)),
                                style: TextStyle(color: colors.textPrimary, fontSize: 14),
                                items: [
                                  DropdownMenuItem<String?>(value: null, child: Text('No category', style: TextStyle(color: colors.textMuted))),
                                  ..._categories.map((c) => DropdownMenuItem(value: c, child: Text(c))),
                                ],
                                onChanged: (v) => setState(() => _selectedCategory = v),
                              ),
                            ),
                          ),
                          const SizedBox(height: 20),

                          // Order Time
                          _FieldLabel('Order Time', colors),
                          const SizedBox(height: 8),
                          InkWell(
                            onTap: _pickTime,
                            borderRadius: BorderRadius.circular(12),
                            child: Container(
                              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
                              decoration: BoxDecoration(
                                color: colors.surface,
                                borderRadius: BorderRadius.circular(12),
                                border: Border.all(color: colors.divider),
                              ),
                              child: Row(
                                children: [
                                  Icon(Icons.access_time, color: colors.primaryLight, size: 18),
                                  const SizedBox(width: 12),
                                  Text(
                                    TimeOfDay.fromDateTime(_selectedTime).format(context),
                                    style: TextStyle(color: colors.textPrimary, fontSize: 15),
                                  ),
                                  const Spacer(),
                                  Icon(Icons.expand_more, color: colors.textMuted),
                                ],
                              ),
                            ),
                          ),
                          const SizedBox(height: 20),

                          // Notes
                          _FieldLabel('Notes (optional)', colors),
                          const SizedBox(height: 8),
                          TextFormField(
                            controller: _notesController,
                            style: TextStyle(color: colors.textPrimary),
                            maxLines: 2,
                            decoration: _inputDeco(
                              hint: 'e.g. extra spicy, large portion...',
                              icon: Icons.notes,
                              colors: colors,
                            ),
                          ),
                          const SizedBox(height: 32),

                          // Submit Button
                          SizedBox(
                            width: double.infinity,
                            child: ElevatedButton(
                              onPressed: isLoading ? null : _submit,
                              style: ElevatedButton.styleFrom(
                                padding: const EdgeInsets.symmetric(vertical: 16),
                                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                              ),
                              child: isLoading
                                  ? const SizedBox(
                                      height: 20,
                                      width: 20,
                                      child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                                    )
                                  : const Text(
                                      'Log & Analyze',
                                      style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
                                    ),
                            ),
                          ),
                          const SizedBox(height: 8),
                          Center(
                            child: Text(
                              'Your entry will be analyzed for late-night risk',
                              style: TextStyle(color: colors.textMuted, fontSize: 12),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
          ),
        ],
      ),
    );
  }

  InputDecoration _inputDeco({
    required String hint,
    required IconData icon,
    required NightBiteColors colors,
  }) {
    return InputDecoration(
      hintText: hint,
      hintStyle: TextStyle(color: colors.textMuted, fontSize: 14),
      prefixIcon: Icon(icon, color: colors.textMuted, size: 18),
      filled: true,
      fillColor: colors.surface,
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(12),
        borderSide: BorderSide(color: colors.divider),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(12),
        borderSide: BorderSide(color: colors.divider),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(12),
        borderSide: BorderSide(color: colors.primary, width: 1.5),
      ),
      contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 14),
    );
  }
}

class _FieldLabel extends StatelessWidget {
  final String label;
  final NightBiteColors colors;
  const _FieldLabel(this.label, this.colors);

  @override
  Widget build(BuildContext context) {
    return Text(
      label,
      style: TextStyle(
        color: colors.textSecondary,
        fontSize: 13,
        fontWeight: FontWeight.w600,
        letterSpacing: 0.2,
      ),
    );
  }
}

class _SuccessState extends StatelessWidget {
  final NightBiteColors colors;
  const _SuccessState({required this.colors});

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Container(
            padding: const EdgeInsets.all(24),
            decoration: BoxDecoration(
              color: colors.success.withValues(alpha: 0.1),
              shape: BoxShape.circle,
            ),
            child: Icon(Icons.check_circle_outline, size: 64, color: colors.success),
          ),
          const SizedBox(height: 20),
          Text(
            'Order Logged!',
            style: TextStyle(
              fontSize: 22,
              fontWeight: FontWeight.bold,
              color: colors.textPrimary,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            'Running risk analysis...',
            style: TextStyle(color: colors.textMuted, fontSize: 14),
          ),
        ],
      ),
    );
  }
}
