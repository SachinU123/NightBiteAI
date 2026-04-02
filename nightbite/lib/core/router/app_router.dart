import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../features/auth/providers/auth_provider.dart';
import '../../features/auth/presentation/splash_screen.dart';
import '../../features/auth/presentation/login_screen.dart';
import '../../features/auth/presentation/register_screen.dart';
import '../../features/main/presentation/main_tab_shell.dart';
import '../../features/permissions/presentation/permission_onboarding_screen.dart';

final routerProvider = Provider<GoRouter>((ref) {
  final authState = ref.watch(authProvider);

  return GoRouter(
    initialLocation: '/splash',
    routes: [
      GoRoute(
        path: '/splash',
        builder: (context, state) => const SplashScreen(),
      ),
      GoRoute(
        path: '/login',
        builder: (context, state) => const LoginScreen(),
      ),
      GoRoute(
        path: '/register',
        builder: (context, state) => const RegisterScreen(),
      ),
      GoRoute(
        path: '/onboarding',
        builder: (context, state) => const PermissionOnboardingScreen(),
      ),
      GoRoute(
        path: '/main',
        builder: (context, state) => const MainTabShell(),
      ),
    ],
    redirect: (context, state) {
      final isLoading = authState.isLoading;
      final isAuthenticated = authState.isAuthenticated;
      final path = state.uri.toString();

      final isSplash = path == '/splash';
      final isLogin = path == '/login';
      final isRegister = path == '/register';

      // While loading persisted token — stay on splash
      if (isLoading) {
        return isSplash ? null : '/splash';
      }

      // Not authenticated → must be on login or register
      if (!isAuthenticated) {
        if (isLogin || isRegister) return null;
        return '/login';
      }

      // Authenticated — redirect away from auth/splash screens
      if (isAuthenticated) {
        if (isSplash || isLogin || isRegister) {
          // First visit after login → go to permission onboarding once,
          // then /main on subsequent logins
          return '/onboarding';
        }
      }

      return null;
    },
  );
});
