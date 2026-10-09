import 'dart:async';
import 'package:flutter/material.dart';

/// Xbox controls with independent pointer ownership for simultaneous inputs.
class GamepadControls extends StatelessWidget {
  final void Function(String) send;
  final bool enabled;
  const GamepadControls({super.key, required this.send, this.enabled = true});

  Widget button(String label, String key, {Color color = Colors.white70}) =>
      PadHoldButton(label: label, color: color, enabled: enabled,
        onDown: () => send('press $key'), onUp: () => send('release $key'));

  Widget get dpad => SizedBox(width: 150, height: 150, child: Stack(children: [
    Positioned(left: 50, top: 0, child: button('↑', 'up')),
    Positioned(left: 50, top: 100, child: button('↓', 'down')),
    Positioned(left: 0, top: 50, child: button('←', 'left')),
    Positioned(left: 100, top: 50, child: button('→', 'right')),
  ]));

  Widget get actions => SizedBox(width: 150, height: 150, child: Stack(children: [
    Positioned(left: 50, top: 0, child: button('Y', 'y', color: Colors.amber)),
    Positioned(left: 50, top: 100, child: button('A', 'a', color: Colors.green)),
    Positioned(left: 0, top: 50, child: button('X', 'x', color: Colors.blue)),
    Positioned(left: 100, top: 50, child: button('B', 'b', color: Colors.red)),
  ]));

  @override
  Widget build(BuildContext context) => LayoutBuilder(builder: (context, bounds) {
    // A fixed logical board scales as a whole on compact landscape displays.
    return Center(child: FittedBox(fit: BoxFit.contain, child: SizedBox(
      width: 720, height: 300,
      child: Column(children: [
        Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
          button('LB', 'l1'),
          button('BACK', 'select'),
          button('XBOX', 'hotkey'),
          button('START', 'start'),
          button('RB', 'r1'),
        ]),
        const SizedBox(height: 12),
        Expanded(child: Row(
          mainAxisAlignment: MainAxisAlignment.spaceEvenly,
          children: [
            Column(mainAxisAlignment: MainAxisAlignment.spaceEvenly, children: [
              AnalogStick(key: const ValueKey('left-stick'), side: 'left',
                enabled: enabled, send: send),
              button('L3', 'l3'),
            ]),
            dpad,
            actions,
            Column(mainAxisAlignment: MainAxisAlignment.spaceEvenly, children: [
              AnalogStick(key: const ValueKey('right-stick'), side: 'right',
                enabled: enabled, send: send),
              button('R3', 'r3'),
            ]),
          ],
        )),
      ]),
    )));
  });
}

class PadHoldButton extends StatefulWidget {
  final String label;
  final Color color;
  final bool enabled;
  final VoidCallback onDown;
  final VoidCallback onUp;
  const PadHoldButton({super.key, required this.label, required this.onDown,
    required this.onUp, this.color = Colors.white70, this.enabled = true});
  @override
  State<PadHoldButton> createState() => _PadHoldButtonState();
}

class _PadHoldButtonState extends State<PadHoldButton> {
  int? _pointer;
  void _release() {
    if (_pointer == null) return;
    _pointer = null;
    widget.onUp();
    if (mounted) setState(() {});
  }
  @override
  void didUpdateWidget(PadHoldButton oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (!widget.enabled) _release();
  }
  @override
  void dispose() {
    if (_pointer != null) widget.onUp();
    super.dispose();
  }
  @override
  Widget build(BuildContext context) => Semantics(
    label: widget.label, button: true, enabled: widget.enabled,
    child: Listener(
      behavior: HitTestBehavior.opaque,
      onPointerDown: (event) {
        if (!widget.enabled || _pointer != null) return;
        _pointer = event.pointer;
        widget.onDown();
        setState(() {});
      },
      onPointerUp: (event) { if (event.pointer == _pointer) _release(); },
      onPointerCancel: (event) { if (event.pointer == _pointer) _release(); },
      child: Container(width: 50, height: 50,
        alignment: Alignment.center,
        decoration: BoxDecoration(
          color: _pointer == null ? const Color(0xFF1C2230) : widget.color.withValues(alpha: 0.35),
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: widget.enabled ? widget.color : Colors.white12, width: 2)),
        child: Text(widget.label, style: TextStyle(
          color: widget.enabled ? widget.color : Colors.white24,
          fontSize: 13, fontWeight: FontWeight.bold)),
      ),
    ),
  );
}

class AnalogStick extends StatefulWidget {
  final String side;
  final bool enabled;
  final void Function(String) send;
  const AnalogStick({super.key, required this.side, required this.send,
    this.enabled = true});
  @override
  State<AnalogStick> createState() => _AnalogStickState();
}

class _AnalogStickState extends State<AnalogStick> {
  int? _pointer;
  Offset _position = Offset.zero;
  Offset? _pending;
  Timer? _timer;
  static const _radius = 48.0;

  void _send(Offset position) {
    // A small dead zone prevents drift, while the remaining range is continuous.
    final length = position.distance;
    final normalized = length <= 0.08 ? Offset.zero :
      position / length * ((length - 0.08) / 0.92).clamp(0.0, 1.0).toDouble();
    final x = (normalized.dx * 32767).round();
    final y = (normalized.dy * 32767).round();
    widget.send('stick ${widget.side} $x $y');
  }
  void _move(Offset localPosition) {
    var position = (localPosition - const Offset(72, 72)) / _radius;
    if (position.distance > 1) position /= position.distance;
    setState(() => _position = position);
    _pending = position;
    if (_timer != null) return;
    _send(_pending!);
    _pending = null;
    _timer = Timer(const Duration(milliseconds: 16), () {
      _timer = null;
      if (_pending != null) {
        _send(_pending!);
        _pending = null;
      }
    });
  }
  void _release() {
    _timer?.cancel();
    _timer = null;
    _pending = null;
    if (_pointer != null) _send(Offset.zero);
    _pointer = null;
    if (mounted) setState(() => _position = Offset.zero);
  }
  @override
  void didUpdateWidget(AnalogStick oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (!widget.enabled) _release();
  }
  @override
  void dispose() {
    _timer?.cancel();
    if (_pointer != null) _send(Offset.zero);
    super.dispose();
  }
  @override
  Widget build(BuildContext context) => Semantics(
    label: '${widget.side} analog stick', enabled: widget.enabled,
    child: Listener(
      behavior: HitTestBehavior.opaque,
      onPointerDown: (event) {
        if (!widget.enabled || _pointer != null) return;
        _pointer = event.pointer;
        _move(event.localPosition);
      },
      onPointerMove: (event) {
        if (event.pointer == _pointer) _move(event.localPosition);
      },
      onPointerUp: (event) { if (event.pointer == _pointer) _release(); },
      onPointerCancel: (event) { if (event.pointer == _pointer) _release(); },
      child: SizedBox(width: 144, height: 144,
        child: CustomPaint(painter: _StickPainter(_position, widget.enabled))),
    ),
  );
}

class _StickPainter extends CustomPainter {
  final Offset position;
  final bool enabled;
  const _StickPainter(this.position, this.enabled);
  @override
  void paint(Canvas canvas, Size size) {
    final center = size.center(Offset.zero);
    canvas.drawCircle(center, 68, Paint()..color = const Color(0xFF1C2230));
    canvas.drawCircle(center, 68, Paint()
      ..color = enabled ? Colors.white38 : Colors.white12
      ..style = PaintingStyle.stroke..strokeWidth = 2);
    final knob = center + position * 48;
    canvas.drawCircle(knob, 24, Paint()
      ..shader = const LinearGradient(colors: [Color(0xFF50FA7B), Color(0xFF267B50)])
        .createShader(Rect.fromCircle(center: knob, radius: 24)));
    canvas.drawLine(center - const Offset(5, 0), center + const Offset(5, 0),
      Paint()..color = Colors.white24..strokeWidth = 1);
    canvas.drawLine(center - const Offset(0, 5), center + const Offset(0, 5),
      Paint()..color = Colors.white24..strokeWidth = 1);
  }
  @override
  bool shouldRepaint(_StickPainter oldDelegate) =>
      oldDelegate.position != position || oldDelegate.enabled != enabled;
}
