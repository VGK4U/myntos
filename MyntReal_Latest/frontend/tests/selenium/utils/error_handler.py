"""
DC Protocol: Strict Error Handler for Selenium Tests
Stops on error, identifies root cause, and manages fix/re-validation flow
"""

import sys
import traceback
from datetime import datetime
from typing import Optional, List, Dict, Any, Callable
from enum import Enum


class ErrorSeverity(Enum):
    CRITICAL = 1
    ERROR = 2
    WARNING = 3
    INFO = 4


class TestError:
    """Represents a detected test error with full context"""
    
    def __init__(
        self,
        message: str,
        severity: ErrorSeverity,
        source: str = "unknown",
        url: str = "",
        screenshot_path: str = "",
        stack_trace: str = "",
        fix_suggestion: str = ""
    ):
        self.message = message
        self.severity = severity
        self.source = source
        self.url = url
        self.screenshot_path = screenshot_path
        self.stack_trace = stack_trace
        self.fix_suggestion = fix_suggestion
        self.timestamp = datetime.now()
        self.resolved = False
        
    def to_dict(self) -> Dict:
        return {
            'message': self.message,
            'severity': self.severity.name,
            'source': self.source,
            'url': self.url,
            'screenshot_path': self.screenshot_path,
            'stack_trace': self.stack_trace,
            'fix_suggestion': self.fix_suggestion,
            'timestamp': self.timestamp.isoformat(),
            'resolved': self.resolved
        }


class ErrorHandler:
    """
    DC Protocol: Strict error handling with stop-fix-validate flow
    """
    
    def __init__(self, browser_manager=None):
        self.browser = browser_manager
        self.errors: List[TestError] = []
        self.current_test: str = ""
        self.stop_on_error: bool = True
        self.max_retries: int = 3
        
    def set_current_test(self, test_name: str):
        """Set the current test context for error tracking"""
        self.current_test = test_name
        
    def detect_console_errors(self, ignore_network_errors: bool = True) -> List[TestError]:
        """Detect JavaScript console errors
        
        Args:
            ignore_network_errors: If True, ignore console errors about network responses
        """
        if not self.browser:
            return []
            
        detected = []
        self.browser.capture_console_logs()
        
        for error in self.browser.runtime_errors:
            message = error.get('message', 'Unknown console error')
            
            if ignore_network_errors:
                if '403' in message or '401' in message or '404' in message:
                    continue
                if 'status of 403' in message.lower() or 'status of 401' in message.lower():
                    continue
                if 'failed to load resource' in message.lower():
                    continue
                if '/api/v1/' in message:
                    continue
                if message.startswith('http://') or message.startswith('https://'):
                    continue
                
            test_error = TestError(
                message=message,
                severity=ErrorSeverity.ERROR,
                source='console',
                url=self.browser.get_current_url()
            )
            detected.append(test_error)
            self.errors.append(test_error)
            
        return detected
    
    def detect_network_errors(self, ignore_403: bool = True) -> List[TestError]:
        """Detect network/API errors
        
        Args:
            ignore_403: If True, treat 403 Forbidden as expected access control (not errors)
        """
        if not self.browser:
            return []
            
        detected = []
        self.browser.capture_network_errors()
        
        for error in self.browser.network_errors:
            status = error.get('status', 0)
            
            if status == 403 and ignore_403:
                continue
                
            if status >= 500:
                severity = ErrorSeverity.CRITICAL
            elif status == 401:
                severity = ErrorSeverity.WARNING
            else:
                severity = ErrorSeverity.ERROR
                
            test_error = TestError(
                message=f"HTTP {status} - {error.get('url', '')}",
                severity=severity,
                source='network',
                url=error.get('url', '')
            )
            detected.append(test_error)
            self.errors.append(test_error)
            
        return detected
    
    def detect_ui_errors(self) -> List[TestError]:
        """Detect UI-related errors (missing elements, broken layouts)"""
        detected = []
        
        if self.browser and self.browser.driver:
            try:
                error_elements = self.browser.driver.find_elements(
                    "css selector", 
                    ".error, .error-message, .alert-danger, [class*='error']"
                )
                for elem in error_elements:
                    if elem.is_displayed():
                        test_error = TestError(
                            message=f"UI Error Element: {elem.text[:100]}",
                            severity=ErrorSeverity.WARNING,
                            source='ui',
                            url=self.browser.get_current_url()
                        )
                        detected.append(test_error)
                        self.errors.append(test_error)
            except:
                pass
                
        return detected
    
    def run_all_detections(self) -> List[TestError]:
        """Run all error detection methods"""
        all_errors = []
        all_errors.extend(self.detect_console_errors())
        all_errors.extend(self.detect_network_errors())
        all_errors.extend(self.detect_ui_errors())
        return all_errors
    
    def should_stop(self) -> bool:
        """Check if execution should stop based on detected errors"""
        critical_errors = [e for e in self.errors if e.severity in [ErrorSeverity.CRITICAL, ErrorSeverity.ERROR] and not e.resolved]
        return self.stop_on_error and len(critical_errors) > 0
    
    def get_unresolved_errors(self) -> List[TestError]:
        """Get list of unresolved errors"""
        return [e for e in self.errors if not e.resolved]
    
    def mark_resolved(self, error: TestError):
        """Mark an error as resolved"""
        error.resolved = True
        
    def clear_errors(self):
        """Clear all tracked errors"""
        self.errors = []
        if self.browser:
            self.browser.runtime_errors = []
            self.browser.network_errors = []
    
    def print_error_report(self):
        """Print detailed error report"""
        if not self.errors:
            print("\n✅ No errors detected")
            return
            
        print("\n" + "="*60)
        print("❌ ERROR REPORT - DC Protocol")
        print("="*60)
        
        unresolved = self.get_unresolved_errors()
        resolved = [e for e in self.errors if e.resolved]
        
        print(f"\n📊 Summary:")
        print(f"   Total Errors: {len(self.errors)}")
        print(f"   Unresolved: {len(unresolved)}")
        print(f"   Resolved: {len(resolved)}")
        
        if unresolved:
            print(f"\n⚠️ UNRESOLVED ERRORS ({len(unresolved)}):")
            for i, error in enumerate(unresolved, 1):
                print(f"\n   {i}. [{error.severity.name}] {error.source.upper()}")
                print(f"      Message: {error.message[:100]}")
                print(f"      URL: {error.url}")
                print(f"      Time: {error.timestamp.strftime('%H:%M:%S')}")
                if error.fix_suggestion:
                    print(f"      Fix: {error.fix_suggestion}")
        
        print("="*60)
    
    def validate_no_errors(self) -> bool:
        """
        Validate that there are no console, network, or UI errors
        Returns True if validation passes (no errors)
        """
        self.run_all_detections()
        
        critical_errors = [
            e for e in self.get_unresolved_errors() 
            if e.severity in [ErrorSeverity.CRITICAL, ErrorSeverity.ERROR]
        ]
        
        if critical_errors:
            print(f"\n❌ VALIDATION FAILED: {len(critical_errors)} error(s) detected")
            return False
        
        print("\n✅ VALIDATION PASSED: No errors detected")
        return True
