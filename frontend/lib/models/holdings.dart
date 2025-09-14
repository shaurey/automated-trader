class HoldingsSummary {
  final double? totalValue;
  final double? totalCostBasis;
  final double? totalGainLoss;
  final double? totalGainLossPercent;
  final List<AccountSummary> accounts;
  final List<TopHolding> topHoldings;
  final List<SectorAllocation> sectorAllocation;

  HoldingsSummary({
    required this.totalValue,
    required this.totalCostBasis,
    required this.totalGainLoss,
    required this.totalGainLossPercent,
    required this.accounts,
    required this.topHoldings,
    required this.sectorAllocation,
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
  final String? sector;
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
    required this.sector,
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
      sector: json['sector'] as String?,
      industry: json['industry'] as String?,
      currency: json['currency'] as String?,
      openedAt: _dt(json['opened_at']),
      lastUpdate: _dt(json['last_update']),
    );
  }
}