import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';
import '../providers/strategies_provider.dart';
import '../widgets/loading_widget.dart';
import '../widgets/error_widget.dart';
import '../widgets/report_viewer_dialog.dart';
import '../models/strategies.dart';

class StrategiesScreen extends ConsumerWidget {
  const StrategiesScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final filteredRunsAsync = ref.watch(filteredStrategyRunsProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Strategies'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () {
              ref.invalidate(strategyRunsProvider);
              ref.invalidate(latestStrategyRunsProvider);
            },
            tooltip: 'Refresh Strategies',
          ),
          IconButton(
            icon: const Icon(Icons.filter_list),
            onPressed: () {
              _showFilterDialog(context, ref);
            },
            tooltip: 'Filter Strategies',
          ),
        ],
      ),
      body: Column(
        children: [
          _buildFiltersSection(context, ref),
          Expanded(
            child: filteredRunsAsync.when(
              data: (runsResponse) => _buildStrategiesContent(context, ref, runsResponse),
              loading: () => const LoadingWidget(message: 'Loading strategies...'),
              error: (error, stackTrace) => ErrorDisplayWidget(
                error: error.toString(),
                onRetry: () => ref.invalidate(strategyRunsProvider),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildFiltersSection(BuildContext context, WidgetRef ref) {
    final selectedStrategy = ref.watch(selectedStrategyCodeProvider);
    final selectedStatus = ref.watch(selectedStatusProvider);
    final sortMode = ref.watch(strategySortModeProvider);

    return Card(
      margin: const EdgeInsets.all(16),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  flex: 2,
                  child: TextField(
                    decoration: const InputDecoration(
                      labelText: 'Search strategies',
                      hintText: 'Search by strategy code or status',
                      prefixIcon: Icon(Icons.search),
                      border: OutlineInputBorder(),
                      isDense: true,
                    ),
                    onChanged: (value) {
                      ref.read(strategySearchQueryProvider.notifier).state = value;
                    },
                  ),
                ),
                const SizedBox(width: 16),
                Expanded(
                  child: DropdownButtonFormField<StrategySortMode>(
                    decoration: const InputDecoration(
                      labelText: 'Sort by',
                      border: OutlineInputBorder(),
                      isDense: true,
                    ),
                    value: sortMode,
                    items: StrategySortMode.values.map((mode) {
                      return DropdownMenuItem(
                        value: mode,
                        child: Text(mode.displayName),
                      );
                    }).toList(),
                    onChanged: (value) {
                      if (value != null) {
                        ref.read(strategySortModeProvider.notifier).state = value;
                      }
                    },
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            Row(
              children: [
                Expanded(
                  child: DropdownButtonFormField<String?>(
                    decoration: const InputDecoration(
                      labelText: 'Strategy',
                      border: OutlineInputBorder(),
                      isDense: true,
                    ),
                    value: selectedStrategy,
                    items: const [
                      DropdownMenuItem<String?>(
                        value: null,
                        child: Text('All Strategies'),
                      ),
                      DropdownMenuItem<String?>(
                        value: 'bullish_breakout',
                        child: Text('Bullish Breakout'),
                      ),
                      DropdownMenuItem<String?>(
                        value: 'leap_entry',
                        child: Text('LEAP Entry'),
                      ),
                    ],
                    onChanged: (value) {
                      ref.read(selectedStrategyCodeProvider.notifier).state = value;
                    },
                  ),
                ),
                const SizedBox(width: 16),
                Expanded(
                  child: DropdownButtonFormField<String?>(
                    decoration: const InputDecoration(
                      labelText: 'Status',
                      border: OutlineInputBorder(),
                      isDense: true,
                    ),
                    value: selectedStatus,
                    items: const [
                      DropdownMenuItem<String?>(
                        value: null,
                        child: Text('All Status'),
                      ),
                      DropdownMenuItem<String?>(
                        value: 'ok',
                        child: Text('Completed'),
                      ),
                      DropdownMenuItem<String?>(
                        value: 'error',
                        child: Text('Error'),
                      ),
                      DropdownMenuItem<String?>(
                        value: 'timeout',
                        child: Text('Timeout'),
                      ),
                    ],
                    onChanged: (value) {
                      ref.read(selectedStatusProvider.notifier).state = value;
                    },
                  ),
                ),
                const SizedBox(width: 16),
                FilledButton.icon(
                  onPressed: () {
                    ref.read(strategySearchQueryProvider.notifier).state = '';
                    ref.read(selectedStrategyCodeProvider.notifier).state = null;
                    ref.read(selectedStatusProvider.notifier).state = null;
                    ref.read(strategySortModeProvider.notifier).state = StrategySortMode.startedAtDesc;
                  },
                  icon: const Icon(Icons.clear),
                  label: const Text('Clear'),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildStrategiesContent(BuildContext context, WidgetRef ref, StrategyRunsResponse runsResponse) {
    if (runsResponse.runs.isEmpty) {
      return NoDataWidget(
        title: 'No Strategy Runs Found',
        message: 'No strategy runs match your current filters. Try adjusting your search criteria.',
        icon: Icons.insights_outlined,
        onRefresh: () => ref.invalidate(strategyRunsProvider),
      );
    }

    final isWideScreen = MediaQuery.of(context).size.width > 1200;

    return Column(
      children: [
        if (runsResponse.strategyStats != null) _buildStatsCard(context, runsResponse.strategyStats!),
        Expanded(
          child: isWideScreen
              ? _buildDataTable(context, ref, runsResponse.runs)
              : _buildMobileList(context, ref, runsResponse.runs),
        ),
        _buildPagination(context, ref, runsResponse),
      ],
    );
  }

  Widget _buildStatsCard(BuildContext context, Map<String, dynamic> stats) {
    final theme = Theme.of(context);
    
    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.spaceAround,
          children: [
            _buildStatItem(theme, 'Strategies', stats['unique_strategies']?.toString() ?? '0'),
            _buildStatItem(theme, 'Total Runs', stats['total_runs']?.toString() ?? '0'),
            _buildStatItem(theme, 'Avg Pass Rate', '${stats['avg_pass_rate']?.toStringAsFixed(1) ?? '0'}%'),
            _buildStatItem(theme, 'Last Run', _formatDateTime(stats['last_run'])),
          ],
        ),
      ),
    );
  }

  Widget _buildStatItem(ThemeData theme, String label, String value) {
    return Column(
      children: [
        Text(
          value,
          style: theme.textTheme.headlineSmall?.copyWith(
            fontWeight: FontWeight.bold,
            color: theme.colorScheme.primary,
          ),
        ),
        Text(
          label,
          style: theme.textTheme.bodySmall?.copyWith(
            color: theme.colorScheme.onSurfaceVariant,
          ),
        ),
      ],
    );
  }

  Widget _buildDataTable(BuildContext context, WidgetRef ref, List<StrategyRunSummary> runs) {
    final theme = Theme.of(context);

    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Card(
        child: SingleChildScrollView(
          scrollDirection: Axis.horizontal,
          child: DataTable(
            columnSpacing: 24,
            columns: const [
              DataColumn(label: Text('Strategy')),
              DataColumn(label: Text('Started')),
              DataColumn(label: Text('Completed')),
              DataColumn(label: Text('Universe Size')),
              DataColumn(label: Text('Passed')),
              DataColumn(label: Text('Pass Rate')),
              DataColumn(label: Text('Avg Score')),
              DataColumn(label: Text('Duration')),
              DataColumn(label: Text('Status')),
              DataColumn(label: Text('Actions')),
            ],
            rows: runs.map((run) {
              return DataRow(
                cells: [
                  DataCell(
                    Text(
                      run.strategyCode,
                      style: theme.textTheme.bodyMedium?.copyWith(
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),
                  DataCell(Text(_formatDateTime(run.startedAt))),
                  DataCell(Text(run.completedAt != null ? _formatDateTime(run.completedAt!) : '—')),
                  DataCell(Text(run.universeSize?.toString() ?? '—')),
                  DataCell(Text(run.passedCount?.toString() ?? '—')),
                  DataCell(
                    Text(
                      run.passRate != null ? '${run.passRate!.toStringAsFixed(1)}%' : '—',
                      style: TextStyle(
                        color: _getPassRateColor(theme, run.passRate),
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ),
                  DataCell(Text(run.avgScore?.toStringAsFixed(1) ?? '—')),
                  DataCell(Text(_formatDuration(run.durationMs))),
                  DataCell(
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                      decoration: BoxDecoration(
                        color: _getStatusColor(theme, run.exitStatus),
                        borderRadius: BorderRadius.circular(12),
                      ),
                      child: Text(
                        run.exitStatus ?? 'unknown',
                        style: theme.textTheme.bodySmall?.copyWith(
                          color: Colors.white,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ),
                  ),
                  DataCell(
                    Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        IconButton(
                          icon: const Icon(Icons.visibility),
                          onPressed: () => _showRunDetails(context, ref, run.runId),
                          tooltip: 'View Details',
                        ),
                        IconButton(
                          icon: const Icon(Icons.list),
                          onPressed: () => _showRunResults(context, ref, run.runId),
                          tooltip: 'View Results',
                        ),
                        IconButton(
                          icon: const Icon(Icons.article),
                          onPressed: () => _showReportViewer(context, run.runId, run.strategyCode),
                          tooltip: 'View Report',
                        ),
                      ],
                    ),
                  ),
                ],
              );
            }).toList(),
          ),
        ),
      ),
    );
  }

  Widget _buildMobileList(BuildContext context, WidgetRef ref, List<StrategyRunSummary> runs) {
    return ListView.builder(
      padding: const EdgeInsets.all(16),
      itemCount: runs.length,
      itemBuilder: (context, index) {
        final run = runs[index];
        return _buildMobileRunCard(context, ref, run);
      },
    );
  }

  Widget _buildMobileRunCard(BuildContext context, WidgetRef ref, StrategyRunSummary run) {
    final theme = Theme.of(context);

    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  run.strategyCode,
                  style: theme.textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
                ),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                  decoration: BoxDecoration(
                    color: _getStatusColor(theme, run.exitStatus),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Text(
                    run.exitStatus ?? 'unknown',
                    style: theme.textTheme.bodySmall?.copyWith(
                      color: Colors.white,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Text(
              'Started: ${_formatDateTime(run.startedAt)}',
              style: theme.textTheme.bodySmall,
            ),
            if (run.completedAt != null)
              Text(
                'Completed: ${_formatDateTime(run.completedAt!)}',
                style: theme.textTheme.bodySmall,
              ),
            const SizedBox(height: 12),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Pass Rate',
                      style: theme.textTheme.bodySmall?.copyWith(
                        color: theme.colorScheme.onSurfaceVariant,
                      ),
                    ),
                    Text(
                      run.passRate != null ? '${run.passRate!.toStringAsFixed(1)}%' : '—',
                      style: theme.textTheme.titleMedium?.copyWith(
                        color: _getPassRateColor(theme, run.passRate),
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ],
                ),
                Column(
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: [
                    Text(
                      'Passed',
                      style: theme.textTheme.bodySmall?.copyWith(
                        color: theme.colorScheme.onSurfaceVariant,
                      ),
                    ),
                    Text(
                      '${run.passedCount ?? 0}/${run.universeSize ?? 0}',
                      style: theme.textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ],
                ),
              ],
            ),
            const SizedBox(height: 12),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceEvenly,
              children: [
                TextButton.icon(
                  onPressed: () => _showRunDetails(context, ref, run.runId),
                  icon: const Icon(Icons.visibility),
                  label: const Text('Details'),
                ),
                TextButton.icon(
                  onPressed: () => _showRunResults(context, ref, run.runId),
                  icon: const Icon(Icons.list),
                  label: const Text('Results'),
                ),
                TextButton.icon(
                  onPressed: () => _showReportViewer(context, run.runId, run.strategyCode),
                  icon: const Icon(Icons.article),
                  label: const Text('Report'),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildPagination(BuildContext context, WidgetRef ref, StrategyRunsResponse runsResponse) {
    final page = ref.watch(strategyRunsPageProvider);
    final totalPages = (runsResponse.totalCount / runsResponse.pageSize).ceil();

    if (totalPages <= 1) return const SizedBox.shrink();

    return Card(
      margin: const EdgeInsets.all(16),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text('Page ${page + 1} of $totalPages'),
            Row(
              children: [
                IconButton(
                  onPressed: page > 0
                      ? () => ref.read(strategyRunsPageProvider.notifier).state = page - 1
                      : null,
                  icon: const Icon(Icons.chevron_left),
                ),
                IconButton(
                  onPressed: page < totalPages - 1
                      ? () => ref.read(strategyRunsPageProvider.notifier).state = page + 1
                      : null,
                  icon: const Icon(Icons.chevron_right),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Color _getPassRateColor(ThemeData theme, double? passRate) {
    if (passRate == null) return theme.colorScheme.onSurfaceVariant;
    if (passRate >= 70) return Colors.green;
    if (passRate >= 40) return Colors.orange;
    return Colors.red;
  }

  Color _getStatusColor(ThemeData theme, String? status) {
    switch (status) {
      case 'ok':
        return Colors.green;
      case 'error':
        return Colors.red;
      case 'timeout':
        return Colors.orange;
      default:
        return theme.colorScheme.onSurfaceVariant;
    }
  }

  String _formatDateTime(String dateTimeStr) {
    try {
      final dateTime = DateTime.parse(dateTimeStr);
      return DateFormat('MMM dd, HH:mm').format(dateTime);
    } catch (e) {
      return dateTimeStr;
    }
  }

  String _formatDuration(int? durationMs) {
    if (durationMs == null) return '—';
    final seconds = (durationMs / 1000).round();
    if (seconds < 60) return '${seconds}s';
    final minutes = (seconds / 60).round();
    return '${minutes}m';
  }

  void _showRunDetails(BuildContext context, WidgetRef ref, String runId) {
    showDialog(
      context: context,
      builder: (context) => _RunDetailsDialog(runId: runId),
    );
  }

  void _showRunResults(BuildContext context, WidgetRef ref, String runId) {
    showDialog(
      context: context,
      builder: (context) => _RunResultsDialog(runId: runId),
    );
  }

  void _showFilterDialog(BuildContext context, WidgetRef ref) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Filter Options'),
        content: const Text('Advanced filtering options coming soon!'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('OK'),
          ),
        ],
      ),
    );
  }

  void _showReportViewer(BuildContext context, String runId, String strategyCode) {
    showDialog(
      context: context,
      builder: (context) => ReportViewerDialog(
        runId: runId,
        strategyCode: strategyCode,
      ),
    );
  }
}

class _RunDetailsDialog extends ConsumerWidget {
  final String runId;

  const _RunDetailsDialog({required this.runId});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final runDetailAsync = ref.watch(strategyRunDetailProvider(runId));

    return Dialog(
      child: Container(
        width: 600,
        height: 500,
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Strategy Run Details',
              style: Theme.of(context).textTheme.headlineSmall,
            ),
            const SizedBox(height: 16),
            Expanded(
              child: runDetailAsync.when(
                data: (runDetail) => _buildRunDetailContent(context, runDetail),
                loading: () => const LoadingWidget(message: 'Loading run details...'),
                error: (error, stackTrace) => ErrorDisplayWidget(
                  error: error.toString(),
                  onRetry: () => ref.invalidate(strategyRunDetailProvider(runId)),
                ),
              ),
            ),
            Row(
              mainAxisAlignment: MainAxisAlignment.end,
              children: [
                TextButton(
                  onPressed: () => Navigator.of(context).pop(),
                  child: const Text('Close'),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildRunDetailContent(BuildContext context, StrategyRunDetail runDetail) {
    return SingleChildScrollView(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _buildDetailRow('Strategy', runDetail.strategyCode),
          _buildDetailRow('Version', runDetail.version),
          _buildDetailRow('Started', runDetail.startedAt),
          _buildDetailRow('Completed', runDetail.completedAt ?? 'Not completed'),
          _buildDetailRow('Universe Size', runDetail.universeSize?.toString() ?? 'Unknown'),
          _buildDetailRow('Results', '${runDetail.passedCount ?? 0}/${runDetail.totalResults ?? 0} passed'),
          _buildDetailRow('Pass Rate', runDetail.passRate != null ? '${runDetail.passRate!.toStringAsFixed(1)}%' : 'Unknown'),
          _buildDetailRow('Avg Score', runDetail.avgScore?.toStringAsFixed(2) ?? 'Unknown'),
          _buildDetailRow('Max Score', runDetail.maxScore?.toStringAsFixed(2) ?? 'Unknown'),
          _buildDetailRow('Duration', runDetail.durationMs != null ? '${(runDetail.durationMs! / 1000).toStringAsFixed(1)}s' : 'Unknown'),
          _buildDetailRow('Status', runDetail.exitStatus ?? 'Unknown'),
        ],
      ),
    );
  }

  Widget _buildDetailRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 120,
            child: Text(
              '$label:',
              style: const TextStyle(fontWeight: FontWeight.w600),
            ),
          ),
          Expanded(child: Text(value)),
        ],
      ),
    );
  }
}

class _RunResultsDialog extends ConsumerWidget {
  final String runId;

  const _RunResultsDialog({required this.runId});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    // Show ALL actionable results (both positive signals and trim/exit signals)
    final filter = StrategyResultsFilter(runId: runId);
    final resultsAsync = ref.watch(strategyRunResultsProvider(filter));

    return Dialog(
      child: Container(
        width: 800,
        height: 600,
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Strategy Results',
              style: Theme.of(context).textTheme.headlineSmall,
            ),
            const SizedBox(height: 16),
            Expanded(
              child: resultsAsync.when(
                data: (resultsResponse) => _buildResultsContent(context, resultsResponse),
                loading: () => const LoadingWidget(message: 'Loading results...'),
                error: (error, stackTrace) => ErrorDisplayWidget(
                  error: error.toString(),
                  onRetry: () => ref.invalidate(strategyRunResultsProvider(filter)),
                ),
              ),
            ),
            Row(
              mainAxisAlignment: MainAxisAlignment.end,
              children: [
                TextButton(
                  onPressed: () => Navigator.of(context).pop(),
                  child: const Text('Close'),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildResultsContent(BuildContext context, StrategyResultsResponse resultsResponse) {
    return Column(
      children: [
        Text('${resultsResponse.results.length} actionable results (of ${resultsResponse.totalCount} total evaluated)'),
        Text('Includes: Buy signals, Strong Buy signals, Trim positions, and Exit positions',
             style: Theme.of(context).textTheme.bodySmall?.copyWith(color: Colors.grey[600])),
        const SizedBox(height: 16),
        Expanded(
          child: ListView.builder(
            itemCount: resultsResponse.results.length,
            // Add performance optimizations for large lists
            itemExtent: 80.0, // Fixed height for better performance
            physics: const AlwaysScrollableScrollPhysics(), // Better scrolling behavior
            cacheExtent: 200, // Cache items beyond viewport for smoother scrolling
            itemBuilder: (context, index) {
              final result = resultsResponse.results[index];
              return Card(
                margin: const EdgeInsets.only(bottom: 8),
                elevation: 2, // Reduce elevation for better performance
                child: ListTile(
                  title: Text(
                    result.ticker,
                    style: const TextStyle(fontWeight: FontWeight.bold),
                  ),
                  subtitle: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Score: ${result.score?.toStringAsFixed(1) ?? 'N/A'}',
                        style: const TextStyle(
                          fontWeight: FontWeight.w600,
                          fontSize: 14,
                        ),
                      ),
                      if (result.companyName != null)
                        Text(
                          result.companyName!,
                          style: const TextStyle(fontSize: 12, color: Colors.grey),
                          overflow: TextOverflow.ellipsis,
                        ),
                    ],
                  ),
                  trailing: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                    decoration: BoxDecoration(
                      color: _getClassificationColor(result.classification),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Text(
                      result.classification ?? 'Unknown',
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 12,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),
                  isThreeLine: result.companyName != null,
                ),
              );
            },
          ),
        ),
      ],
    );
  }

  Color _getClassificationColor(String? classification) {
    switch (classification?.toLowerCase()) {
      case 'buy':
        return Colors.green;
      case 'watch':
        return Colors.orange;
      case 'hold':
        return Colors.blue;
      case 'sell':
        return Colors.red;
      default:
        return Colors.grey;
    }
  }
}
