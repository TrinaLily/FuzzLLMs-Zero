#!/usr/bin/env bash

# Accept working directory parameter
WORK_DIR="$1"
SOURCE_FILE="$2"

if [ -z "$WORK_DIR" ] || [ -z "$SOURCE_FILE" ]; then
    echo "Usage: $0 <work_dir> <source_file>"
    exit 1
fi

get_project_root() {
    local script_dir
    script_dir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
    echo "$(dirname "$(dirname "$script_dir")")"
}

PROJECT_ROOT="$(get_project_root)"

# Get GCC compiler path
GCC_PATH="${PROJECT_ROOT}/target/g++/GCC-13-COVERAGE/bin/g++"

# Check if GCC exists
if [ ! -f "$GCC_PATH" ]; then
    echo "Error: GCC compiler not found at $GCC_PATH"
    echo "Please run the build script first: bash build_script/g++_build.sh"
    exit 1
fi


# Generate output filename (in coverage directory)
OUTPUT_FILE="${WORK_DIR}/coverage"

# Compile C++ code
# Use C++23 standard, enable coverage detection
# Use -fprofile-dir to specify output directory for coverage files (.gcno, .gcda)
"$GCC_PATH" \
    -x c++ \
    -std=c++23 \
    --coverage \
    "$SOURCE_FILE" \
    -o "$OUTPUT_FILE"

# Return compilation result
exit $?
