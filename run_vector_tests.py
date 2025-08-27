#!/usr/bin/env python3
"""
Comprehensive Test Runner for ChromaDB Vector Integration
Runs all tests and generates detailed reports with findings and recommendations
"""

import sys
import os
import unittest
import time
import json
from io import StringIO
from datetime import datetime
import traceback

# Add project paths
sys.path.insert(0, '/home/ec2-user/redact-terraform')
sys.path.insert(0, '/home/ec2-user/redact-terraform/api_code')
sys.path.insert(0, '/home/ec2-user/redact-terraform/tests')

class TestResult:
    """Store test results for reporting"""
    
    def __init__(self):
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0
        self.skipped_tests = 0
        self.error_tests = 0
        self.test_details = []
        self.start_time = None
        self.end_time = None
        
    def add_result(self, test_name, status, message="", duration=0):
        """Add a test result"""
        self.test_details.append({
            "test_name": test_name,
            "status": status,
            "message": message,
            "duration": duration
        })
        
        self.total_tests += 1
        if status == "PASS":
            self.passed_tests += 1
        elif status == "FAIL":
            self.failed_tests += 1
        elif status == "SKIP":
            self.skipped_tests += 1
        elif status == "ERROR":
            self.error_tests += 1


class VectorTestRunner:
    """Test runner for vector integration tests"""
    
    def __init__(self):
        self.results = TestResult()
        self.report_file = None
        
    def check_dependencies(self):
        """Check if required dependencies are available"""
        dependencies = {
            "chromadb": False,
            "requests": False,
            "boto3": False,
            "psutil": False
        }
        
        print("=== Checking Dependencies ===")
        
        # Check ChromaDB
        try:
            import chromadb
            dependencies["chromadb"] = True
            print("✅ ChromaDB available")
        except ImportError:
            print("❌ ChromaDB not available")
            print("   Install: pip install chromadb")
        
        # Check requests
        try:
            import requests
            dependencies["requests"] = True
            print("✅ requests available")
        except ImportError:
            print("❌ requests not available")
        
        # Check boto3
        try:
            import boto3
            dependencies["boto3"] = True
            print("✅ boto3 available")
        except ImportError:
            print("❌ boto3 not available")
        
        # Check psutil (optional)
        try:
            import psutil
            dependencies["psutil"] = True
            print("✅ psutil available (for performance monitoring)")
        except ImportError:
            print("⚠️  psutil not available (performance monitoring limited)")
        
        return dependencies
    
    def run_test_suite(self, test_module_name, test_class_name=None):
        """Run a specific test suite"""
        suite_start = time.time()
        print(f"\n{'='*60}")
        print(f"Running Test Suite: {test_module_name}")
        print(f"{'='*60}")
        
        try:
            # Import the test module
            test_module = __import__(test_module_name)
            
            # Create test loader
            loader = unittest.TestLoader()
            
            if test_class_name:
                # Load specific test class
                test_class = getattr(test_module, test_class_name)
                suite = loader.loadTestsFromTestCase(test_class)
            else:
                # Load all tests from module
                suite = loader.loadTestsFromModule(test_module)
            
            # Create custom test result to capture details
            stream = StringIO()
            runner = unittest.TextTestRunner(stream=stream, verbosity=2)
            result = runner.run(suite)
            
            # Process results
            suite_duration = time.time() - suite_start
            
            for test, error in result.errors:
                test_name = f"{test_module_name}.{test._testMethodName}"
                self.results.add_result(test_name, "ERROR", str(error), 0)
            
            for test, failure in result.failures:
                test_name = f"{test_module_name}.{test._testMethodName}"
                self.results.add_result(test_name, "FAIL", str(failure), 0)
            
            # Count successful tests
            successful_tests = result.testsRun - len(result.errors) - len(result.failures) - len(result.skipped)
            for i in range(successful_tests):
                self.results.add_result(f"{test_module_name}.test_{i}", "PASS", "", 0)
            
            # Count skipped tests
            for test, reason in result.skipped:
                test_name = f"{test_module_name}.{test._testMethodName}"
                self.results.add_result(test_name, "SKIP", reason, 0)
            
            print(f"Suite completed in {suite_duration:.2f}s")
            print(f"Tests run: {result.testsRun}, Errors: {len(result.errors)}, Failures: {len(result.failures)}, Skipped: {len(result.skipped)}")
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to run test suite {test_module_name}: {e}")
            traceback.print_exc()
            return False
    
    def run_all_tests(self):
        """Run all vector integration tests"""
        self.results.start_time = datetime.now()
        
        print("🚀 Starting Comprehensive ChromaDB Vector Integration Test Suite")
        print(f"Start time: {self.results.start_time}")
        
        # Check dependencies first
        dependencies = self.check_dependencies()
        
        # Define test suites in order of execution
        test_suites = [
            ("test_auth_utils", None, "Authentication utilities"),
            ("test_chromadb_client", None, "ChromaDB client unit tests"),
            ("test_vector_api_integration", None, "Vector API integration tests"),
            ("test_vector_performance", None, "Performance tests"),
            ("test_vector_security", None, "Security and isolation tests"),
            ("test_vector_export", None, "Export functionality tests")
        ]
        
        # Run each test suite
        for module_name, class_name, description in test_suites:
            print(f"\n📋 {description}")
            success = self.run_test_suite(module_name, class_name)
            if not success:
                print(f"⚠️  Suite {module_name} had issues")
        
        # Run live API tests separately
        self.run_live_api_tests()
        
        self.results.end_time = datetime.now()
        total_duration = (self.results.end_time - self.results.start_time).total_seconds()
        
        print(f"\n🏁 All tests completed in {total_duration:.1f}s")
        
        # Generate report
        self.generate_report()
    
    def run_live_api_tests(self):
        """Run live API tests against deployed endpoints"""
        print(f"\n{'='*60}")
        print("Running Live API Tests")
        print(f"{'='*60}")
        
        try:
            # Test the existing endpoint test script
            from test_vector_endpoints import main as test_endpoints_main
            
            # Capture output
            original_stdout = sys.stdout
            sys.stdout = captured_output = StringIO()
            
            try:
                test_endpoints_main()
                output = captured_output.getvalue()
                
                # Parse results from output
                if "🎉" in output:
                    self.results.add_result("live_api_tests", "PASS", "All live endpoints responding", 0)
                else:
                    self.results.add_result("live_api_tests", "FAIL", "Some live endpoints not responding", 0)
                    
            except Exception as e:
                self.results.add_result("live_api_tests", "ERROR", str(e), 0)
            finally:
                sys.stdout = original_stdout
                
        except ImportError as e:
            print(f"⚠️  Live API tests not available: {e}")
            self.results.add_result("live_api_tests", "SKIP", "Test script not available", 0)
    
    def generate_report(self):
        """Generate comprehensive test report"""
        report_filename = f"vector_integration_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        self.report_file = report_filename
        
        # Calculate success rate
        success_rate = (self.results.passed_tests / self.results.total_tests * 100) if self.results.total_tests > 0 else 0
        
        # Create detailed report
        report = {
            "test_run_info": {
                "start_time": self.results.start_time.isoformat(),
                "end_time": self.results.end_time.isoformat(),
                "total_duration_seconds": (self.results.end_time - self.results.start_time).total_seconds(),
                "report_generated": datetime.now().isoformat()
            },
            "summary": {
                "total_tests": self.results.total_tests,
                "passed_tests": self.results.passed_tests,
                "failed_tests": self.results.failed_tests,
                "skipped_tests": self.results.skipped_tests,
                "error_tests": self.results.error_tests,
                "success_rate_percent": round(success_rate, 2)
            },
            "test_details": self.results.test_details,
            "findings": self.analyze_results(),
            "recommendations": self.generate_recommendations(),
            "deployment_status": self.assess_deployment_status()
        }
        
        # Save report
        with open(report_filename, 'w') as f:
            json.dump(report, f, indent=2)
        
        # Print summary
        self.print_report_summary(report)
        
        return report
    
    def analyze_results(self):
        """Analyze test results and generate findings"""
        findings = {
            "critical_issues": [],
            "warnings": [],
            "successes": [],
            "performance_notes": []
        }
        
        # Analyze by test type
        chromadb_tests = [t for t in self.results.test_details if "chromadb_client" in t["test_name"]]
        api_tests = [t for t in self.results.test_details if "api_integration" in t["test_name"]]
        security_tests = [t for t in self.results.test_details if "security" in t["test_name"]]
        performance_tests = [t for t in self.results.test_details if "performance" in t["test_name"]]
        export_tests = [t for t in self.results.test_details if "export" in t["test_name"]]
        
        # Critical issues
        failed_critical = [t for t in chromadb_tests + api_tests if t["status"] == "FAIL"]
        if failed_critical:
            findings["critical_issues"].append({
                "issue": "Core functionality tests failed",
                "impact": "HIGH",
                "affected_tests": len(failed_critical),
                "description": "Basic ChromaDB or API functionality is not working"
            })
        
        # Security issues
        failed_security = [t for t in security_tests if t["status"] == "FAIL"]
        if failed_security:
            findings["critical_issues"].append({
                "issue": "Security test failures",
                "impact": "HIGH", 
                "affected_tests": len(failed_security),
                "description": "User isolation or security boundaries may be compromised"
            })
        
        # Performance warnings
        slow_performance = [t for t in performance_tests if t["status"] == "FAIL"]
        if slow_performance:
            findings["warnings"].append({
                "issue": "Performance concerns",
                "impact": "MEDIUM",
                "affected_tests": len(slow_performance),
                "description": "Some operations may be slower than expected"
            })
        
        # Successes
        if self.results.passed_tests > 0:
            findings["successes"].append({
                "achievement": "Basic functionality working",
                "tests_passed": self.results.passed_tests,
                "description": f"{self.results.passed_tests} tests passed successfully"
            })
        
        return findings
    
    def generate_recommendations(self):
        """Generate recommendations based on test results"""
        recommendations = {
            "immediate_actions": [],
            "improvements": [],
            "monitoring": [],
            "next_steps": []
        }
        
        # Immediate actions based on failures
        if self.results.failed_tests > 0:
            recommendations["immediate_actions"].append({
                "priority": "HIGH",
                "action": "Fix failing tests",
                "description": f"{self.results.failed_tests} tests are failing and need immediate attention",
                "estimated_effort": "2-4 hours"
            })
        
        if self.results.error_tests > 0:
            recommendations["immediate_actions"].append({
                "priority": "HIGH", 
                "action": "Resolve test errors",
                "description": f"{self.results.error_tests} tests have errors that prevent proper execution",
                "estimated_effort": "1-2 hours"
            })
        
        # Improvements
        if self.results.skipped_tests > 0:
            recommendations["improvements"].append({
                "priority": "MEDIUM",
                "action": "Enable skipped tests",
                "description": f"{self.results.skipped_tests} tests were skipped, likely due to missing dependencies",
                "estimated_effort": "1-3 hours"
            })
        
        # Monitoring recommendations
        recommendations["monitoring"].append({
            "metric": "Vector storage performance",
            "description": "Monitor response times for vector operations",
            "threshold": "< 5 seconds for batches of 100 chunks"
        })
        
        recommendations["monitoring"].append({
            "metric": "User isolation",
            "description": "Regular testing of user data isolation",
            "frequency": "Weekly"
        })
        
        # Next steps
        success_rate = (self.results.passed_tests / self.results.total_tests * 100) if self.results.total_tests > 0 else 0
        
        if success_rate >= 80:
            recommendations["next_steps"].append({
                "step": "Deploy to production",
                "description": "Test results indicate the system is ready for production deployment",
                "prerequisites": ["Fix any critical issues", "Performance optimization"]
            })
        elif success_rate >= 60:
            recommendations["next_steps"].append({
                "step": "Staged deployment",
                "description": "Deploy to staging environment for additional testing",
                "prerequisites": ["Fix failing tests", "Address security concerns"]
            })
        else:
            recommendations["next_steps"].append({
                "step": "Development focus",
                "description": "Continue development and testing before deployment",
                "prerequisites": ["Fix major issues", "Improve test coverage"]
            })
        
        return recommendations
    
    def assess_deployment_status(self):
        """Assess readiness for deployment"""
        success_rate = (self.results.passed_tests / self.results.total_tests * 100) if self.results.total_tests > 0 else 0
        
        # Check critical areas
        has_security_failures = any("security" in t["test_name"] and t["status"] == "FAIL" for t in self.results.test_details)
        has_api_failures = any("api" in t["test_name"] and t["status"] == "FAIL" for t in self.results.test_details)
        has_chromadb_failures = any("chromadb" in t["test_name"] and t["status"] == "FAIL" for t in self.results.test_details)
        
        if success_rate >= 90 and not has_security_failures:
            status = "READY"
            confidence = "HIGH"
        elif success_rate >= 80 and not has_security_failures and not has_api_failures:
            status = "MOSTLY_READY"
            confidence = "MEDIUM"
        elif success_rate >= 60:
            status = "NEEDS_WORK"
            confidence = "LOW"
        else:
            status = "NOT_READY"
            confidence = "VERY_LOW"
        
        return {
            "status": status,
            "confidence": confidence,
            "success_rate": success_rate,
            "critical_issues": {
                "security_failures": has_security_failures,
                "api_failures": has_api_failures,
                "chromadb_failures": has_chromadb_failures
            },
            "recommendation": self.get_deployment_recommendation(status)
        }
    
    def get_deployment_recommendation(self, status):
        """Get deployment recommendation based on status"""
        recommendations = {
            "READY": "System is ready for production deployment. Proceed with confidence.",
            "MOSTLY_READY": "System is mostly ready. Address minor issues before production deployment.",
            "NEEDS_WORK": "System needs additional work before deployment. Focus on fixing failing tests.",
            "NOT_READY": "System is not ready for deployment. Significant issues need resolution."
        }
        return recommendations.get(status, "Unknown status")
    
    def print_report_summary(self, report):
        """Print a summary of the test report"""
        print(f"\n{'='*80}")
        print("📊 COMPREHENSIVE TEST REPORT SUMMARY")
        print(f"{'='*80}")
        
        # Summary statistics
        summary = report["summary"]
        print(f"\n📈 Test Results:")
        print(f"   Total Tests: {summary['total_tests']}")
        print(f"   ✅ Passed: {summary['passed_tests']}")
        print(f"   ❌ Failed: {summary['failed_tests']}")
        print(f"   ⚠️  Errors: {summary['error_tests']}")
        print(f"   ⏭️  Skipped: {summary['skipped_tests']}")
        print(f"   📊 Success Rate: {summary['success_rate_percent']}%")
        
        # Deployment status
        deployment = report["deployment_status"]
        status_emoji = {"READY": "🟢", "MOSTLY_READY": "🟡", "NEEDS_WORK": "🟠", "NOT_READY": "🔴"}
        print(f"\n🚀 Deployment Status: {status_emoji.get(deployment['status'], '❓')} {deployment['status']}")
        print(f"   Confidence: {deployment['confidence']}")
        print(f"   Recommendation: {deployment['recommendation']}")
        
        # Critical findings
        findings = report["findings"]
        if findings["critical_issues"]:
            print(f"\n🚨 Critical Issues ({len(findings['critical_issues'])}):")
            for issue in findings["critical_issues"]:
                print(f"   • {issue['issue']} (Impact: {issue['impact']})")
        
        if findings["warnings"]:
            print(f"\n⚠️  Warnings ({len(findings['warnings'])}):")
            for warning in findings["warnings"]:
                print(f"   • {warning['issue']} (Impact: {warning['impact']})")
        
        # Immediate actions
        recommendations = report["recommendations"]
        if recommendations["immediate_actions"]:
            print(f"\n🎯 Immediate Actions Required:")
            for action in recommendations["immediate_actions"]:
                print(f"   • {action['action']} (Priority: {action['priority']})")
                print(f"     {action['description']}")
        
        # Report file location
        print(f"\n📄 Detailed report saved to: {self.report_file}")
        
        print(f"\n{'='*80}")
        print("🎯 Test run completed. Review the detailed report for full analysis.")
        print(f"{'='*80}")


def main():
    """Run the comprehensive test suite"""
    print("ChromaDB Vector Integration - Comprehensive Test Suite")
    print("=" * 60)
    
    # Create test runner
    runner = VectorTestRunner()
    
    # Run all tests
    runner.run_all_tests()
    
    return runner.report_file


if __name__ == "__main__":
    report_file = main()
    print(f"\nTest report generated: {report_file}")