import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../../core/theme/app_colors_extension.dart';
import '../../providers/chat_provider.dart';

/// AI Coach tab — full-screen chat with Claude backend.
/// Quick action prompts PREFILL the input — user must press send themselves.
class AiCoachTab extends ConsumerStatefulWidget {
  const AiCoachTab({super.key});

  @override
  ConsumerState<AiCoachTab> createState() => _AiCoachTabState();
}

class _AiCoachTabState extends ConsumerState<AiCoachTab> {
  final _controller = TextEditingController();
  final _scrollCtrl = ScrollController();

  // Quick action prompts — these prefill the chat input, NOT auto-send
  static const _quickPrompts = [
    'Analyze my late-night ordering pattern for this month.',
    'Suggest healthier swaps based on my recent late-night orders.',
    'Why is my recurring late-night order pattern risky?',
    'What do my order times say about my eating habits?',
    'Which foods should I avoid after 11 PM?',
  ];

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

  void _prefill(String text) {
    _controller.text = text;
    _controller.selection = TextSelection.fromPosition(
      TextPosition(offset: text.length),
    );
    ref.read(chatProvider.notifier).clearPrefill();
  }

  @override
  Widget build(BuildContext context) {
    final chatState = ref.watch(chatProvider);
    final colors = context.appColors;

    // Consume any pending prefill (from Home quick actions or History)
    if (chatState.pendingPrefill != null) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        _prefill(chatState.pendingPrefill!);
      });
    }

    if (chatState.messages.length > 1) _scrollToBottom();

    return Column(
      children: [
        // ── Header ──────────────────────────────────────────────────────────
        Container(
          padding: const EdgeInsets.fromLTRB(20, 16, 20, 16),
          decoration: BoxDecoration(
            color: colors.surface,
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
                child: Icon(Icons.psychology, color: colors.primaryLight, size: 22),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'AI Coach',
                      style: TextStyle(
                        fontSize: 18,
                        fontWeight: FontWeight.bold,
                        color: colors.textPrimary,
                      ),
                    ),
                    Text(
                      'Powered by Claude · Knows your history',
                      style: TextStyle(fontSize: 11, color: colors.textMuted),
                    ),
                  ],
                ),
              ),
              // Clear chat
              if (chatState.messages.length > 1)
                IconButton(
                  icon: Icon(Icons.refresh, color: colors.textSecondary, size: 20),
                  tooltip: 'Clear chat',
                  onPressed: () {
                    ref.read(chatProvider.notifier).clearChat();
                    _controller.clear();
                  },
                ),
            ],
          ),
        ),

        // ── Quick prompts ────────────────────────────────────────────────────
        if (chatState.messages.length <= 1 && !chatState.isLoading)
          _QuickPromptCarousel(
            prompts: _quickPrompts,
            colors: colors,
            onTap: _prefill, // prefill only — do NOT auto-send
          ),

        // ── Messages ────────────────────────────────────────────────────────
        Expanded(
          child: ListView.builder(
            controller: _scrollCtrl,
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
            itemCount: chatState.messages.length + (chatState.isLoading ? 1 : 0),
            itemBuilder: (context, index) {
              // Typing indicator
              if (index == chatState.messages.length) {
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

              final msg = chatState.messages[index];
              return Padding(
                padding: const EdgeInsets.only(bottom: 12),
                child: Row(
                  mainAxisAlignment:
                      msg.isUser ? MainAxisAlignment.end : MainAxisAlignment.start,
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
                          color: msg.isError ? colors.riskHigh : colors.primaryLight,
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
                            height: 1.5,
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

        // ── Input bar ────────────────────────────────────────────────────────
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
                  enabled: !chatState.isLoading,
                  style: TextStyle(color: colors.textPrimary, fontSize: 14),
                  textCapitalization: TextCapitalization.sentences,
                  onSubmitted: (_) => _send(),
                  maxLines: 3,
                  minLines: 1,
                  decoration: InputDecoration(
                    hintText: chatState.isLoading
                        ? 'Coach is thinking...'
                        : 'Ask your AI Coach...',
                    hintStyle: TextStyle(color: colors.textMuted, fontSize: 14),
                    filled: true,
                    fillColor: colors.background,
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(20),
                      borderSide: BorderSide.none,
                    ),
                    contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                  ),
                ),
              ),
              const SizedBox(width: 10),
              GestureDetector(
                onTap: chatState.isLoading ? null : _send,
                child: AnimatedContainer(
                  duration: const Duration(milliseconds: 200),
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: chatState.isLoading ? colors.divider : colors.primary,
                    shape: BoxShape.circle,
                  ),
                  child: chatState.isLoading
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
    );
  }
}

// ── Quick Prompt Carousel ────────────────────────────────────────────────────

class _QuickPromptCarousel extends StatelessWidget {
  final List<String> prompts;
  final NightBiteColors colors;
  final void Function(String) onTap;

  const _QuickPromptCarousel({
    required this.prompts,
    required this.colors,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 12, 16, 8),
          child: Text(
            'Quick questions — tap to prefill',
            style: TextStyle(
              fontSize: 11,
              color: colors.textMuted,
              letterSpacing: 0.5,
            ),
          ),
        ),
        SingleChildScrollView(
          scrollDirection: Axis.horizontal,
          padding: const EdgeInsets.symmetric(horizontal: 16),
          child: Row(
            children: prompts
                .map((prompt) => Padding(
                      padding: const EdgeInsets.only(right: 8),
                      child: ActionChip(
                        label: Text(
                          prompt,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                        backgroundColor: colors.surfaceHighlight,
                        labelStyle: TextStyle(color: colors.textSecondary, fontSize: 12),
                        side: BorderSide(color: colors.divider),
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                        onPressed: () => onTap(prompt),
                      ),
                    ))
                .toList(),
          ),
        ),
        const SizedBox(height: 8),
      ],
    );
  }
}

// ── Animated typing dot ──────────────────────────────────────────────────────

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
