#!/usr/bin/env bash
# Project-Agent 一键启动脚本
# 用法: ./run.sh [--reset]
set -e
cd "$(dirname "$0")"

RESET=""
if [ "$1" = "--reset" ]; then
  RESET="--reset"
fi

exec python3 -m server.main --port 8787 $RESET
