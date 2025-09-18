import 'package:flutter/material.dart';
import 'package:flutter_markdown/flutter_markdown.dart';
import '../services/report_service.dart';
import '../services/file_save_service.dart';

class ReportViewerDialog extends StatefulWidget {
  final String runId;
  final String strategyCode;

  const ReportViewerDialog({
    super.key,
    required this.runId,
    required this.strategyCode,
  });

  @override
  State<ReportViewerDialog> createState() => _ReportViewerDialogState();
}

class _ReportViewerDialogState extends State<ReportViewerDialog> {
  bool _isLoading = true;
  String? _reportContent;
  String? _errorMessage;
  bool _isSaving = false;

  @override
  void initState() {
    super.initState();
    _loadReport();
  }

  Future<void> _loadReport() async {
    try {
      setState(() {
        _isLoading = true;
        _errorMessage = null;
      });

      final reportContent = await ReportService.generateReport(widget.runId);
      
      if (mounted) {
        setState(() {
          _reportContent = reportContent;
          _isLoading = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _errorMessage = e.toString();
          _isLoading = false;
        });
      }
    }
  }

  Future<void> _saveReport() async {
    if (_reportContent == null) return;

    try {
      setState(() {
        _isSaving = true;
      });

      final fileName = FileSaveService.generateReportFileName(
        widget.strategyCode,
        widget.runId,
      );

      final success = await FileSaveService.saveFile(
        content: _reportContent!,
        fileName: fileName,
        mimeType: 'text/markdown',
      );

      if (mounted) {
        setState(() {
          _isSaving = false;
        });

        if (success) {
          _showSuccessMessage(fileName);
        } else {
          _showErrorMessage('Failed to save report');
        }
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _isSaving = false;
        });
        _showErrorMessage('Error saving report: $e');
      }
    }
  }

  void _showSuccessMessage(String fileName) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Report saved successfully!'),
            SizedBox(height: 4),
            Text(
              fileName,
              style: TextStyle(fontSize: 12, color: Colors.white70),
            ),
            SizedBox(height: 4),
            Text(
              FileSaveService.getSaveLocationDescription(),
              style: TextStyle(fontSize: 12, color: Colors.white70),
            ),
          ],
        ),
        backgroundColor: Colors.green,
        duration: Duration(seconds: 4),
        action: SnackBarAction(
          label: 'OK',
          textColor: Colors.white,
          onPressed: () {
            ScaffoldMessenger.of(context).hideCurrentSnackBar();
          },
        ),
      ),
    );
  }

  void _showErrorMessage(String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        backgroundColor: Colors.red,
        duration: Duration(seconds: 3),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Dialog.fullscreen(
      child: Scaffold(
        appBar: AppBar(
          title: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('Strategy Report'),
              Text(
                '${widget.strategyCode} - ${widget.runId.substring(0, 8)}...',
                style: TextStyle(fontSize: 14, fontWeight: FontWeight.normal),
              ),
            ],
          ),
          actions: [
            if (_reportContent != null && !_isSaving)
              IconButton(
                onPressed: _saveReport,
                icon: Icon(Icons.download),
                tooltip: 'Save Report',
              ),
            if (_isSaving)
              Padding(
                padding: EdgeInsets.all(16),
                child: SizedBox(
                  width: 20,
                  height: 20,
                  child: CircularProgressIndicator(strokeWidth: 2),
                ),
              ),
            IconButton(
              onPressed: () => Navigator.of(context).pop(),
              icon: Icon(Icons.close),
              tooltip: 'Close',
            ),
          ],
        ),
        body: _buildBody(),
      ),
    );
  }

  Widget _buildBody() {
    if (_isLoading) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            CircularProgressIndicator(),
            SizedBox(height: 16),
            Text('Generating report...'),
          ],
        ),
      );
    }

    if (_errorMessage != null) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.error_outline,
              size: 64,
              color: Colors.red,
            ),
            SizedBox(height: 16),
            Text(
              'Failed to generate report',
              style: Theme.of(context).textTheme.headlineSmall,
            ),
            SizedBox(height: 8),
            Text(
              _errorMessage!,
              textAlign: TextAlign.center,
              style: TextStyle(color: Colors.red),
            ),
            SizedBox(height: 16),
            ElevatedButton.icon(
              onPressed: _loadReport,
              icon: Icon(Icons.refresh),
              label: Text('Retry'),
            ),
          ],
        ),
      );
    }

    if (_reportContent == null) {
      return Center(
        child: Text('No report content available'),
      );
    }

    return Container(
      padding: EdgeInsets.all(16),
      child: SingleChildScrollView(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Report actions bar
            Container(
              padding: EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: Theme.of(context).colorScheme.surface,
                borderRadius: BorderRadius.circular(8),
                border: Border.all(
                  color: Theme.of(context).colorScheme.outline.withOpacity(0.2),
                ),
              ),
              child: Row(
                children: [
                  Icon(Icons.description, size: 20),
                  SizedBox(width: 8),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'Strategy Execution Report',
                          style: TextStyle(fontWeight: FontWeight.bold),
                        ),
                        Text(
                          'Generated on ${DateTime.now().toLocal().toString().substring(0, 19)}',
                          style: TextStyle(
                            fontSize: 12,
                            color: Theme.of(context).colorScheme.onSurface.withOpacity(0.6),
                          ),
                        ),
                      ],
                    ),
                  ),
                  ElevatedButton.icon(
                    onPressed: _isSaving ? null : _saveReport,
                    icon: _isSaving
                        ? SizedBox(
                            width: 16,
                            height: 16,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          )
                        : Icon(Icons.download, size: 16),
                    label: Text(_isSaving ? 'Saving...' : 'Save'),
                    style: ElevatedButton.styleFrom(
                      padding: EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                    ),
                  ),
                ],
              ),
            ),
            SizedBox(height: 16),
            
            // Markdown content
            Container(
              width: double.infinity,
              padding: EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: Theme.of(context).colorScheme.surface,
                borderRadius: BorderRadius.circular(8),
                border: Border.all(
                  color: Theme.of(context).colorScheme.outline.withOpacity(0.2),
                ),
              ),
              child: MarkdownBody(
                data: _reportContent!,
                selectable: true,
                styleSheet: _buildMarkdownStyleSheet(),
                onTapLink: (text, href, title) {
                  // Handle link taps if needed
                  debugPrint('Link tapped: $href');
                },
              ),
            ),
          ],
        ),
      ),
    );
  }

  MarkdownStyleSheet _buildMarkdownStyleSheet() {
    final theme = Theme.of(context);
    
    return MarkdownStyleSheet(
      h1: theme.textTheme.headlineLarge?.copyWith(
        color: theme.colorScheme.primary,
        fontWeight: FontWeight.bold,
      ),
      h2: theme.textTheme.headlineMedium?.copyWith(
        color: theme.colorScheme.primary,
        fontWeight: FontWeight.w600,
      ),
      h3: theme.textTheme.headlineSmall?.copyWith(
        color: theme.colorScheme.primary,
        fontWeight: FontWeight.w600,
      ),
      h4: theme.textTheme.titleLarge?.copyWith(
        color: theme.colorScheme.primary,
        fontWeight: FontWeight.w500,
      ),
      h5: theme.textTheme.titleMedium?.copyWith(
        color: theme.colorScheme.primary,
        fontWeight: FontWeight.w500,
      ),
      h6: theme.textTheme.titleSmall?.copyWith(
        color: theme.colorScheme.primary,
        fontWeight: FontWeight.w500,
      ),
      p: theme.textTheme.bodyMedium?.copyWith(
        height: 1.5,
      ),
      code: TextStyle(
        fontFamily: 'monospace',
        backgroundColor: theme.colorScheme.surfaceVariant,
        color: theme.colorScheme.onSurfaceVariant,
        fontSize: 13,
      ),
      codeblockDecoration: BoxDecoration(
        color: theme.colorScheme.surfaceVariant,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(
          color: theme.colorScheme.outline.withOpacity(0.2),
        ),
      ),
      codeblockPadding: EdgeInsets.all(12),
      blockquote: theme.textTheme.bodyMedium?.copyWith(
        color: theme.colorScheme.onSurface.withOpacity(0.7),
        fontStyle: FontStyle.italic,
      ),
      blockquoteDecoration: BoxDecoration(
        color: theme.colorScheme.surfaceVariant.withOpacity(0.3),
        border: Border(
          left: BorderSide(
            color: theme.colorScheme.primary,
            width: 4,
          ),
        ),
      ),
      tableBorder: TableBorder.all(
        color: theme.colorScheme.outline.withOpacity(0.2),
        width: 1,
      ),
      tableHead: theme.textTheme.bodyMedium?.copyWith(
        fontWeight: FontWeight.bold,
        color: theme.colorScheme.onSurface,
      ),
      tableBody: theme.textTheme.bodyMedium,
      tableCellsPadding: EdgeInsets.all(8),
      tableCellsDecoration: BoxDecoration(
        color: theme.colorScheme.surface,
      ),
      tableHeadAlign: TextAlign.left,
      listBullet: theme.textTheme.bodyMedium?.copyWith(
        color: theme.colorScheme.primary,
      ),
      horizontalRuleDecoration: BoxDecoration(
        border: Border(
          top: BorderSide(
            color: theme.colorScheme.outline.withOpacity(0.3),
            width: 1,
          ),
        ),
      ),
    );
  }
}

/// A simplified report viewer for smaller screens or embedded use
class CompactReportViewer extends StatelessWidget {
  final String reportContent;
  final VoidCallback? onSave;
  final bool isSaving;

  const CompactReportViewer({
    super.key,
    required this.reportContent,
    this.onSave,
    this.isSaving = false,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      height: 400,
      padding: EdgeInsets.all(16),
      child: Column(
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                'Strategy Report',
                style: Theme.of(context).textTheme.titleMedium,
              ),
              if (onSave != null)
                ElevatedButton.icon(
                  onPressed: isSaving ? null : onSave,
                  icon: isSaving
                      ? SizedBox(
                          width: 16,
                          height: 16,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : Icon(Icons.download, size: 16),
                  label: Text(isSaving ? 'Saving...' : 'Save'),
                  style: ElevatedButton.styleFrom(
                    padding: EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                  ),
                ),
            ],
          ),
          SizedBox(height: 16),
          Expanded(
            child: Container(
              width: double.infinity,
              padding: EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: Theme.of(context).colorScheme.surface,
                borderRadius: BorderRadius.circular(8),
                border: Border.all(
                  color: Theme.of(context).colorScheme.outline.withOpacity(0.2),
                ),
              ),
              child: SingleChildScrollView(
                child: MarkdownBody(
                  data: reportContent,
                  selectable: true,
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}