import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/stock_detail.dart';
import '../services/api_service.dart';

class StockInfoState {
  final String? symbol;
  final StockDetail? detail;
  final bool isLoading;
  final String? error;
  final bool hasSearched;

  const StockInfoState({
    this.symbol,
    this.detail,
    this.isLoading = false,
    this.error,
    this.hasSearched = false,
  });

  static const Object _sentinel = Object();

  StockInfoState copyWith({
    Object? symbol = _sentinel,
    Object? detail = _sentinel,
    bool? isLoading,
    Object? error = _sentinel,
    bool? hasSearched,
  }) {
    return StockInfoState(
      symbol: symbol == _sentinel ? this.symbol : symbol as String?,
      detail: detail == _sentinel ? this.detail : detail as StockDetail?,
      isLoading: isLoading ?? this.isLoading,
      error: error == _sentinel ? this.error : error as String?,
      hasSearched: hasSearched ?? this.hasSearched,
    );
  }
}

class StockInfoController extends StateNotifier<StockInfoState> {
  StockInfoController() : super(const StockInfoState());

  Future<void> fetchStock(
    String symbol, {
    bool includeTechnical = true,
    bool includePerformance = true,
  }) async {
    final trimmed = symbol.trim();
    if (trimmed.isEmpty) {
      state = state.copyWith(error: 'Please enter a stock symbol.');
      return;
    }

    final normalized = trimmed.toUpperCase();

    state = state.copyWith(
      symbol: normalized,
      isLoading: true,
      error: null,
      hasSearched: true,
    );

    try {
      final detail = await ApiService.getStockInfo(
        normalized,
        includeTechnical: includeTechnical,
        includePerformance: includePerformance,
      );

      state = state.copyWith(
        symbol: detail.ticker.isNotEmpty ? detail.ticker : normalized,
        detail: detail,
        isLoading: false,
        error: null,
        hasSearched: true,
      );
    } catch (e) {
      state = state.copyWith(
        detail: null,
        isLoading: false,
        error: e.toString(),
        hasSearched: true,
      );
    }
  }

  Future<void> refresh({
    bool includeTechnical = true,
    bool includePerformance = true,
  }) async {
    final symbol = state.symbol;
    if (symbol == null || symbol.isEmpty) {
      return;
    }
    await fetchStock(
      symbol,
      includeTechnical: includeTechnical,
      includePerformance: includePerformance,
    );
  }

  void clearError() {
    state = state.copyWith(error: null);
  }
}

final stockInfoProvider =
    StateNotifierProvider<StockInfoController, StockInfoState>((ref) {
  return StockInfoController();
});

final instrumentTickersProvider = FutureProvider<List<String>>((ref) async {
  return ApiService.getInstrumentTickers(limit: 250);
});

// Strategy History State and Controller
class StrategyHistoryState {
  final String? symbol;
  final StrategyHistoryResponse? history;
  final bool isLoading;
  final String? error;

  const StrategyHistoryState({
    this.symbol,
    this.history,
    this.isLoading = false,
    this.error,
  });

  static const Object _sentinel = Object();

  StrategyHistoryState copyWith({
    Object? symbol = _sentinel,
    Object? history = _sentinel,
    bool? isLoading,
    Object? error = _sentinel,
  }) {
    return StrategyHistoryState(
      symbol: symbol == _sentinel ? this.symbol : symbol as String?,
      history: history == _sentinel ? this.history : history as StrategyHistoryResponse?,
      isLoading: isLoading ?? this.isLoading,
      error: error == _sentinel ? this.error : error as String?,
    );
  }
}

class StrategyHistoryController extends StateNotifier<StrategyHistoryState> {
  StrategyHistoryController() : super(const StrategyHistoryState());

  Future<void> fetchStrategyHistory(String symbol, {int? limit}) async {
    final trimmed = symbol.trim();
    if (trimmed.isEmpty) {
      state = state.copyWith(error: 'Please enter a stock symbol.');
      return;
    }

    final normalized = trimmed.toUpperCase();

    state = state.copyWith(
      symbol: normalized,
      isLoading: true,
      error: null,
    );

    try {
      final history = await ApiService.getStockStrategyHistory(
        normalized,
        limit: limit,
      );

      state = state.copyWith(
        symbol: normalized,
        history: history,
        isLoading: false,
        error: null,
      );
    } catch (e) {
      state = state.copyWith(
        history: null,
        isLoading: false,
        error: e.toString(),
      );
    }
  }

  Future<void> refresh() async {
    final symbol = state.symbol;
    if (symbol == null || symbol.isEmpty) {
      return;
    }
    await fetchStrategyHistory(symbol);
  }

  void clearError() {
    state = state.copyWith(error: null);
  }

  void clear() {
    state = const StrategyHistoryState();
  }
}

final strategyHistoryProvider =
    StateNotifierProvider<StrategyHistoryController, StrategyHistoryState>((ref) {
  return StrategyHistoryController();
});
