import 'package:flutter/material.dart';
import 'package:fl_chart/fl_chart.dart';
import 'package:intl/intl.dart';
import '../models/holdings.dart';

class TopHoldingsChart extends StatefulWidget {
  final List<TopHolding> holdings;
  final int maxItems;

  const TopHoldingsChart({
    required this.holdings,
    this.maxItems = 10,
    super.key,
  });

  @override
  State<TopHoldingsChart> createState() => _TopHoldingsChartState();
}

class _TopHoldingsChartState extends State<TopHoldingsChart> {
  int touchedIndex = -1;

  @override
  Widget build(BuildContext context) {
    if (widget.holdings.isEmpty) {
      return _buildEmptyState(context);
    }

    final displayHoldings = widget.holdings.take(widget.maxItems).toList();

    return Column(
      children: [
        Expanded(
          child: _buildBarChart(context, displayHoldings),
        ),
        const SizedBox(height: 16),
        _buildHoldingsList(context, displayHoldings),
      ],
    );
  }

  Widget _buildBarChart(BuildContext context, List<TopHolding> holdings) {
    return BarChart(
      BarChartData(
        alignment: BarChartAlignment.spaceAround,
        maxY: holdings.isNotEmpty
            ? (holdings.first.marketValue ?? 0.0) * 1.1
            : 100000,
        barTouchData: BarTouchData(
          touchCallback: (FlTouchEvent event, barTouchResponse) {
            setState(() {
              if (!event.isInterestedForInteractions ||
                  barTouchResponse == null ||
                  barTouchResponse.spot == null) {
                touchedIndex = -1;
                return;
              }
              touchedIndex = barTouchResponse.spot!.touchedBarGroupIndex;
            });
          },
          touchTooltipData: BarTouchTooltipData(
            tooltipBgColor: Theme.of(context).colorScheme.inverseSurface,
            tooltipRoundedRadius: 8,
            getTooltipItem: (group, groupIndex, rod, rodIndex) {
              final holding = holdings[groupIndex];
              final formatter = NumberFormat.currency(symbol: '\$', decimalDigits: 0);
              
              return BarTooltipItem(
                '${holding.ticker}\n${formatter.format(holding.marketValue ?? 0.0)}',
                TextStyle(
                  color: Theme.of(context).colorScheme.onInverseSurface,
                  fontWeight: FontWeight.bold,
                ),
              );
            },
          ),
        ),
        titlesData: FlTitlesData(
          show: true,
          rightTitles: const AxisTitles(
            sideTitles: SideTitles(showTitles: false),
          ),
          topTitles: const AxisTitles(
            sideTitles: SideTitles(showTitles: false),
          ),
          bottomTitles: AxisTitles(
            sideTitles: SideTitles(
              showTitles: true,
              getTitlesWidget: (value, meta) {
                final index = value.toInt();
                if (index >= 0 && index < holdings.length) {
                  return Padding(
                    padding: const EdgeInsets.only(top: 8.0),
                    child: Text(
                      holdings[index].ticker,
                      style: Theme.of(context).textTheme.bodySmall,
                    ),
                  );
                }
                return const SizedBox.shrink();
              },
              reservedSize: 30,
            ),
          ),
          leftTitles: AxisTitles(
            sideTitles: SideTitles(
              showTitles: true,
              getTitlesWidget: (value, meta) {
                final formatter = NumberFormat.compact();
                return Text(
                  '\$${formatter.format(value)}',
                  style: Theme.of(context).textTheme.bodySmall,
                );
              },
              reservedSize: 60,
            ),
          ),
        ),
        borderData: FlBorderData(show: false),
        barGroups: _buildBarGroups(context, holdings),
        gridData: FlGridData(
          show: true,
          drawVerticalLine: false,
          horizontalInterval: holdings.isNotEmpty
              ? (holdings.first.marketValue ?? 0.0) / 5
              : 20000,
          getDrawingHorizontalLine: (value) {
            return FlLine(
              color: Theme.of(context).colorScheme.outline.withOpacity(0.2),
              strokeWidth: 1,
            );
          },
        ),
      ),
    );
  }

  List<BarChartGroupData> _buildBarGroups(BuildContext context, List<TopHolding> holdings) {
    final colorScheme = Theme.of(context).colorScheme;
    
    return holdings.asMap().entries.map((entry) {
      final index = entry.key;
      final holding = entry.value;
      final isTouched = index == touchedIndex;
      
      final barColor = (holding.gainLoss ?? 0.0) >= 0
          ? Colors.green
          : Colors.red;

      return BarChartGroupData(
        x: index,
        barRods: [
          BarChartRodData(
            toY: holding.marketValue ?? 0.0,
            color: isTouched
                ? barColor.withOpacity(0.8)
                : barColor.withOpacity(0.6),
            width: isTouched ? 20 : 16,
            borderRadius: const BorderRadius.only(
              topLeft: Radius.circular(4),
              topRight: Radius.circular(4),
            ),
          ),
        ],
      );
    }).toList();
  }

  Widget _buildHoldingsList(BuildContext context, List<TopHolding> holdings) {
    final theme = Theme.of(context);
    final formatter = NumberFormat.currency(symbol: '\$', decimalDigits: 2);

    return Container(
      height: 120,
      decoration: BoxDecoration(
        color: theme.colorScheme.surfaceVariant.withOpacity(0.3),
        borderRadius: BorderRadius.circular(8),
      ),
      child: ListView.builder(
        scrollDirection: Axis.horizontal,
        padding: const EdgeInsets.all(8),
        itemCount: holdings.length,
        itemBuilder: (context, index) {
          final holding = holdings[index];
          final isPositive = (holding.gainLoss ?? 0.0) >= 0;
          final gainLossColor = isPositive ? Colors.green : Colors.red;

          return Container(
            width: 120,
            margin: const EdgeInsets.only(right: 8),
            padding: const EdgeInsets.all(8),
            decoration: BoxDecoration(
              color: theme.colorScheme.surface,
              borderRadius: BorderRadius.circular(6),
              border: Border.all(
                color: theme.colorScheme.outline.withOpacity(0.2),
              ),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  holding.ticker,
                  style: theme.textTheme.titleSmall?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
                ),
                Text(
                  holding.companyName ?? 'Unknown Company',
                  style: theme.textTheme.bodySmall?.copyWith(
                    color: theme.colorScheme.onSurfaceVariant,
                  ),
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                ),
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      formatter.format(holding.marketValue ?? 0.0),
                      style: theme.textTheme.bodySmall?.copyWith(
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                    Text(
                      '${isPositive ? '+' : ''}${(holding.gainLossPercent ?? 0.0).toStringAsFixed(1)}%',
                      style: theme.textTheme.bodySmall?.copyWith(
                        color: gainLossColor,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ],
                ),
              ],
            ),
          );
        },
      ),
    );
  }

  Widget _buildEmptyState(BuildContext context) {
    final theme = Theme.of(context);
    
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(
            Icons.bar_chart,
            size: 64,
            color: theme.colorScheme.onSurfaceVariant,
          ),
          const SizedBox(height: 16),
          Text(
            'No holdings data available',
            style: theme.textTheme.titleMedium?.copyWith(
              color: theme.colorScheme.onSurfaceVariant,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            'Add some holdings to see top positions',
            style: theme.textTheme.bodyMedium?.copyWith(
              color: theme.colorScheme.onSurfaceVariant,
            ),
          ),
        ],
      ),
    );
  }
}