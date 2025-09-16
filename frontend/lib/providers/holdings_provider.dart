import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/holdings.dart';
import '../services/api_service.dart';

// Holdings Summary Provider
final holdingsSummaryProvider = FutureProvider<HoldingsSummary>((ref) async {
  return await ApiService.getHoldingsSummary();
});

// Positions Provider with optional filters
final positionsProvider = FutureProvider.family<PositionsResponse, PositionsFilter>((ref, filter) async {
  return await ApiService.getPositions(
    account: filter.account,
    ticker: filter.ticker,
    limit: filter.limit,
  );
});

// Instruments Provider
final instrumentsProvider = FutureProvider.family<Map<String, dynamic>, InstrumentsFilter>((ref, filter) async {
  return await ApiService.getInstruments(
    page: filter.page,
    size: filter.size,
    ticker: filter.ticker,
    sector: filter.sector,
    instrumentType: filter.instrumentType,
  );
});

// Health Check Provider
final healthCheckProvider = FutureProvider<Map<String, dynamic>>((ref) async {
  return await ApiService.healthCheck();
});

// Selected filters state providers
final selectedAccountProvider = StateProvider<String?>((ref) => null);
final selectedStyleProvider = StateProvider<String?>((ref) => null);
final searchQueryProvider = StateProvider<String>((ref) => '');
final sortModeProvider = StateProvider<SortMode>((ref) => SortMode.valueDesc);

// Accounts list provider
final accountsProvider = FutureProvider<List<String>>((ref) async {
  try {
    final accounts = await ApiService.getAccounts();
    return accounts;
  } catch (e) {
    // Return empty list on failure to keep UI functional
    return [];
  }
});

// Filtered positions provider that combines positions with filters
final filteredPositionsProvider = Provider<AsyncValue<List<Position>>>((ref) {
  final positionsAsync = ref.watch(positionsProvider(const PositionsFilter()));
  final selectedAccount = ref.watch(selectedAccountProvider);
  final selectedStyle = ref.watch(selectedStyleProvider);
  final searchQuery = ref.watch(searchQueryProvider);
  final sortMode = ref.watch(sortModeProvider);

  return positionsAsync.when(
    data: (positionsResponse) {
      var positions = positionsResponse.positions;

      // Apply filters
      if (selectedAccount != null && selectedAccount.isNotEmpty) {
        positions = positions.where((p) => p.account == selectedAccount).toList();
      }

      if (selectedStyle != null && selectedStyle.isNotEmpty) {
        positions = positions.where((p) => p.styleCategory == selectedStyle).toList();
      }

      if (searchQuery.isNotEmpty) {
        final query = searchQuery.toLowerCase();
        positions = positions.where((p) {
          final comp = p.companyName?.toLowerCase() ?? '';
            return p.ticker.toLowerCase().contains(query) || comp.contains(query);
        }).toList();
      }

      // Apply sorting
      double _nv(double? v) => v ?? 0.0;
      switch (sortMode) {
        case SortMode.valueDesc:
          positions.sort((a, b) => _nv(b.marketValue).compareTo(_nv(a.marketValue)));
          break;
        case SortMode.valueAsc:
          positions.sort((a, b) => _nv(a.marketValue).compareTo(_nv(b.marketValue)));
          break;
        case SortMode.gainLossDesc:
          positions.sort((a, b) => _nv(b.unrealizedGainLoss).compareTo(_nv(a.unrealizedGainLoss)));
          break;
        case SortMode.gainLossAsc:
          positions.sort((a, b) => _nv(a.unrealizedGainLoss).compareTo(_nv(b.unrealizedGainLoss)));
          break;
        case SortMode.ticker:
          positions.sort((a, b) => a.ticker.compareTo(b.ticker));
          break;
      }

      return AsyncValue.data(positions);
    },
    loading: () => const AsyncValue.loading(),
    error: (error, stackTrace) => AsyncValue.error(error, stackTrace),
  );
});

// Refresh provider to trigger data refresh
final refreshProvider = StateProvider<int>((ref) => 0);

// Auto-refresh provider (refreshes every 30 seconds)
final autoRefreshProvider = StreamProvider<int>((ref) {
  return Stream.periodic(const Duration(seconds: 30), (count) => count);
});

// Provider that triggers refresh when auto-refresh emits
final refreshTriggerProvider = Provider<void>((ref) {
  ref.listen(autoRefreshProvider, (previous, next) {
    next.whenData((value) {
      // Invalidate providers to trigger refresh
      ref.invalidate(holdingsSummaryProvider);
      ref.invalidate(positionsProvider);
    });
  });
});

// Filter classes
class PositionsFilter {
  final String? account;
  final String? ticker;
  final int? limit;

  const PositionsFilter({
    this.account,
    this.ticker,
    this.limit,
  });
}

class InstrumentsFilter {
  final int? page;
  final int? size;
  final String? ticker;
  final String? sector;
  final String? instrumentType;

  const InstrumentsFilter({
    this.page,
    this.size,
    this.ticker,
    this.sector,
    this.instrumentType,
  });
}

enum SortMode {
  valueDesc,
  valueAsc,
  gainLossDesc,
  gainLossAsc,
  ticker,
}

extension SortModeExtension on SortMode {
  String get displayName {
    switch (this) {
      case SortMode.valueDesc:
        return 'Value (High to Low)';
      case SortMode.valueAsc:
        return 'Value (Low to High)';
      case SortMode.gainLossDesc:
        return 'Gain/Loss (High to Low)';
      case SortMode.gainLossAsc:
        return 'Gain/Loss (Low to High)';
      case SortMode.ticker:
        return 'Ticker (A-Z)';
    }
  }
}