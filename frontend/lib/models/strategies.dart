class StrategyMetrics {
  final double? close;
  final double? score;
  final double? changePct;
  final double? rsi14;
  final double? macd;
  final double? macdSignal;
  final double? macdHist;
  final double? sma10;
  final double? sma50;
  final double? sma200;
  final bool? sma10Above;
  final bool? sma50Above;
  final bool? sma200Above;
  final int? volume;
  final int? volAvg20;
  final double? volumeMultiple;
  final double? volContinuityRatio;
  final double? refHigh;
  final double? breakoutPct;
  final double? extensionPct;
  final double? breakoutMoveAtr;
  final String? risk;
  final String? recommendation;
  final String? entryQuality;
  final double? suggestedStop;
  final double? atr14;
  final int? pointsSma;
  final int? pointsMacd;
  final int? pointsRsi;
  final int? pointsVolume;
  final int? pointsHigh;
  final int? extraScore;

  StrategyMetrics({
    this.close,
    this.score,
    this.changePct,
    this.rsi14,
    this.macd,
    this.macdSignal,
    this.macdHist,
    this.sma10,
    this.sma50,
    this.sma200,
    this.sma10Above,
    this.sma50Above,
    this.sma200Above,
    this.volume,
    this.volAvg20,
    this.volumeMultiple,
    this.volContinuityRatio,
    this.refHigh,
    this.breakoutPct,
    this.extensionPct,
    this.breakoutMoveAtr,
    this.risk,
    this.recommendation,
    this.entryQuality,
    this.suggestedStop,
    this.atr14,
    this.pointsSma,
    this.pointsMacd,
    this.pointsRsi,
    this.pointsVolume,
    this.pointsHigh,
    this.extraScore,
  });

  static double? _num(dynamic v) => (v is num) ? v.toDouble() : (v == null ? null : double.tryParse(v.toString()));
  static int? _int(dynamic v) => (v is int) ? v : (v == null ? null : int.tryParse(v.toString()));
  static bool? _bool(dynamic v) => (v is bool) ? v : (v == null ? null : v.toString().toLowerCase() == 'true');

  factory StrategyMetrics.fromJson(Map<String, dynamic> json) {
    return StrategyMetrics(
      close: _num(json['close']),
      score: _num(json['score']),
      changePct: _num(json['change_pct']),
      rsi14: _num(json['rsi14']),
      macd: _num(json['macd']),
      macdSignal: _num(json['macd_signal']),
      macdHist: _num(json['macd_hist']),
      sma10: _num(json['sma10']),
      sma50: _num(json['sma50']),
      sma200: _num(json['sma200']),
      sma10Above: _bool(json['sma10_above']),
      sma50Above: _bool(json['sma50_above']),
      sma200Above: _bool(json['sma200_above']),
      volume: _int(json['volume']),
      volAvg20: _int(json['vol_avg20']),
      volumeMultiple: _num(json['volume_multiple']),
      volContinuityRatio: _num(json['vol_continuity_ratio']),
      refHigh: _num(json['ref_high']),
      breakoutPct: _num(json['breakout_pct']),
      extensionPct: _num(json['extension_pct']),
      breakoutMoveAtr: _num(json['breakout_move_atr']),
      risk: json['risk'] as String?,
      recommendation: json['recommendation'] as String?,
      entryQuality: json['entry_quality'] as String?,
      suggestedStop: _num(json['suggested_stop']),
      atr14: _num(json['atr14']),
      pointsSma: _int(json['points_sma']),
      pointsMacd: _int(json['points_macd']),
      pointsRsi: _int(json['points_rsi']),
      pointsVolume: _int(json['points_volume']),
      pointsHigh: _int(json['points_high']),
      extraScore: _int(json['extra_score']),
    );
  }
}

class StrategyResult {
  final String runId;
  final String strategyCode;
  final String ticker;
  final bool passed;
  final double? score;
  final String? classification;
  final List<String> reasons;
  final StrategyMetrics metrics;
  final String createdAt;
  final String? companyName;
  final String? sector;
  final String? industry;
  final String instrumentType;

  StrategyResult({
    required this.runId,
    required this.strategyCode,
    required this.ticker,
    required this.passed,
    required this.score,
    required this.classification,
    required this.reasons,
    required this.metrics,
    required this.createdAt,
    this.companyName,
    this.sector,
    this.industry,
    required this.instrumentType,
  });

  static double? _num(dynamic v) => (v is num) ? v.toDouble() : (v == null ? null : double.tryParse(v.toString()));

  factory StrategyResult.fromJson(Map<String, dynamic> json) {
    final reasonsRaw = json['reasons'];
    final metricsRaw = json['metrics'] ?? {};
    
    return StrategyResult(
      runId: json['run_id'] as String? ?? '',
      strategyCode: json['strategy_code'] as String? ?? '',
      ticker: json['ticker'] as String? ?? '',
      passed: json['passed'] as bool? ?? false,
      score: _num(json['score']),
      classification: json['classification'] as String?,
      reasons: reasonsRaw is List ? reasonsRaw.cast<String>() : <String>[],
      metrics: StrategyMetrics.fromJson(metricsRaw),
      createdAt: json['created_at'] as String? ?? '',
      companyName: json['company_name'] as String?,
      sector: json['sector'] as String?,
      industry: json['industry'] as String?,
      instrumentType: json['instrument_type'] as String? ?? 'stock',
    );
  }
}

class StrategyRunSummary {
  final String runId;
  final String strategyCode;
  final String startedAt;
  final String? completedAt;
  final int? universeSize;
  final int? passedCount;
  final double? passRate;
  final double? avgScore;
  final int? durationMs;
  final String? exitStatus;

  StrategyRunSummary({
    required this.runId,
    required this.strategyCode,
    required this.startedAt,
    this.completedAt,
    this.universeSize,
    this.passedCount,
    this.passRate,
    this.avgScore,
    this.durationMs,
    this.exitStatus,
  });

  static double? _num(dynamic v) => (v is num) ? v.toDouble() : (v == null ? null : double.tryParse(v.toString()));
  static int? _int(dynamic v) => (v is int) ? v : (v == null ? null : int.tryParse(v.toString()));

  factory StrategyRunSummary.fromJson(Map<String, dynamic> json) {
    return StrategyRunSummary(
      runId: json['run_id'] as String? ?? '',
      strategyCode: json['strategy_code'] as String? ?? '',
      startedAt: json['started_at'] as String? ?? '',
      completedAt: json['completed_at'] as String?,
      universeSize: _int(json['universe_size']),
      passedCount: _int(json['passed_count']),
      passRate: _num(json['pass_rate']),
      avgScore: _num(json['avg_score']),
      durationMs: _int(json['duration_ms']),
      exitStatus: json['exit_status'] as String?,
    );
  }
}

class StrategyRunDetail {
  final String runId;
  final String strategyCode;
  final String version;
  final String paramsHash;
  final String paramsJson;
  final String startedAt;
  final String? completedAt;
  final String? universeSource;
  final int? universeSize;
  final int? minScore;
  final String? exitStatus;
  final int? durationMs;
  final int? passedCount;
  final int? totalResults;
  final double? passRate;
  final double? avgScore;
  final double? maxScore;
  final double? minScoreActual;
  final Map<String, int>? scoreRanges;
  final List<StrategyResult> topResults;

  StrategyRunDetail({
    required this.runId,
    required this.strategyCode,
    required this.version,
    required this.paramsHash,
    required this.paramsJson,
    required this.startedAt,
    this.completedAt,
    this.universeSource,
    this.universeSize,
    this.minScore,
    this.exitStatus,
    this.durationMs,
    this.passedCount,
    this.totalResults,
    this.passRate,
    this.avgScore,
    this.maxScore,
    this.minScoreActual,
    this.scoreRanges,
    required this.topResults,
  });

  static double? _num(dynamic v) => (v is num) ? v.toDouble() : (v == null ? null : double.tryParse(v.toString()));
  static int? _int(dynamic v) => (v is int) ? v : (v == null ? null : int.tryParse(v.toString()));

  factory StrategyRunDetail.fromJson(Map<String, dynamic> json) {
    final topResultsRaw = json['top_results'];
    final scoreRangesRaw = json['score_ranges'];
    
    return StrategyRunDetail(
      runId: json['run_id'] as String? ?? '',
      strategyCode: json['strategy_code'] as String? ?? '',
      version: json['version'] as String? ?? '',
      paramsHash: json['params_hash'] as String? ?? '',
      paramsJson: json['params_json'] as String? ?? '',
      startedAt: json['started_at'] as String? ?? '',
      completedAt: json['completed_at'] as String?,
      universeSource: json['universe_source'] as String?,
      universeSize: _int(json['universe_size']),
      minScore: _int(json['min_score']),
      exitStatus: json['exit_status'] as String?,
      durationMs: _int(json['duration_ms']),
      passedCount: _int(json['passed_count']),
      totalResults: _int(json['total_results']),
      passRate: _num(json['pass_rate']),
      avgScore: _num(json['avg_score']),
      maxScore: _num(json['max_score']),
      minScoreActual: _num(json['min_score_actual']),
      scoreRanges: scoreRangesRaw is Map<String, dynamic> 
          ? scoreRangesRaw.map((k, v) => MapEntry(k, v is int ? v : int.tryParse(v.toString()) ?? 0))
          : null,
      topResults: topResultsRaw is List
          ? topResultsRaw.map((r) => StrategyResult.fromJson(r)).toList()
          : <StrategyResult>[],
    );
  }
}

class StrategyRunsResponse {
  final List<StrategyRunSummary> runs;
  final int totalCount;
  final int page;
  final int pageSize;
  final Map<String, dynamic>? strategyStats;

  StrategyRunsResponse({
    required this.runs,
    required this.totalCount,
    required this.page,
    required this.pageSize,
    this.strategyStats,
  });

  factory StrategyRunsResponse.fromJson(Map<String, dynamic> json) {
    final runsRaw = json['runs'];
    return StrategyRunsResponse(
      runs: runsRaw is List
          ? runsRaw.map((r) => StrategyRunSummary.fromJson(r)).toList()
          : <StrategyRunSummary>[],
      totalCount: json['total_count'] as int? ?? 0,
      page: json['page'] as int? ?? 1,
      pageSize: json['page_size'] as int? ?? 20,
      strategyStats: json['strategy_stats'] as Map<String, dynamic>?,
    );
  }
}

class StrategyResultsResponse {
  final String runId;
  final String strategyCode;
  final List<StrategyResult> results;
  final int totalCount;
  final int passedCount;
  final int failedCount;
  final int page;
  final int pageSize;
  final Map<String, dynamic> summary;

  StrategyResultsResponse({
    required this.runId,
    required this.strategyCode,
    required this.results,
    required this.totalCount,
    required this.passedCount,
    required this.failedCount,
    required this.page,
    required this.pageSize,
    required this.summary,
  });

  factory StrategyResultsResponse.fromJson(Map<String, dynamic> json) {
    final resultsRaw = json['results'];
    return StrategyResultsResponse(
      runId: json['run_id'] as String? ?? '',
      strategyCode: json['strategy_code'] as String? ?? '',
      results: resultsRaw is List
          ? resultsRaw.map((r) => StrategyResult.fromJson(r)).toList()
          : <StrategyResult>[],
      totalCount: json['total_count'] as int? ?? 0,
      passedCount: json['passed_count'] as int? ?? 0,
      failedCount: json['failed_count'] as int? ?? 0,
      page: json['page'] as int? ?? 1,
      pageSize: json['page_size'] as int? ?? 50,
      summary: json['summary'] as Map<String, dynamic>? ?? {},
    );
  }
}

class StrategyLatestResponse {
  final List<StrategyRunDetail> latestRuns;
  final List<String> strategies;
  final int totalStrategies;

  StrategyLatestResponse({
    required this.latestRuns,
    required this.strategies,
    required this.totalStrategies,
  });

  factory StrategyLatestResponse.fromJson(Map<String, dynamic> json) {
    final latestRunsRaw = json['latest_runs'];
    final strategiesRaw = json['strategies'];
    
    return StrategyLatestResponse(
      latestRuns: latestRunsRaw is List
          ? latestRunsRaw.map((r) => StrategyRunDetail.fromJson(r)).toList()
          : <StrategyRunDetail>[],
      strategies: strategiesRaw is List
          ? strategiesRaw.cast<String>()
          : <String>[],
      totalStrategies: json['total_strategies'] as int? ?? 0,
    );
  }
}

// Strategy Execution Models for Real-Time Progress Tracking

enum ExecutionState {
  queued,
  starting,
  running,
  completing,
  completed,
  cancelled,
  error,
}

extension ExecutionStateExtension on ExecutionState {
  String get value {
    switch (this) {
      case ExecutionState.queued:
        return 'queued';
      case ExecutionState.starting:
        return 'starting';
      case ExecutionState.running:
        return 'running';
      case ExecutionState.completing:
        return 'completing';
      case ExecutionState.completed:
        return 'completed';
      case ExecutionState.cancelled:
        return 'cancelled';
      case ExecutionState.error:
        return 'error';
    }
  }

  static ExecutionState fromString(String value) {
    switch (value.toLowerCase()) {
      case 'queued':
        return ExecutionState.queued;
      case 'starting':
        return ExecutionState.starting;
      case 'running':
        return ExecutionState.running;
      case 'completing':
        return ExecutionState.completing;
      case 'completed':
        return ExecutionState.completed;
      case 'cancelled':
        return ExecutionState.cancelled;
      case 'error':
        return ExecutionState.error;
      default:
        return ExecutionState.error;
    }
  }
}

enum ProgressEventType {
  started,
  progress,
  tickerCompleted,
  stageCompleted,
  completed,
  error,
  cancelled,
}

extension ProgressEventTypeExtension on ProgressEventType {
  String get value {
    switch (this) {
      case ProgressEventType.started:
        return 'started';
      case ProgressEventType.progress:
        return 'progress';
      case ProgressEventType.tickerCompleted:
        return 'ticker_completed';
      case ProgressEventType.stageCompleted:
        return 'stage_completed';
      case ProgressEventType.completed:
        return 'completed';
      case ProgressEventType.error:
        return 'error';
      case ProgressEventType.cancelled:
        return 'cancelled';
    }
  }

  static ProgressEventType fromString(String value) {
    switch (value.toLowerCase()) {
      case 'started':
        return ProgressEventType.started;
      case 'progress':
        return ProgressEventType.progress;
      case 'ticker_completed':
        return ProgressEventType.tickerCompleted;
      case 'stage_completed':
        return ProgressEventType.stageCompleted;
      case 'completed':
        return ProgressEventType.completed;
      case 'error':
        return ProgressEventType.error;
      case 'cancelled':
        return ProgressEventType.cancelled;
      default:
        return ProgressEventType.error;
    }
  }
}

class ExecutionOptions {
  final String priority;
  final bool notifyOnCompletion;
  final int? maxExecutionTime;

  ExecutionOptions({
    this.priority = 'normal',
    this.notifyOnCompletion = false,
    this.maxExecutionTime,
  });

  Map<String, dynamic> toJson() {
    return {
      'priority': priority,
      'notify_on_completion': notifyOnCompletion,
      if (maxExecutionTime != null) 'max_execution_time': maxExecutionTime,
    };
  }

  factory ExecutionOptions.fromJson(Map<String, dynamic> json) {
    return ExecutionOptions(
      priority: json['priority'] as String? ?? 'normal',
      notifyOnCompletion: json['notify_on_completion'] as bool? ?? false,
      maxExecutionTime: json['max_execution_time'] as int?,
    );
  }
}

class StrategyExecutionRequest {
  final String strategyCode;
  final Map<String, dynamic> parameters;
  final ExecutionOptions? options;

  StrategyExecutionRequest({
    required this.strategyCode,
    required this.parameters,
    this.options,
  });

  Map<String, dynamic> toJson() {
    return {
      'strategy_code': strategyCode,
      'parameters': parameters,
      if (options != null) 'options': options!.toJson(),
    };
  }

  factory StrategyExecutionRequest.fromJson(Map<String, dynamic> json) {
    return StrategyExecutionRequest(
      strategyCode: json['strategy_code'] as String,
      parameters: json['parameters'] as Map<String, dynamic>,
      options: json['options'] != null
          ? ExecutionOptions.fromJson(json['options'])
          : null,
    );
  }
}

class StrategyExecutionResponse {
  final String runId;
  final ExecutionState status;
  final String message;
  final String strategyCode;
  final int totalTickers;
  final String executionStartedAt;

  StrategyExecutionResponse({
    required this.runId,
    required this.status,
    required this.message,
    required this.strategyCode,
    required this.totalTickers,
    required this.executionStartedAt,
  });

  factory StrategyExecutionResponse.fromJson(Map<String, dynamic> json) {
    return StrategyExecutionResponse(
      runId: json['run_id'] as String,
      status: ExecutionStateExtension.fromString(json['status'] as String),
      message: json['message'] as String,
      strategyCode: json['strategy_code'] as String,
      totalTickers: json['total_tickers'] as int,
      executionStartedAt: json['execution_started_at'] as String,
    );
  }
}

class ProgressEvent {
  final ProgressEventType eventType;
  final DateTime timestamp;
  final String runId;
  final String? stage;
  final double? progressPercent;
  final String? currentItem;
  final int? totalItems;
  final int? completedItems;
  final String message;
  final Map<String, dynamic>? metrics;

  ProgressEvent({
    required this.eventType,
    required this.timestamp,
    required this.runId,
    this.stage,
    this.progressPercent,
    this.currentItem,
    this.totalItems,
    this.completedItems,
    required this.message,
    this.metrics,
  });

  factory ProgressEvent.fromJson(Map<String, dynamic> json) {
    return ProgressEvent(
      eventType: ProgressEventTypeExtension.fromString(json['event_type'] as String),
      timestamp: DateTime.parse(json['timestamp'] as String),
      runId: json['run_id'] as String,
      stage: json['stage'] as String?,
      progressPercent: (json['progress_percent'] as num?)?.toDouble(),
      currentItem: json['current_item'] as String?,
      totalItems: json['total_items'] as int?,
      completedItems: json['completed_items'] as int?,
      message: json['message'] as String,
      metrics: json['metrics'] as Map<String, dynamic>?,
    );
  }
}

class ExecutionStatus {
  final String runId;
  final ExecutionState status;
  final double? progressPercent;
  final String? currentStage;
  final String? startedAt;
  final String? estimatedCompletion;
  final bool canCancel;
  final Map<String, dynamic>? metrics;

  ExecutionStatus({
    required this.runId,
    required this.status,
    this.progressPercent,
    this.currentStage,
    this.startedAt,
    this.estimatedCompletion,
    required this.canCancel,
    this.metrics,
  });

  factory ExecutionStatus.fromJson(Map<String, dynamic> json) {
    return ExecutionStatus(
      runId: json['run_id'] as String,
      status: ExecutionStateExtension.fromString(json['status'] as String),
      progressPercent: (json['progress_percent'] as num?)?.toDouble(),
      currentStage: json['current_stage'] as String?,
      startedAt: json['started_at'] as String?,
      estimatedCompletion: json['estimated_completion'] as String?,
      canCancel: json['can_cancel'] as bool? ?? false,
      metrics: json['metrics'] as Map<String, dynamic>?,
    );
  }
}

class ExecutionCancelResponse {
  final bool cancelled;
  final String message;

  ExecutionCancelResponse({
    required this.cancelled,
    required this.message,
  });

  factory ExecutionCancelResponse.fromJson(Map<String, dynamic> json) {
    return ExecutionCancelResponse(
      cancelled: json['cancelled'] as bool,
      message: json['message'] as String,
    );
  }
}

class QueuedExecution {
  final String runId;
  final String strategyCode;
  final ExecutionState status;
  final int position;
  final String? startedAt;
  final String? estimatedStart;

  QueuedExecution({
    required this.runId,
    required this.strategyCode,
    required this.status,
    required this.position,
    this.startedAt,
    this.estimatedStart,
  });

  factory QueuedExecution.fromJson(Map<String, dynamic> json) {
    return QueuedExecution(
      runId: json['run_id'] as String,
      strategyCode: json['strategy_code'] as String,
      status: ExecutionStateExtension.fromString(json['status'] as String),
      position: json['position'] as int,
      startedAt: json['started_at'] as String?,
      estimatedStart: json['estimated_start'] as String?,
    );
  }
}

class ExecutionQueueResponse {
  final List<QueuedExecution> queue;
  final int totalQueued;
  final int maxConcurrent;

  ExecutionQueueResponse({
    required this.queue,
    required this.totalQueued,
    required this.maxConcurrent,
  });

  factory ExecutionQueueResponse.fromJson(Map<String, dynamic> json) {
    final queueRaw = json['queue'];
    return ExecutionQueueResponse(
      queue: queueRaw is List
          ? queueRaw.map((q) => QueuedExecution.fromJson(q)).toList()
          : <QueuedExecution>[],
      totalQueued: json['total_queued'] as int? ?? 0,
      maxConcurrent: json['max_concurrent'] as int? ?? 1,
    );
  }
}