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

export JAVA_HOME="/usr/lib/jvm/java-11-opendjk-amd64/"
export PATH="$JAVA_HOME/bin:$PATH"

JACOCO_AGENT="${PROJECT_ROOT}/target/java/jacocoagent.jar"

# 将覆盖率文件放到工作目录中
DEST_FILE="${WORK_DIR}/coverage/jacoco.exec"
APPEND="true"

# 确保覆盖率目录存在，但不删除累积的覆盖率数据
mkdir -p "$(dirname "$DEST_FILE")"

exec java \
  -javaagent:"${JACOCO_AGENT}=destfile=${DEST_FILE},output=file,append=${APPEND}" \
  --module-path "$JAVA_HOME/bin" \
  --add-modules java.compiler \
  -m jdk.compiler/com.sun.tools.javac.Main \
  "$SOURCE_FILE"
