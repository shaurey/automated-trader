import 'package:flutter/foundation.dart';

double? _parseDouble(dynamic value) {
  if (value == null) return null;
  if (value is num) return value.toDouble();
  if (value is String) return double.tryParse(value);
  return null;
}

int? _parseInt(dynamic value) {
  if (value == null) return null;
  if (value is int) return value;
  if (value is num) return value.toInt();
  if (value is String) return int.tryParse(value);
  return null;
}

DateTime? _parseDateTime(dynamic value) {
  if (value == null) return null;
  if (value is DateTime) return value;
  if (value is String) {
    return DateTime.tryParse(value);
  }
  return null;
}

class StockDetail {
  final String ticker;
  final DateTime? timestamp;
  final MarketData? marketData;
  final CompanyInfo? companyInfo;
  final TechnicalIndicators? technicalIndicators;
  final PerformanceMetrics? performanceMetrics;
  final DataQuality? dataQuality;
  final Map<String, dynamic> extra;

  StockDetail({
    required this.ticker,
    required this.timestamp,
    required this.marketData,
    required this.companyInfo,
    required this.technicalIndicators,
    required this.performanceMetrics,
    required this.dataQuality,
    required this.extra,
  });

  factory StockDetail.fromJson(Map<String, dynamic> json) {
    final data = Map<String, dynamic>.from(json);

    final market = data['market_data'] is Map<String, dynamic>
        ? MarketData.fromJson(data['market_data'] as Map<String, dynamic>)
        : null;
    final company = data['company_info'] is Map<String, dynamic>
        ? CompanyInfo.fromJson(data['company_info'] as Map<String, dynamic>)
        : null;
    final technical = data['technical_indicators'] is Map<String, dynamic>
        ? TechnicalIndicators.fromJson(
            data['technical_indicators'] as Map<String, dynamic>,
          )
        : null;
    final performance = data['performance_metrics'] is Map<String, dynamic>
        ? PerformanceMetrics.fromJson(
            data['performance_metrics'] as Map<String, dynamic>,
          )
        : null;
    final quality = data['data_quality'] is Map<String, dynamic>
        ? DataQuality.fromJson(data['data_quality'] as Map<String, dynamic>)
        : null;

    final timestamp = _parseDateTime(data['timestamp']);
    final ticker = (data['ticker'] ?? data['symbol'] ?? '').toString();

    data.remove('market_data');
    data.remove('company_info');
    data.remove('technical_indicators');
    data.remove('performance_metrics');
    data.remove('data_quality');
    data.remove('timestamp');
    data.remove('ticker');
    data.remove('symbol');

    return StockDetail(
      ticker: ticker,
      timestamp: timestamp,
      marketData: market,
      companyInfo: company,
      technicalIndicators: technical,
      performanceMetrics: performance,
      dataQuality: quality,
      extra: data,
    );
  }
}

class MarketData {
  final double? price;
  final double? change;
  final double? changePercent;
  final int? volume;
  final double? high;
  final double? low;
  final double? open;
  final double? previousClose;
  final DateTime? timestamp;
  final Map<String, dynamic> extra;

  const MarketData({
    this.price,
    this.change,
    this.changePercent,
    this.volume,
    this.high,
    this.low,
    this.open,
    this.previousClose,
    this.timestamp,
    this.extra = const {},
  });

  factory MarketData.fromJson(Map<String, dynamic> json) {
    final data = Map<String, dynamic>.from(json);
    final market = MarketData(
      price: _parseDouble(data['price']),
      change: _parseDouble(data['change']),
      changePercent: _parseDouble(data['change_percent']),
      volume: _parseInt(data['volume']),
      high: _parseDouble(data['high']),
      low: _parseDouble(data['low']),
      open: _parseDouble(data['open']),
      previousClose: _parseDouble(data['previous_close'] ?? data['prev_close']),
      timestamp: _parseDateTime(data['timestamp']),
      extra: data,
    );
    return market;
  }
}

class CompanyInfo {
  final String? companyName;
  final String? sector;
  final String? industry;
  final String? country;
  final String? currency;
  final int? employees;
  final double? marketCap;
  final String? description;
  final String? website;
  final Map<String, dynamic> extra;

  const CompanyInfo({
    this.companyName,
    this.sector,
    this.industry,
    this.country,
    this.currency,
    this.employees,
    this.marketCap,
    this.description,
    this.website,
    this.extra = const {},
  });

  factory CompanyInfo.fromJson(Map<String, dynamic> json) {
    final data = Map<String, dynamic>.from(json);
    return CompanyInfo(
      companyName: data['company_name']?.toString(),
      sector: data['sector']?.toString(),
      industry: data['industry']?.toString(),
      country: data['country']?.toString(),
      currency: data['currency']?.toString(),
      employees: _parseInt(data['employees']),
      marketCap: _parseDouble(data['market_cap']),
      description: data['description']?.toString(),
      website: data['website']?.toString(),
      extra: data,
    );
  }
}

class TechnicalIndicators {
  final double? sma10;
  final double? sma20;
  final double? sma50;
  final double? sma200;
  final double? ema12;
  final double? ema26;
  final double? rsi14;
  final double? macdLine;
  final double? macdSignal;
  final double? macdHistogram;
  final double? bbUpper;
  final double? bbMiddle;
  final double? bbLower;
  final double? bbPosition;
  final double? volumeSma20;
  final double? volumeRatio;
  final double? priceVsSma10;
  final double? priceVsSma20;
  final double? priceVsSma50;
  final double? priceVsSma200;
  final double? atr14;
  final Map<String, dynamic> extra;

  const TechnicalIndicators({
    this.sma10,
    this.sma20,
    this.sma50,
    this.sma200,
    this.ema12,
    this.ema26,
    this.rsi14,
    this.macdLine,
    this.macdSignal,
    this.macdHistogram,
    this.bbUpper,
    this.bbMiddle,
    this.bbLower,
    this.bbPosition,
    this.volumeSma20,
    this.volumeRatio,
    this.priceVsSma10,
    this.priceVsSma20,
    this.priceVsSma50,
    this.priceVsSma200,
    this.atr14,
    this.extra = const {},
  });

  factory TechnicalIndicators.fromJson(Map<String, dynamic> json) {
    final data = Map<String, dynamic>.from(json);
    return TechnicalIndicators(
      sma10: _parseDouble(data['sma_10']),
      sma20: _parseDouble(data['sma_20']),
      sma50: _parseDouble(data['sma_50']),
      sma200: _parseDouble(data['sma_200']),
      ema12: _parseDouble(data['ema_12']),
      ema26: _parseDouble(data['ema_26']),
      rsi14: _parseDouble(data['rsi_14']),
      macdLine: _parseDouble(data['macd_line']),
      macdSignal: _parseDouble(data['macd_signal']),
      macdHistogram: _parseDouble(data['macd_histogram']),
      bbUpper: _parseDouble(data['bb_upper']),
      bbMiddle: _parseDouble(data['bb_middle']),
      bbLower: _parseDouble(data['bb_lower']),
      bbPosition: _parseDouble(data['bb_position']),
      volumeSma20: _parseDouble(data['volume_sma_20']),
      volumeRatio: _parseDouble(data['volume_ratio']),
      priceVsSma10: _parseDouble(data['price_vs_sma10']),
      priceVsSma20: _parseDouble(data['price_vs_sma20']),
      priceVsSma50: _parseDouble(data['price_vs_sma50']),
      priceVsSma200: _parseDouble(data['price_vs_sma200']),
      atr14: _parseDouble(data['atr_14']),
      extra: data,
    );
  }
}

class PerformanceMetrics {
  final double? totalReturn;
  final double? annualizedReturn;
  final double? volatility;
  final double? dailyVolatility;
  final double? maxDrawdown;
  final double? sharpeRatio;
  final double? oneMonthReturn;
  final double? threeMonthReturn;
  final double? sixMonthReturn;
  final double? fiftyTwoWeekHigh;
  final double? fiftyTwoWeekLow;
  final double? distanceFrom52WeekHigh;
  final double? distanceFrom52WeekLow;
  final Map<String, dynamic> extra;

  const PerformanceMetrics({
    this.totalReturn,
    this.annualizedReturn,
    this.volatility,
    this.dailyVolatility,
    this.maxDrawdown,
    this.sharpeRatio,
    this.oneMonthReturn,
    this.threeMonthReturn,
    this.sixMonthReturn,
    this.fiftyTwoWeekHigh,
    this.fiftyTwoWeekLow,
    this.distanceFrom52WeekHigh,
    this.distanceFrom52WeekLow,
    this.extra = const {},
  });

  factory PerformanceMetrics.fromJson(Map<String, dynamic> json) {
    final data = Map<String, dynamic>.from(json);
    return PerformanceMetrics(
      totalReturn: _parseDouble(data['total_return']),
      annualizedReturn: _parseDouble(data['annualized_return']),
      volatility: _parseDouble(data['volatility']),
      dailyVolatility: _parseDouble(data['daily_volatility']),
      maxDrawdown: _parseDouble(data['max_drawdown']),
      sharpeRatio: _parseDouble(data['sharpe_ratio']),
      oneMonthReturn:
          _parseDouble(data['1_month_return'] ?? data['one_month_return']),
      threeMonthReturn:
          _parseDouble(data['3_month_return'] ?? data['three_month_return']),
      sixMonthReturn:
          _parseDouble(data['6_month_return'] ?? data['six_month_return']),
      fiftyTwoWeekHigh:
          _parseDouble(data['52_week_high'] ?? data['fifty_two_week_high']),
      fiftyTwoWeekLow:
          _parseDouble(data['52_week_low'] ?? data['fifty_two_week_low']),
      distanceFrom52WeekHigh: _parseDouble(
          data['distance_from_52w_high'] ?? data['distance_from_52_week_high']),
      distanceFrom52WeekLow: _parseDouble(
          data['distance_from_52w_low'] ?? data['distance_from_52_week_low']),
      extra: data,
    );
  }
}

class DataQuality {
  final bool hasMarketData;
  final bool hasCompanyInfo;
  final bool hasTechnicalData;
  final bool hasPerformanceData;
  final Map<String, dynamic> extra;

  const DataQuality({
    required this.hasMarketData,
    required this.hasCompanyInfo,
    required this.hasTechnicalData,
    required this.hasPerformanceData,
    this.extra = const {},
  });

  factory DataQuality.fromJson(Map<String, dynamic> json) {
    final data = Map<String, dynamic>.from(json);
    return DataQuality(
      hasMarketData: data['has_market_data'] == true,
      hasCompanyInfo: data['has_company_info'] == true,
      hasTechnicalData: data['has_technical_data'] == true,
      hasPerformanceData: data['has_performance_data'] == true,
      extra: data,
    );
  }
}

class StrategyHistoryItem {
  final String runId;
  final String strategyCode;
  final String ticker;
  final bool passed;
  final double? score;
  final String? classification;
  final List<String> reasons;
  final Map<String, dynamic> metrics;
  final DateTime? createdAt;
  final DateTime? runStartedAt;
  final DateTime? runCompletedAt;
  final Map<String, dynamic> runParams;
  final Map<String, dynamic> extra;

  const StrategyHistoryItem({
    required this.runId,
    required this.strategyCode,
    required this.ticker,
    required this.passed,
    this.score,
    this.classification,
    this.reasons = const [],
    this.metrics = const {},
    this.createdAt,
    this.runStartedAt,
    this.runCompletedAt,
    this.runParams = const {},
    this.extra = const {},
  });

  factory StrategyHistoryItem.fromJson(Map<String, dynamic> json) {
    final data = Map<String, dynamic>.from(json);
    
    return StrategyHistoryItem(
      runId: data['run_id']?.toString() ?? '',
      strategyCode: data['strategy_code']?.toString() ?? '',
      ticker: data['ticker']?.toString() ?? '',
      passed: data['passed'] == true,
      score: _parseDouble(data['score']),
      classification: data['classification']?.toString(),
      reasons: (data['reasons'] as List?)?.map((e) => e.toString()).toList() ?? [],
      metrics: (data['metrics'] as Map<String, dynamic>?) ?? {},
      createdAt: _parseDateTime(data['created_at']),
      runStartedAt: _parseDateTime(data['run_started_at']),
      runCompletedAt: _parseDateTime(data['run_completed_at']),
      runParams: (data['run_params'] as Map<String, dynamic>?) ?? {},
      extra: data,
    );
  }
}

class StrategyHistoryResponse {
  final String symbol;
  final int totalExecutions;
  final List<StrategyHistoryItem> executions;
  final Map<String, dynamic> extra;

  const StrategyHistoryResponse({
    required this.symbol,
    required this.totalExecutions,
    required this.executions,
    this.extra = const {},
  });

  factory StrategyHistoryResponse.fromJson(Map<String, dynamic> json) {
    final data = Map<String, dynamic>.from(json);
    
    final executionsList = (data['executions'] as List?) ?? [];
    final executions = executionsList
        .map((e) => StrategyHistoryItem.fromJson(e as Map<String, dynamic>))
        .toList();

    return StrategyHistoryResponse(
      symbol: data['symbol']?.toString() ?? '',
      totalExecutions: _parseInt(data['total_executions']) ?? 0,
      executions: executions,
      extra: data,
    );
  }
}
