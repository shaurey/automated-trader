import 'package:flutter/material.dart';
import 'package:fl_chart/fl_chart.dart';
import '../models/holdings.dart';

class SectorAllocationChart extends StatefulWidget {
  final List<SectorAllocation> sectorData;

  const SectorAllocationChart({
    required this.sectorData,
    super.key,
  });

  @override
  State<SectorAllocationChart> createState() => _SectorAllocationChartState();
}

class _SectorAllocationChartState extends State<SectorAllocationChart> {
  int touchedIndex = -1;

  @override
  Widget build(BuildContext context) {
    if (widget.sectorData.isEmpty) {
      return _buildEmptyState(context);
    }

    return Row(
      children: [
        Expanded(
          flex: 3,
          child: _buildPieChart(context),
        ),
        const SizedBox(width: 24),
        Expanded(
          flex: 2,
          child: _buildLegend(context),
        ),
      ],
    );
  }

  Widget _buildPieChart(BuildContext context) {
    return PieChart(
      PieChartData(
        pieTouchData: PieTouchData(
          touchCallback: (FlTouchEvent event, pieTouchResponse) {
            setState(() {
              if (!event.isInterestedForInteractions ||
                  pieTouchResponse == null ||
                  pieTouchResponse.touchedSection == null) {
                touchedIndex = -1;
                return;
              }
              touchedIndex = pieTouchResponse.touchedSection!.touchedSectionIndex;
            });
          },
        ),
        borderData: FlBorderData(show: false),
        sectionsSpace: 2,
        centerSpaceRadius: 40,
        sections: _buildPieSections(),
      ),
    );
  }

  List<PieChartSectionData> _buildPieSections() {
    final colorScheme = Theme.of(context).colorScheme;
    final colors = _getSectorColors(colorScheme);

    return widget.sectorData.asMap().entries.map((entry) {
      final index = entry.key;
      final sector = entry.value;
      final isTouched = index == touchedIndex;
      final fontSize = isTouched ? 16.0 : 14.0;
      final radius = isTouched ? 110.0 : 100.0;
      final color = colors[index % colors.length];

      return PieChartSectionData(
        color: color,
        value: sector.weight ?? 0.0,
        title: '${(sector.weight ?? 0.0).toStringAsFixed(1)}%',
        radius: radius,
        titleStyle: TextStyle(
          fontSize: fontSize,
          fontWeight: FontWeight.bold,
          color: Colors.white,
          shadows: const [
            Shadow(
              color: Colors.black26,
              offset: Offset(0.5, 0.5),
              blurRadius: 1,
            ),
          ],
        ),
      );
    }).toList();
  }

  Widget _buildLegend(BuildContext context) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;
    final colors = _getSectorColors(colorScheme);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        Text(
          'Sectors',
          style: theme.textTheme.titleMedium?.copyWith(
            fontWeight: FontWeight.bold,
          ),
        ),
        const SizedBox(height: 16),
        ...widget.sectorData.asMap().entries.map((entry) {
          final index = entry.key;
          final sector = entry.value;
          final color = colors[index % colors.length];
          
          return Padding(
            padding: const EdgeInsets.only(bottom: 8.0),
            child: Row(
              children: [
                Container(
                  width: 16,
                  height: 16,
                  decoration: BoxDecoration(
                    color: color,
                    borderRadius: BorderRadius.circular(2),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        sector.sector,
                        style: theme.textTheme.bodyMedium?.copyWith(
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                      Text(
                        '\$${((sector.value ?? 0.0) / 1000).toStringAsFixed(1)}K (${(sector.weight ?? 0.0).toStringAsFixed(1)}%)',
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
        }).toList(),
      ],
    );
  }

  Widget _buildEmptyState(BuildContext context) {
    final theme = Theme.of(context);
    
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(
            Icons.pie_chart_outline,
            size: 64,
            color: theme.colorScheme.onSurfaceVariant,
          ),
          const SizedBox(height: 16),
          Text(
            'No sector data available',
            style: theme.textTheme.titleMedium?.copyWith(
              color: theme.colorScheme.onSurfaceVariant,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            'Add some holdings to see sector allocation',
            style: theme.textTheme.bodyMedium?.copyWith(
              color: theme.colorScheme.onSurfaceVariant,
            ),
          ),
        ],
      ),
    );
  }

  List<Color> _getSectorColors(ColorScheme colorScheme) {
    return [
      colorScheme.primary,
      colorScheme.secondary,
      colorScheme.tertiary,
      colorScheme.error,
      colorScheme.primary.withOpacity(0.7),
      colorScheme.secondary.withOpacity(0.7),
      colorScheme.tertiary.withOpacity(0.7),
      colorScheme.error.withOpacity(0.7),
      const Color(0xFF8E24AA),
      const Color(0xFF00ACC1),
      const Color(0xFF6D4C41),
      const Color(0xFF546E7A),
    ];
  }
}