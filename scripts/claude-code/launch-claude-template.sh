#!/bin/bash
# Claude Code Launch Template for TracLine
# Copy this file for each AI developer (e.g., launch-claude-ai1.sh, launch-claude-ai2.sh)

# ==============================================================================
# TracLine Development Environment Setup
# ==============================================================================

# Set up TracLine environment variables
export PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

# AI Developer Configuration - CUSTOMIZE THESE
export TASK_ASSIGNEE="AI-Developer-1"  # Change this for each AI developer
export MEMBER_ID="AI-Developer-1"      # Same as TASK_ASSIGNEE
export MEMBER_ROLE="ENGINEER"          # ENGINEER, DESIGNER, PM, QA, etc.
export TRACLINE_PROJECT_ID="MAIN-PROJECT"  # Your project ID

# TracLine configuration file
export CLAUDE_CONTEXT_FILE="${PROJECT_ROOT}/CLAUDE.md"
export ANTHROPIC_INIT_FILE="$CLAUDE_CONTEXT_FILE"

echo "🤖 TracLine Development Environment"
echo "Project: ${TRACLINE_PROJECT_ID}"
echo "Member: ${MEMBER_ID} (${MEMBER_ROLE})"
echo "Root: ${PROJECT_ROOT}"
echo "Context: ${CLAUDE_CONTEXT_FILE}"

# Verify TracLine installation
if ! command -v tracline &> /dev/null; then
    echo "⚠️  TracLine CLI not found. Installing..."
    cd "${PROJECT_ROOT}" && pip install -e .
fi

# Launch Claude Code
echo "🚀 Launching Claude Code for ${TASK_ASSIGNEE}..."
claude --dangerously-skip-permissions