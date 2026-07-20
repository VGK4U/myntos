"""
DC Protocol: Test Runner with Strict Error Handling
Executes tests with stop-on-error, fix verification, and re-validation
"""

import time
import sys
from datetime import datetime
from typing import Callable, List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

from utils.browser_manager import BrowserManager
from utils.error_handler import ErrorHandler, ErrorSeverity, TestError
from config.settings import BASE_URL


class TestStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    BLOCKED = "blocked"
    SKIPPED = "skipped"


@dataclass
class TestResult:
    name: str
    status: TestStatus
    duration: float = 0.0
    errors: List[TestError] = None
    screenshot_path: str = ""
    url: str = ""
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []


class TestRunner:
    """
    DC Protocol: Strict Test Runner with Real-time Monitoring
    Stops on error, validates fixes, ensures 100% pass before proceeding
    """
    
    def __init__(self, headless: bool = False, vnc_mode: bool = False):
        self.headless = headless
        self.vnc_mode = vnc_mode
        self.browser: Optional[BrowserManager] = None
        self.error_handler: Optional[ErrorHandler] = None
        self.results: List[TestResult] = []
        self.current_test: str = ""
        self.stop_on_first_error: bool = True
        
    def setup(self):
        """Initialize browser and error handler"""
        self.browser = BrowserManager(headless=self.headless, vnc_mode=self.vnc_mode)
        self.browser.setup()
        self.error_handler = ErrorHandler(self.browser)
        
    def teardown(self):
        """Cleanup resources"""
        if self.browser:
            self.browser.cleanup()
            
    def run_test(self, test_name: str, test_func: Callable, *args, **kwargs) -> TestResult:
        """
        Run a single test with full error monitoring
        Stops immediately on any error detection
        """
        print(f"\n{'='*60}")
        print(f"🧪 TEST: {test_name}")
        print(f"{'='*60}")
        
        self.current_test = test_name
        self.error_handler.set_current_test(test_name)
        self.error_handler.clear_errors()
        
        start_time = time.time()
        result = TestResult(name=test_name, status=TestStatus.RUNNING)
        
        try:
            test_func(*args, **kwargs)
            
            self.browser.dismiss_alert()
            time.sleep(1)
            
            self.error_handler.run_all_detections()
            
            if self.error_handler.should_stop():
                result.status = TestStatus.FAILED
                result.errors = self.error_handler.get_unresolved_errors()
                result.screenshot_path = self.browser.take_screenshot(f"FAIL_{test_name}")
                print(f"\n❌ TEST FAILED: {test_name}")
                print(f"   Errors detected: {len(result.errors)}")
                
                self.error_handler.print_error_report()
                
                if self.stop_on_first_error:
                    print("\n⛔ EXECUTION STOPPED - Fix required before proceeding")
                    return result
            else:
                result.status = TestStatus.PASSED
                print(f"\n✅ TEST PASSED: {test_name}")
                
        except Exception as e:
            result.status = TestStatus.FAILED
            result.errors = [TestError(
                message=str(e),
                severity=ErrorSeverity.CRITICAL,
                source='exception',
                stack_trace=str(e)
            )]
            result.screenshot_path = self.browser.take_screenshot(f"ERROR_{test_name}")
            print(f"\n❌ TEST ERROR: {test_name}")
            print(f"   Exception: {str(e)[:100]}")
            
        finally:
            result.duration = time.time() - start_time
            result.url = self.browser.get_current_url()
            self.results.append(result)
            
        return result
    
    def run_test_suite(self, tests: List[tuple]) -> Dict:
        """
        Run a suite of tests with strict error handling
        Stops on first error and requires fix before continuing
        
        Args:
            tests: List of (test_name, test_func, args, kwargs) tuples
        """
        print("\n" + "="*70)
        print("🔬 SELENIUM TEST SUITE - DC Protocol Strict Mode")
        print("="*70)
        print(f"   Mode: {'Headless' if self.headless else 'VISIBLE BROWSER'}")
        print(f"   Base URL: {BASE_URL}")
        print(f"   Tests to run: {len(tests)}")
        print(f"   Stop on error: {self.stop_on_first_error}")
        print("="*70)
        
        suite_start = time.time()
        blocked_count = 0
        
        try:
            self.setup()
            
            for i, test_item in enumerate(tests, 1):
                if len(test_item) == 2:
                    test_name, test_func = test_item
                    args, kwargs = (), {}
                elif len(test_item) == 3:
                    test_name, test_func, args = test_item
                    kwargs = {}
                else:
                    test_name, test_func, args, kwargs = test_item
                
                print(f"\n[{i}/{len(tests)}] Running: {test_name}")
                
                result = self.run_test(test_name, test_func, *args, **kwargs)
                
                if result.status == TestStatus.FAILED and self.stop_on_first_error:
                    for remaining in tests[i:]:
                        remaining_name = remaining[0]
                        self.results.append(TestResult(
                            name=remaining_name,
                            status=TestStatus.BLOCKED
                        ))
                        blocked_count += 1
                    break
                    
        except Exception as e:
            print(f"\n❌ SUITE ERROR: {e}")
            
        finally:
            self.teardown()
            
        suite_duration = time.time() - suite_start
        
        passed = sum(1 for r in self.results if r.status == TestStatus.PASSED)
        failed = sum(1 for r in self.results if r.status == TestStatus.FAILED)
        blocked = sum(1 for r in self.results if r.status == TestStatus.BLOCKED)
        
        summary = {
            'total': len(tests),
            'passed': passed,
            'failed': failed,
            'blocked': blocked,
            'duration': suite_duration,
            'results': [r.__dict__ for r in self.results],
            'success': failed == 0 and blocked == 0
        }
        
        self.print_summary(summary)
        return summary
    
    def print_summary(self, summary: Dict):
        """Print test execution summary"""
        print("\n" + "="*70)
        print("📊 TEST EXECUTION SUMMARY")
        print("="*70)
        print(f"   Total Tests: {summary['total']}")
        print(f"   ✅ Passed: {summary['passed']}")
        print(f"   ❌ Failed: {summary['failed']}")
        print(f"   ⏸️ Blocked: {summary['blocked']}")
        print(f"   ⏱️ Duration: {summary['duration']:.2f}s")
        print("="*70)
        
        if summary['failed'] > 0:
            print("\n⚠️ ERRORS REQUIRE ATTENTION:")
            for result in self.results:
                if result.status == TestStatus.FAILED and result.errors:
                    print(f"\n   📍 {result.name}:")
                    for error in result.errors[:3]:
                        print(f"      - {error.message[:80]}")
            print("\n⛔ Fix all errors and re-run validation before proceeding")
        else:
            print("\n✅ ALL TESTS PASSED - Ready to proceed")
        
        print("="*70)
        
    def validate_fix(self, test_name: str, test_func: Callable, *args, **kwargs) -> bool:
        """
        Re-run a specific test to validate a fix
        Returns True if the test passes
        """
        print(f"\n🔄 RE-VALIDATING: {test_name}")
        
        self.results = []
        result = self.run_test(test_name, test_func, *args, **kwargs)
        
        if result.status == TestStatus.PASSED:
            print(f"✅ FIX VALIDATED: {test_name}")
            return True
        else:
            print(f"❌ FIX NOT COMPLETE: {test_name}")
            return False
