import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/strategies.dart';
import '../services/api_service.dart';

// Strategy Runs Provider with filters
final strategyRunsProvider = FutureProvider.family<StrategyRunsResponse, StrategyRunsFilter>((ref, filter) async {
  return await ApiService.getStrategyRuns(
    strategyCode: filter.strategyCode,
    status: filter.status,
    dateFrom: filter.dateFrom,
    dateTo: filter.dateTo,
    limit: filter.limit,
    offset: filter.offset,
    orderBy: filter.orderBy,
    orderDesc: filter.orderDesc,
  );
});

// Strategy Run Detail Provider
final strategyRunDetailProvider = FutureProvider.family<StrategyRunDetail, String>((ref, runId) async {
  return await ApiService.getStrategyRunDetail(runId);
});

// Strategy Run Results Provider
final strategyRunResultsProvider = FutureProvider.family<StrategyResultsResponse, StrategyResultsFilter>((ref, filter) async {
  return await ApiService.getStrategyRunResults(
    filter.runId,
    passed: filter.passed,
    minScore: filter.minScore,
    maxScore: filter.maxScore,
    classification: filter.classification,
    ticker: filter.ticker,
    sector: filter.sector,
    limit: filter.limit,
    offset: filter.offset,
    orderBy: filter.orderBy,
    orderDesc: filter.orderDesc,
  );
});

// Latest Strategy Runs Provider
final latestStrategyRunsProvider = FutureProvider.family<StrategyLatestResponse, LatestStrategyFilter>((ref, filter) async {
  return await ApiService.getLatestStrategyRuns(
    strategyCodes: filter.strategyCodes,
    limit: filter.limit,
  );
});

// Selected filters state providers
final selectedStrategyCodeProvider = StateProvider<String?>((ref) => null);
final selectedStatusProvider = StateProvider<String?>((ref) => null);
final strategySearchQueryProvider = StateProvider<String>((ref) => '');
final strategySortModeProvider = StateProvider<StrategySortMode>((ref) => StrategySortMode.startedAtDesc);

// Results filters
final selectedPassedFilterProvider = StateProvider<bool?>((ref) => null);
final selectedClassificationProvider = StateProvider<String?>((ref) => null);
final selectedSectorProvider = StateProvider<String?>((ref) => null);
final resultsSortModeProvider = StateProvider<ResultsSortMode>((ref) => ResultsSortMode.scoreDesc);

// Pagination providers
final strategyRunsPageProvider = StateProvider<int>((ref) => 0);
final strategyResultsPageProvider = StateProvider<int>((ref) => 0);

// Filtered strategy runs provider
final filteredStrategyRunsProvider = Provider<AsyncValue<StrategyRunsResponse>>((ref) {
  final selectedStrategy = ref.watch(selectedStrategyCodeProvider);
  final selectedStatus = ref.watch(selectedStatusProvider);
  final searchQuery = ref.watch(strategySearchQueryProvider);
  final sortMode = ref.watch(strategySortModeProvider);
  final page = ref.watch(strategyRunsPageProvider);

  final filter = StrategyRunsFilter(
    strategyCode: selectedStrategy,
    status: selectedStatus,
    limit: 20,
    offset: page * 20,
    orderBy: sortMode.orderBy,
    orderDesc: sortMode.orderDesc,
  );

  return ref.watch(strategyRunsProvider(filter));
});

// Filter classes
class StrategyRunsFilter {
  final String? strategyCode;
  final String? status;
  final String? dateFrom;
  final String? dateTo;
  final int? limit;
  final int? offset;
  final String? orderBy;
  final bool? orderDesc;

  const StrategyRunsFilter({
    this.strategyCode,
    this.status,
    this.dateFrom,
    this.dateTo,
    this.limit,
    this.offset,
    this.orderBy,
    this.orderDesc,
  });

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is StrategyRunsFilter &&
          runtimeType == other.runtimeType &&
          strategyCode == other.strategyCode &&
          status == other.status &&
          dateFrom == other.dateFrom &&
          dateTo == other.dateTo &&
          limit == other.limit &&
          offset == other.offset &&
          orderBy == other.orderBy &&
          orderDesc == other.orderDesc;

  @override
  int get hashCode =>
      strategyCode.hashCode ^
      status.hashCode ^
      dateFrom.hashCode ^
      dateTo.hashCode ^
      limit.hashCode ^
      offset.hashCode ^
      orderBy.hashCode ^
      orderDesc.hashCode;
}

class StrategyResultsFilter {
  final String runId;
  final bool? passed;
  final double? minScore;
  final double? maxScore;
  final String? classification;
  final String? ticker;
  final String? sector;
  final int? limit;
  final int? offset;
  final String? orderBy;
  final bool? orderDesc;

  const StrategyResultsFilter({
    required this.runId,
    this.passed,
    this.minScore,
    this.maxScore,
    this.classification,
    this.ticker,
    this.sector,
    this.limit,
    this.offset,
    this.orderBy,
    this.orderDesc,
  });

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is StrategyResultsFilter &&
          runtimeType == other.runtimeType &&
          runId == other.runId &&
          passed == other.passed &&
          minScore == other.minScore &&
          maxScore == other.maxScore &&
          classification == other.classification &&
          ticker == other.ticker &&
          sector == other.sector &&
          limit == other.limit &&
          offset == other.offset &&
          orderBy == other.orderBy &&
          orderDesc == other.orderDesc;

  @override
  int get hashCode =>
      runId.hashCode ^
      passed.hashCode ^
      minScore.hashCode ^
      maxScore.hashCode ^
      classification.hashCode ^
      ticker.hashCode ^
      sector.hashCode ^
      limit.hashCode ^
      offset.hashCode ^
      orderBy.hashCode ^
      orderDesc.hashCode;
}

class LatestStrategyFilter {
  final String? strategyCodes;
  final int? limit;

  const LatestStrategyFilter({
    this.strategyCodes,
    this.limit,
  });

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is LatestStrategyFilter &&
          runtimeType == other.runtimeType &&
          strategyCodes == other.strategyCodes &&
          limit == other.limit;

  @override
  int get hashCode => strategyCodes.hashCode ^ limit.hashCode;
}

enum StrategySortMode {
  startedAtDesc,
  startedAtAsc,
  passRateDesc,
  passRateAsc,
  strategyCode,
}

extension StrategySortModeExtension on StrategySortMode {
  String get displayName {
    switch (this) {
      case StrategySortMode.startedAtDesc:
        return 'Started (Newest First)';
      case StrategySortMode.startedAtAsc:
        return 'Started (Oldest First)';
      case StrategySortMode.passRateDesc:
        return 'Pass Rate (High to Low)';
      case StrategySortMode.passRateAsc:
        return 'Pass Rate (Low to High)';
      case StrategySortMode.strategyCode:
        return 'Strategy Code (A-Z)';
    }
  }

  String get orderBy {
    switch (this) {
      case StrategySortMode.startedAtDesc:
      case StrategySortMode.startedAtAsc:
        return 'started_at';
      case StrategySortMode.passRateDesc:
      case StrategySortMode.passRateAsc:
        return 'passed_count';
      case StrategySortMode.strategyCode:
        return 'strategy_code';
    }
  }

  bool get orderDesc {
    switch (this) {
      case StrategySortMode.startedAtDesc:
      case StrategySortMode.passRateDesc:
        return true;
      case StrategySortMode.startedAtAsc:
      case StrategySortMode.passRateAsc:
      case StrategySortMode.strategyCode:
        return false;
    }
  }
}

enum ResultsSortMode {
  scoreDesc,
  scoreAsc,
  ticker,
  createdAtDesc,
}

extension ResultsSortModeExtension on ResultsSortMode {
  String get displayName {
    switch (this) {
      case ResultsSortMode.scoreDesc:
        return 'Score (High to Low)';
      case ResultsSortMode.scoreAsc:
        return 'Score (Low to High)';
      case ResultsSortMode.ticker:
        return 'Ticker (A-Z)';
      case ResultsSortMode.createdAtDesc:
        return 'Created (Newest First)';
    }
  }

  String get orderBy {
    switch (this) {
      case ResultsSortMode.scoreDesc:
      case ResultsSortMode.scoreAsc:
        return 'score';
      case ResultsSortMode.ticker:
        return 'ticker';
      case ResultsSortMode.createdAtDesc:
        return 'created_at';
    }
  }

  bool get orderDesc {
    switch (this) {
      case ResultsSortMode.scoreDesc:
      case ResultsSortMode.createdAtDesc:
        return true;
      case ResultsSortMode.scoreAsc:
      case ResultsSortMode.ticker:
        return false;
    }
  }
}