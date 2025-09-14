import 'dart:convert';
import 'package:http/http.dart' as http;
import '../models/holdings.dart';

class ApiService {
  static const String baseUrl = 'http://localhost:8000';
  static const Duration timeout = Duration(seconds: 30);

  static final http.Client _client = http.Client();

  // Holdings endpoints
  static Future<HoldingsSummary> getHoldingsSummary() async {
    try {
      final response = await _client
          .get(
            Uri.parse('$baseUrl/api/holdings/summary'),
            headers: {'Content-Type': 'application/json'},
          )
          .timeout(timeout);

      if (response.statusCode == 200) {
        final jsonData = json.decode(response.body);
        return HoldingsSummary.fromJson(jsonData);
      } else {
        throw ApiException(
          'Failed to load holdings summary: ${response.statusCode}',
          response.statusCode,
        );
      }
    } catch (e) {
      if (e is ApiException) rethrow;
      throw ApiException('Network error: ${e.toString()}', 0);
    }
  }

  static Future<PositionsResponse> getPositions({
    String? account,
    String? ticker,
    int? limit,
  }) async {
    try {
      final queryParams = <String, String>{};
      if (account != null) queryParams['account'] = account;
      if (ticker != null) queryParams['ticker'] = ticker;
      if (limit != null) queryParams['limit'] = limit.toString();

      final uri = Uri.parse('$baseUrl/api/holdings/positions')
          .replace(queryParameters: queryParams.isNotEmpty ? queryParams : null);

      final response = await _client
          .get(
            uri,
            headers: {'Content-Type': 'application/json'},
          )
          .timeout(timeout);

      if (response.statusCode == 200) {
        final jsonData = json.decode(response.body);
        return PositionsResponse.fromJson(jsonData);
      } else {
        throw ApiException(
          'Failed to load positions: ${response.statusCode}',
          response.statusCode,
        );
      }
    } catch (e) {
      if (e is ApiException) rethrow;
      throw ApiException('Network error: ${e.toString()}', 0);
    }
  }

  // Instruments endpoint
  static Future<Map<String, dynamic>> getInstruments({
    int? page,
    int? size,
    String? ticker,
    String? sector,
    String? instrumentType,
  }) async {
    try {
      final queryParams = <String, String>{};
      if (page != null) queryParams['page'] = page.toString();
      if (size != null) queryParams['size'] = size.toString();
      if (ticker != null) queryParams['ticker'] = ticker;
      if (sector != null) queryParams['sector'] = sector;
      if (instrumentType != null) queryParams['instrument_type'] = instrumentType;

      final uri = Uri.parse('$baseUrl/api/instruments')
          .replace(queryParameters: queryParams.isNotEmpty ? queryParams : null);

      final response = await _client
          .get(
            uri,
            headers: {'Content-Type': 'application/json'},
          )
          .timeout(timeout);

      if (response.statusCode == 200) {
        return json.decode(response.body);
      } else {
        throw ApiException(
          'Failed to load instruments: ${response.statusCode}',
          response.statusCode,
        );
      }
    } catch (e) {
      if (e is ApiException) rethrow;
      throw ApiException('Network error: ${e.toString()}', 0);
    }
  }

  // Health check endpoint
  static Future<Map<String, dynamic>> healthCheck() async {
    try {
      final response = await _client
          .get(
            Uri.parse('$baseUrl/api/health'),
            headers: {'Content-Type': 'application/json'},
          )
          .timeout(timeout);

      if (response.statusCode == 200) {
        return json.decode(response.body);
      } else {
        throw ApiException(
          'Health check failed: ${response.statusCode}',
          response.statusCode,
        );
      }
    } catch (e) {
      if (e is ApiException) rethrow;
      throw ApiException('Network error: ${e.toString()}', 0);
    }
  }

  // Dispose method to close the client
  static void dispose() {
    _client.close();
  }
}

class ApiException implements Exception {
  final String message;
  final int statusCode;

  ApiException(this.message, this.statusCode);

  @override
  String toString() => 'ApiException: $message (Status: $statusCode)';
}

// Helper class for API states
class ApiState<T> {
  final bool isLoading;
  final T? data;
  final String? error;

  const ApiState({
    this.isLoading = false,
    this.data,
    this.error,
  });

  ApiState<T> copyWith({
    bool? isLoading,
    T? data,
    String? error,
  }) {
    return ApiState<T>(
      isLoading: isLoading ?? this.isLoading,
      data: data ?? this.data,
      error: error ?? this.error,
    );
  }

  bool get hasData => data != null;
  bool get hasError => error != null;
  bool get isIdle => !isLoading && !hasError && !hasData;
}