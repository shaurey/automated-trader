import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../providers/holdings_provider.dart';
import '../widgets/sector_allocation_chart.dart';
import '../widgets/top_holdings_chart.dart';
import '../widgets/loading_widget.dart';
import '../widgets/error_widget.dart';

class ChartsScreen extends ConsumerWidget {
  const ChartsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final holdingsSummaryAsync = ref.watch(holdingsSummaryProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Charts & Analytics'),
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
          await ref.read(holdingsSummaryProvider.future);
        },
        child: holdingsSummaryAsync.when(
          data: (summary) => _buildChartsView(context, summary),
          loading: () => const LoadingWidget(message: 'Loading charts...'),
          error: (error, stackTrace) => ErrorDisplayWidget(
            error: error.toString(),
            onRetry: () => ref.invalidate(holdingsSummaryProvider),
          ),
        ),
      ),
    );
  }

  Widget _buildChartsView(BuildContext context, dynamic summary) {
    final theme = Theme.of(context);
    final isWideScreen = MediaQuery.of(context).size.width > 1200;
    final isMediumScreen = MediaQuery.of(context).size.width > 800;

    return SingleChildScrollView(
      padding: const EdgeInsets.all(16.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Page Header
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Portfolio Analytics',
                    style: theme.textTheme.headlineMedium?.copyWith(
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    'Visual analysis of your portfolio composition and performance',
                    style: theme.textTheme.bodyMedium?.copyWith(
                      color: theme.colorScheme.onSurfaceVariant,
                    ),
                  ),
                ],
              ),
              OutlinedButton.icon(
                onPressed: () {
                  _showExportDialog(context);
                },
                icon: const Icon(Icons.download),
                label: const Text('Export'),
              ),
            ],
          ),
          const SizedBox(height: 32),

          // Charts Grid
          if (isWideScreen)
            // Wide screen: 2x2 grid
            Column(
              children: [
                Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Expanded(
                      child: _buildSectorAllocationCard(context, summary),
                    ),
                    const SizedBox(width: 24),
                    Expanded(
                      child: _buildTopHoldingsCard(context, summary),
                    ),
                  ],
                ),
                const SizedBox(height: 24),
                Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Expanded(
                      child: _buildPerformanceCard(context, summary),
                    ),
                    const SizedBox(width: 24),
                    Expanded(
                      child: _buildAllocationBreakdownCard(context, summary),
                    ),
                  ],
                ),
              ],
            )
          else
            // Medium/Small screen: stacked layout
            Column(
              children: [
                _buildSectorAllocationCard(context, summary),
                const SizedBox(height: 24),
                _buildTopHoldingsCard(context, summary),
                const SizedBox(height: 24),
                if (isMediumScreen)
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Expanded(
                        child: _buildPerformanceCard(context, summary),
                      ),
                      const SizedBox(width: 24),
                      Expanded(
                        child: _buildAllocationBreakdownCard(context, summary),
                      ),
                    ],
                  )
                else ...[
                  _buildPerformanceCard(context, summary),
                  const SizedBox(height: 24),
                  _buildAllocationBreakdownCard(context, summary),
                ],
              ],
            ),

          const SizedBox(height: 32),

          // Additional Analytics Section
          _buildAnalyticsInsights(context, summary),
        ],
      ),
    );
  }

  Widget _buildSectorAllocationCard(BuildContext context, dynamic summary) {
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
                  icon: const Icon(Icons.fullscreen),
                  onPressed: () {
                    _showFullScreenChart(context, 'Sector Allocation', summary.sectorAllocation);
                  },
                  tooltip: 'View fullscreen',
                ),
              ],
            ),
            const SizedBox(height: 16),
            SizedBox(
              height: 400,
              child: SectorAllocationChart(sectorData: summary.sectorAllocation),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildTopHoldingsCard(BuildContext context, dynamic summary) {
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
                IconButton(
                  icon: const Icon(Icons.fullscreen),
                  onPressed: () {
                    _showFullScreenChart(context, 'Top Holdings', summary.topHoldings);
                  },
                  tooltip: 'View fullscreen',
                ),
              ],
            ),
            const SizedBox(height: 16),
            SizedBox(
              height: 400,
              child: TopHoldingsChart(holdings: summary.topHoldings),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildPerformanceCard(BuildContext context, dynamic summary) {
    final theme = Theme.of(context);
    final isPositive = summary.totalGainLoss >= 0;
    final performanceColor = isPositive ? Colors.green : Colors.red;

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(24.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Performance Summary',
              style: theme.textTheme.headlineSmall,
            ),
            const SizedBox(height: 24),
            SizedBox(
              height: 300,
              child: Column(
                children: [
                  // Performance Gauge (placeholder)
                  Expanded(
                    child: Center(
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Container(
                            width: 120,
                            height: 120,
                            decoration: BoxDecoration(
                              shape: BoxShape.circle,
                              border: Border.all(
                                color: performanceColor,
                                width: 8,
                              ),
                            ),
                            child: Center(
                              child: Column(
                                mainAxisAlignment: MainAxisAlignment.center,
                                children: [
                                  Text(
                                    '${isPositive ? '+' : ''}${summary.totalGainLossPercent.toStringAsFixed(1)}%',
                                    style: theme.textTheme.headlineMedium?.copyWith(
                                      color: performanceColor,
                                      fontWeight: FontWeight.bold,
                                    ),
                                  ),
                                  Text(
                                    'Total Return',
                                    style: theme.textTheme.bodySmall?.copyWith(
                                      color: theme.colorScheme.onSurfaceVariant,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ),
                          const SizedBox(height: 16),
                          Text(
                            'Portfolio Performance',
                            style: theme.textTheme.titleMedium,
                          ),
                        ],
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildAllocationBreakdownCard(BuildContext context, dynamic summary) {
    final theme = Theme.of(context);

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(24.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Allocation Breakdown',
              style: theme.textTheme.headlineSmall,
            ),
            const SizedBox(height: 24),
            SizedBox(
              height: 300,
              child: ListView.builder(
                itemCount: summary.sectorAllocation.length,
                itemBuilder: (context, index) {
                  final sector = summary.sectorAllocation[index];
                  return Padding(
                    padding: const EdgeInsets.only(bottom: 16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            Text(
                              sector.sector,
                              style: theme.textTheme.bodyMedium,
                            ),
                            Text(
                              '${sector.weight.toStringAsFixed(1)}%',
                              style: theme.textTheme.bodyMedium?.copyWith(
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 4),
                        LinearProgressIndicator(
                          value: sector.weight / 100,
                          backgroundColor: theme.colorScheme.surfaceContainerHighest,
                          valueColor: AlwaysStoppedAnimation<Color>(
                            theme.colorScheme.primary,
                          ),
                        ),
                      ],
                    ),
                  );
                },
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildAnalyticsInsights(BuildContext context, dynamic summary) {
    final theme = Theme.of(context);

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(24.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Portfolio Insights',
              style: theme.textTheme.headlineSmall,
            ),
            const SizedBox(height: 16),
            _buildInsightRow(
              context,
              Icons.pie_chart,
              'Diversification',
              'Portfolio is spread across ${summary.sectorAllocation.length} sectors',
            ),
            _buildInsightRow(
              context,
              Icons.trending_up,
              'Top Performer',
              summary.topHoldings.isNotEmpty && summary.topHoldings.first.gainLoss > 0
                  ? '${summary.topHoldings.first.ticker} (+${summary.topHoldings.first.gainLossPercent.toStringAsFixed(1)}%)'
                  : 'No significant gains',
            ),
            _buildInsightRow(
              context,
              Icons.account_balance,
              'Largest Position',
              summary.topHoldings.isNotEmpty
                  ? '${summary.topHoldings.first.ticker} (${summary.topHoldings.first.weight.toStringAsFixed(1)}%)'
                  : 'No data available',
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildInsightRow(BuildContext context, IconData icon, String title, String description) {
    final theme = Theme.of(context);

    return Padding(
      padding: const EdgeInsets.only(bottom: 16),
      child: Row(
        children: [
          Icon(
            icon,
            color: theme.colorScheme.primary,
            size: 24,
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: theme.textTheme.titleSmall?.copyWith(
                    fontWeight: FontWeight.w600,
                  ),
                ),
                Text(
                  description,
                  style: theme.textTheme.bodySmall?.copyWith(
                    color: theme.colorScheme.onSurfaceVariant,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  void _showFullScreenChart(BuildContext context, String title, dynamic data) {
    showDialog(
      context: context,
      builder: (context) => Dialog.fullscreen(
        child: Scaffold(
          appBar: AppBar(
            title: Text(title),
            leading: IconButton(
              icon: const Icon(Icons.close),
              onPressed: () => Navigator.of(context).pop(),
            ),
          ),
          body: Padding(
            padding: const EdgeInsets.all(24),
            child: title == 'Sector Allocation'
                ? SectorAllocationChart(sectorData: data)
                : TopHoldingsChart(holdings: data),
          ),
        ),
      ),
    );
  }

  void _showExportDialog(BuildContext context) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Export Charts'),
        content: const Text('Choose export format:'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () {
              Navigator.of(context).pop();
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(content: Text('PNG export coming soon!')),
              );
            },
            child: const Text('PNG'),
          ),
          TextButton(
            onPressed: () {
              Navigator.of(context).pop();
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
}