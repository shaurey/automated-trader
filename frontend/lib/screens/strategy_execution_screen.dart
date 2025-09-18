import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../models/strategies.dart';
import '../providers/execution_provider.dart';
import '../widgets/loading_widget.dart';
import '../widgets/error_widget.dart';
import '../widgets/report_viewer_dialog.dart';
import '../services/api_service.dart';

class StrategyExecutionScreen extends ConsumerStatefulWidget {
  const StrategyExecutionScreen({super.key});

  @override
  ConsumerState<StrategyExecutionScreen> createState() => _StrategyExecutionScreenState();
}

class _StrategyExecutionScreenState extends ConsumerState<StrategyExecutionScreen>
    with TickerProviderStateMixin {
  late TabController _tabController;
  
  // Form controllers
  final _strategyCodeController = TextEditingController();
  final _tickersController = TextEditingController();
  final _minVolumeController = TextEditingController();
  final _priorityController = TextEditingController(text: 'normal');
  
  // Available strategy codes
  final List<String> _availableStrategies = [
    'bullish_breakout',
    'leap_entry',
    'value_screener',
  ];

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 3, vsync: this);
    _strategyCodeController.text = _availableStrategies.first;
    
    // Start monitoring the execution queue
    Future.microtask(() {
      ref.read(executionProvider.notifier).startQueueMonitoring();
    });
  }

  @override
  void dispose() {
    _tabController.dispose();
    _strategyCodeController.dispose();
    _tickersController.dispose();
    _minVolumeController.dispose();
    _priorityController.dispose();
    
    // Stop monitoring
    ref.read(executionProvider.notifier).stopQueueMonitoring();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final executionState = ref.watch(executionProvider);
    final activeExecutions = ref.watch(activeExecutionsProvider);
    final queueStatus = ref.watch(queueStatusProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Strategy Execution'),
        bottom: TabBar(
          controller: _tabController,
          tabs: const [
            Tab(icon: Icon(Icons.play_arrow), text: 'Execute'),
            Tab(icon: Icon(Icons.timeline), text: 'Monitor'),
            Tab(icon: Icon(Icons.queue), text: 'Queue'),
          ],
        ),
      ),
      body: TabBarView(
        controller: _tabController,
        children: [
          _buildExecutionTab(executionState),
          _buildMonitorTab(activeExecutions),
          _buildQueueTab(queueStatus),
        ],
      ),
    );
  }

  Widget _buildExecutionTab(ExecutionProviderState state) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16.0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Strategy Configuration',
                    style: Theme.of(context).textTheme.headlineSmall,
                  ),
                  const SizedBox(height: 16),
                  _buildStrategyForm(),
                ],
              ),
            ),
          ),
          const SizedBox(height: 16),
          if (state.error != null) ...[
            ErrorDisplayWidget(
              error: state.error!,
              onRetry: () => ref.read(executionProvider.notifier).clearError(),
            ),
            const SizedBox(height: 16),
          ],
          _buildExecuteButton(state.isLoading),
        ],
      ),
    );
  }

  Widget _buildStrategyForm() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Strategy Selection
        DropdownButtonFormField<String>(
          value: _strategyCodeController.text,
          decoration: const InputDecoration(
            labelText: 'Strategy',
            border: OutlineInputBorder(),
          ),
          items: _availableStrategies.map((strategy) {
            return DropdownMenuItem(
              value: strategy,
              child: Text(_formatStrategyName(strategy)),
            );
          }).toList(),
          onChanged: (value) {
            if (value != null) {
              _strategyCodeController.text = value;
            }
          },
        ),
        const SizedBox(height: 16),
        
        // Tickers Input
        TextFormField(
          controller: _tickersController,
          decoration: const InputDecoration(
            labelText: 'Tickers (comma-separated)',
            hintText: 'AAPL, MSFT, GOOGL',
            border: OutlineInputBorder(),
            helperText: 'Leave empty to use default universe',
          ),
          maxLines: 2,
        ),
        const SizedBox(height: 16),
        
        // Min Volume Input
        TextFormField(
          controller: _minVolumeController,
          decoration: const InputDecoration(
            labelText: 'Minimum Volume',
            hintText: '1000000',
            border: OutlineInputBorder(),
          ),
          keyboardType: TextInputType.number,
        ),
        const SizedBox(height: 16),
        
        // Priority Selection
        DropdownButtonFormField<String>(
          value: _priorityController.text,
          decoration: const InputDecoration(
            labelText: 'Priority',
            border: OutlineInputBorder(),
          ),
          items: const [
            DropdownMenuItem(value: 'low', child: Text('Low')),
            DropdownMenuItem(value: 'normal', child: Text('Normal')),
            DropdownMenuItem(value: 'high', child: Text('High')),
          ],
          onChanged: (value) {
            if (value != null) {
              _priorityController.text = value;
            }
          },
        ),
      ],
    );
  }

  Widget _buildExecuteButton(bool isLoading) {
    return SizedBox(
      width: double.infinity,
      child: ElevatedButton.icon(
        onPressed: isLoading ? null : _executeStrategy,
        icon: isLoading 
            ? const SizedBox(
                width: 20,
                height: 20,
                child: CircularProgressIndicator(strokeWidth: 2),
              )
            : const Icon(Icons.play_arrow),
        label: Text(isLoading ? 'Executing...' : 'Execute Strategy'),
        style: ElevatedButton.styleFrom(
          padding: const EdgeInsets.all(16),
        ),
      ),
    );
  }

  Widget _buildMonitorTab(List<ExecutionStatus> activeExecutions) {
    if (activeExecutions.isEmpty) {
      return const Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.timeline, size: 64, color: Colors.grey),
            SizedBox(height: 16),
            Text(
              'No active executions',
              style: TextStyle(fontSize: 18, color: Colors.grey),
            ),
          ],
        ),
      );
    }

    return ListView.builder(
      padding: const EdgeInsets.all(16),
      itemCount: activeExecutions.length,
      itemBuilder: (context, index) {
        final execution = activeExecutions[index];
        return ExecutionMonitorCard(execution: execution);
      },
    );
  }

  Widget _buildQueueTab(ExecutionQueueResponse? queueStatus) {
    if (queueStatus == null) {
      return const Center(child: LoadingWidget());
    }

    if (queueStatus.queue.isEmpty) {
      return const Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.queue, size: 64, color: Colors.grey),
            SizedBox(height: 16),
            Text(
              'No executions in queue',
              style: TextStyle(fontSize: 18, color: Colors.grey),
            ),
          ],
        ),
      );
    }

    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.all(16),
          child: Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceAround,
                children: [
                  Column(
                    children: [
                      Text(
                        '${queueStatus.totalQueued}',
                        style: Theme.of(context).textTheme.headlineMedium,
                      ),
                      const Text('Queued'),
                    ],
                  ),
                  Column(
                    children: [
                      Text(
                        '${queueStatus.maxConcurrent}',
                        style: Theme.of(context).textTheme.headlineMedium,
                      ),
                      const Text('Max Concurrent'),
                    ],
                  ),
                ],
              ),
            ),
          ),
        ),
        Expanded(
          child: ListView.builder(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            itemCount: queueStatus.queue.length,
            itemBuilder: (context, index) {
              final execution = queueStatus.queue[index];
              return QueueItemCard(execution: execution);
            },
          ),
        ),
      ],
    );
  }

  String _formatStrategyName(String strategyCode) {
    return strategyCode
        .split('_')
        .map((word) => word[0].toUpperCase() + word.substring(1))
        .join(' ');
  }

  void _executeStrategy() async {
    final parameters = <String, dynamic>{};
    
    // Add tickers if provided
    if (_tickersController.text.trim().isNotEmpty) {
      final tickers = _tickersController.text
          .split(',')
          .map((e) => e.trim().toUpperCase())
          .where((e) => e.isNotEmpty)
          .toList();
      parameters['tickers'] = tickers;
    }
    
    // Add min_volume if provided
    if (_minVolumeController.text.trim().isNotEmpty) {
      final minVolume = int.tryParse(_minVolumeController.text.trim());
      if (minVolume != null) {
        parameters['min_volume'] = minVolume;
      }
    }

    final request = StrategyExecutionRequest(
      strategyCode: _strategyCodeController.text,
      parameters: parameters,
      options: ExecutionOptions(
        priority: _priorityController.text,
        notifyOnCompletion: true,
      ),
    );

    final runId = await ref.read(executionProvider.notifier).executeStrategy(request);
    
    if (runId != null) {
      // Start progress monitoring
      ref.read(progressProvider.notifier).startProgressMonitoring(runId);
      
      // Switch to monitor tab
      _tabController.animateTo(1);
      
      // Show success message
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Strategy execution started: $runId'),
            backgroundColor: Colors.green,
          ),
        );
      }
    }
  }
}

class ExecutionMonitorCard extends ConsumerWidget {
  final ExecutionStatus execution;

  const ExecutionMonitorCard({
    required this.execution,
    super.key,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final progressEvents = ref.watch(progressEventsProvider(execution.runId));
    final latestEvent = ref.watch(latestProgressEventProvider(execution.runId));

    return Card(
      margin: const EdgeInsets.only(bottom: 16),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Run ID: ${execution.runId.substring(0, 8)}...',
                        style: Theme.of(context).textTheme.titleMedium,
                      ),
                      Text(
                        _getStatusText(execution.status),
                        style: TextStyle(
                          color: _getStatusColor(execution.status),
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ],
                  ),
                ),
                if (execution.canCancel)
                  IconButton(
                    onPressed: () => _cancelExecution(context, ref),
                    icon: const Icon(Icons.cancel),
                    tooltip: 'Cancel Execution',
                  ),
              ],
            ),
            const SizedBox(height: 12),
            
            // Progress Bar
            if (execution.progressPercent != null) ...[
              LinearProgressIndicator(
                value: execution.progressPercent! / 100,
                backgroundColor: Colors.grey[300],
              ),
              const SizedBox(height: 8),
              Text('${execution.progressPercent!.toStringAsFixed(1)}% complete'),
              const SizedBox(height: 12),
            ],
            
            // Current Stage
            if (execution.currentStage != null) ...[
              Text(
                'Stage: ${execution.currentStage}',
                style: Theme.of(context).textTheme.bodyMedium,
              ),
              const SizedBox(height: 8),
            ],
            
            // Latest Progress Message
            if (latestEvent != null) ...[
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: Colors.grey[100],
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Text(
                  latestEvent.message,
                  style: Theme.of(context).textTheme.bodySmall,
                ),
              ),
              const SizedBox(height: 8),
            ],
            
            // Action Buttons
            Row(
              children: [
                TextButton.icon(
                  onPressed: () => _showProgressDetails(context, progressEvents),
                  icon: const Icon(Icons.info_outline),
                  label: const Text('View Details'),
                ),
                const Spacer(),
                if (execution.status == ExecutionState.completed) ...[
                  ElevatedButton.icon(
                    onPressed: () => _viewResults(context, ref),
                    icon: const Icon(Icons.visibility),
                    label: const Text('View Results'),
                  ),
                  const SizedBox(width: 8),
                  ElevatedButton.icon(
                    onPressed: () => _generateReport(context),
                    icon: const Icon(Icons.description),
                    label: const Text('Generate Report'),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Theme.of(context).colorScheme.secondary,
                      foregroundColor: Theme.of(context).colorScheme.onSecondary,
                    ),
                  ),
                ],
              ],
            ),
          ],
        ),
      ),
    );
  }

  String _getStatusText(ExecutionState status) {
    switch (status) {
      case ExecutionState.queued:
        return 'Queued';
      case ExecutionState.starting:
        return 'Starting';
      case ExecutionState.running:
        return 'Running';
      case ExecutionState.completing:
        return 'Completing';
      case ExecutionState.completed:
        return 'Completed';
      case ExecutionState.cancelled:
        return 'Cancelled';
      case ExecutionState.error:
        return 'Error';
    }
  }

  Color _getStatusColor(ExecutionState status) {
    switch (status) {
      case ExecutionState.queued:
        return Colors.orange;
      case ExecutionState.starting:
      case ExecutionState.running:
      case ExecutionState.completing:
        return Colors.blue;
      case ExecutionState.completed:
        return Colors.green;
      case ExecutionState.cancelled:
        return Colors.grey;
      case ExecutionState.error:
        return Colors.red;
    }
  }

  void _cancelExecution(BuildContext context, WidgetRef ref) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Cancel Execution'),
        content: const Text('Are you sure you want to cancel this execution?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: const Text('No'),
          ),
          TextButton(
            onPressed: () => Navigator.of(context).pop(true),
            child: const Text('Yes'),
          ),
        ],
      ),
    );

    if (confirmed == true) {
      await ref.read(executionProvider.notifier).cancelExecution(execution.runId);
    }
  }

  void _showProgressDetails(BuildContext context, List<ProgressEvent> events) {
    showDialog(
      context: context,
      builder: (context) => ProgressDetailsDialog(
        runId: execution.runId,
        events: events,
      ),
    );
  }

  void _viewResults(BuildContext context, WidgetRef ref) {
    // Navigate to the strategies screen where results can be viewed
    // For now, we'll show the run details in the current screen
    _showResultsDialog(context, ref);
  }
  
  void _showResultsDialog(BuildContext context, WidgetRef ref) async {
    try {
      // Fetch the run details using the existing API
      final runDetail = await ApiService.getStrategyRunDetail(execution.runId);
      
      if (context.mounted) {
        showDialog(
          context: context,
          barrierDismissible: true,
          builder: (context) => AlertDialog(
            title: Text('Strategy Results - ${runDetail.strategyCode}'),
            content: Container(
              width: double.maxFinite,
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('Run ID: ${runDetail.runId}'),
                  SizedBox(height: 8),
                  if (runDetail.passedCount != null)
                    Text('Passed: ${runDetail.passedCount} / ${runDetail.totalResults ?? 0}'),
                  if (runDetail.passRate != null)
                    Text('Pass Rate: ${(runDetail.passRate! * 100).toStringAsFixed(1)}%'),
                  if (runDetail.avgScore != null)
                    Text('Average Score: ${runDetail.avgScore!.toStringAsFixed(2)}'),
                  SizedBox(height: 16),
                  Text('Top Results:', style: TextStyle(fontWeight: FontWeight.bold)),
                  SizedBox(height: 8),
                  ...runDetail.topResults.take(5).map((result) => Padding(
                    padding: EdgeInsets.only(bottom: 4),
                    child: Text('${result.ticker}: ${result.score?.toStringAsFixed(2) ?? "N/A"}'),
                  )),
                ],
              ),
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.of(context).pop(),
                child: Text('Close'),
              ),
              TextButton(
                onPressed: () {
                  Navigator.of(context).pop();
                  context.goNamed('strategies');
                },
                child: Text('View Full Results'),
              ),
            ],
          ),
        );
      }
    } catch (e) {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Failed to load results: $e'),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
  }

  void _generateReport(BuildContext context) async {
    try {
      // First, get the strategy run details to obtain the strategy code
      final runDetail = await ApiService.getStrategyRunDetail(execution.runId);
      
      if (context.mounted) {
        showDialog(
          context: context,
          builder: (context) => ReportViewerDialog(
            runId: execution.runId,
            strategyCode: runDetail.strategyCode,
          ),
        );
      }
    } catch (e) {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Failed to load strategy details: $e'),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
  }
}

class QueueItemCard extends ConsumerWidget {
  final QueuedExecution execution;

  const QueueItemCard({
    required this.execution,
    super.key,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      child: ListTile(
        leading: CircleAvatar(
          backgroundColor: _getStatusColor(execution.status),
          child: Text('${execution.position + 1}'),
        ),
        title: Text(execution.strategyCode),
        subtitle: Text('Run ID: ${execution.runId.substring(0, 8)}...'),
        trailing: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          crossAxisAlignment: CrossAxisAlignment.end,
          children: [
            Text(
              _getStatusText(execution.status),
              style: TextStyle(
                color: _getStatusColor(execution.status),
                fontWeight: FontWeight.bold,
              ),
            ),
            if (execution.estimatedStart != null)
              Text(
                'ETA: ${DateTime.parse(execution.estimatedStart!).toLocal().toString().substring(11, 16)}',
                style: Theme.of(context).textTheme.bodySmall,
              ),
          ],
        ),
      ),
    );
  }

  String _getStatusText(ExecutionState status) {
    switch (status) {
      case ExecutionState.queued:
        return 'Queued';
      case ExecutionState.starting:
        return 'Starting';
      case ExecutionState.running:
        return 'Running';
      case ExecutionState.completing:
        return 'Completing';
      case ExecutionState.completed:
        return 'Completed';
      case ExecutionState.cancelled:
        return 'Cancelled';
      case ExecutionState.error:
        return 'Error';
    }
  }

  Color _getStatusColor(ExecutionState status) {
    switch (status) {
      case ExecutionState.queued:
        return Colors.orange;
      case ExecutionState.starting:
      case ExecutionState.running:
      case ExecutionState.completing:
        return Colors.blue;
      case ExecutionState.completed:
        return Colors.green;
      case ExecutionState.cancelled:
        return Colors.grey;
      case ExecutionState.error:
        return Colors.red;
    }
  }
}

class ProgressDetailsDialog extends StatelessWidget {
  final String runId;
  final List<ProgressEvent> events;

  const ProgressDetailsDialog({
    required this.runId,
    required this.events,
    super.key,
  });

  @override
  Widget build(BuildContext context) {
    return Dialog(
      child: Container(
        width: MediaQuery.of(context).size.width * 0.8,
        height: MediaQuery.of(context).size.height * 0.8,
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  'Progress Details',
                  style: Theme.of(context).textTheme.headlineSmall,
                ),
                IconButton(
                  onPressed: () => Navigator.of(context).pop(),
                  icon: const Icon(Icons.close),
                ),
              ],
            ),
            Text(
              'Run ID: $runId',
              style: Theme.of(context).textTheme.bodyMedium,
            ),
            const SizedBox(height: 16),
            Expanded(
              child: ListView.builder(
                itemCount: events.length,
                itemBuilder: (context, index) {
                  final event = events[events.length - 1 - index]; // Reverse order
                  return Card(
                    margin: const EdgeInsets.only(bottom: 8),
                    child: Padding(
                      padding: const EdgeInsets.all(12),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            mainAxisAlignment: MainAxisAlignment.spaceBetween,
                            children: [
                              Text(
                                event.eventType.value,
                                style: Theme.of(context).textTheme.titleSmall?.copyWith(
                                  color: _getEventTypeColor(event.eventType),
                                  fontWeight: FontWeight.bold,
                                ),
                              ),
                              Text(
                                event.timestamp.toLocal().toString().substring(11, 19),
                                style: Theme.of(context).textTheme.bodySmall,
                              ),
                            ],
                          ),
                          const SizedBox(height: 4),
                          Text(event.message),
                          if (event.stage != null) ...[
                            const SizedBox(height: 4),
                            Text(
                              'Stage: ${event.stage}',
                              style: Theme.of(context).textTheme.bodySmall,
                            ),
                          ],
                          if (event.progressPercent != null) ...[
                            const SizedBox(height: 8),
                            LinearProgressIndicator(
                              value: event.progressPercent! / 100,
                              backgroundColor: Colors.grey[300],
                            ),
                            Text('${event.progressPercent!.toStringAsFixed(1)}%'),
                          ],
                        ],
                      ),
                    ),
                  );
                },
              ),
            ),
          ],
        ),
      ),
    );
  }

  Color _getEventTypeColor(ProgressEventType eventType) {
    switch (eventType) {
      case ProgressEventType.started:
        return Colors.blue;
      case ProgressEventType.progress:
        return Colors.green;
      case ProgressEventType.tickerCompleted:
        return Colors.teal;
      case ProgressEventType.stageCompleted:
        return Colors.indigo;
      case ProgressEventType.completed:
        return Colors.green;
      case ProgressEventType.error:
        return Colors.red;
      case ProgressEventType.cancelled:
        return Colors.orange;
    }
  }
}