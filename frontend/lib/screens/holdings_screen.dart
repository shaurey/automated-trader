import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';
import '../providers/holdings_provider.dart';
import '../widgets/loading_widget.dart';
import '../widgets/error_widget.dart';
import '../models/holdings.dart';

class HoldingsScreen extends ConsumerWidget {
  const HoldingsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final filteredPositionsAsync = ref.watch(filteredPositionsProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Holdings'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () {
              ref.invalidate(positionsProvider);
            },
            tooltip: 'Refresh Holdings',
          ),
          IconButton(
            icon: const Icon(Icons.filter_list),
            onPressed: () {
              _showFilterDialog(context, ref);
            },
            tooltip: 'Filter Holdings',
          ),
        ],
      ),
      body: Column(
        children: [
          _buildFiltersSection(context, ref),
          Expanded(
            child: filteredPositionsAsync.when(
              data: (positions) => _buildHoldingsTable(context, ref, positions),
              loading: () => const LoadingWidget(message: 'Loading holdings...'),
              error: (error, stackTrace) => ErrorDisplayWidget(
                error: error.toString(),
                onRetry: () => ref.invalidate(positionsProvider),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildFiltersSection(BuildContext context, WidgetRef ref) {
    final selectedAccount = ref.watch(selectedAccountProvider);
    final selectedStyle = ref.watch(selectedStyleProvider);
    final sortMode = ref.watch(sortModeProvider);
    final accountsAsync = ref.watch(accountsProvider);

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
                      labelText: 'Search holdings',
                      hintText: 'Search by ticker or company name',
                      prefixIcon: Icon(Icons.search),
                      border: OutlineInputBorder(),
                      isDense: true,
                    ),
                    onChanged: (value) {
                      ref.read(searchQueryProvider.notifier).state = value;
                    },
                  ),
                ),
                const SizedBox(width: 16),
                Expanded(
                  child: DropdownButtonFormField<SortMode>(
                    decoration: const InputDecoration(
                      labelText: 'Sort by',
                      border: OutlineInputBorder(),
                      isDense: true,
                    ),
                    value: sortMode,
                    items: SortMode.values.map((mode) {
                      return DropdownMenuItem(
                        value: mode,
                        child: Text(mode.displayName),
                      );
                    }).toList(),
                    onChanged: (value) {
                      if (value != null) {
                        ref.read(sortModeProvider.notifier).state = value;
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
                      labelText: 'Account',
                      border: OutlineInputBorder(),
                      isDense: true,
                    ),
                    value: selectedAccount,
                    items: accountsAsync.when<List<DropdownMenuItem<String?>>>(
                      data: (accounts) {
                        final items = <DropdownMenuItem<String?>>[
                          const DropdownMenuItem<String?>(
                            value: null,
                            child: Text('All Accounts'),
                          ),
                        ];
                        items.addAll(accounts.map((acct) => DropdownMenuItem<String?>(
                              value: acct,
                              child: Text(acct),
                            )));
                        return items;
                      },
                      loading: () => const [
                        DropdownMenuItem<String?>(
                          value: null,
                          child: Text('Loading...'),
                        )
                      ],
                      error: (err, st) => const [
                        DropdownMenuItem<String?>(
                          value: null,
                          child: Text('All Accounts'),
                        )
                      ],
                    ),
                    onChanged: (value) {
                      ref.read(selectedAccountProvider.notifier).state = value;
                    },
                  ),
                ),
                const SizedBox(width: 16),
                Expanded(
                  child: DropdownButtonFormField<String?>(
                    decoration: const InputDecoration(
                      labelText: 'Style',
                      border: OutlineInputBorder(),
                      isDense: true,
                    ),
                    value: selectedStyle,
                    items: [
                      const DropdownMenuItem<String?>(
                        value: null,
                        child: Text('All Styles'),
                      ),
                      // TODO: Load actual styles from API
                      const DropdownMenuItem<String?>(
                        value: 'growth',
                        child: Text('Growth'),
                      ),
                      const DropdownMenuItem<String?>(
                        value: 'value',
                        child: Text('Value'),
                      ),
                      const DropdownMenuItem<String?>(
                        value: 'income',
                        child: Text('Income'),
                      ),
                    ],
                    onChanged: (value) {
                      ref.read(selectedStyleProvider.notifier).state = value;
                    },
                  ),
                ),
                const SizedBox(width: 16),
                FilledButton.icon(
                  onPressed: () {
                    ref.read(searchQueryProvider.notifier).state = '';
                    ref.read(selectedAccountProvider.notifier).state = null;
                    ref.read(selectedStyleProvider.notifier).state = null;
                    ref.read(sortModeProvider.notifier).state = SortMode.valueDesc;
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

  Widget _buildHoldingsTable(BuildContext context, WidgetRef ref, List<Position> positions) {
    if (positions.isEmpty) {
      return const NoDataWidget(
        title: 'No Holdings Found',
        message: 'No holdings match your current filters. Try adjusting your search criteria.',
        icon: Icons.account_balance_wallet_outlined,
      );
    }

    final isWideScreen = MediaQuery.of(context).size.width > 1200;

    if (isWideScreen) {
      return _buildDataTable(context, positions);
    } else {
      return _buildMobileList(context, positions);
    }
  }

  Widget _buildDataTable(BuildContext context, List<Position> positions) {
    final theme = Theme.of(context);
    final formatter = NumberFormat.currency(symbol: '\$', decimalDigits: 2);

    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Card(
        child: SingleChildScrollView(
          scrollDirection: Axis.horizontal,
          child: DataTable(
            columnSpacing: 24,
            columns: const [
              DataColumn(label: Text('Ticker')),
              DataColumn(label: Text('Company')),
              DataColumn(label: Text('Quantity')),
              DataColumn(label: Text('Current Price')),
              DataColumn(label: Text('Market Value')),
              DataColumn(label: Text('Cost Basis')),
              DataColumn(label: Text('Gain/Loss')),
              DataColumn(label: Text('% Change')),
              DataColumn(label: Text('Weight')),
              DataColumn(label: Text('Style')),
            ],
            rows: positions.map((position) {
              final isPositive = (position.unrealizedGainLoss ?? 0) >= 0;
              final gainLossColor = isPositive ? Colors.green : Colors.red;

              return DataRow(
                cells: [
                  DataCell(
                    Text(
                      position.ticker,
                      style: theme.textTheme.bodyMedium?.copyWith(
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),
                  DataCell(
                    SizedBox(
                      width: 200,
                      child: Text(
                        position.companyName ?? '—',
                        style: theme.textTheme.bodySmall,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                  ),
                  DataCell(Text(position.quantity.toStringAsFixed(0))),
                  DataCell(Text(position.currentPrice == null ? '—' : formatter.format(position.currentPrice))),
                  DataCell(Text(position.marketValue == null ? '—' : formatter.format(position.marketValue))),
                  DataCell(Text(position.costBasis == null ? '—' : formatter.format(position.costBasis))),
                  DataCell(
                    Text(
                      position.unrealizedGainLoss == null ? '—' : '${isPositive ? '+' : ''}${formatter.format(position.unrealizedGainLoss)}',
                      style: TextStyle(color: gainLossColor),
                    ),
                  ),
                  DataCell(
                    Text(
            position.unrealizedGainLossPercent == null
              ? '—'
              : '${isPositive ? '+' : ''}${position.unrealizedGainLossPercent!.toStringAsFixed(2)}%',
                      style: TextStyle(
                        color: gainLossColor,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ),
          DataCell(Text(
          position.marketValue == null
            ? '—'
            : _getTotalValue(positions) == 0
              ? '0.0%'
              : '${((position.marketValue! / _getTotalValue(positions)) * 100).toStringAsFixed(1)}%',
          )),
                  DataCell(
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                      decoration: BoxDecoration(
                        color: theme.colorScheme.secondaryContainer,
                        borderRadius: BorderRadius.circular(12),
                      ),
                      child: Text(
                        position.styleCategory ?? '—',
                        style: theme.textTheme.bodySmall?.copyWith(
                          color: theme.colorScheme.onSecondaryContainer,
                        ),
                      ),
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

  Widget _buildMobileList(BuildContext context, List<Position> positions) {
    return ListView.builder(
      padding: const EdgeInsets.all(16),
      itemCount: positions.length,
      itemBuilder: (context, index) {
        final position = positions[index];
        return _buildMobilePositionCard(context, position);
      },
    );
  }

  Widget _buildMobilePositionCard(BuildContext context, Position position) {
    final theme = Theme.of(context);
    final formatter = NumberFormat.currency(symbol: '\$', decimalDigits: 2);
    final isPositive = (position.unrealizedGainLoss ?? 0) >= 0;
    final gainLossColor = isPositive ? Colors.green : Colors.red;

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
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      position.ticker,
                      style: theme.textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    Text(
                      position.companyName ?? '—',
                      style: theme.textTheme.bodySmall?.copyWith(
                        color: theme.colorScheme.onSurfaceVariant,
                      ),
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ],
                ),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                  decoration: BoxDecoration(
                    color: theme.colorScheme.secondaryContainer,
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Text(
                    position.styleCategory ?? '—',
                    style: theme.textTheme.bodySmall?.copyWith(
                      color: theme.colorScheme.onSecondaryContainer,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Market Value',
                      style: theme.textTheme.bodySmall?.copyWith(
                        color: theme.colorScheme.onSurfaceVariant,
                      ),
                    ),
                    Text(
                      position.marketValue == null ? '—' : formatter.format(position.marketValue),
                      style: theme.textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ],
                ),
                Column(
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: [
                    Text(
                      'Gain/Loss',
                      style: theme.textTheme.bodySmall?.copyWith(
                        color: theme.colorScheme.onSurfaceVariant,
                      ),
                    ),
                    Text(
                      position.unrealizedGainLoss == null ? '—' : '${isPositive ? '+' : ''}${formatter.format(position.unrealizedGainLoss)}',
                      style: theme.textTheme.titleMedium?.copyWith(
                        color: gainLossColor,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    Text(
            position.unrealizedGainLossPercent == null
              ? '—'
              : '${isPositive ? '+' : ''}${position.unrealizedGainLossPercent!.toStringAsFixed(2)}%',
                      style: theme.textTheme.bodySmall?.copyWith(
                        color: gainLossColor,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ],
                ),
              ],
            ),
            const SizedBox(height: 8),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  'Qty: ${position.quantity.toStringAsFixed(0)}',
                  style: theme.textTheme.bodySmall,
                ),
                Text(
                  'Price: ${position.currentPrice == null ? '—' : formatter.format(position.currentPrice)}',
                  style: theme.textTheme.bodySmall,
                ),
                Text(
                  'Cost: ${position.costBasis == null ? '—' : formatter.format(position.costBasis)}',
                  style: theme.textTheme.bodySmall,
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  double _getTotalValue(List<Position> positions) {
  return positions.fold(0.0, (sum, position) => sum + (position.marketValue ?? 0));
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
}