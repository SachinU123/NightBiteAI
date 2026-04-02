import 'package:flutter_test/flutter_test.dart';
import 'package:nightbite/main.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

void main() {
  testWidgets('App starts without error', (WidgetTester tester) async {
    await tester.pumpWidget(const ProviderScope(child: NightBiteApp()));
  });
}
