import 'dart:convert';
import 'dart:io';
import 'package:flutter/foundation.dart';
import 'package:universal_html/html.dart' as html;
import 'package:path_provider/path_provider.dart';
import 'package:permission_handler/permission_handler.dart';

class FileSaveService {
  /// Save a file with cross-platform support
  static Future<bool> saveFile({
    required String content,
    required String fileName,
    String? mimeType,
  }) async {
    try {
      if (kIsWeb) {
        return _saveFileWeb(content, fileName, mimeType);
      } else {
        return await _saveFileNative(content, fileName);
      }
    } catch (e) {
      debugPrint('Error saving file: $e');
      return false;
    }
  }

  /// Save file on web platform using HTML5 download API
  static bool _saveFileWeb(String content, String fileName, String? mimeType) {
    try {
      // Create a blob with the content
      final bytes = utf8.encode(content);
      final blob = html.Blob([bytes], mimeType ?? 'text/markdown');
      
      // Create a download URL
      final url = html.Url.createObjectUrlFromBlob(blob);
      
      // Create a temporary anchor element and trigger download
      final anchor = html.AnchorElement(href: url)
        ..setAttribute('download', fileName)
        ..style.display = 'none';
      
      html.document.body?.children.add(anchor);
      anchor.click();
      html.document.body?.children.remove(anchor);
      
      // Clean up the URL
      html.Url.revokeObjectUrl(url);
      
      return true;
    } catch (e) {
      debugPrint('Error saving file on web: $e');
      return false;
    }
  }

  /// Save file on native platforms (iOS, Android, Desktop)
  static Future<bool> _saveFileNative(String content, String fileName) async {
    try {
      if (Platform.isAndroid || Platform.isIOS) {
        return await _saveFileMobile(content, fileName);
      } else {
        return await _saveFileDesktop(content, fileName);
      }
    } catch (e) {
      debugPrint('Error saving file on native platform: $e');
      return false;
    }
  }

  /// Save file on mobile platforms
  static Future<bool> _saveFileMobile(String content, String fileName) async {
    try {
      // Request storage permission on Android
      if (Platform.isAndroid) {
        final status = await Permission.storage.request();
        if (!status.isGranted) {
          debugPrint('Storage permission denied');
          return false;
        }
      }

      // Get the downloads directory
      Directory? directory;
      if (Platform.isAndroid) {
        directory = Directory('/storage/emulated/0/Download');
        if (!await directory.exists()) {
          directory = await getExternalStorageDirectory();
        }
      } else if (Platform.isIOS) {
        directory = await getApplicationDocumentsDirectory();
      }

      if (directory == null) {
        debugPrint('Could not get directory');
        return false;
      }

      // Create the file
      final file = File('${directory.path}/$fileName');
      await file.writeAsString(content);
      
      debugPrint('File saved to: ${file.path}');
      return true;
    } catch (e) {
      debugPrint('Error saving file on mobile: $e');
      return false;
    }
  }

  /// Save file on desktop platforms
  static Future<bool> _saveFileDesktop(String content, String fileName) async {
    try {
      // Get the downloads directory
      Directory? directory;
      
      if (Platform.isWindows) {
        directory = Directory('${Platform.environment['USERPROFILE']}\\Downloads');
      } else if (Platform.isMacOS) {
        directory = Directory('${Platform.environment['HOME']}/Downloads');
      } else if (Platform.isLinux) {
        directory = Directory('${Platform.environment['HOME']}/Downloads');
      }

      if (directory == null || !await directory.exists()) {
        // Fallback to documents directory
        directory = await getApplicationDocumentsDirectory();
      }

      // Create the file
      final file = File('${directory.path}/$fileName');
      await file.writeAsString(content);
      
      debugPrint('File saved to: ${file.path}');
      return true;
    } catch (e) {
      debugPrint('Error saving file on desktop: $e');
      return false;
    }
  }

  /// Generate a unique filename with timestamp
  static String generateFileName(String baseName, String extension) {
    final timestamp = DateTime.now().toIso8601String()
        .replaceAll(':', '-')
        .replaceAll('.', '-')
        .substring(0, 19);
    return '${baseName}_$timestamp.$extension';
  }

  /// Generate a filename for a strategy report
  static String generateReportFileName(String strategyCode, String runId) {
    final timestamp = DateTime.now().toIso8601String()
        .replaceAll(':', '-')
        .replaceAll('.', '-')
        .substring(0, 19);
    final shortRunId = runId.length > 8 ? runId.substring(0, 8) : runId;
    return 'strategy_report_${strategyCode}_${shortRunId}_$timestamp.md';
  }

  /// Check if the platform supports file saving
  static bool get isSupported {
    return kIsWeb || Platform.isAndroid || Platform.isIOS || 
           Platform.isWindows || Platform.isMacOS || Platform.isLinux;
  }

  /// Get a user-friendly description of where files are saved
  static String getSaveLocationDescription() {
    if (kIsWeb) {
      return 'Downloaded to your default downloads folder';
    } else if (Platform.isAndroid) {
      return 'Saved to Downloads folder';
    } else if (Platform.isIOS) {
      return 'Saved to app documents folder';
    } else if (Platform.isWindows || Platform.isMacOS || Platform.isLinux) {
      return 'Saved to Downloads folder';
    } else {
      return 'Saved to device storage';
    }
  }

  /// Save multiple files as a ZIP (future enhancement)
  static Future<bool> saveAsZip({
    required Map<String, String> files,
    required String zipFileName,
  }) async {
    // This is a placeholder for future ZIP functionality
    // For now, we'll just save the first file
    if (files.isNotEmpty) {
      final firstEntry = files.entries.first;
      return await saveFile(
        content: firstEntry.value,
        fileName: firstEntry.key,
      );
    }
    return false;
  }

  /// Check if storage permission is granted (mobile only)
  static Future<bool> checkStoragePermission() async {
    if (Platform.isAndroid) {
      final status = await Permission.storage.status;
      return status.isGranted;
    }
    return true; // No permission needed for other platforms
  }

  /// Request storage permission (mobile only)
  static Future<bool> requestStoragePermission() async {
    if (Platform.isAndroid) {
      final status = await Permission.storage.request();
      return status.isGranted;
    }
    return true; // No permission needed for other platforms
  }
}

/// Exception thrown when file save operations fail
class FileSaveException implements Exception {
  final String message;
  final dynamic originalError;

  FileSaveException(this.message, [this.originalError]);

  @override
  String toString() => 'FileSaveException: $message';
}

/// File save result with additional information
class FileSaveResult {
  final bool success;
  final String? filePath;
  final String? errorMessage;

  FileSaveResult({
    required this.success,
    this.filePath,
    this.errorMessage,
  });

  factory FileSaveResult.success(String filePath) {
    return FileSaveResult(success: true, filePath: filePath);
  }

  factory FileSaveResult.failure(String errorMessage) {
    return FileSaveResult(success: false, errorMessage: errorMessage);
  }
}