import 'dart:async';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/strategies.dart';
import '../services/api_service.dart';

// State classes for execution management
class ExecutionProviderState {
  final Map<String, ExecutionStatus> activeExecutions;
  final ExecutionQueueResponse? queueStatus;
  final String? error;
  final bool isLoading;

  const ExecutionProviderState({
    this.activeExecutions = const {},
    this.queueStatus,
    this.error,
    this.isLoading = false,
  });

  ExecutionProviderState copyWith({
    Map<String, ExecutionStatus>? activeExecutions,
    ExecutionQueueResponse? queueStatus,
    String? error,
    bool? isLoading,
  }) {
    return ExecutionProviderState(
      activeExecutions: activeExecutions ?? this.activeExecutions,
      queueStatus: queueStatus ?? this.queueStatus,
      error: error,
      isLoading: isLoading ?? this.isLoading,
    );
  }
}

class ProgressState {
  final Map<String, List<ProgressEvent>> progressEvents;
  final Map<String, StreamSubscription> activeStreams;

  const ProgressState({
    this.progressEvents = const {},
    this.activeStreams = const {},
  });

  ProgressState copyWith({
    Map<String, List<ProgressEvent>>? progressEvents,
    Map<String, StreamSubscription>? activeStreams,
  }) {
    return ProgressState(
      progressEvents: progressEvents ?? this.progressEvents,
      activeStreams: activeStreams ?? this.activeStreams,
    );
  }
}

// Execution state notifier
class ExecutionNotifier extends StateNotifier<ExecutionProviderState> {
  ExecutionNotifier() : super(const ExecutionProviderState());

  Timer? _queueUpdateTimer;

  @override
  void dispose() {
    _queueUpdateTimer?.cancel();
    super.dispose();
  }

  void startQueueMonitoring() {
    _queueUpdateTimer?.cancel();
    _queueUpdateTimer = Timer.periodic(
      const Duration(seconds: 5),
      (_) => _updateQueue(),
    );
  }

  void stopQueueMonitoring() {
    _queueUpdateTimer?.cancel();
  }

  Future<String?> executeStrategy(StrategyExecutionRequest request) async {
    state = state.copyWith(isLoading: true, error: null);

    try {
      final response = await ApiService.executeStrategy(request);
      
      // Add to active executions
      final newActiveExecutions = Map<String, ExecutionStatus>.from(state.activeExecutions);
      newActiveExecutions[response.runId] = ExecutionStatus(
        runId: response.runId,
        status: response.status,
        progressPercent: 0.0,
        currentStage: 'Starting...',
        startedAt: DateTime.now().toIso8601String(),
        estimatedCompletion: null,
        canCancel: true,
        metrics: null,
      );

      state = state.copyWith(
        activeExecutions: newActiveExecutions,
        isLoading: false,
      );

      // Start monitoring this execution
      _monitorExecution(response.runId);
      
      return response.runId;
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: e.toString(),
      );
      return null;
    }
  }

  Future<void> cancelExecution(String runId) async {
    try {
      await ApiService.cancelExecution(runId);
      
      // Update the execution status
      final newActiveExecutions = Map<String, ExecutionStatus>.from(state.activeExecutions);
      final currentStatus = newActiveExecutions[runId];
      if (currentStatus != null) {
        newActiveExecutions[runId] = ExecutionStatus(
          runId: currentStatus.runId,
          status: ExecutionState.cancelled,
          progressPercent: currentStatus.progressPercent,
          currentStage: 'Cancelled',
          startedAt: currentStatus.startedAt,
          estimatedCompletion: null,
          canCancel: false,
          metrics: currentStatus.metrics,
        );
      }

      state = state.copyWith(activeExecutions: newActiveExecutions);
    } catch (e) {
      state = state.copyWith(error: e.toString());
    }
  }

  void _monitorExecution(String runId) {
    Timer.periodic(const Duration(seconds: 2), (timer) async {
      try {
        final status = await ApiService.getExecutionStatus(runId);
        
        final newActiveExecutions = Map<String, ExecutionStatus>.from(state.activeExecutions);
        newActiveExecutions[runId] = status;

        state = state.copyWith(activeExecutions: newActiveExecutions);

        // Stop monitoring if execution is complete, but keep showing results
        if (status.status == ExecutionState.completed ||
            status.status == ExecutionState.cancelled ||
            status.status == ExecutionState.error) {
          timer.cancel();
          
          // For completed executions, try to fetch additional summary data
          if (status.status == ExecutionState.completed) {
            _fetchExecutionSummary(runId);
          }
        }
      } catch (e) {
        timer.cancel();
      }
    });
  }
  
  Future<void> _fetchExecutionSummary(String runId) async {
    try {
      // Fetch execution results from simplified router
      final resultsData = await ApiService.getStrategyExecutionResults(runId);
      
      // Update the execution status with summary information
      final newActiveExecutions = Map<String, ExecutionStatus>.from(state.activeExecutions);
      final currentExecution = newActiveExecutions[runId];
      
      if (currentExecution != null) {
        final metrics = Map<String, dynamic>.from(currentExecution.metrics ?? {});
        metrics.addAll({
          'passed_count': resultsData['qualifying_count'] ?? 0,
          'total_results': resultsData['total_evaluated'] ?? 0,
          'pass_rate': _calculatePassRate(resultsData['qualifying_count'], resultsData['total_evaluated']),
          'avg_score': _calculateAvgScore(resultsData['qualifying_results']),
          'duration_ms': resultsData['execution_time_ms'] ?? 0,
        });
        
        newActiveExecutions[runId] = ExecutionStatus(
          runId: currentExecution.runId,
          status: currentExecution.status,
          progressPercent: 100.0,
          currentStage: _buildCompletionSummaryFromResults(resultsData),
          startedAt: currentExecution.startedAt,
          estimatedCompletion: currentExecution.estimatedCompletion,
          canCancel: false,
          metrics: metrics,
        );
        
        state = state.copyWith(activeExecutions: newActiveExecutions);
      }
    } catch (e) {
      // Silently handle errors in fetching summary
    }
  }
  
  double _calculatePassRate(dynamic qualifyingCount, dynamic totalEvaluated) {
    final qualifying = (qualifyingCount is int) ? qualifyingCount : (qualifyingCount is String ? int.tryParse(qualifyingCount) ?? 0 : 0);
    final total = (totalEvaluated is int) ? totalEvaluated : (totalEvaluated is String ? int.tryParse(totalEvaluated) ?? 0 : 0);
    return total > 0 ? qualifying / total : 0.0;
  }
  
  double _calculateAvgScore(dynamic qualifyingResults) {
    if (qualifyingResults is! List || qualifyingResults.isEmpty) return 0.0;
    
    double totalScore = 0.0;
    int count = 0;
    
    for (final result in qualifyingResults) {
      if (result is Map && result['score'] != null) {
        final score = result['score'];
        if (score is num) {
          totalScore += score.toDouble();
          count++;
        }
      }
    }
    
    return count > 0 ? totalScore / count : 0.0;
  }
  
  String _buildCompletionSummaryFromResults(Map<String, dynamic> resultsData) {
    final parts = <String>[];
    
    final qualifyingCount = resultsData['qualifying_count'] ?? 0;
    final totalEvaluated = resultsData['total_evaluated'] ?? 0;
    
    if (qualifyingCount is int && totalEvaluated is int) {
      parts.add('$qualifyingCount/$totalEvaluated passed');
      
      if (totalEvaluated > 0) {
        final passRate = (qualifyingCount / totalEvaluated * 100);
        parts.add('${passRate.toStringAsFixed(1)}% pass rate');
      }
    }
    
    final avgScore = _calculateAvgScore(resultsData['qualifying_results']);
    if (avgScore > 0) {
      parts.add('avg score: ${avgScore.toStringAsFixed(1)}');
    }
    
    return parts.isNotEmpty ? parts.join(', ') : 'Completed';
  }
  
  String _buildCompletionSummary(runDetail) {
    final parts = <String>[];
    
    if (runDetail.passedCount != null && runDetail.totalResults != null) {
      parts.add('${runDetail.passedCount}/${runDetail.totalResults} passed');
    }
    
    if (runDetail.passRate != null) {
      parts.add('${(runDetail.passRate * 100).toStringAsFixed(1)}% pass rate');
    }
    
    if (runDetail.avgScore != null) {
      parts.add('avg score: ${runDetail.avgScore.toStringAsFixed(1)}');
    }
    
    return parts.isNotEmpty ? parts.join(', ') : 'Completed';
  }

  Future<void> _updateQueue() async {
    try {
      final queueStatus = await ApiService.getExecutionQueue();
      state = state.copyWith(queueStatus: queueStatus);
    } catch (e) {
      // Silently handle queue update errors
    }
  }

  void clearError() {
    state = state.copyWith(error: null);
  }

  void removeExecution(String runId) {
    final newActiveExecutions = Map<String, ExecutionStatus>.from(state.activeExecutions);
    newActiveExecutions.remove(runId);
    state = state.copyWith(activeExecutions: newActiveExecutions);
  }
}

// Progress events notifier
class ProgressNotifier extends StateNotifier<ProgressState> {
  ProgressNotifier() : super(const ProgressState());

  @override
  void dispose() {
    // Cancel all active streams
    for (final subscription in state.activeStreams.values) {
      subscription.cancel();
    }
    super.dispose();
  }

  void startProgressMonitoring(String runId) {
    if (state.activeStreams.containsKey(runId)) {
      return; // Already monitoring
    }

    // Progress monitoring is now handled by ExecutionNotifier's _monitorExecution
    // No separate SSE streams needed - just mark as being monitored
    _addProgressEvent(
      runId,
      ProgressEvent(
        eventType: ProgressEventType.started,
        timestamp: DateTime.now(),
        runId: runId,
        message: 'Progress monitoring started',
      ),
    );
  }

  void _addProgressEvent(String runId, ProgressEvent event) {
    final newProgressEvents = Map<String, List<ProgressEvent>>.from(state.progressEvents);
    final currentEvents = List<ProgressEvent>.from(newProgressEvents[runId] ?? []);
    currentEvents.add(event);
    
    // Keep only the last 100 events per execution
    if (currentEvents.length > 100) {
      currentEvents.removeRange(0, currentEvents.length - 100);
    }
    
    newProgressEvents[runId] = currentEvents;
    state = state.copyWith(progressEvents: newProgressEvents);
  }

  void _stopProgressMonitoring(String runId) {
    final newActiveStreams = Map<String, StreamSubscription>.from(state.activeStreams);
    newActiveStreams[runId]?.cancel();
    newActiveStreams.remove(runId);

    state = state.copyWith(activeStreams: newActiveStreams);
  }

  void stopProgressMonitoring(String runId) {
    _stopProgressMonitoring(runId);
  }

  void clearProgressEvents(String runId) {
    final newProgressEvents = Map<String, List<ProgressEvent>>.from(state.progressEvents);
    newProgressEvents.remove(runId);
    state = state.copyWith(progressEvents: newProgressEvents);
  }

  List<ProgressEvent> getProgressEvents(String runId) {
    return state.progressEvents[runId] ?? [];
  }

  ProgressEvent? getLatestProgressEvent(String runId) {
    final events = state.progressEvents[runId];
    return events?.isNotEmpty == true ? events!.last : null;
  }
}

// Providers
final executionProvider = StateNotifierProvider<ExecutionNotifier, ExecutionProviderState>((ref) {
  return ExecutionNotifier();
});

final progressProvider = StateNotifierProvider<ProgressNotifier, ProgressState>((ref) {
  return ProgressNotifier();
});

// Computed providers
final activeExecutionsProvider = Provider<List<ExecutionStatus>>((ref) {
  final state = ref.watch(executionProvider);
  return state.activeExecutions.values.toList();
});

final queueStatusProvider = Provider<ExecutionQueueResponse?>((ref) {
  final state = ref.watch(executionProvider);
  return state.queueStatus;
});

// Provider for getting progress events for a specific run ID
final progressEventsProvider = Provider.family<List<ProgressEvent>, String>((ref, runId) {
  final state = ref.watch(progressProvider);
  return state.progressEvents[runId] ?? [];
});

// Provider for getting the latest progress event for a specific run ID
final latestProgressEventProvider = Provider.family<ProgressEvent?, String>((ref, runId) {
  final events = ref.watch(progressEventsProvider(runId));
  return events.isNotEmpty ? events.last : null;
});