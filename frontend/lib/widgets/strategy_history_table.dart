import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import '../models/stock_detail.dart';

class StrategyHistoryTable extends StatelessWidget {
  final List<StrategyHistoryItem> executions;
  final bool isLoading;
  final String? error;
  final VoidCallback? onRetry;

  const StrategyHistoryTable({
    super.key,
    required this.executions,
    this.isLoading = false,
    this.error,
    this.onRetry,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.timeline),
                const SizedBox(width: 8),
                Text(
                  'Strategy History',
                  style: theme.textTheme.titleLarge?.copyWith(
                    fontWeight: FontWeight.w600,
                  ),
                ),
                const Spacer(),
                if (executions.isNotEmpty)
                  Chip(
                    label: Text('${executions.length} executions'),
                    avatar: const Icon(Icons.history, size: 16),
                  ),
              ],
            ),
            const SizedBox(height: 16),
            if (isLoading)
              const Center(
                child: Padding(
                  padding: EdgeInsets.all(24),
                  child: CircularProgressIndicator(),
                ),
              )
            else if (error != null)
              _buildErrorWidget(context, error!, onRetry)
            else if (executions.isEmpty)
              _buildEmptyWidget(context)
            else
              _buildTable(context),
          ],
        ),
      ),
    );
  }

  Widget _buildErrorWidget(BuildContext context, String error, VoidCallback? onRetry) {
    final theme = Theme.of(context);
    
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: theme.colorScheme.errorContainer.withOpacity(0.1),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Row(
        children: [
          Icon(
            Icons.error_outline,
            color: theme.colorScheme.error,
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Failed to load strategy history',
                  style: theme.textTheme.titleSmall?.copyWith(
                    color: theme.colorScheme.error,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  error,
                  style: theme.textTheme.bodySmall?.copyWith(
                    color: theme.colorScheme.onErrorContainer,
                  ),
                ),
              ],
            ),
          ),
          if (onRetry != null) ...[
            const SizedBox(width: 12),
            TextButton(
              onPressed: onRetry,
              child: const Text('Retry'),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildEmptyWidget(BuildContext context) {
    final theme = Theme.of(context);
    
    return Container(
      padding: const EdgeInsets.all(24),
      child: Column(
        children: [
          Icon(
            Icons.timeline_outlined,
            size: 48,
            color: theme.colorScheme.onSurfaceVariant,
          ),
          const SizedBox(height: 16),
          Text(
            'No strategy history',
            style: theme.textTheme.titleMedium?.copyWith(
              fontWeight: FontWeight.w600,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            'This stock has not been evaluated by any strategies yet.',
            style: theme.textTheme.bodyMedium?.copyWith(
              color: theme.colorScheme.onSurfaceVariant,
            ),
            textAlign: TextAlign.center,
          ),
        ],
      ),
    );
  }

  Widget _buildTable(BuildContext context) {
    final theme = Theme.of(context);
    
    return Column(
      children: [
        // Header row
        Container(
          padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 16),
          decoration: BoxDecoration(
            color: theme.colorScheme.surfaceVariant.withOpacity(0.5),
            borderRadius: const BorderRadius.vertical(top: Radius.circular(8)),
          ),
          child: Row(
            children: [
              Expanded(
                flex: 2,
                child: Text(
                  'Strategy',
                  style: theme.textTheme.labelMedium?.copyWith(
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
              Expanded(
                child: Text(
                  'Result',
                  style: theme.textTheme.labelMedium?.copyWith(
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
              Expanded(
                child: Text(
                  'Score',
                  style: theme.textTheme.labelMedium?.copyWith(
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
              Expanded(
                flex: 2,
                child: Text(
                  'Date',
                  style: theme.textTheme.labelMedium?.copyWith(
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
            ],
          ),
        ),
        // Data rows
        Container(
          decoration: BoxDecoration(
            border: Border.all(
              color: theme.colorScheme.outline.withOpacity(0.2),
            ),
            borderRadius: const BorderRadius.vertical(bottom: Radius.circular(8)),
          ),
          child: Column(
            children: executions.take(10).map((execution) => _buildTableRow(context, execution)).toList(),
          ),
        ),
        if (executions.length > 10) ...[
          const SizedBox(height: 12),
          Text(
            'Showing first 10 of ${executions.length} executions',
            style: theme.textTheme.bodySmall?.copyWith(
              color: theme.colorScheme.onSurfaceVariant,
            ),
          ),
        ],
      ],
    );
  }

  Widget _buildTableRow(BuildContext context, StrategyHistoryItem execution) {
    final theme = Theme.of(context);
    final dateFormat = DateFormat('MMM d, y');
    
    final resultColor = execution.passed
        ? theme.colorScheme.tertiary
        : theme.colorScheme.error;
    
    final resultIcon = execution.passed
        ? Icons.check_circle
        : Icons.cancel;

    return Container(
      padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 16),
      decoration: BoxDecoration(
        border: Border(
          bottom: BorderSide(
            color: theme.colorScheme.outline.withOpacity(0.1),
            width: 1,
          ),
        ),
      ),
      child: Row(
        children: [
          // Strategy name
          Expanded(
            flex: 2,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  _formatStrategyName(execution.strategyCode),
                  style: theme.textTheme.bodyMedium?.copyWith(
                    fontWeight: FontWeight.w500,
                  ),
                ),
                if (execution.classification != null) ...[
                  const SizedBox(height: 2),
                  Text(
                    execution.classification!,
                    style: theme.textTheme.bodySmall?.copyWith(
                      color: theme.colorScheme.onSurfaceVariant,
                    ),
                  ),
                ],
              ],
            ),
          ),
          // Result
          Expanded(
            child: Row(
              children: [
                Icon(
                  resultIcon,
                  size: 16,
                  color: resultColor,
                ),
                const SizedBox(width: 4),
                Text(
                  execution.passed ? 'Pass' : 'Fail',
                  style: theme.textTheme.bodyMedium?.copyWith(
                    color: resultColor,
                    fontWeight: FontWeight.w500,
                  ),
                ),
              ],
            ),
          ),
          // Score
          Expanded(
            child: Text(
              execution.score != null 
                  ? execution.score!.toStringAsFixed(2)
                  : '-',
              style: theme.textTheme.bodyMedium,
            ),
          ),
          // Date
          Expanded(
            flex: 2,
            child: Text(
              execution.runStartedAt != null
                  ? dateFormat.format(execution.runStartedAt!)
                  : execution.createdAt != null
                      ? dateFormat.format(execution.createdAt!)
                      : '-',
              style: theme.textTheme.bodyMedium?.copyWith(
                color: theme.colorScheme.onSurfaceVariant,
              ),
            ),
          ),
        ],
      ),
    );
  }

  String _formatStrategyName(String strategyCode) {
    // Convert strategy codes to readable names
    switch (strategyCode.toLowerCase()) {
      case 'bullish_breakout':
        return 'Bullish Breakout';
      case 'leap_entry':
        return 'LEAP Entry';
      case 'momentum':
        return 'Momentum';
      case 'value':
        return 'Value';
      case 'growth':
        return 'Growth';
      default:
        // Convert snake_case to Title Case
        return strategyCode
            .split('_')
            .map((word) => word.isNotEmpty 
                ? word[0].toUpperCase() + word.substring(1).toLowerCase()
                : '')
            .join(' ');
    }
  }
}