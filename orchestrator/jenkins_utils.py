# =============================================================================
# DEPRECATED - This file is no longer used
# =============================================================================
#
# This file contained regex-based console log parsing that was:
# 1. Language-specific (only worked for Maven/Java output)
# 2. Brittle (broke when pipeline format changed)
# 3. Redundant (Claude can interpret raw logs naturally)
#
# The new approach (implemented Nov 2025):
# - Jenkins MCP server: Smart truncation at 50k chars (head + tail)
# - Orchestrator: Pass raw logs directly to Claude
# - Claude: Interprets any console output format (language-agnostic)
#
# This file can be safely deleted. Kept temporarily for reference.
# =============================================================================

raise ImportError(
    "jenkins_utils.py is deprecated. "
    "Console logs are now passed directly to Claude for language-agnostic analysis. "
    "Please remove this import from your code."
)
