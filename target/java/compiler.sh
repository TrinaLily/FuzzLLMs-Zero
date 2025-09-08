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

export JAVA_HOME="/usr/lib/jvm/java-11-opendjk-amd64/"
export PATH="$JAVA_HOME/bin:$PATH"

JACOCO_AGENT="${PROJECT_ROOT}/target/java/jacocoagent.jar"

# Put coverage files in working directory
DEST_FILE="${WORK_DIR}/coverage/jacoco.exec"
APPEND="true"

# Ensure coverage directory exists, but do not delete accumulated coverage data
mkdir -p "$(dirname "$DEST_FILE")"

exec java \
  -javaagent:"${JACOCO_AGENT}=destfile=${DEST_FILE},output=file,append=${APPEND}" \
  --module-path "$JAVA_HOME/bin" \
  --add-modules java.compiler \
  -m jdk.compiler/com.sun.tools.javac.Main \
  "$SOURCE_FILE"
