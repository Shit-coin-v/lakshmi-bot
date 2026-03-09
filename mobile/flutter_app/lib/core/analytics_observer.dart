import 'package:flutter/widgets.dart';
import 'analytics_service.dart';

class AnalyticsNavigatorObserver extends NavigatorObserver {
  final _analytics = AnalyticsService();

  @override
  void didPush(Route<dynamic> route, Route<dynamic>? previousRoute) {
    super.didPush(route, previousRoute);
    final name = route.settings.name;
    if (name != null && name.isNotEmpty) {
      _analytics.trackScreenView(name);
    }
  }
}
