import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';
import '../providers/holdings_provider.dart';
import '../widgets/portfolio_summary_cards.dart';
import '../widgets/sector_allocation_chart.dart';
import '../widgets/style_allocation_chart.dart';
import '../widgets/top_holdings_chart.dart';
import '../widgets/loading_widget.dart';
import '../widgets/error_widget.dart';

class DashboardScreen extends ConsumerWidget {
  const DashboardScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final holdingsSummaryAsync = ref.watch(holdingsSummaryProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Portfolio Dashboard'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () {
              ref.invalidate(holdingsSummaryProvider);
            },
            tooltip: 'Refresh Data',
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: () async {
          ref.invalidate(holdingsSummaryProvider);
          // Wait for the refresh to complete
          await ref.read(holdingsSummaryProvider.future);
        },
        child: holdingsSummaryAsync.when(
          data: (summary) => _buildDashboard(context, summary),
          loading: () => const LoadingWidget(message: 'Loading portfolio data...'),
          error: (error, stackTrace) => ErrorDisplayWidget(
            error: error.toString(),
            onRetry: () => ref.invalidate(holdingsSummaryProvider),
          ),
        ),
      ),
    );
  }

  Widget _buildDashboard(BuildContext context, dynamic summary) {
    final theme = Theme.of(context);
    final isWideScreen = MediaQuery.of(context).size.width > 1200;

    return SingleChildScrollView(
      padding: const EdgeInsets.all(16.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Last updated timestamp
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
            decoration: BoxDecoration(
              color: theme.colorScheme.secondaryContainer,
              borderRadius: BorderRadius.circular(8),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(
                  Icons.schedule,
                  size: 16,
                  color: theme.colorScheme.onSecondaryContainer,
                ),
                const SizedBox(width: 8),
                Text(
                  'Last updated: ${DateFormat('MMM dd, HH:mm').format(DateTime.now())}',
                  style: theme.textTheme.bodySmall?.copyWith(
                    color: theme.colorScheme.onSecondaryContainer,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 24),

          // Portfolio Summary Cards
          PortfolioSummaryCards(summary: summary),
          const SizedBox(height: 32),

          // Charts Section
          if (isWideScreen)
            // Wide screen: three-column layout
            Column(
              children: [
                // Allocation charts row
                Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Expanded(
                      flex: 1,
                      child: _buildSectorAllocationSection(context, summary),
                    ),
                    const SizedBox(width: 16),
                    Expanded(
                      flex: 1,
                      child: _buildStyleAllocationSection(context, summary),
                    ),
                  ],
                ),
                const SizedBox(height: 32),
                // Top holdings section
                _buildTopHoldingsSection(context, summary),
              ],
            )
          else
            // Medium/Small screen: stacked layout
            Column(
              children: [
                _buildSectorAllocationSection(context, summary),
                const SizedBox(height: 24),
                _buildStyleAllocationSection(context, summary),
                const SizedBox(height: 32),
                _buildTopHoldingsSection(context, summary),
              ],
            ),

          const SizedBox(height: 32),

          // Quick Actions Section
          _buildQuickActionsSection(context),
        ],
      ),
    );
  }

  Widget _buildSectorAllocationSection(BuildContext context, dynamic summary) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(24.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  'Sector Allocation',
                  style: Theme.of(context).textTheme.headlineSmall,
                ),
                IconButton(
                  icon: const Icon(Icons.info_outline),
                  onPressed: () {
                    _showSectorInfo(context);
                  },
                  tooltip: 'Sector allocation breakdown',
                ),
              ],
            ),
            const SizedBox(height: 16),
            SizedBox(
              height: 300,
              child: SectorAllocationChart(sectorData: summary.sectorAllocation),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildStyleAllocationSection(BuildContext context, dynamic summary) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(24.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  'Style Allocation',
                  style: Theme.of(context).textTheme.headlineSmall,
                ),
                IconButton(
                  icon: const Icon(Icons.info_outline),
                  onPressed: () {
                    _showStyleInfo(context);
                  },
                  tooltip: 'Style allocation breakdown',
                ),
              ],
            ),
            const SizedBox(height: 16),
            SizedBox(
              height: 300,
              child: StyleAllocationChart(styleData: summary.styleAllocation),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildTopHoldingsSection(BuildContext context, dynamic summary) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(24.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  'Top Holdings',
                  style: Theme.of(context).textTheme.headlineSmall,
                ),
                TextButton(
                  onPressed: () {
                    // Navigate to holdings page
                  },
                  child: const Text('View All'),
                ),
              ],
            ),
            const SizedBox(height: 16),
            SizedBox(
              height: 300,
              child: TopHoldingsChart(holdings: summary.topHoldings),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildQuickActionsSection(BuildContext context) {
    final theme = Theme.of(context);

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(24.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Quick Actions',
              style: theme.textTheme.headlineSmall,
            ),
            const SizedBox(height: 16),
            Wrap(
              spacing: 12,
              runSpacing: 12,
              children: [
                _buildActionChip(
                  context,
                  icon: Icons.account_balance_wallet,
                  label: 'View Holdings',
                  onTap: () {
                    // Navigate to holdings
                  },
                ),
                _buildActionChip(
                  context,
                  icon: Icons.analytics,
                  label: 'View Charts',
                  onTap: () {
                    // Navigate to charts
                  },
                ),
                _buildActionChip(
                  context,
                  icon: Icons.download,
                  label: 'Export Data',
                  onTap: () {
                    _showExportDialog(context);
                  },
                ),
                _buildActionChip(
                  context,
                  icon: Icons.settings,
                  label: 'Settings',
                  onTap: () {
                    _showSettingsDialog(context);
                  },
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildActionChip(
    BuildContext context, {
    required IconData icon,
    required String label,
    required VoidCallback onTap,
  }) {
    return ActionChip(
      avatar: Icon(icon, size: 18),
      label: Text(label),
      onPressed: onTap,
    );
  }

  void _showSectorInfo(BuildContext context) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Sector Allocation'),
        content: const Text(
          'This chart shows how your portfolio is distributed across different market sectors. '
          'Diversification across sectors can help reduce risk.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('Got it'),
          ),
        ],
      ),
    );
  }

  void _showStyleInfo(BuildContext context) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Style Allocation'),
        content: const Text(
          'This chart shows how your portfolio is distributed across different investment styles. '
          'Growth stocks focus on capital appreciation, Value stocks are undervalued by the market, '
          'and Income stocks provide regular dividend payments.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('Got it'),
          ),
        ],
      ),
    );
  }

  void _showExportDialog(BuildContext context) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Export Portfolio Data'),
        content: const Text('Choose export format:'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () {
              Navigator.of(context).pop();
              // TODO: Implement CSV export
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(content: Text('CSV export coming soon!')),
              );
            },
            child: const Text('CSV'),
          ),
          TextButton(
            onPressed: () {
              Navigator.of(context).pop();
              // TODO: Implement PDF export
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(content: Text('PDF export coming soon!')),
              );
            },
            child: const Text('PDF'),
          ),
        ],
      ),
    );
  }

  void _showSettingsDialog(BuildContext context) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Settings'),
        content: const Text('Settings panel coming soon!'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('OK'),
          ),
        ],
      ),
    );
  }
}