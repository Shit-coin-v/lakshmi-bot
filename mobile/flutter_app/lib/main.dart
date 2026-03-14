import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:google_fonts/google_fonts.dart';

// Localization
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
import 'features/auth/screens/registration_choice_screen.dart';
import 'features/auth/screens/login_choice_screen.dart';
import 'features/auth/screens/telegram_register_info_screen.dart';
import 'features/home/screens/main_shell.dart';
import 'features/home/screens/home_screen.dart';
import 'features/home/screens/profile_screen.dart';
import 'features/cart/screens/cart_screen.dart';
import 'features/orders/screens/orders_screen.dart';
import 'features/orders/screens/order_status_screen.dart';
import 'features/notifications/screens/notifications_screen.dart';
import 'features/loyalty/screens/loyalty_screen.dart';
import 'features/address/screens/saved_addresses_screen.dart';
import 'features/notifications/screens/notification_settings_screen.dart';
import 'features/orders/screens/order_details_screen.dart';
import 'features/notifications/screens/notification_detail_screen.dart';
import 'features/catalog/screens/category_tree_screen.dart';
import 'features/catalog/screens/category_products_screen.dart';

import 'core/api_client.dart';
import 'core/analytics_observer.dart';
import 'core/analytics_service.dart';
import 'core/push_notification_service.dart';
import 'features/auth/providers/auth_provider.dart';

@pragma('vm:entry-point')
Future<void> _firebaseMessagingBackgroundHandler(RemoteMessage message) async {
  if (Firebase.apps.isEmpty) {
    await Firebase.initializeApp();
  }
}

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();

  try {
    await Firebase.initializeApp();
    FirebaseMessaging.onBackgroundMessage(_firebaseMessagingBackgroundHandler);
  } catch (e) {
    debugPrint('Firebase init failed: $e');
  }

  await initializeDateFormatting('ru', null);

  // Restore Bearer token before any widget init to avoid 403 on early requests
  await ApiClient().restoreTokenFromStorage();

  runApp(const ProviderScope(child: LakshmiMarketApp()));
}

// Global Theme Colors
const Color kPrimaryGreen = Color(0xFF4CAF50);
const Color kLightGreen = Color(0xFFC8E6C9);
const Color kBackground = Color(0xFFF9F9F9);

final _rootNavigatorKey = GlobalKey<NavigatorState>();

const _publicRoutes = <String>{
  '/',
  '/login',
  '/login-choice',
  '/register',
  '/register-choice',
  '/register-telegram',
  '/qr-auth',
  '/verify-email',
  '/reset-password',
};

GoRouter _createRouter(WidgetRef ref) {
  return GoRouter(
    navigatorKey: _rootNavigatorKey,
    initialLocation: '/',
    observers: [AnalyticsNavigatorObserver()],
    redirect: (context, state) {
      final isLoggedIn = ref.read(authProvider) != null;
      final location = state.matchedLocation;
      if (!isLoggedIn && !_publicRoutes.contains(location)) {
        return '/login-choice';
      }
      return null;
    },
    routes: [
      GoRoute(path: '/', builder: (context, state) => const WelcomeScreen()),
      GoRoute(
          path: '/login',
          builder: (context, state) => const LoginScreen()),
      GoRoute(
        path: '/login-choice',
        builder: (context, state) => const LoginChoiceScreen(),
      ),
      GoRoute(
        path: '/register',
        builder: (context, state) => const RegistrationScreen(),
      ),
      GoRoute(
        path: '/register-choice',
        builder: (context, state) => const RegistrationChoiceScreen(),
      ),
      GoRoute(
        path: '/register-telegram',
        builder: (context, state) => const TelegramRegisterInfoScreen(),
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
      StatefulShellRoute.indexedStack(
        builder: (context, state, navigationShell) =>
            MainShell(navigationShell: navigationShell),
        branches: [
          // Tab 0: Products
          StatefulShellBranch(routes: [
            GoRoute(
              path: '/home',
              builder: (ctx, st) => const HomeScreen(),
              routes: [
                GoRoute(
                  path: 'categories',
                  builder: (ctx, st) => const CategoryTreeScreen(),
                  routes: [
                    GoRoute(
                      path: 'sub/:id',
                      builder: (ctx, st) {
                        final id = int.parse(st.pathParameters['id']!);
                        final title = st.uri.queryParameters['title'] ?? 'Категория';
                        return CategoryTreeScreen(parentId: id, title: title);
                      },
                    ),
                    GoRoute(
                      path: 'products/:categoryId',
                      builder: (ctx, st) {
                        final categoryId = int.parse(st.pathParameters['categoryId']!);
                        final title = st.uri.queryParameters['title'] ?? 'Товары';
                        return CategoryProductsScreen(
                          categoryId: categoryId,
                          title: title,
                        );
                      },
                    ),
                  ],
                ),
                GoRoute(
                  path: 'cart',
                  builder: (ctx, st) => const CartScreen(),
                ),
                GoRoute(
                  path: 'notifications',
                  builder: (ctx, st) => const NotificationsScreen(),
                ),
                GoRoute(
                  path: 'notifications/:id',
                  builder: (ctx, st) {
                    final id = st.pathParameters['id']!;
                    return NotificationDetailScreen(notificationId: id);
                  },
                ),
                GoRoute(
                  path: 'saved-addresses',
                  builder: (ctx, st) {
                    final select =
                        st.uri.queryParameters['select'] == 'true';
                    return SavedAddressesScreen(selectionMode: select);
                  },
                ),
                GoRoute(
                  path: 'order-status/:id',
                  builder: (ctx, st) {
                    final id = int.parse(st.pathParameters['id']!);
                    final isNew =
                        st.uri.queryParameters['new'] == 'true';
                    return OrderStatusScreen(
                        orderId: id, fromOrderCreation: isNew);
                  },
                ),
              ],
            ),
          ]),
          // Tab 1: Loyalty card
          StatefulShellBranch(routes: [
            GoRoute(
              path: '/loyalty',
              builder: (ctx, st) => const LoyaltyScreen(),
            ),
          ]),
          // Tab 2: Profile
          StatefulShellBranch(routes: [
            GoRoute(
              path: '/profile',
              builder: (ctx, st) => const ProfileScreen(),
              routes: [
                GoRoute(
                  path: 'orders',
                  builder: (ctx, st) => const OrdersScreen(),
                ),
                GoRoute(
                  path: 'order-status/:id',
                  builder: (ctx, st) {
                    final id = int.parse(st.pathParameters['id']!);
                    return OrderStatusScreen(orderId: id);
                  },
                ),
                GoRoute(
                  path: 'order-details/:id',
                  builder: (ctx, st) {
                    final id = int.parse(st.pathParameters['id']!);
                    return OrderDetailsScreen(orderId: id);
                  },
                ),
                GoRoute(
                  path: 'saved-addresses',
                  builder: (ctx, st) {
                    final select =
                        st.uri.queryParameters['select'] == 'true';
                    return SavedAddressesScreen(selectionMode: select);
                  },
                ),
                GoRoute(
                  path: 'notification-settings',
                  builder: (ctx, st) =>
                      const NotificationSettingsScreen(),
                ),
              ],
            ),
          ]),
        ],
      ),
    ],
  );
}

class LakshmiMarketApp extends ConsumerStatefulWidget {
  const LakshmiMarketApp({super.key});

  @override
  ConsumerState<LakshmiMarketApp> createState() => _LakshmiMarketAppState();
}

class _LakshmiMarketAppState extends ConsumerState<LakshmiMarketApp> with WidgetsBindingObserver {
  late final GoRouter _router;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _router = _createRouter(ref);
    _initPush();
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) {
      AnalyticsService().trackSessionStart();
    } else if (state == AppLifecycleState.paused) {
      AnalyticsService().trackSessionEnd();
    }
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
