import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:batocera_remote/widgets/gamepad_controls.dart';

void main() {
  Future<void> mount(WidgetTester tester, List<String> commands,
      {bool enabled = true, Size size = const Size(800, 400)}) async {
    tester.view.devicePixelRatio = 1;
    tester.view.physicalSize = size;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    await tester.pumpWidget(MaterialApp(home: Scaffold(
      body: GamepadControls(send: commands.add, enabled: enabled))));
  }

  testWidgets('stick and button support simultaneous independent touches', (tester) async {
    final commands = <String>[];
    await mount(tester, commands);
    final stick = find.byKey(const ValueKey('left-stick'));
    final center = tester.getCenter(stick);
    final finger = await tester.startGesture(center, pointer: 1);
    await finger.moveTo(center + const Offset(40, -20));
    await tester.pump(const Duration(milliseconds: 20));
    expect(commands.any((c) => c.startsWith('stick left ') && c != 'stick left 0 0'), isTrue);
    final button = await tester.startGesture(tester.getCenter(find.text('A')), pointer: 2);
    expect(commands, contains('press a'));
    await button.up();
    expect(commands.last, 'release a');
    await finger.cancel();
    expect(commands.last, 'stick left 0 0');
    await tester.pump(const Duration(milliseconds: 30));
    expect(commands.last, 'stick left 0 0');
  });

  testWidgets('second finger cannot release the first finger button', (tester) async {
    final commands = <String>[];
    await mount(tester, commands);
    final center = tester.getCenter(find.text('RB'));
    final first = await tester.startGesture(center, pointer: 3);
    final second = await tester.startGesture(center, pointer: 4);
    await second.up();
    expect(commands, ['press r1']);
    await first.cancel();
    expect(commands, ['press r1', 'release r1']);
  });

  testWidgets('disabling controls releases held stick and buttons', (tester) async {
    final commands = <String>[];
    await mount(tester, commands);
    final finger = await tester.startGesture(
      tester.getCenter(find.byKey(const ValueKey('right-stick'))) + const Offset(35, 0),
      pointer: 5);
    final button = await tester.startGesture(tester.getCenter(find.text('L3')), pointer: 6);
    await mount(tester, commands, enabled: false);
    expect(commands, contains('release l3'));
    expect(commands.lastWhere((c) => c.startsWith('stick right')), 'stick right 0 0');
    final count = commands.length;
    await finger.moveBy(const Offset(20, 0));
    await button.up();
    await finger.up();
    await tester.pump(const Duration(milliseconds: 30));
    expect(commands.length, count);
  });

  testWidgets('compact landscape layout has no overflow and has Xbox button colors', (tester) async {
    final commands = <String>[];
    await mount(tester, commands, size: const Size(568, 240));
    expect(tester.takeException(), isNull);
    expect(find.byType(AnalogStick), findsNWidgets(2));
    for (final entry in {'A': Colors.green, 'B': Colors.red, 'X': Colors.blue, 'Y': Colors.amber}.entries) {
      final button = tester.widget<PadHoldButton>(
        find.ancestor(of: find.text(entry.key), matching: find.byType(PadHoldButton)));
      expect(button.color, entry.value);
    }
  });

  testWidgets('disabled controller does not send commands', (tester) async {
    final commands = <String>[];
    await mount(tester, commands, enabled: false);
    await tester.tap(find.text('A'));
    final gesture = await tester.startGesture(tester.getCenter(find.byType(AnalogStick).first));
    await gesture.moveBy(const Offset(30, 0));
    await gesture.up();
    await tester.pump(const Duration(milliseconds: 30));
    expect(commands, isEmpty);
  });
}
