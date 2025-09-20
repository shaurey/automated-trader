class HoldingsSummary {
  final double? totalValue;
  final double? totalCostBasis;
  final double? totalGainLoss;
  final double? totalGainLossPercent;
  final List<AccountSummary> accounts;
  final List<TopHolding> topHoldings;
  final List<SectorAllocation> sectorAllocation;
  final List<StyleAllocation> styleAllocation;

  HoldingsSummary({
    required this.totalValue,
    required this.totalCostBasis,
    required this.totalGainLoss,
    required this.totalGainLossPercent,
    required this.accounts,
    required this.topHoldings,
    required this.sectorAllocation,
    required this.styleAllocation,
  });

  static double? _numOrNull(dynamic v) {
    if (v == null) return null;
    if (v is num) return v.toDouble();
    return double.tryParse(v.toString());
  }

  factory HoldingsSummary.fromJson(Map<String, dynamic> json) {
    final accountsRaw = json['accounts'];
    final topRaw = json['top_holdings'];
    final sectorRaw = json['sector_allocation'];
    final styleRaw = json['style_allocation'];
    return HoldingsSummary(
      totalValue: _numOrNull(json['total_value']),
      totalCostBasis: _numOrNull(json['total_cost_basis']),
      totalGainLoss: _numOrNull(json['total_gain_loss']),
      totalGainLossPercent: _numOrNull(json['total_gain_loss_percent']),
      accounts: accountsRaw is List
          ? accountsRaw.map((a) => AccountSummary.fromJson(a)).toList()
          : <AccountSummary>[],
      topHoldings: topRaw is List
          ? topRaw.map((h) => TopHolding.fromJson(h)).toList()
          : <TopHolding>[],
      sectorAllocation: sectorRaw is List
          ? sectorRaw.map((s) => SectorAllocation.fromJson(s)).toList()
          : <SectorAllocation>[],
      styleAllocation: styleRaw is List
          ? styleRaw.map((s) => StyleAllocation.fromJson(s)).toList()
          : <StyleAllocation>[],
    );
  }
}

class AccountSummary {
  final String account;
  final double? value;
  final double? costBasis;
  final double? gainLoss;
  final double? gainLossPercent;
  final int positionsCount;

  AccountSummary({
    required this.account,
    required this.value,
    required this.costBasis,
    required this.gainLoss,
    required this.gainLossPercent,
    required this.positionsCount,
  });

  static double? _num(dynamic v) => (v is num) ? v.toDouble() : (v == null ? null : double.tryParse(v.toString()));

  factory AccountSummary.fromJson(Map<String, dynamic> json) {
    return AccountSummary(
      account: json['account'] as String? ?? 'UNKNOWN',
      value: _num(json['value']),
      costBasis: _num(json['cost_basis']),
      gainLoss: _num(json['gain_loss']),
      gainLossPercent: _num(json['gain_loss_percent']),
      positionsCount: (json['positions_count'] as int?) ?? 0,
    );
  }
}

class TopHolding {
  final String ticker;
  final String? companyName;
  final double quantity;
  final double? currentPrice;
  final double? marketValue;
  final double? costBasis;
  final double? gainLoss;
  final double? gainLossPercent;
  final double? weight;

  TopHolding({
    required this.ticker,
    required this.companyName,
    required this.quantity,
    required this.currentPrice,
    required this.marketValue,
    required this.costBasis,
    required this.gainLoss,
    required this.gainLossPercent,
    required this.weight,
  });

  static double? _num(dynamic v) => (v is num) ? v.toDouble() : (v == null ? null : double.tryParse(v.toString()));

  factory TopHolding.fromJson(Map<String, dynamic> json) {
    return TopHolding(
      ticker: json['ticker'] as String? ?? 'UNKNOWN',
      companyName: json['company_name'] as String?,
      quantity: _num(json['quantity']) ?? 0.0,
      currentPrice: _num(json['current_price']),
      marketValue: _num(json['market_value']),
      costBasis: _num(json['cost_basis']),
      gainLoss: _num(json['gain_loss']),
      gainLossPercent: _num(json['gain_loss_percent']),
      weight: _num(json['weight']),
    );
  }
}

class SectorAllocation {
  final String sector;
  final double? value;
  final double? weight;

  SectorAllocation({
    required this.sector,
    required this.value,
    required this.weight,
  });

  static double? _num(dynamic v) => (v is num) ? v.toDouble() : (v == null ? null : double.tryParse(v.toString()));

  factory SectorAllocation.fromJson(Map<String, dynamic> json) {
    return SectorAllocation(
      sector: json['sector'] as String? ?? 'Unknown',
      value: _num(json['value']),
      weight: _num(json['weight']),
    );
  }
}

class StyleAllocation {
  final String styleCategory;
  final double? value;
  final double? weight;

  StyleAllocation({
    required this.styleCategory,
    required this.value,
    required this.weight,
  });

  static double? _num(dynamic v) => (v is num) ? v.toDouble() : (v == null ? null : double.tryParse(v.toString()));

  factory StyleAllocation.fromJson(Map<String, dynamic> json) {
    return StyleAllocation(
      styleCategory: json['style_category'] as String? ?? 'Unknown',
      value: _num(json['value']),
      weight: _num(json['weight']),
    );
  }
}

class PositionsResponse {
  final List<Position> positions;

  PositionsResponse({required this.positions});

  factory PositionsResponse.fromJson(Map<String, dynamic> json) {
    return PositionsResponse(
      positions: (json['positions'] as List)
          .map((position) => Position.fromJson(position))
          .toList(),
    );
  }
}

class Position {
  final int? holdingId;
  final String account;
  final String ticker;
  final String? companyName;
  final double quantity;
  final double? costBasis;
  final double? currentPrice;
  final double? marketValue;
  final double? unrealizedGainLoss;
  final double? unrealizedGainLossPercent;
  final String? styleCategory;
  final String? industry;
  final String? currency;
  final DateTime? openedAt;
  final DateTime? lastUpdate;

  Position({
    required this.holdingId,
    required this.account,
    required this.ticker,
    required this.companyName,
    required this.quantity,
    required this.costBasis,
    required this.currentPrice,
    required this.marketValue,
    required this.unrealizedGainLoss,
    required this.unrealizedGainLossPercent,
    required this.styleCategory,
    required this.industry,
    required this.currency,
    required this.openedAt,
    required this.lastUpdate,
  });

  static double? _num(dynamic v) => (v is num) ? v.toDouble() : (v == null ? null : double.tryParse(v.toString()));

  static DateTime? _dt(dynamic v) {
    if (v == null) return null;
    try { return DateTime.parse(v as String); } catch (_) { return null; }
  }

  factory Position.fromJson(Map<String, dynamic> json) {
    return Position(
      holdingId: json['holding_id'] as int?,
      account: json['account'] as String? ?? 'UNKNOWN',
      ticker: json['ticker'] as String? ?? 'UNKNOWN',
      companyName: json['company_name'] as String?,
      quantity: _num(json['quantity']) ?? 0.0,
      costBasis: _num(json['cost_basis']),
      currentPrice: _num(json['current_price']),
      marketValue: _num(json['market_value']),
      unrealizedGainLoss: _num(json['unrealized_gain_loss']),
      unrealizedGainLossPercent: _num(json['unrealized_gain_loss_percent']),
      styleCategory: json['style_category'] as String?,
      industry: json['industry'] as String?,
      currency: json['currency'] as String?,
      openedAt: _dt(json['opened_at']),
      lastUpdate: _dt(json['last_update']),
    );
  }
}

// Holdings Import Models
class DetectedAccount {
  final String accountNumber;
  final String? accountName;
  final int recordCount;
  final List<String> sampleTickers;

  DetectedAccount({
    required this.accountNumber,
    this.accountName,
    required this.recordCount,
    required this.sampleTickers,
  });

  factory DetectedAccount.fromJson(Map<String, dynamic> json) {
    return DetectedAccount(
      accountNumber: json['account_number'] as String? ?? '',
      accountName: json['account_name'] as String?,
      recordCount: json['record_count'] as int? ?? 0,
      sampleTickers: (json['sample_tickers'] as List?)
          ?.map((ticker) => ticker.toString())
          .toList() ?? [],
    );
  }
}

class ImportedHoldingRecord {
  final String ticker;
  final String accountNumber;
  final String? accountName;
  final double quantity;
  final double costBasis;
  final double? currentValue;
  final int rowNumber;
  final String status;
  final String? errorMessage;

  ImportedHoldingRecord({
    required this.ticker,
    required this.accountNumber,
    this.accountName,
    required this.quantity,
    required this.costBasis,
    this.currentValue,
    required this.rowNumber,
    this.status = 'success',
    this.errorMessage,
  });

  factory ImportedHoldingRecord.fromJson(Map<String, dynamic> json) {
    return ImportedHoldingRecord(
      ticker: json['ticker'] as String? ?? '',
      accountNumber: json['account_number'] as String? ?? '',
      accountName: json['account_name'] as String?,
      quantity: (json['quantity'] as num?)?.toDouble() ?? 0.0,
      costBasis: (json['cost_basis'] as num?)?.toDouble() ?? 0.0,
      currentValue: (json['current_value'] as num?)?.toDouble(),
      rowNumber: json['row_number'] as int? ?? 0,
      status: json['status'] as String? ?? 'success',
      errorMessage: json['error_message'] as String?,
    );
  }
}

class AccountImportSummary {
  final String accountNumber;
  final String? accountName;
  final int totalRowsProcessed;
  final int recordsImported;
  final int recordsSkipped;
  final int recordsFailed;
  final int existingHoldingsDeleted;
  final bool importSuccessful;

  AccountImportSummary({
    required this.accountNumber,
    this.accountName,
    required this.totalRowsProcessed,
    required this.recordsImported,
    required this.recordsSkipped,
    required this.recordsFailed,
    required this.existingHoldingsDeleted,
    required this.importSuccessful,
  });

  factory AccountImportSummary.fromJson(Map<String, dynamic> json) {
    return AccountImportSummary(
      accountNumber: json['account_number'] as String? ?? '',
      accountName: json['account_name'] as String?,
      totalRowsProcessed: json['total_rows_processed'] as int? ?? 0,
      recordsImported: json['records_imported'] as int? ?? 0,
      recordsSkipped: json['records_skipped'] as int? ?? 0,
      recordsFailed: json['records_failed'] as int? ?? 0,
      existingHoldingsDeleted: json['existing_holdings_deleted'] as int? ?? 0,
      importSuccessful: json['import_successful'] as bool? ?? false,
    );
  }
}

class HoldingsImportSummary {
  final int totalRowsProcessed;
  final int totalAccountsDetected;
  final int totalRecordsImported;
  final int totalRecordsSkipped;
  final int totalRecordsFailed;
  final int totalExistingHoldingsDeleted;
  final bool importSuccessful;
  final List<AccountImportSummary> accountSummaries;

  HoldingsImportSummary({
    required this.totalRowsProcessed,
    required this.totalAccountsDetected,
    required this.totalRecordsImported,
    required this.totalRecordsSkipped,
    required this.totalRecordsFailed,
    required this.totalExistingHoldingsDeleted,
    required this.importSuccessful,
    required this.accountSummaries,
  });

  factory HoldingsImportSummary.fromJson(Map<String, dynamic> json) {
    return HoldingsImportSummary(
      totalRowsProcessed: json['total_rows_processed'] as int? ?? 0,
      totalAccountsDetected: json['total_accounts_detected'] as int? ?? 0,
      totalRecordsImported: json['total_records_imported'] as int? ?? 0,
      totalRecordsSkipped: json['total_records_skipped'] as int? ?? 0,
      totalRecordsFailed: json['total_records_failed'] as int? ?? 0,
      totalExistingHoldingsDeleted: json['total_existing_holdings_deleted'] as int? ?? 0,
      importSuccessful: json['import_successful'] as bool? ?? false,
      accountSummaries: (json['account_summaries'] as List?)
          ?.map((summary) => AccountImportSummary.fromJson(summary))
          .toList() ?? [],
    );
  }
}

class HoldingsImportResponse {
  final List<DetectedAccount> detectedAccounts;
  final HoldingsImportSummary importSummary;
  final List<ImportedHoldingRecord> importedRecords;
  final List<String> errors;
  final List<String> warnings;
  final DateTime timestamp;

  HoldingsImportResponse({
    required this.detectedAccounts,
    required this.importSummary,
    required this.importedRecords,
    required this.errors,
    required this.warnings,
    required this.timestamp,
  });

  factory HoldingsImportResponse.fromJson(Map<String, dynamic> json) {
    return HoldingsImportResponse(
      detectedAccounts: (json['detected_accounts'] as List?)
          ?.map((account) => DetectedAccount.fromJson(account))
          .toList() ?? [],
      importSummary: HoldingsImportSummary.fromJson(
        json['import_summary'] as Map<String, dynamic>? ?? {},
      ),
      importedRecords: (json['imported_records'] as List?)
          ?.map((record) => ImportedHoldingRecord.fromJson(record))
          .toList() ?? [],
      errors: (json['errors'] as List?)
          ?.map((error) => error.toString())
          .toList() ?? [],
      warnings: (json['warnings'] as List?)
          ?.map((warning) => warning.toString())
          .toList() ?? [],
      timestamp: json['timestamp'] != null
          ? DateTime.parse(json['timestamp'] as String)
          : DateTime.now(),
    );
  }
}