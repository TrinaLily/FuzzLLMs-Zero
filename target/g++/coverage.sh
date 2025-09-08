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

# 获取GCC相关路径
GCOV_PATH="${PROJECT_ROOT}/target/g++/GCC-13-COVERAGE/bin/gcov"

# 检查gcov工具是否存在
if [ ! -f "$GCOV_PATH" ]; then
    echo "Error: gcov tool not found at $GCOV_PATH"
    exit 1
fi

# 工作目录中的覆盖率数据目录
COVERAGE_DIR="${PROJECT_ROOT}/target/g++/gcc-coverage-build/gcc"

# 检查覆盖率目录是否存在
if [ ! -d "$COVERAGE_DIR" ]; then
    echo "0"
    exit 1
fi

# 进入工作目录的覆盖率目录
cd "$COVERAGE_DIR"


# 运行lcov命令收集覆盖率数据
lcov --capture --directory . --output-file coverage.info --gcov-tool "$GCOV_PATH" >/dev/null 2>&1

# 检查是否成功生成覆盖率信息
if [ ! -f "coverage.info" ] || [ ! -s "coverage.info" ]; then
    echo "0"
    exit 1
fi

# 生成覆盖率摘要
COVERAGE_SUMMARY=$(lcov --summary coverage.info 2>/dev/null)

# 从摘要中提取覆盖的行数
COVERED_LINES=$(echo "$COVERAGE_SUMMARY" | grep "lines......:" | sed 's/.*(\([0-9]*\).*/\1/')

# 如果没有找到覆盖行数，默认为0
if [ -z "$COVERED_LINES" ]; then
    COVERED_LINES=0
fi

# 只输出覆盖的行数
echo "${COVERED_LINES}"

