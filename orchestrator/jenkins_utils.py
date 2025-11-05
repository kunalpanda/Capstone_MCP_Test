# Add this to orchestrator/orchestrator.py or create a new file orchestrator/jenkins_utils.py

import re
from typing import Dict, List, Optional

def summarize_jenkins_console(console_log: str) -> Dict:
    """
    Intelligently summarize Jenkins console output by extracting only key information.
    
    Returns a structured summary with:
    - Build status
    - Triggered by
    - Branch/commit info
    - Test results summary
    - Failed tests (without full stack traces)
    - Build duration
    - Key errors
    """
    
    summary = {
        "triggered_by": None,
        "branch": None,
        "commit_sha": None,
        "commit_message": None,
        "build_status": None,
        "test_summary": {},
        "failed_tests": [],
        "errors": [],
        "duration": None,
        "key_stages": []
    }
    
    lines = console_log.split('\n')
    
    # Extract triggered by
    for line in lines[:20]:  # Check first 20 lines
        if "Started by user" in line:
            summary["triggered_by"] = line.replace("Started by user", "").strip()
            break
    
    # Extract branch and commit info
    for line in lines:
        if "Checking out Revision" in line:
            # Extract commit SHA and branch
            match = re.search(r'Revision (\w+) \((refs/remotes/origin/([^)]+))\)', line)
            if match:
                summary["commit_sha"] = match.group(1)
                summary["branch"] = match.group(3)
        
        if "Commit message:" in line:
            # Get the next line or extract from this line
            summary["commit_message"] = line.replace("Commit message:", "").strip().strip('"')
    
    # Extract test results summary
    test_summary_section = False
    for i, line in enumerate(lines):
        if "[INFO] T E S T S" in line:
            test_summary_section = True
        
        if test_summary_section:
            # Look for test class results
            if "Tests run:" in line and "in com.bankapp" in line:
                # Extract class name
                class_match = re.search(r'in ([\w.]+)', line)
                if class_match:
                    test_class = class_match.group(1)
                
                # Extract test counts
                counts_match = re.search(r'Tests run: (\d+), Failures: (\d+), Errors: (\d+), Skipped: (\d+)', line)
                if counts_match:
                    if test_class not in summary["test_summary"]:
                        summary["test_summary"][test_class] = {}
                    summary["test_summary"][test_class] = {
                        "total": int(counts_match.group(1)),
                        "failures": int(counts_match.group(2)),
                        "errors": int(counts_match.group(3)),
                        "skipped": int(counts_match.group(4))
                    }
    
    # Extract overall test summary
    for line in lines:
        if line.startswith("[ERROR] Tests run:"):
            match = re.search(r'Tests run: (\d+), Failures: (\d+), Errors: (\d+), Skipped: (\d+)', line)
            if match:
                summary["test_summary"]["TOTAL"] = {
                    "total": int(match.group(1)),
                    "failures": int(match.group(2)),
                    "errors": int(match.group(3)),
                    "skipped": int(match.group(4))
                }
    
    # Extract failed test details (without stack traces)
    failed_test = None
    capturing_error = False
    
    for i, line in enumerate(lines):
        # Detect failed test
        if "[ERROR]" in line and "Time elapsed:" in line and "FAILURE!" in line:
            # Extract test name and class
            test_match = re.search(r'([a-zA-Z.]+)\.([a-zA-Z]+)\s+Time elapsed:', line)
            if test_match:
                failed_test = {
                    "class": test_match.group(1),
                    "method": test_match.group(2),
                    "error_type": None,
                    "error_message": None
                }
                capturing_error = True
        
        # Capture error message (first line only)
        elif capturing_error and failed_test:
            # Look for the assertion error
            if "AssertionFailedError:" in line or "Exception:" in line:
                error_parts = line.split(":")
                if len(error_parts) >= 2:
                    failed_test["error_type"] = error_parts[0].strip().split(".")[-1]
                    failed_test["error_message"] = ":".join(error_parts[1:]).strip()
                
                summary["failed_tests"].append(failed_test)
                failed_test = None
                capturing_error = False
    
    # Extract build status
    for line in reversed(lines[-50:]):  # Check last 50 lines
        if "BUILD SUCCESS" in line:
            summary["build_status"] = "SUCCESS"
            break
        elif "BUILD FAILURE" in line:
            summary["build_status"] = "FAILURE"
            break
        elif "Finished: SUCCESS" in line:
            summary["build_status"] = "SUCCESS"
            break
        elif "Finished: FAILURE" in line:
            summary["build_status"] = "FAILURE"
            break
    
    # Extract duration
    for line in reversed(lines[-50:]):
        if "Total time:" in line:
            time_match = re.search(r'Total time:\s+([\d.]+\s+\w+)', line)
            if time_match:
                summary["duration"] = time_match.group(1)
                break
    
    # Extract key error messages
    for line in lines:
        if line.startswith("[ERROR] Failed to execute goal"):
            summary["errors"].append(line.replace("[ERROR]", "").strip())
    
    # Extract stage information
    current_stage = None
    for line in lines:
        if "[Pipeline] stage" in line and "{ (" in line:
            stage_match = re.search(r'\{ \(([^)]+)\)', line)
            if stage_match:
                current_stage = stage_match.group(1)
                if current_stage not in summary["key_stages"]:
                    summary["key_stages"].append(current_stage)
    
    return summary


def format_jenkins_summary(summary: Dict) -> str:
    """
    Format the summary dictionary into a readable string.
    """
    output = []
    
    output.append("=" * 60)
    output.append("JENKINS BUILD SUMMARY")
    output.append("=" * 60)
    
    # Build info
    if summary["triggered_by"]:
        output.append(f"👤 Triggered by: {summary['triggered_by']}")
    
    if summary["branch"]:
        output.append(f"🌿 Branch: {summary['branch']}")
    
    if summary["commit_sha"]:
        output.append(f"📝 Commit: {summary['commit_sha'][:8]}")
    
    if summary["commit_message"]:
        output.append(f"💬 Message: {summary['commit_message']}")
    
    if summary["duration"]:
        output.append(f"⏱️  Duration: {summary['duration']}")
    
    # Build status
    if summary["build_status"]:
        status_icon = "✅" if summary["build_status"] == "SUCCESS" else "❌"
        output.append(f"{status_icon} Status: {summary['build_status']}")
    
    output.append("")
    
    # Test summary
    if summary["test_summary"]:
        output.append("🧪 TEST RESULTS")
        output.append("-" * 60)
        
        for test_class, results in summary["test_summary"].items():
            if test_class == "TOTAL":
                output.append(f"\n📊 OVERALL: {results['total']} tests, "
                            f"{results['failures']} failures, "
                            f"{results['errors']} errors, "
                            f"{results['skipped']} skipped")
            else:
                status = "✅" if results['failures'] == 0 and results['errors'] == 0 else "❌"
                output.append(f"{status} {test_class}: "
                            f"{results['total']} tests, "
                            f"{results['failures']} failures")
    
    # Failed tests
    if summary["failed_tests"]:
        output.append("\n❌ FAILED TESTS")
        output.append("-" * 60)
        for test in summary["failed_tests"]:
            output.append(f"• {test['class']}.{test['method']}")
            if test['error_type']:
                output.append(f"  Type: {test['error_type']}")
            if test['error_message']:
                output.append(f"  Message: {test['error_message']}")
            output.append("")
    
    # Errors
    if summary["errors"]:
        output.append("🚨 BUILD ERRORS")
        output.append("-" * 60)
        for error in summary["errors"]:
            output.append(f"• {error}")
    
    # Stages
    if summary["key_stages"]:
        output.append("\n🔄 PIPELINE STAGES")
        output.append("-" * 60)
        output.append(", ".join(summary["key_stages"]))
    
    output.append("=" * 60)
    
    return "\n".join(output)


def get_summarized_console_output(console_log: str, format_output: bool = True) -> str:
    """
    Main function to get summarized Jenkins console output.
    
    Args:
        console_log: Raw Jenkins console output
        format_output: If True, return formatted string; if False, return JSON
    
    Returns:
        Formatted summary string or JSON
    """
    summary = summarize_jenkins_console(console_log)
    
    if format_output:
        return format_jenkins_summary(summary)
    else:
        import json
        return json.dumps(summary, indent=2)