#!/usr/bin/env bash

# 接受工作目录参数
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

# 获取GCC编译器路径
GCC_PATH="${PROJECT_ROOT}/target/g++/GCC-13-COVERAGE/bin/g++"

# 检查GCC是否存在
if [ ! -f "$GCC_PATH" ]; then
    echo "Error: GCC compiler not found at $GCC_PATH"
    echo "Please run the build script first: bash build_script/g++_build.sh"
    exit 1
fi


# 生成输出文件名（在覆盖率目录中）
OUTPUT_FILE="${WORK_DIR}/coverage"

# 编译C++代码
# 使用C++23标准，启用覆盖率检测
# 使用-fprofile-dir指定覆盖率文件(.gcno, .gcda)的输出目录
"$GCC_PATH" \
    -x c++ \
    -std=c++23 \
    --coverage \
    "$SOURCE_FILE" \
    -o "$OUTPUT_FILE"

# 返回编译结果
exit $?
