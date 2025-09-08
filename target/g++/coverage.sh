#!/usr/bin/env bash

set -euo pipefail

# Accept working directory parameter
WORK_DIR="$1"

if [ -z "$WORK_DIR" ]; then
    echo "Usage: $0 <work_dir>"
    exit 1
fi

get_project_root() {
    local script_dir
    script_dir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
    echo "$(dirname "$(dirname "$script_dir")")"
}

PROJECT_ROOT="$(get_project_root)"

# Get GCC related paths
GCOV_PATH="${PROJECT_ROOT}/target/g++/GCC-13-COVERAGE/bin/gcov"

# Check if gcov tool exists
if [ ! -f "$GCOV_PATH" ]; then
    echo "Error: gcov tool not found at $GCOV_PATH"
    exit 1
fi

# Coverage data directory in working directory
COVERAGE_DIR="${PROJECT_ROOT}/target/g++/gcc-coverage-build/gcc"

# Check if coverage directory exists
if [ ! -d "$COVERAGE_DIR" ]; then
    echo "0"
    exit 1
fi

# Enter coverage directory in working directory
cd "$COVERAGE_DIR"


# Run lcov command to collect coverage data
lcov --capture --directory . --output-file coverage.info --gcov-tool "$GCOV_PATH" >/dev/null 2>&1

# Check if coverage information was successfully generated
if [ ! -f "coverage.info" ] || [ ! -s "coverage.info" ]; then
    echo "0"
    exit 1
fi

# Generate coverage summary
COVERAGE_SUMMARY=$(lcov --summary coverage.info 2>/dev/null)

# Extract covered lines from summary
COVERED_LINES=$(echo "$COVERAGE_SUMMARY" | grep "lines......:" | sed 's/.*(\([0-9]*\).*/\1/')

# If no covered lines found, default to 0
if [ -z "$COVERED_LINES" ]; then
    COVERED_LINES=0
fi

# Only output covered lines
echo "${COVERED_LINES}"

