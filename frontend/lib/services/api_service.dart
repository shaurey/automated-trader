import 'dart:convert';
import 'dart:async';
import 'package:http/http.dart' as http;
import '../models/holdings.dart';
import '../models/strategies.dart';

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

  // Accounts endpoint
  static Future<List<String>> getAccounts() async {
    try {
      final uri = Uri.parse('$baseUrl/api/holdings/accounts');
      final response = await _client
          .get(
            uri,
            headers: {'Content-Type': 'application/json'},
          )
          .timeout(timeout);

      if (response.statusCode == 200) {
        final jsonData = json.decode(response.body);
        if (jsonData is Map && jsonData['accounts'] is List) {
          final accounts = (jsonData['accounts'] as List)
              .map((e) => (e['account'] ?? '').toString())
              .where((s) => s.isNotEmpty)
              .toList();
          return accounts;
        } else {
          throw ApiException('Unexpected accounts response shape', response.statusCode);
        }
      } else {
        throw ApiException(
          'Failed to load accounts: ${response.statusCode}',
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

  // Strategies endpoints
  static Future<StrategyRunsResponse> getStrategyRuns({
    String? strategyCode,
    String? status,
    String? dateFrom,
    String? dateTo,
    int? limit,
    int? offset,
    String? orderBy,
    bool? orderDesc,
  }) async {
    try {
      final queryParams = <String, String>{};
      if (strategyCode != null) queryParams['strategy_code'] = strategyCode;
      if (status != null) queryParams['status'] = status;
      if (dateFrom != null) queryParams['date_from'] = dateFrom;
      if (dateTo != null) queryParams['date_to'] = dateTo;
      if (limit != null) queryParams['limit'] = limit.toString();
      if (offset != null) queryParams['offset'] = offset.toString();
      if (orderBy != null) queryParams['order_by'] = orderBy;
      if (orderDesc != null) queryParams['order_desc'] = orderDesc.toString();

      final uri = Uri.parse('$baseUrl/api/strategies/runs')
          .replace(queryParameters: queryParams.isNotEmpty ? queryParams : null);

      final response = await _client
          .get(
            uri,
            headers: {'Content-Type': 'application/json'},
          )
          .timeout(timeout);

      if (response.statusCode == 200) {
        final jsonData = json.decode(response.body);
        return StrategyRunsResponse.fromJson(jsonData);
      } else {
        throw ApiException(
          'Failed to load strategy runs: ${response.statusCode}',
          response.statusCode,
        );
      }
    } catch (e) {
      if (e is ApiException) rethrow;
      throw ApiException('Network error: ${e.toString()}', 0);
    }
  }

  static Future<StrategyRunDetail> getStrategyRunDetail(String runId) async {
    try {
      final response = await _client
          .get(
            Uri.parse('$baseUrl/api/strategies/runs/$runId'),
            headers: {'Content-Type': 'application/json'},
          )
          .timeout(timeout);

      if (response.statusCode == 200) {
        final jsonData = json.decode(response.body);
        return StrategyRunDetail.fromJson(jsonData);
      } else {
        throw ApiException(
          'Failed to load strategy run detail: ${response.statusCode}',
          response.statusCode,
        );
      }
    } catch (e) {
      if (e is ApiException) rethrow;
      throw ApiException('Network error: ${e.toString()}', 0);
    }
  }

  static Future<StrategyResultsResponse> getStrategyRunResults(
    String runId, {
    bool? passed,
    double? minScore,
    double? maxScore,
    String? classification,
    String? ticker,
    String? sector,
    int? limit,
    int? offset,
    String? orderBy,
    bool? orderDesc,
  }) async {
    try {
      final queryParams = <String, String>{};
      if (passed != null) queryParams['passed'] = passed.toString();
      if (minScore != null) queryParams['min_score'] = minScore.toString();
      if (maxScore != null) queryParams['max_score'] = maxScore.toString();
      if (classification != null) queryParams['classification'] = classification;
      if (ticker != null) queryParams['ticker'] = ticker;
      if (sector != null) queryParams['sector'] = sector;
      if (limit != null) queryParams['limit'] = limit.toString();
      if (offset != null) queryParams['offset'] = offset.toString();
      if (orderBy != null) queryParams['order_by'] = orderBy;
      if (orderDesc != null) queryParams['order_desc'] = orderDesc.toString();

      final uri = Uri.parse('$baseUrl/api/strategies/runs/$runId/results')
          .replace(queryParameters: queryParams.isNotEmpty ? queryParams : null);

      final response = await _client
          .get(
            uri,
            headers: {'Content-Type': 'application/json'},
          )
          .timeout(timeout);

      if (response.statusCode == 200) {
        final jsonData = json.decode(response.body);
        return StrategyResultsResponse.fromJson(jsonData);
      } else {
        throw ApiException(
          'Failed to load strategy run results: ${response.statusCode}',
          response.statusCode,
        );
      }
    } catch (e) {
      if (e is ApiException) rethrow;
      throw ApiException('Network error: ${e.toString()}', 0);
    }
  }

  static Future<StrategyLatestResponse> getLatestStrategyRuns({
    String? strategyCodes,
    int? limit,
  }) async {
    try {
      final queryParams = <String, String>{};
      if (strategyCodes != null) queryParams['strategy_codes'] = strategyCodes;
      if (limit != null) queryParams['limit'] = limit.toString();

      final uri = Uri.parse('$baseUrl/api/strategies/latest')
          .replace(queryParameters: queryParams.isNotEmpty ? queryParams : null);

      final response = await _client
          .get(
            uri,
            headers: {'Content-Type': 'application/json'},
          )
          .timeout(timeout);

      if (response.statusCode == 200) {
        final jsonData = json.decode(response.body);
        return StrategyLatestResponse.fromJson(jsonData);
      } else {
        throw ApiException(
          'Failed to load latest strategy runs: ${response.statusCode}',
          response.statusCode,
        );
      }
    } catch (e) {
      if (e is ApiException) rethrow;
      throw ApiException('Network error: ${e.toString()}', 0);
    }
  }

  // Strategy Execution endpoints
  static Future<StrategyExecutionResponse> executeStrategy(
    StrategyExecutionRequest request,
  ) async {
    try {
      final response = await _client
          .post(
            Uri.parse('$baseUrl/api/strategies/execute'),
            headers: {'Content-Type': 'application/json'},
            body: json.encode(request.toJson()),
          )
          .timeout(timeout);

     if (response.statusCode == 200) {
        final jsonData = json.decode(response.body);
        return StrategyExecutionResponse.fromJson(jsonData);
      } else {
        throw ApiException(
          'Failed to execute strategy: ${response.statusCode}',
          response.statusCode,
        );
      }
    } catch (e) {
      if (e is ApiException) rethrow;
      throw ApiException('Network error: ${e.toString()}', 0);
    }
  }

  static Future<ExecutionStatus> getExecutionStatus(String runId) async {
    try {
      final response = await _client
          .get(
            Uri.parse('$baseUrl/api/strategies/status/$runId'),
            headers: {'Content-Type': 'application/json'},
          )
          .timeout(timeout);

      if (response.statusCode == 200) {
        final jsonData = json.decode(response.body);
        return ExecutionStatus.fromJson(jsonData);
      } else {
        throw ApiException(
          'Failed to get execution status: ${response.statusCode}',
          response.statusCode,
        );
      }
    } catch (e) {
      if (e is ApiException) rethrow;
      throw ApiException('Network error: ${e.toString()}', 0);
    }
  }

  static Future<Map<String, dynamic>> getStrategyExecutionResults(String runId) async {
    try {
      final response = await _client
          .get(
            Uri.parse('$baseUrl/api/strategies/results/$runId'),
            headers: {'Content-Type': 'application/json'},
          )
          .timeout(timeout);

      if (response.statusCode == 200) {
        final jsonData = json.decode(response.body);
        return jsonData;
      } else {
        throw ApiException(
          'Failed to get execution results: ${response.statusCode}',
          response.statusCode,
        );
      }
    } catch (e) {
      if (e is ApiException) rethrow;
      throw ApiException('Network error: ${e.toString()}', 0);
    }
  }

  static Future<ExecutionCancelResponse> cancelExecution(String runId) async {
    try {
      final response = await _client
          .post(
            Uri.parse('$baseUrl/api/strategies/cancel/$runId'),
            headers: {'Content-Type': 'application/json'},
          )
          .timeout(timeout);

      if (response.statusCode == 200) {
        final jsonData = json.decode(response.body);
        return ExecutionCancelResponse.fromJson(jsonData);
      } else {
        throw ApiException(
          'Failed to cancel execution: ${response.statusCode}',
          response.statusCode,
        );
      }
    } catch (e) {
      if (e is ApiException) rethrow;
      throw ApiException('Network error: ${e.toString()}', 0);
    }
  }

  static Future<ExecutionQueueResponse> getExecutionQueue() async {
    try {
      final response = await _client
          .get(
            Uri.parse('$baseUrl/api/strategies/queue'),
            headers: {'Content-Type': 'application/json'},
          )
          .timeout(timeout);

      if (response.statusCode == 200) {
        final jsonData = json.decode(response.body);
        return ExecutionQueueResponse.fromJson(jsonData);
      } else {
        throw ApiException(
          'Failed to get execution queue: ${response.statusCode}',
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