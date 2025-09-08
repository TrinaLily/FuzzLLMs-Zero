#!/usr/bin/env bash

set -euo pipefail

# 接受工作目录参数
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

JACOCLI="${PROJECT_ROOT}/target/java/jacococli.jar"

EXEC_FILE="${WORK_DIR}/coverage/jacoco.exec"

CLASSFILES="${PROJECT_ROOT}/target/java/compiler-classes/classes"

OUTPUT_DIR="${WORK_DIR}/coverage/coverage-report"

XML_REPORT="$OUTPUT_DIR/report.xml"

mkdir -p "$OUTPUT_DIR"

java -jar "$JACOCLI" report \
    "$EXEC_FILE" \
    --classfiles "$CLASSFILES" \
    --xml "$XML_REPORT" >/dev/null

COVERED_LINES=$(xmllint --xpath 'string(/report/counter[@type="LINE"]/@covered)' "$XML_REPORT")

# 只输出覆盖的行数
echo "${COVERED_LINES}"
