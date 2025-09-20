import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:file_picker/file_picker.dart';
import 'package:intl/intl.dart';
import '../providers/holdings_provider.dart';
import '../models/holdings.dart';

class HoldingsImportDialog extends ConsumerStatefulWidget {
  const HoldingsImportDialog({super.key});

  @override
  ConsumerState<HoldingsImportDialog> createState() => _HoldingsImportDialogState();
}

class _HoldingsImportDialogState extends ConsumerState<HoldingsImportDialog> {
  bool _replaceExisting = true;
  PlatformFile? _selectedFile;
  bool _showResults = false;

  @override
  void dispose() {
    super.dispose();
  }

  Future<void> _pickFile() async {
    try {
      final result = await FilePicker.platform.pickFiles(
        type: FileType.custom,
        allowedExtensions: ['csv'],
        allowMultiple: false,
      );

      if (result != null && result.files.isNotEmpty) {
        setState(() {
          _selectedFile = result.files.first;
        });
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Error selecting file: $e'),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
  }

  Future<void> _importFile() async {
    if (_selectedFile == null) {
      return;
    }

    final success = await ref.read(holdingsImportProvider.notifier).importHoldingsFromFile(
      fileBytes: _selectedFile!.bytes!,
      fileName: _selectedFile!.name,
      replaceExisting: _replaceExisting,
    );

    if (mounted) {
      setState(() {
        _showResults = true;
      });

      if (success) {
        // Also trigger the refresh watcher
        ref.read(refreshHoldingsAfterImportProvider);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final importState = ref.watch(holdingsImportProvider);

    if (_showResults && importState.lastImportResult != null) {
      return _buildResultsDialog(context, theme, importState.lastImportResult!);
    }

    return AlertDialog(
      title: const Text('Import Holdings from CSV'),
      content: SizedBox(
        width: 500,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Import holdings data from a CSV file. The CSV should contain columns for Symbol, Quantity, Current Value, Cost Basis Total, Account Number, and optionally Account Name. Account information will be automatically detected from the CSV.',
              style: theme.textTheme.bodyMedium,
            ),
            const SizedBox(height: 16),

            // File selection
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                border: Border.all(color: theme.colorScheme.outline),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Column(
                children: [
                  if (_selectedFile == null) ...[
                    Icon(
                      Icons.upload_file,
                      size: 48,
                      color: theme.colorScheme.primary,
                    ),
                    const SizedBox(height: 8),
                    Text(
                      'Select CSV File',
                      style: theme.textTheme.titleMedium,
                    ),
                    const SizedBox(height: 4),
                    Text(
                      'Click to browse for a CSV file',
                      style: theme.textTheme.bodySmall?.copyWith(
                        color: theme.colorScheme.onSurfaceVariant,
                      ),
                    ),
                  ] else ...[
                    Row(
                      children: [
                        Icon(
                          Icons.description,
                          color: theme.colorScheme.primary,
                        ),
                        const SizedBox(width: 8),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                _selectedFile!.name,
                                style: theme.textTheme.bodyMedium?.copyWith(
                                  fontWeight: FontWeight.w500,
                                ),
                              ),
                              Text(
                                '${(_selectedFile!.size / 1024).toStringAsFixed(1)} KB',
                                style: theme.textTheme.bodySmall?.copyWith(
                                  color: theme.colorScheme.onSurfaceVariant,
                                ),
                              ),
                            ],
                          ),
                        ),
                        IconButton(
                          onPressed: () => setState(() => _selectedFile = null),
                          icon: const Icon(Icons.close),
                          tooltip: 'Remove file',
                        ),
                      ],
                    ),
                  ],
                  const SizedBox(height: 8),
                  FilledButton.icon(
                    onPressed: _pickFile,
                    icon: const Icon(Icons.folder_open),
                    label: Text(_selectedFile == null ? 'Browse Files' : 'Change File'),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 16),

            // Options
            CheckboxListTile(
              title: const Text('Replace existing holdings'),
              subtitle: const Text('Remove all existing holdings for this account before importing'),
              value: _replaceExisting,
              onChanged: (value) => setState(() => _replaceExisting = value ?? true),
              controlAffinity: ListTileControlAffinity.leading,
            ),

            if (importState.error != null) ...[
              const SizedBox(height: 16),
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: theme.colorScheme.errorContainer,
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Row(
                  children: [
                    Icon(
                      Icons.error_outline,
                      color: theme.colorScheme.onErrorContainer,
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        importState.error!,
                        style: theme.textTheme.bodyMedium?.copyWith(
                          color: theme.colorScheme.onErrorContainer,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: importState.isImporting ? null : () => Navigator.of(context).pop(),
          child: const Text('Cancel'),
        ),
        FilledButton(
          onPressed: (_selectedFile != null && !importState.isImporting)
              ? _importFile
              : null,
          child: importState.isImporting
              ? const SizedBox(
                  width: 16,
                  height: 16,
                  child: CircularProgressIndicator(strokeWidth: 2),
                )
              : const Text('Import'),
        ),
      ],
    );
  }

  Widget _buildResultsDialog(BuildContext context, ThemeData theme, HoldingsImportResponse result) {
    final formatter = NumberFormat('#,##0');

    return AlertDialog(
      title: Row(
        children: [
          Icon(
            result.importSummary.importSuccessful ? Icons.check_circle : Icons.error,
            color: result.importSummary.importSuccessful ? Colors.green : Colors.red,
          ),
          const SizedBox(width: 8),
          Text(result.importSummary.importSuccessful ? 'Import Successful' : 'Import Failed'),
        ],
      ),
      content: SizedBox(
        width: 600,
        child: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Detected Accounts
              if (result.detectedAccounts.isNotEmpty) ...[
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'Detected Accounts',
                          style: theme.textTheme.titleMedium,
                        ),
                        const SizedBox(height: 12),
                        ...result.detectedAccounts.map((account) => Padding(
                          padding: const EdgeInsets.symmetric(vertical: 4),
                          child: Row(
                            mainAxisAlignment: MainAxisAlignment.spaceBetween,
                            children: [
                              Expanded(
                                child: Text(
                                  account.accountName != null
                                    ? '${account.accountNumber} (${account.accountName})'
                                    : account.accountNumber,
                                  style: theme.textTheme.bodyMedium?.copyWith(
                                    fontWeight: FontWeight.w500,
                                  ),
                                ),
                              ),
                              Text(
                                '${formatter.format(account.recordCount)} records',
                                style: theme.textTheme.bodySmall,
                              ),
                            ],
                          ),
                        )),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: 16),
              ],

              // Overall Summary
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Overall Import Summary',
                        style: theme.textTheme.titleMedium,
                      ),
                      const SizedBox(height: 12),
                      _buildSummaryRow('Total Rows Processed:', formatter.format(result.importSummary.totalRowsProcessed)),
                      _buildSummaryRow('Accounts Detected:', formatter.format(result.importSummary.totalAccountsDetected)),
                      _buildSummaryRow('Total Records Imported:', formatter.format(result.importSummary.totalRecordsImported)),
                      _buildSummaryRow('Total Records Skipped:', formatter.format(result.importSummary.totalRecordsSkipped)),
                      _buildSummaryRow('Total Records Failed:', formatter.format(result.importSummary.totalRecordsFailed)),
                      if (result.importSummary.totalExistingHoldingsDeleted > 0)
                        _buildSummaryRow('Total Existing Holdings Deleted:', formatter.format(result.importSummary.totalExistingHoldingsDeleted)),
                    ],
                  ),
                ),
              ),

              // Per-Account Details
              if (result.importSummary.accountSummaries.isNotEmpty) ...[
                const SizedBox(height: 16),
                Text(
                  'Per-Account Details',
                  style: theme.textTheme.titleMedium,
                ),
                const SizedBox(height: 8),
                ...result.importSummary.accountSummaries.map((accountSummary) => Card(
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          accountSummary.accountName != null
                            ? '${accountSummary.accountNumber} (${accountSummary.accountName})'
                            : accountSummary.accountNumber,
                          style: theme.textTheme.titleSmall,
                        ),
                        const SizedBox(height: 8),
                        _buildSummaryRow('Rows Processed:', formatter.format(accountSummary.totalRowsProcessed)),
                        _buildSummaryRow('Records Imported:', formatter.format(accountSummary.recordsImported)),
                        _buildSummaryRow('Records Skipped:', formatter.format(accountSummary.recordsSkipped)),
                        _buildSummaryRow('Records Failed:', formatter.format(accountSummary.recordsFailed)),
                        if (accountSummary.existingHoldingsDeleted > 0)
                          _buildSummaryRow('Existing Holdings Deleted:', formatter.format(accountSummary.existingHoldingsDeleted)),
                        Row(
                          children: [
                            Text('Status: '),
                            Icon(
                              accountSummary.importSuccessful ? Icons.check_circle_outline : Icons.error_outline,
                              size: 16,
                              color: accountSummary.importSuccessful ? Colors.green : Colors.red,
                            ),
                            const SizedBox(width: 4),
                            Text(
                              accountSummary.importSuccessful ? 'Success' : 'Failed',
                              style: TextStyle(
                                color: accountSummary.importSuccessful ? Colors.green : Colors.red,
                                fontWeight: FontWeight.w500,
                              ),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                )),
              ],

              // Errors and warnings
              if (result.errors.isNotEmpty) ...[
                const SizedBox(height: 16),
                Text(
                  'Errors:',
                  style: theme.textTheme.titleSmall?.copyWith(color: Colors.red),
                ),
                const SizedBox(height: 4),
                Container(
                  constraints: const BoxConstraints(maxHeight: 100),
                  child: SingleChildScrollView(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: result.errors.map((error) => Text(
                        '• $error',
                        style: theme.textTheme.bodySmall?.copyWith(color: Colors.red),
                      )).toList(),
                    ),
                  ),
                ),
              ],

              if (result.warnings.isNotEmpty) ...[
                const SizedBox(height: 16),
                Text(
                  'Warnings:',
                  style: theme.textTheme.titleSmall?.copyWith(color: Colors.orange),
                ),
                const SizedBox(height: 4),
                Container(
                  constraints: const BoxConstraints(maxHeight: 100),
                  child: SingleChildScrollView(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: result.warnings.map((warning) => Text(
                        '• $warning',
                        style: theme.textTheme.bodySmall?.copyWith(color: Colors.orange),
                      )).toList(),
                    ),
                  ),
                ),
              ],
            ],
          ),
        ),
      ),
      actions: [
        FilledButton(
          onPressed: () {
            ref.read(holdingsImportProvider.notifier).clearImportState();
            Navigator.of(context).pop();
          },
          child: const Text('Close'),
        ),
      ],
    );
  }

  Widget _buildSummaryRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 2),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label),
          Text(
            value,
            style: const TextStyle(fontWeight: FontWeight.w500),
          ),
        ],
      ),
    );
  }
}