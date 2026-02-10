import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:google_fonts/google_fonts.dart';

// Локализация
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:intl/date_symbol_data_local.dart';

// Screens Imports
import 'features/auth/screens/welcome_screen.dart';
import 'features/auth/screens/login_screen.dart';
import 'features/auth/screens/registration_screen.dart';
import 'features/auth/screens/qr_auth_screen.dart';
import 'features/auth/screens/verify_email_screen.dart';
import 'features/auth/screens/reset_password_screen.dart';
import 'features/auth/screens/telegram_link_choice_screen.dart';
import 'features/auth/screens/link_telegram_scan_screen.dart';
import 'features/auth/screens/generate_qr_screen.dart';
import 'features/home/screens/main_shell.dart';
import 'features/cart/screens/cart_screen.dart';
import 'features/orders/screens/orders_screen.dart';
import 'features/orders/screens/order_status_screen.dart';
import 'features/notifications/screens/notifications_screen.dart';
import 'features/loyalty/screens/loyalty_screen.dart';
import 'features/address/screens/saved_addresses_screen.dart';
import 'features/notifications/screens/notification_settings_screen.dart';
import 'features/orders/screens/order_details_screen.dart';
import 'features/notifications/screens/notification_detail_screen.dart';

import 'core/push_notification_service.dart';

@pragma('vm:entry-point')
Future<void> _firebaseMessagingBackgroundHandler(RemoteMessage message) async {
  // В фоне тоже нужна инициализация Firebase
  await Firebase.initializeApp();
}

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();

  await Firebase.initializeApp();

  FirebaseMessaging.onBackgroundMessage(_firebaseMessagingBackgroundHandler);

  await initializeDateFormatting('ru', null);

  runApp(const ProviderScope(child: LakshmiMarketApp()));
}

// Global Theme Colors
const Color kPrimaryGreen = Color(0xFF4CAF50);
const Color kLightGreen = Color(0xFFC8E6C9);
const Color kBackground = Color(0xFFF9F9F9);

final _rootNavigatorKey = GlobalKey<NavigatorState>();

final _router = GoRouter(
  navigatorKey: _rootNavigatorKey,
  initialLocation: '/',
  routes: [
    GoRoute(path: '/', builder: (context, state) => const WelcomeScreen()),
    GoRoute(path: '/login', builder: (context, state) => const LoginScreen()),
    GoRoute(
      path: '/register',
      builder: (context, state) => const RegistrationScreen(),
    ),
    GoRoute(
      path: '/qr-auth',
      builder: (context, state) => const QrAuthScreen(),
    ),
    GoRoute(
      path: '/verify-email',
      builder: (context, state) {
        final email = state.extra as String? ?? '';
        return VerifyEmailScreen(email: email);
      },
    ),
    GoRoute(
      path: '/reset-password',
      builder: (context, state) => const ResetPasswordScreen(),
    ),
    GoRoute(
      path: '/telegram-link-choice',
      builder: (context, state) => const TelegramLinkChoiceScreen(),
    ),
    GoRoute(
      path: '/link-telegram-scan',
      builder: (context, state) => const LinkTelegramScanScreen(),
    ),
    GoRoute(
      path: '/generate-qr',
      builder: (context, state) => const GenerateQrScreen(),
    ),
    GoRoute(path: '/home', builder: (context, state) => const MainShell()),
    GoRoute(
      path: '/loyalty',
      builder: (context, state) => const LoyaltyScreen(),
    ),
    GoRoute(path: '/cart', builder: (context, state) => const CartScreen()),
    GoRoute(path: '/orders', builder: (context, state) => const OrdersScreen()),
    GoRoute(
      path: '/notifications',
      builder: (context, state) => const NotificationsScreen(),
    ),
    GoRoute(
      path: '/notifications/:id',
      builder: (context, state) {
        final id = state.pathParameters['id']!;
        return NotificationDetailScreen(notificationId: id);
      },
    ),
    GoRoute(
      path: '/notification-settings',
      builder: (context, state) => const NotificationSettingsScreen(),
    ),
    GoRoute(
      path: '/saved-addresses',
      builder: (context, state) {
        final select = state.uri.queryParameters['select'] == 'true';
        return SavedAddressesScreen(selectionMode: select);
      },
    ),
    GoRoute(
      path: '/order-status/:id',
      builder: (context, state) {
        final id = int.parse(state.pathParameters['id']!);
        final isNew = state.uri.queryParameters['new'] == 'true';
        return OrderStatusScreen(orderId: id, fromOrderCreation: isNew);
      },
    ),
    GoRoute(
      path: '/order-details/:id',
      builder: (context, state) {
        final id = int.parse(state.pathParameters['id']!);
        return OrderDetailsScreen(orderId: id);
      },
    ),
  ],
);

class LakshmiMarketApp extends ConsumerStatefulWidget {
  const LakshmiMarketApp({super.key});

  @override
  ConsumerState<LakshmiMarketApp> createState() => _LakshmiMarketAppState();
}

class _LakshmiMarketAppState extends ConsumerState<LakshmiMarketApp> {
  @override
  void initState() {
    super.initState();
    _initPush();
  }

  Future<void> _initPush() async {
    await ref.read(pushNotificationServiceProvider).initialize(_router);
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp.router(
      title: 'Lakshmi Market',
      debugShowCheckedModeBanner: false,

      localizationsDelegates: const [
        GlobalMaterialLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
      ],
      supportedLocales: const [Locale('ru')],

      theme: ThemeData(
        useMaterial3: true,
        scaffoldBackgroundColor: kBackground,
        colorScheme: ColorScheme.fromSeed(
          seedColor: kPrimaryGreen,
          primary: kPrimaryGreen,
          surface: kBackground,
        ),
        textTheme: GoogleFonts.interTextTheme(),
        inputDecorationTheme: InputDecorationTheme(
          filled: true,
          fillColor: Colors.white,
          border: OutlineInputBorder(
            borderRadius: BorderRadius.circular(12),
            borderSide: BorderSide.none,
          ),
          enabledBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(12),
            borderSide: const BorderSide(color: Colors.black12),
          ),
          focusedBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(12),
            borderSide: const BorderSide(color: kPrimaryGreen, width: 2),
          ),
          contentPadding: const EdgeInsets.symmetric(
            horizontal: 16,
            vertical: 16,
          ),
        ),
        elevatedButtonTheme: ElevatedButtonThemeData(
          style: ElevatedButton.styleFrom(
            backgroundColor: kPrimaryGreen,
            foregroundColor: Colors.white,
            elevation: 0,
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(30),
            ),
            padding: const EdgeInsets.symmetric(vertical: 16),
            textStyle: const TextStyle(
              fontSize: 16,
              fontWeight: FontWeight.bold,
            ),
          ),
        ),
      ),
      routerConfig: _router,
    );
  }
}
