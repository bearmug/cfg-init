#!/bin/sh
set -eu
umask 077
BASE="$HOME/.omp/agent/cache/decider-shadow"
export HF_HOME="$BASE/hf" HF_HUB_CACHE="$BASE/hf/hub"
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
export DECIDER_MODEL="$BASE/hf/hub/models--Mapika--decider-0.8b/snapshots/a0a01d6f8135298f400a8c856b355793012ae971"
export DECIDER_DEVICE=mps DECIDER_COMPILE=0 DECIDER_FP8=0 DECIDER_WARMUP=0 DECIDER_SHARED=0
exec "$BASE/.venv/bin/python" -m uvicorn decider.serve:app --host 127.0.0.1 --port 18742 --no-access-log
