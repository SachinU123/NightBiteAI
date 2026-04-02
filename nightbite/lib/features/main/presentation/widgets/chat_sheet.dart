import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../../core/theme/app_colors_extension.dart';
import '../../providers/chat_provider.dart';

class AiCoachChatSheet extends ConsumerStatefulWidget {
  final String? initialPrompt;

  const AiCoachChatSheet({super.key, this.initialPrompt});

  @override
  ConsumerState<AiCoachChatSheet> createState() => _AiCoachChatSheetState();
}

class _AiCoachChatSheetState extends ConsumerState<AiCoachChatSheet> {
  final _controller = TextEditingController();
  final _scrollCtrl = ScrollController();
  bool _hasInitializedPrompt = false;

  @override
  void initState() {
    super.initState();
    // Ensure the sheet size handles initial prompt correctly
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (widget.initialPrompt != null && !_hasInitializedPrompt) {
        _hasInitializedPrompt = true;
        _controller.text = widget.initialPrompt!;
        _send();
      }
    });
  }

  @override
  void dispose() {
    _controller.dispose();
    _scrollCtrl.dispose();
    super.dispose();
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollCtrl.hasClients) {
        _scrollCtrl.animateTo(
          _scrollCtrl.position.maxScrollExtent + 120,
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeOut,
        );
      }
    });
  }

  void _send() {
    final text = _controller.text.trim();
    if (text.isEmpty) return;
    _controller.clear();
    ref.read(chatProvider.notifier).sendMessage(text);
    _scrollToBottom();
  }

  @override
  Widget build(BuildContext context) {
    final chatState = ref.watch(chatProvider);
    final messages = chatState.messages;
    final isLoading = chatState.isLoading;
    final colors = context.appColors;

    // Auto-scroll when messages change
    if (messages.isNotEmpty) _scrollToBottom();

    return Container(
      height: MediaQuery.of(context).size.height * 0.88,
      decoration: BoxDecoration(
        color: colors.background,
        borderRadius: const BorderRadius.vertical(top: Radius.circular(24)),
      ),
      child: Column(
        children: [
          // ── Handle bar ──────────────────────────────────────────────────
          Container(
            width: 40,
            height: 4,
            margin: const EdgeInsets.symmetric(vertical: 12),
            decoration: BoxDecoration(
              color: colors.divider,
              borderRadius: BorderRadius.circular(2),
            ),
          ),

          // ── Header ──────────────────────────────────────────────────────
          Container(
            padding: const EdgeInsets.fromLTRB(20, 0, 12, 16),
            decoration: BoxDecoration(
              border: Border(bottom: BorderSide(color: colors.divider)),
            ),
            child: Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(10),
                  decoration: BoxDecoration(
                    color: colors.primary.withValues(alpha: 0.15),
                    shape: BoxShape.circle,
                  ),
                  child: Icon(Icons.psychology, color: colors.primaryLight, size: 24),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('AI Coach',
                          style: TextStyle(
                              fontSize: 17,
                              fontWeight: FontWeight.bold,
                              color: colors.textPrimary)),
                      Text('Powered by Claude · Knows your history',
                          style: TextStyle(
                              fontSize: 11, color: colors.primaryLight)),
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

          // ── Fast Prompts ────────────────────────────────────────────────
          if (messages.isEmpty && !isLoading)
            SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              padding: const EdgeInsets.all(16),
              child: Row(
                children: [
                  _buildPromptChip('Analyze my recent late-night behavior', colors),
                  const SizedBox(width: 8),
                  _buildPromptChip('Why do I order most after midnight?', colors),
                  const SizedBox(width: 8),
                  _buildPromptChip('Suggest healthier alternatives', colors),
                ],
              ),
            ),

          // ── Messages ────────────────────────────────────────────────────
          Expanded(
            child: ListView.builder(
              controller: _scrollCtrl,
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
              itemCount: messages.length + (isLoading ? 1 : 0),
              itemBuilder: (context, index) {
                // Typing indicator
                if (index == messages.length) {
                  return Padding(
                    padding: const EdgeInsets.only(top: 8),
                    child: Row(
                      children: [
                        Container(
                          padding: const EdgeInsets.all(10),
                          decoration: BoxDecoration(
                            color: colors.surfaceHighlight,
                            shape: BoxShape.circle,
                          ),
                          child: Icon(Icons.psychology, size: 14, color: colors.primaryLight),
                        ),
                        const SizedBox(width: 8),
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                          decoration: BoxDecoration(
                            color: colors.surfaceHighlight,
                            borderRadius: BorderRadius.circular(20),
                          ),
                          child: Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              _Dot(delay: 0, colors: colors),
                              const SizedBox(width: 4),
                              _Dot(delay: 200, colors: colors),
                              const SizedBox(width: 4),
                              _Dot(delay: 400, colors: colors),
                            ],
                          ),
                        ),
                      ],
                    ),
                  );
                }

                final msg = messages[index];
                return Padding(
                  padding: const EdgeInsets.only(bottom: 12),
                  child: Row(
                    mainAxisAlignment: msg.isUser
                        ? MainAxisAlignment.end
                        : MainAxisAlignment.start,
                    crossAxisAlignment: CrossAxisAlignment.end,
                    children: [
                      if (!msg.isUser) ...[
                        Container(
                          padding: const EdgeInsets.all(6),
                          decoration: BoxDecoration(
                            color: msg.isError
                                ? colors.riskHigh.withValues(alpha: 0.2)
                                : colors.surfaceHighlight,
                            shape: BoxShape.circle,
                          ),
                          child: Icon(
                            msg.isError ? Icons.error_outline : Icons.psychology,
                            size: 14,
                            color: msg.isError
                                ? colors.riskHigh
                                : colors.primaryLight,
                          ),
                        ),
                        const SizedBox(width: 8),
                      ],
                      Flexible(
                        child: Container(
                          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                          decoration: BoxDecoration(
                            color: msg.isUser
                                ? colors.primary
                                : msg.isError
                                    ? colors.riskHigh.withValues(alpha: 0.1)
                                    : colors.surfaceHighlight,
                            borderRadius: BorderRadius.only(
                              topLeft: const Radius.circular(20),
                              topRight: const Radius.circular(20),
                              bottomLeft: Radius.circular(msg.isUser ? 20 : 4),
                              bottomRight: Radius.circular(msg.isUser ? 4 : 20),
                            ),
                            border: msg.isError
                                ? Border.all(color: colors.riskHigh.withValues(alpha: 0.3))
                                : null,
                          ),
                          child: Text(
                            msg.text,
                            style: TextStyle(
                              color: msg.isUser
                                  ? Colors.white
                                  : msg.isError
                                      ? colors.riskHigh
                                      : colors.textPrimary,
                              fontSize: 14,
                              height: 1.45,
                            ),
                          ),
                        ),
                      ),
                      if (msg.isUser) const SizedBox(width: 8),
                    ],
                  ),
                );
              },
            ),
          ),

          // ── Input Bar ───────────────────────────────────────────────────
          Container(
            padding: EdgeInsets.only(
              left: 16,
              right: 16,
              top: 12,
              bottom: MediaQuery.of(context).viewInsets.bottom + 16,
            ),
            decoration: BoxDecoration(
              color: colors.surface,
              border: Border(top: BorderSide(color: colors.divider)),
            ),
            child: Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _controller,
                    enabled: !isLoading,
                    style: TextStyle(color: colors.textPrimary, fontSize: 14),
                    textCapitalization: TextCapitalization.sentences,
                    onSubmitted: (_) => _send(),
                    decoration: InputDecoration(
                      hintText: isLoading
                          ? 'Coach is thinking...'
                          : 'Ask your coach...',
                      hintStyle: TextStyle(color: colors.textMuted, fontSize: 14),
                      filled: true,
                      fillColor: colors.background,
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(24),
                        borderSide: BorderSide.none,
                      ),
                      contentPadding: const EdgeInsets.symmetric(horizontal: 18, vertical: 12),
                    ),
                  ),
                ),
                const SizedBox(width: 10),
                GestureDetector(
                  onTap: isLoading ? null : _send,
                  child: AnimatedContainer(
                    duration: const Duration(milliseconds: 200),
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: isLoading
                          ? colors.divider
                          : colors.primary,
                      shape: BoxShape.circle,
                    ),
                    child: isLoading
                        ? const SizedBox(
                            width: 20,
                            height: 20,
                            child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2),
                          )
                        : const Icon(Icons.send, color: Colors.white, size: 20),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildPromptChip(String text, NightBiteColors colors) {
    return ActionChip(
      label: Text(text),
      backgroundColor: colors.surfaceHighlight,
      labelStyle: TextStyle(color: colors.textSecondary, fontSize: 13),
      side: BorderSide(color: colors.divider),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      onPressed: () {
        _controller.text = text;
        _send();
      },
    );
  }
}

// ── Animated typing dot ───────────────────────────────────────────────────────

class _Dot extends StatefulWidget {
  final int delay;
  final NightBiteColors colors;
  
  const _Dot({required this.delay, required this.colors});

  @override
  State<_Dot> createState() => _DotState();
}

class _DotState extends State<_Dot> with SingleTickerProviderStateMixin {
  late final AnimationController _ctrl;
  late final Animation<double> _opacity;

  @override
  void initState() {
    super.initState();
    _ctrl = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 800),
    )..repeat(reverse: true);

    _opacity = Tween(begin: 0.2, end: 1.0).animate(
      CurvedAnimation(parent: _ctrl, curve: Curves.easeInOut),
    );

    Future.delayed(Duration(milliseconds: widget.delay), () {
      if (mounted) _ctrl.forward();
    });
  }

  @override
  void dispose() {
    _ctrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return FadeTransition(
      opacity: _opacity,
      child: Container(
        width: 6,
        height: 6,
        decoration: BoxDecoration(
          color: widget.colors.primaryLight,
          shape: BoxShape.circle,
        ),
      ),
    );
  }
}
