import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../models/stock_detail.dart';
import '../providers/stock_provider.dart';
import '../widgets/error_widget.dart';
import '../widgets/loading_widget.dart';
import '../widgets/strategy_history_table.dart';

class StockInfoScreen extends ConsumerStatefulWidget {
  const StockInfoScreen({super.key});

  @override
  ConsumerState<StockInfoScreen> createState() => _StockInfoScreenState();
}

class _StockInfoScreenState extends ConsumerState<StockInfoScreen> {
  final TextEditingController _symbolController = TextEditingController();
  final NumberFormat _priceFormat = NumberFormat.simpleCurrency();
  final NumberFormat _volumeFormat = NumberFormat.compact();

  String? _selectedTicker;
  bool _includeTechnical = true;
  bool _includePerformance = true;

  @override
  void initState() {
    super.initState();
  }

  @override
  void dispose() {
    _symbolController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final stockState = ref.watch(stockInfoProvider);
    final tickersAsync = ref.watch(instrumentTickersProvider);
    final theme = Theme.of(context);

    // Listen for symbol changes and update text controller
    ref.listen<StockInfoState>(stockInfoProvider, (previous, next) {
      final nextSymbol = next.symbol;
      if (nextSymbol != null && nextSymbol.isNotEmpty) {
        final upper = nextSymbol.toUpperCase();
        if (_symbolController.text.toUpperCase() != upper) {
          _symbolController.value = TextEditingValue(
            text: upper,
            selection: TextSelection.collapsed(offset: upper.length),
          );
        }
      }
    });

    final List<Widget> content = [
      _buildSelectionCard(context, tickersAsync),
    ];

    if (stockState.isLoading && stockState.detail == null) {
      content.add(const SizedBox(height: 24));
      content.add(
        const LoadingWidget(message: 'Fetching stock information...'),
      );
    } else if (stockState.error != null) {
      content.add(const SizedBox(height: 24));
      content.add(
        ErrorDisplayWidget(
          error: stockState.error!,
          onRetry: _onFetch,
          title: 'Could not load stock data',
        ),
      );
    } else if (stockState.detail != null) {
      if (stockState.isLoading) {
        content.add(
          Padding(
            padding: const EdgeInsets.symmetric(vertical: 8),
            child: LinearProgressIndicator(
              minHeight: 4,
              color: theme.colorScheme.primary,
              backgroundColor: theme.colorScheme.surfaceVariant,
            ),
          ),
        );
      }
      content.addAll(_buildDetailSections(context, stockState.detail!));
    } else {
      content.add(const SizedBox(height: 24));
      content.add(_buildPlaceholderCard(context));
    }

    return Scaffold(
      appBar: AppBar(
        title: const Text('Stock Insights'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            tooltip: 'Refresh',
            onPressed: stockState.symbol == null
                ? null
                : () => ref.read(stockInfoProvider.notifier).refresh(
                      includeTechnical: _includeTechnical,
                      includePerformance: _includePerformance,
                    ),
          ),
        ],
      ),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
          children: content,
        ),
      ),
    );
  }

  Widget _buildSelectionCard(
    BuildContext context,
    AsyncValue<List<String>> tickers,
  ) {
    final theme = Theme.of(context);
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(Icons.search, color: theme.colorScheme.primary),
                const SizedBox(width: 8),
                Text(
                  'Find a Stock',
                  style: theme.textTheme.titleLarge?.copyWith(
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            tickers.when(
              data: (options) {
                final items = options
                    .map(
                      (ticker) => DropdownMenuItem<String>(
                        value: ticker,
                        child: Text(ticker),
                      ),
                    )
                    .toList();
                return DropdownButtonFormField<String>(
                  value: _selectedTicker != null &&
                          options.contains(_selectedTicker)
                      ? _selectedTicker
                      : null,
                  items: items,
                  isExpanded: true,
                  decoration: const InputDecoration(
                    labelText: 'Choose from tracked instruments',
                    border: OutlineInputBorder(),
                    isDense: true,
                  ),
                  onChanged: (value) {
                    setState(() {
                      _selectedTicker = value;
                      if (value != null) {
                        _symbolController.value = TextEditingValue(
                          text: value,
                          selection:
                              TextSelection.collapsed(offset: value.length),
                        );
                      }
                    });
                    if (value != null) {
                      _onFetch(symbolOverride: value);
                    }
                  },
                );
              },
              loading: () => const LinearProgressIndicator(),
              error: (error, _) => Text(
                'Unable to load instrument list',
                style: theme.textTheme.bodySmall?.copyWith(
                  color: theme.colorScheme.error,
                ),
              ),
            ),
            const SizedBox(height: 16),
            TextField(
              controller: _symbolController,
              textCapitalization: TextCapitalization.characters,
              decoration: const InputDecoration(
                labelText: 'Or type a symbol manually',
                hintText: 'e.g. AAPL',
                border: OutlineInputBorder(),
                isDense: true,
              ),
              inputFormatters: [
                FilteringTextInputFormatter.allow(RegExp(r'[A-Za-z0-9\.-]')),
              ],
              onSubmitted: (_) => _onFetch(),
            ),
            const SizedBox(height: 12),
            Wrap(
              spacing: 12,
              runSpacing: 8,
              children: [
                FilterChip(
                  label: const Text('Technical indicators'),
                  selected: _includeTechnical,
                  onSelected: (value) {
                    setState(() => _includeTechnical = value);
                  },
                ),
                FilterChip(
                  label: const Text('Performance metrics'),
                  selected: _includePerformance,
                  onSelected: (value) {
                    setState(() => _includePerformance = value);
                  },
                ),
              ],
            ),
            const SizedBox(height: 16),
            Align(
              alignment: Alignment.centerRight,
              child: FilledButton.icon(
                onPressed: _onFetch,
                icon: const Icon(Icons.trending_up),
                label: const Text('View details'),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildPlaceholderCard(BuildContext context) {
    final theme = Theme.of(context);
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          children: [
            Icon(
              Icons.assessment_outlined,
              size: 48,
              color: theme.colorScheme.primary,
            ),
            const SizedBox(height: 16),
            Text(
              'Search to explore a stock',
              style: theme.textTheme.titleLarge?.copyWith(
                fontWeight: FontWeight.w600,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              'Pick a ticker from your instrument list or enter any valid symbol to see live market data, company profile, and analytics.',
              style: theme.textTheme.bodyMedium?.copyWith(
                color: theme.colorScheme.onSurfaceVariant,
              ),
              textAlign: TextAlign.center,
            ),
          ],
        ),
      ),
    );
  }

  List<Widget> _buildDetailSections(BuildContext context, StockDetail detail) {
    final strategyHistoryState = ref.watch(strategyHistoryProvider);
    final sections = <Widget>[
      _buildOverviewCard(context, detail),
      if (detail.dataQuality != null)
        _buildDataQualityCard(context, detail.dataQuality!),
    ];

    if (detail.companyInfo != null) {
      sections.add(_buildCompanyInfoCard(context, detail.companyInfo!));
    }

    if (_includePerformance) {
      if (detail.performanceMetrics != null) {
        sections
            .add(_buildPerformanceCard(context, detail.performanceMetrics!));
      } else {
        sections.add(
          _buildInfoMessageCard(
            context,
            title: 'Performance metrics',
            message: 'Performance data is not available for this symbol.',
            icon: Icons.insights_outlined,
          ),
        );
      }
    } else {
      sections.add(
        _buildInfoMessageCard(
          context,
          title: 'Performance metrics',
          message:
              'Performance metrics are hidden. Enable the toggle above to include them in the request.',
          icon: Icons.visibility_off,
        ),
      );
    }

    if (_includeTechnical) {
      if (detail.technicalIndicators != null) {
        sections.add(_buildTechnicalCard(context, detail.technicalIndicators!));
      } else {
        sections.add(
          _buildInfoMessageCard(
            context,
            title: 'Technical indicators',
            message:
                'Technical indicator data is not available for this symbol.',
            icon: Icons.auto_graph_outlined,
          ),
        );
      }
    } else {
      sections.add(
        _buildInfoMessageCard(
          context,
          title: 'Technical indicators',
          message:
              'Technical indicators are hidden. Enable the toggle above to request them.',
          icon: Icons.visibility_off,
        ),
      );
    }

    // Add strategy history section
    sections.add(_buildStrategyHistorySection(context, detail.ticker, strategyHistoryState));

    return sections;
  }

  Widget _buildOverviewCard(BuildContext context, StockDetail detail) {
    final theme = Theme.of(context);
    final market = detail.marketData;
    final company = detail.companyInfo;
    final timestamp = market?.timestamp ?? detail.timestamp;
    final changeColor =
        _deltaColor(market?.change ?? market?.changePercent, theme);

    final infoLines = <String>[];
    if (company?.companyName != null &&
        company!.companyName!.isNotEmpty &&
        company.companyName!.toUpperCase() != detail.ticker.toUpperCase()) {
      infoLines.add(company.companyName!);
    }
    if (timestamp != null) {
      infoLines.add('Updated ${_formatDateTime(timestamp)}');
    }

    final metrics = <MapEntry<String, String>>[
      MapEntry('Open', _formatPrice(market?.open)),
      MapEntry('High', _formatPrice(market?.high)),
      MapEntry('Low', _formatPrice(market?.low)),
      MapEntry('Prev close', _formatPrice(market?.previousClose)),
      MapEntry('Volume', _formatVolume(market?.volume)),
    ].where((entry) => entry.value != '-').toList();

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        detail.ticker,
                        style: theme.textTheme.headlineLarge?.copyWith(
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      if (infoLines.isNotEmpty) ...[
                        const SizedBox(height: 4),
                        Text(
                          infoLines.join(' - '),
                          style: theme.textTheme.bodyMedium?.copyWith(
                            color: theme.colorScheme.onSurfaceVariant,
                          ),
                        ),
                      ],
                    ],
                  ),
                ),
                if (company?.sector != null && company!.sector!.isNotEmpty)
                  Chip(
                    label: Text(company.sector!),
                    avatar: const Icon(Icons.apartment, size: 16),
                  ),
              ],
            ),
            const SizedBox(height: 16),
            Row(
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                Text(
                  _formatPrice(market?.price),
                  style: theme.textTheme.displaySmall?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const SizedBox(width: 16),
                if (market?.change != null || market?.changePercent != null)
                  Container(
                    padding:
                        const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                    decoration: BoxDecoration(
                      color: changeColor.withOpacity(0.1),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Text(
                      [
                        if (market?.change != null)
                          _formatChange(market!.change!),
                        if (market?.changePercent != null)
                          '(${_formatPercent(market!.changePercent!)})',
                      ].join(' '),
                      style: theme.textTheme.titleMedium?.copyWith(
                        color: changeColor,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ),
              ],
            ),
            const SizedBox(height: 20),
            if (metrics.isNotEmpty)
              Wrap(
                spacing: 12,
                runSpacing: 12,
                children: metrics
                    .map((entry) =>
                        _buildMetricPill(context, entry.key, entry.value))
                    .toList(),
              ),
          ],
        ),
      ),
    );
  }

  Widget _buildCompanyInfoCard(BuildContext context, CompanyInfo info) {
    final theme = Theme.of(context);

    final details = <MapEntry<String, String>>[
      MapEntry('Industry', info.industry ?? '-'),
      MapEntry('Country', info.country ?? '-'),
      MapEntry('Currency', info.currency ?? '-'),
      MapEntry('Employees', _formatEmployees(info.employees)),
      MapEntry('Market cap',
          _formatMarketCap(info.marketCap, currency: info.currency)),
    ].where((entry) => entry.value != '-').toList();

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.apartment),
                const SizedBox(width: 8),
                Text(
                  'Company profile',
                  style: theme.textTheme.titleLarge?.copyWith(
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            if (details.isNotEmpty)
              Wrap(
                spacing: 16,
                runSpacing: 12,
                children: details
                    .map((entry) =>
                        _buildMetricPill(context, entry.key, entry.value))
                    .toList(),
              ),
            if (info.website != null && info.website!.isNotEmpty) ...[
              const SizedBox(height: 16),
              Row(
                children: [
                  const Icon(Icons.link, size: 18),
                  const SizedBox(width: 8),
                  Flexible(
                    child: Text(
                      info.website!,
                      style: theme.textTheme.bodyMedium?.copyWith(
                        color: theme.colorScheme.primary,
                        decoration: TextDecoration.underline,
                      ),
                    ),
                  ),
                ],
              ),
            ],
            if (info.description != null && info.description!.isNotEmpty) ...[
              const SizedBox(height: 16),
              Text(
                info.description!,
                style: theme.textTheme.bodyMedium?.copyWith(
                  color: theme.colorScheme.onSurfaceVariant,
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildPerformanceCard(
    BuildContext context,
    PerformanceMetrics metrics,
  ) {
    final theme = Theme.of(context);

    final primaryStats = <MapEntry<String, String>>[
      MapEntry('Total return', _formatPercent(metrics.totalReturn)),
      MapEntry('Annualized return', _formatPercent(metrics.annualizedReturn)),
      MapEntry('Volatility', _formatPercent(metrics.volatility)),
      MapEntry('Max drawdown', _formatPercent(metrics.maxDrawdown)),
      MapEntry('Sharpe ratio', _formatNumber(metrics.sharpeRatio, decimals: 2)),
    ].where((entry) => entry.value != '-').toList();

    final periodReturns = <MapEntry<String, String>>[
      MapEntry('1 month', _formatPercent(metrics.oneMonthReturn)),
      MapEntry('3 month', _formatPercent(metrics.threeMonthReturn)),
      MapEntry('6 month', _formatPercent(metrics.sixMonthReturn)),
      MapEntry('52w high', _formatPrice(metrics.fiftyTwoWeekHigh)),
      MapEntry('52w low', _formatPrice(metrics.fiftyTwoWeekLow)),
      MapEntry(
          'Dist. 52w high', _formatPercent(metrics.distanceFrom52WeekHigh)),
      MapEntry('Dist. 52w low', _formatPercent(metrics.distanceFrom52WeekLow)),
    ].where((entry) => entry.value != '-').toList();

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.insights),
                const SizedBox(width: 8),
                Text(
                  'Performance',
                  style: theme.textTheme.titleLarge?.copyWith(
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            if (primaryStats.isNotEmpty) ...[
              Text(
                'Key metrics',
                style: theme.textTheme.titleMedium,
              ),
              const SizedBox(height: 12),
              Wrap(
                spacing: 12,
                runSpacing: 12,
                children: primaryStats
                    .map((entry) =>
                        _buildMetricPill(context, entry.key, entry.value))
                    .toList(),
              ),
            ],
            if (periodReturns.isNotEmpty) ...[
              const SizedBox(height: 20),
              Text(
                'Recent performance',
                style: theme.textTheme.titleMedium,
              ),
              const SizedBox(height: 12),
              Wrap(
                spacing: 12,
                runSpacing: 12,
                children: periodReturns
                    .map((entry) =>
                        _buildMetricPill(context, entry.key, entry.value))
                    .toList(),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildTechnicalCard(
    BuildContext context,
    TechnicalIndicators indicators,
  ) {
    final theme = Theme.of(context);

    final movingAverages = <MapEntry<String, String>>[
      MapEntry('SMA 10', _formatPrice(indicators.sma10)),
      MapEntry('SMA 20', _formatPrice(indicators.sma20)),
      MapEntry('SMA 50', _formatPrice(indicators.sma50)),
      MapEntry('SMA 200', _formatPrice(indicators.sma200)),
      MapEntry('EMA 12', _formatPrice(indicators.ema12)),
      MapEntry('EMA 26', _formatPrice(indicators.ema26)),
    ].where((entry) => entry.value != '-').toList();

    final oscillators = <MapEntry<String, String>>[
      MapEntry('RSI (14)', _formatNumber(indicators.rsi14, decimals: 2)),
      MapEntry('MACD', _formatNumber(indicators.macdLine, decimals: 2)),
      MapEntry('Signal', _formatNumber(indicators.macdSignal, decimals: 2)),
      MapEntry(
          'Histogram', _formatNumber(indicators.macdHistogram, decimals: 2)),
      MapEntry('ATR (14)', _formatNumber(indicators.atr14, decimals: 2)),
    ].where((entry) => entry.value != '-').toList();

    final positioning = <MapEntry<String, String>>[
      MapEntry('Price vs SMA10', _formatPercent(indicators.priceVsSma10)),
      MapEntry('Price vs SMA20', _formatPercent(indicators.priceVsSma20)),
      MapEntry('Price vs SMA50', _formatPercent(indicators.priceVsSma50)),
      MapEntry('Price vs SMA200', _formatPercent(indicators.priceVsSma200)),
      MapEntry('BB Upper', _formatPrice(indicators.bbUpper)),
      MapEntry('BB Lower', _formatPrice(indicators.bbLower)),
      MapEntry(
          'BB Position',
          _formatPercent(indicators.bbPosition != null
              ? indicators.bbPosition! * 100
              : null)),
    ].where((entry) => entry.value != '-').toList();

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.auto_graph),
                const SizedBox(width: 8),
                Text(
                  'Technical indicators',
                  style: theme.textTheme.titleLarge?.copyWith(
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            if (movingAverages.isNotEmpty) ...[
              Text(
                'Moving averages',
                style: theme.textTheme.titleMedium,
              ),
              const SizedBox(height: 12),
              Wrap(
                spacing: 12,
                runSpacing: 12,
                children: movingAverages
                    .map((entry) =>
                        _buildMetricPill(context, entry.key, entry.value))
                    .toList(),
              ),
            ],
            if (oscillators.isNotEmpty) ...[
              const SizedBox(height: 20),
              Text(
                'Momentum',
                style: theme.textTheme.titleMedium,
              ),
              const SizedBox(height: 12),
              Wrap(
                spacing: 12,
                runSpacing: 12,
                children: oscillators
                    .map((entry) =>
                        _buildMetricPill(context, entry.key, entry.value))
                    .toList(),
              ),
            ],
            if (positioning.isNotEmpty) ...[
              const SizedBox(height: 20),
              Text(
                'Price positioning',
                style: theme.textTheme.titleMedium,
              ),
              const SizedBox(height: 12),
              Wrap(
                spacing: 12,
                runSpacing: 12,
                children: positioning
                    .map((entry) =>
                        _buildMetricPill(context, entry.key, entry.value))
                    .toList(),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildDataQualityCard(BuildContext context, DataQuality quality) {
    final theme = Theme.of(context);

    final items = [
      MapEntry('Market data', quality.hasMarketData),
      MapEntry('Company info', quality.hasCompanyInfo),
      MapEntry('Technical data', quality.hasTechnicalData),
      MapEntry('Performance data', quality.hasPerformanceData),
    ];

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Data availability',
              style: theme.textTheme.titleMedium?.copyWith(
                fontWeight: FontWeight.w600,
              ),
            ),
            const SizedBox(height: 12),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: items
                  .map(
                    (entry) => InputChip(
                      label: Text(entry.key),
                      avatar: Icon(
                        entry.value ? Icons.check_circle : Icons.error_outline,
                        size: 18,
                        color: entry.value
                            ? theme.colorScheme.primary
                            : theme.colorScheme.error,
                      ),
                      labelStyle: theme.textTheme.bodyMedium,
                    ),
                  )
                  .toList(),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildInfoMessageCard(
    BuildContext context, {
    required String title,
    required String message,
    required IconData icon,
  }) {
    final theme = Theme.of(context);

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(icon, color: theme.colorScheme.onSurfaceVariant),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title,
                    style: theme.textTheme.titleMedium?.copyWith(
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    message,
                    style: theme.textTheme.bodyMedium?.copyWith(
                      color: theme.colorScheme.onSurfaceVariant,
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

  Widget _buildStrategyHistorySection(BuildContext context, String ticker, StrategyHistoryState strategyHistoryState) {
    // Ensure strategy history is loaded for this ticker
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (strategyHistoryState.symbol != ticker) {
        ref.read(strategyHistoryProvider.notifier).fetchStrategyHistory(ticker);
      }
    });

    return StrategyHistoryTable(
      executions: strategyHistoryState.history?.executions ?? [],
      isLoading: strategyHistoryState.isLoading,
      error: strategyHistoryState.error,
      onRetry: () {
        ref.read(strategyHistoryProvider.notifier).fetchStrategyHistory(ticker);
      },
    );
  }

  Widget _buildMetricPill(BuildContext context, String label, String value) {
    final theme = Theme.of(context);
    return Container(
      width: 140,
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
        color: theme.colorScheme.surfaceVariant.withOpacity(0.6),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            label,
            style: theme.textTheme.labelSmall?.copyWith(
              color: theme.colorScheme.onSurfaceVariant,
            ),
          ),
          const SizedBox(height: 6),
          Text(
            value,
            style: theme.textTheme.titleSmall?.copyWith(
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }

  void _onFetch({String? symbolOverride}) {
    final effectiveSymbol = symbolOverride ?? _symbolController.text.trim();
    ref.read(stockInfoProvider.notifier).fetchStock(
          effectiveSymbol,
          includeTechnical: _includeTechnical,
          includePerformance: _includePerformance,
        );
  }

  String _formatPrice(double? value) {
    if (value == null) return '-';
    return _priceFormat.format(value);
  }

  String _formatMarketCap(double? value, {String? currency}) {
    if (value == null) return '-';
    final compact = _volumeFormat.format(value);
    final symbol = (currency == null ||
            currency.isEmpty ||
            currency.toUpperCase() == 'USD')
        ? '\$'
        : currency.toUpperCase();
    return symbol.length == 1 ? '$symbol$compact' : '$compact $symbol';
  }

  String _formatNumber(double? value, {int decimals = 2}) {
    if (value == null) return '-';
    return value.toStringAsFixed(decimals);
  }

  String _formatEmployees(int? employees) {
    if (employees == null) return '-';
    return _volumeFormat.format(employees);
  }

  String _formatVolume(num? volume) {
    if (volume == null) return '-';
    return _volumeFormat.format(volume);
  }

  String _formatPercent(double? value) {
    if (value == null) return '-';
    return '${value >= 0 ? '+' : ''}${value.toStringAsFixed(2)}%';
  }

  String _formatChange(double value) {
    final prefix = value >= 0 ? '+' : '-';
    final formatted = _priceFormat.format(value.abs());
    return prefix + formatted;
  }

  String _formatDateTime(DateTime value) {
    return DateFormat('MMM d, y - h:mm a').format(value.toLocal());
  }

  Color _deltaColor(double? value, ThemeData theme) {
    if (value == null) {
      return theme.colorScheme.onSurface;
    }
    if (value > 0) {
      return theme.colorScheme.tertiary;
    }
    if (value < 0) {
      return theme.colorScheme.error;
    }
    return theme.colorScheme.onSurface;
  }
}
