import 'package:flutter_test/flutter_test.dart';
import 'package:lakshmi_market/features/notifications/providers/notification_settings_provider.dart';

void main() {
  group('NotificationSettingsNotifier', () {
    late NotificationSettingsNotifier notifier;

    setUp(() {
      notifier = NotificationSettingsNotifier();
    });

    test('initial state has all settings enabled', () {
      final state = notifier.state;

      expect(state.pushOrders, isTrue);
      expect(state.pushPromos, isTrue);
      expect(state.news, isTrue);
    });

    test('togglePushOrders(false) disables pushOrders, others unchanged', () {
      notifier.togglePushOrders(false);
      final state = notifier.state;

      expect(state.pushOrders, isFalse);
      expect(state.pushPromos, isTrue);
      expect(state.news, isTrue);
    });

    test('togglePushPromos(false) disables pushPromos, others unchanged', () {
      notifier.togglePushPromos(false);
      final state = notifier.state;

      expect(state.pushOrders, isTrue);
      expect(state.pushPromos, isFalse);
      expect(state.news, isTrue);
    });

    test('toggleNews(false) disables news, others unchanged', () {
      notifier.toggleNews(false);
      final state = notifier.state;

      expect(state.pushOrders, isTrue);
      expect(state.pushPromos, isTrue);
      expect(state.news, isFalse);
    });
  });
}
