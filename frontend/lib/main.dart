import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import 'screens/dashboard_screen.dart';
import 'screens/holdings_screen.dart';
import 'screens/charts_screen.dart';
import 'screens/strategies_screen.dart';
import 'screens/strategy_execution_screen.dart';
import 'screens/stock_info_screen.dart';

void main() {
  runApp(const ProviderScope(child: TradingApp()));
}

class TradingApp extends StatelessWidget {
  const TradingApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp.router(
      title: 'Trading App',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(
          seedColor: const Color(0xFF2196F3),
          brightness: Brightness.light,
        ),
        useMaterial3: true,
        cardTheme: CardThemeData(
          elevation: 2,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12),
          ),
        ),
        appBarTheme: const AppBarTheme(
          centerTitle: true,
          elevation: 0,
          scrolledUnderElevation: 4,
        ),
      ),
      darkTheme: ThemeData(
        colorScheme: ColorScheme.fromSeed(
          seedColor: const Color(0xFF2196F3),
          brightness: Brightness.dark,
        ),
        useMaterial3: true,
        cardTheme: CardThemeData(
          elevation: 2,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12),
          ),
        ),
        appBarTheme: const AppBarTheme(
          centerTitle: true,
          elevation: 0,
          scrolledUnderElevation: 4,
        ),
      ),
      routerConfig: _router,
    );
  }
}

final GoRouter _router = GoRouter(
  initialLocation: '/',
  routes: [
    ShellRoute(
      builder: (context, state, child) {
        return ScaffoldWithNavigation(child: child);
      },
      routes: [
        GoRoute(
          path: '/',
          name: 'dashboard',
          builder: (context, state) => const DashboardScreen(),
        ),
        GoRoute(
          path: '/holdings',
          name: 'holdings',
          builder: (context, state) => const HoldingsScreen(),
        ),
        GoRoute(
          path: '/charts',
          name: 'charts',
          builder: (context, state) => const ChartsScreen(),
        ),
        GoRoute(
          path: '/strategies',
          name: 'strategies',
          builder: (context, state) => const StrategiesScreen(),
        ),
        GoRoute(
          path: '/execution',
          name: 'execution',
          builder: (context, state) => const StrategyExecutionScreen(),
        ),
        GoRoute(
          path: '/stock-info',
          name: 'stock-info',
          builder: (context, state) => const StockInfoScreen(),
        ),
      ],
    ),
  ],
);

class ScaffoldWithNavigation extends StatefulWidget {
  final Widget child;

  const ScaffoldWithNavigation({required this.child, super.key});

  @override
  State<ScaffoldWithNavigation> createState() => _ScaffoldWithNavigationState();
}

class _ScaffoldWithNavigationState extends State<ScaffoldWithNavigation> {
  int _selectedIndex = 0;

  @override
  Widget build(BuildContext context) {
    final isWideScreen = MediaQuery.of(context).size.width > 800;

    if (isWideScreen) {
      return Scaffold(
        body: Row(
          children: [
            NavigationRail(
              selectedIndex: _selectedIndex,
              onDestinationSelected: _onItemTapped,
              labelType: NavigationRailLabelType.all,
              backgroundColor: Theme.of(context).colorScheme.surface,
              destinations: const [
                NavigationRailDestination(
                  icon: Icon(Icons.dashboard_outlined),
                  selectedIcon: Icon(Icons.dashboard),
                  label: Text('Dashboard'),
                ),
                NavigationRailDestination(
                  icon: Icon(Icons.account_balance_wallet_outlined),
                  selectedIcon: Icon(Icons.account_balance_wallet),
                  label: Text('Holdings'),
                ),
                NavigationRailDestination(
                  icon: Icon(Icons.bar_chart_outlined),
                  selectedIcon: Icon(Icons.bar_chart),
                  label: Text('Charts'),
                ),
                NavigationRailDestination(
                  icon: Icon(Icons.insights_outlined),
                  selectedIcon: Icon(Icons.insights),
                  label: Text('Strategies'),
                ),
                NavigationRailDestination(
                  icon: Icon(Icons.play_arrow_outlined),
                  selectedIcon: Icon(Icons.play_arrow),
                  label: Text('Execute'),
                ),
                NavigationRailDestination(
                  icon: Icon(Icons.assessment_outlined),
                  selectedIcon: Icon(Icons.assessment),
                  label: Text('Stock Info'),
                ),
              ],
            ),
            const VerticalDivider(thickness: 1, width: 1),
            Expanded(child: widget.child),
          ],
        ),
      );
    }

    return Scaffold(
      body: widget.child,
      bottomNavigationBar: NavigationBar(
        selectedIndex: _selectedIndex,
        onDestinationSelected: _onItemTapped,
        destinations: const [
          NavigationDestination(
            icon: Icon(Icons.dashboard_outlined),
            selectedIcon: Icon(Icons.dashboard),
            label: 'Dashboard',
          ),
          NavigationDestination(
            icon: Icon(Icons.account_balance_wallet_outlined),
            selectedIcon: Icon(Icons.account_balance_wallet),
            label: 'Holdings',
          ),
          NavigationDestination(
            icon: Icon(Icons.bar_chart_outlined),
            selectedIcon: Icon(Icons.bar_chart),
            label: 'Charts',
          ),
          NavigationDestination(
            icon: Icon(Icons.insights_outlined),
            selectedIcon: Icon(Icons.insights),
            label: 'Strategies',
          ),
          NavigationDestination(
            icon: Icon(Icons.play_arrow_outlined),
            selectedIcon: Icon(Icons.play_arrow),
            label: 'Execute',
          ),
          NavigationDestination(
            icon: Icon(Icons.assessment_outlined),
            selectedIcon: Icon(Icons.assessment),
            label: 'Stock Info',
          ),
        ],
      ),
    );
  }

  void _onItemTapped(int index) {
    setState(() {
      _selectedIndex = index;
    });

    switch (index) {
      case 0:
        context.goNamed('dashboard');
        break;
      case 1:
        context.goNamed('holdings');
        break;
      case 2:
        context.goNamed('charts');
        break;
      case 3:
        context.goNamed('strategies');
        break;
      case 4:
        context.goNamed('execution');
        break;
      case 5:
        context.goNamed('stock-info');
        break;
    }
  }
}
