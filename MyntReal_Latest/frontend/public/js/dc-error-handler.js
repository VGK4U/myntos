/**
 * DC Protocol Error Handler - Document Control v1.0.0
 * Semantic error logging with audit trails and error severity classification
 * Applied to: Journey Pages (8 pages), Location Trackers, Task Tracker
 * WVV Compliance: Work Verification & Validation with zero negative impact
 */

class DCErrorHandler {
  constructor() {
    this.errorLog = [];
    this.maxLogs = 1000;
    this.errorCodes = {
      // Journey Errors
      'JRN_AUTH_001': { severity: 'CRITICAL', message: 'Authentication token missing', category: 'AUTH' },
      'JRN_AUTH_002': { severity: 'CRITICAL', message: 'Session expired during operation', category: 'AUTH' },
      'JRN_NET_001': { severity: 'ERROR', message: 'Network error - API call failed', category: 'NETWORK' },
      'JRN_NET_002': { severity: 'ERROR', message: 'Network timeout', category: 'NETWORK' },
      'JRN_DATA_001': { severity: 'WARNING', message: 'Data validation failed', category: 'DATA' },
      'JRN_DATA_002': { severity: 'WARNING', message: 'Missing required fields', category: 'DATA' },
      'JRN_PARSE_001': { severity: 'ERROR', message: 'JSON parsing error', category: 'PARSE' },
      'JRN_LOAD_001': { severity: 'WARNING', message: 'Failed to load journeys', category: 'LOAD' },
      'JRN_LOAD_002': { severity: 'WARNING', message: 'Failed to load statistics', category: 'LOAD' },
      'JRN_LOAD_003': { severity: 'WARNING', message: 'Failed to load departments', category: 'LOAD' },
      'JRN_LOAD_004': { severity: 'WARNING', message: 'Failed to load team members', category: 'LOAD' },
      
      // Location Tracker Errors
      'LOC_GPS_001': { severity: 'WARNING', message: 'GPS location data unavailable', category: 'GPS' },
      'LOC_GPS_002': { severity: 'ERROR', message: 'GPS accuracy below threshold', category: 'GPS' },
      'LOC_HIST_001': { severity: 'WARNING', message: 'Failed to load location history', category: 'HISTORY' },
      'LOC_EXPORT_001': { severity: 'WARNING', message: 'Export operation failed', category: 'EXPORT' },
      
      // Task Tracker Errors
      'TSK_LOAD_001': { severity: 'WARNING', message: 'Failed to load tasks', category: 'LOAD' },
      'TSK_LOAD_002': { severity: 'WARNING', message: 'Failed to load analytics', category: 'LOAD' },
      'TSK_LOAD_003': { severity: 'WARNING', message: 'Failed to load statistics', category: 'LOAD' },
    };
  }

  /**
   * Generate semantic DC error code
   * Format: MODULE_TYPE_SEQ (e.g., JRN_AUTH_001)
   */
  generateErrorCode(module, type, sequence) {
    return `${module}_${type}_${String(sequence).padStart(3, '0')}`;
  }

  /**
   * Log error with DC Protocol compliance
   * @param {string} errorCode - Semantic DC error code (JRN_AUTH_001, etc.)
   * @param {string} functionName - Function where error occurred
   * @param {Error|string} error - Error object or message
   * @param {object} context - Additional context (endpoint, payload, etc.)
   */
  logError(errorCode, functionName, error, context = {}) {
    const timestamp = new Date().toISOString();
    const errorInfo = this.errorCodes[errorCode] || {
      severity: 'INFO',
      message: 'Unknown error',
      category: 'MISC'
    };

    const logEntry = {
      timestamp,
      errorCode,
      functionName,
      severity: errorInfo.severity,
      category: errorInfo.category,
      message: errorInfo.message,
      details: error instanceof Error ? error.message : String(error),
      context: this.sanitizeContext(context),
      userAgent: navigator.userAgent.substring(0, 100),
      url: window.location.pathname,
    };

    // Add to in-memory log
    this.errorLog.push(logEntry);
    if (this.errorLog.length > this.maxLogs) {
      this.errorLog.shift();
    }

    // Console logging with color-coded severity
    this.consoleLog(errorCode, logEntry);

    // Store in localStorage for audit trail (last 50 errors)
    this.storeInLocalStorage(logEntry);

    return logEntry;
  }

  /**
   * Sanitize context to prevent logging sensitive data
   */
  sanitizeContext(context) {
    const sanitized = { ...context };
    const sensitiveKeys = ['password', 'token', 'secret', 'apiKey', 'authorization'];
    
    Object.keys(sanitized).forEach(key => {
      if (sensitiveKeys.some(s => key.toLowerCase().includes(s))) {
        sanitized[key] = '[REDACTED]';
      }
    });
    
    return sanitized;
  }

  /**
   * Color-coded console logging by severity
   */
  consoleLog(errorCode, logEntry) {
    const colors = {
      'CRITICAL': '#ff3333',
      'ERROR': '#ff6600',
      'WARNING': '#ffaa00',
      'INFO': '#3366ff'
    };

    const color = colors[logEntry.severity] || '#999999';
    const icon = this.getSeverityIcon(logEntry.severity);

    console.error(
      `%c[DC-${errorCode}] ${icon} ${logEntry.message} in ${logEntry.functionName}`,
      `color: ${color}; font-weight: bold; font-size: 12px;`,
      logEntry
    );
  }

  /**
   * Get severity icon
   */
  getSeverityIcon(severity) {
    const icons = {
      'CRITICAL': '🚨',
      'ERROR': '❌',
      'WARNING': '⚠️',
      'INFO': 'ℹ️'
    };
    return icons[severity] || '❓';
  }

  /**
   * Store error in localStorage for audit trail
   */
  storeInLocalStorage(logEntry) {
    try {
      const key = 'dc_error_audit_trail';
      let trail = JSON.parse(localStorage.getItem(key) || '[]');
      trail.push(logEntry);
      if (trail.length > 50) {
        trail = trail.slice(-50);
      }
      localStorage.setItem(key, JSON.stringify(trail));
    } catch (e) {
      // Silently fail if localStorage is full
    }
  }

  /**
   * Handle API response errors with DC Protocol codes
   */
  handleResponseError(functionName, response, context = {}) {
    const status = response?.status;
    let errorCode;

    if (status === 401 || status === 403) {
      errorCode = 'JRN_AUTH_002';
    } else if (status === 400) {
      errorCode = 'JRN_DATA_001';
    } else if (status >= 500) {
      errorCode = 'JRN_NET_001';
    } else {
      errorCode = 'JRN_NET_001';
    }

    return this.logError(errorCode, functionName, `HTTP ${status}`, {
      ...context,
      httpStatus: status
    });
  }

  /**
   * Get formatted audit trail for admin review
   */
  getAuditTrail() {
    return this.errorLog.slice(-100);
  }

  /**
   * Export error log as JSON (for debugging)
   */
  exportErrorLog() {
    return JSON.stringify(this.getAuditTrail(), null, 2);
  }

  /**
   * Clear error log (admin only)
   */
  clearErrorLog() {
    this.errorLog = [];
    localStorage.removeItem('dc_error_audit_trail');
  }
}

// Global instance
const dcErrorHandler = new DCErrorHandler();
