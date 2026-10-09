import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:batocera_remote/screens/virtual_pad_screen.dart';
import 'package:batocera_remote/widgets/back_handler.dart';
import 'package:batocera_remote/widgets/gamepad_controls.dart';

void main() {
  testWidgets('fullscreen uses landscape and Android back restores portrait', (tester) async {
    final calls = <MethodCall>[];
    tester.view.devicePixelRatio = 1;
    tester.view.physicalSize = const Size(420, 900);
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    tester.binding.defaultBinaryMessenger.setMockMethodCallHandler(
      SystemChannels.platform, (call) async { calls.add(call); return null; });
    addTearDown(() => tester.binding.defaultBinaryMessenger
      .setMockMethodCallHandler(SystemChannels.platform, null));
    await tester.pumpWidget(const MaterialApp(home: VirtualPadScreen()));
    await tester.tap(find.byIcon(Icons.fullscreen));
    await tester.pumpAndSettle();
    tester.view.physicalSize = const Size(800, 360);
    await tester.pumpAndSettle();
    expect(find.byType(GamepadControls), findsOneWidget);
    expect(find.byType(AnalogStick), findsNWidgets(2));
    expect(tester.takeException(), isNull);
    expect(calls.any((call) => call.method == 'SystemChrome.setPreferredOrientations' &&
      (call.arguments as List).contains('DeviceOrientation.landscapeLeft')), isTrue);
    expect(TabBackHandler.handle(1), isTrue);
    // Simulate the OS restoring portrait while the route closes.
    tester.view.physicalSize = const Size(420, 900);
    await tester.pumpAndSettle();
    expect(find.byType(GamepadControls), findsNothing);
    expect(TabBackHandler.hasHandler(1), isFalse);
    expect(calls.lastWhere((c) => c.method == 'SystemChrome.setPreferredOrientations').arguments,
      ['DeviceOrientation.portraitUp', 'DeviceOrientation.portraitDown']);
    expect(calls.lastWhere((c) => c.method == 'SystemChrome.setEnabledSystemUIMode').arguments,
      containsPair('mode', 'SystemUiMode.edgeToEdge'));
    expect(tester.takeException(), isNull);
    await tester.pumpWidget(const SizedBox.shrink());
  });
}
