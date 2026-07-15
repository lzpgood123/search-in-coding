#!/bin/bash
# Batch4 multi-round LLM backlog clearer (resumable).
# Each round: weekly_analysis (skip-benchmarks) + score + build + deploy
# Usage:
#   bash scripts/batch4_clear_backlog.sh [rounds] [max_per_round]
# Defaults: 5 rounds x 1000
set -euo pipefail
cd "$(dirname "$0")/.." || exit 1
source .venv/bin/activate

ROUNDS=${1:-5}
MAX=${2:-1000}
LOG_DIR=logs
mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/batch4-clear-$(date +%Y%m%d-%H%M%S).log"

count_pending() {
  python3 - <<'PY'
import sys
sys.path.insert(0, 'scripts')
from common import load_jsonish
ps = load_jsonish('data/projects.yaml')
pending = sum(1 for p in ps if not p.get('last_analyzed'))
analyzed = sum(1 for p in ps if p.get('last_analyzed'))
print(f'{pending} {analyzed} {len(ps)}')
PY
}

echo "=== batch4 clear backlog start $(date -Is) rounds=$ROUNDS max=$MAX ===" | tee -a "$LOG"
read -r PENDING0 ANALYZED0 TOTAL0 < <(count_pending)
echo "BEFORE pending=$PENDING0 analyzed=$ANALYZED0 total=$TOTAL0" | tee -a "$LOG"

for i in $(seq 1 "$ROUNDS"); do
  echo "" | tee -a "$LOG"
  echo "=== ROUND $i/$ROUNDS start $(date -Is) ===" | tee -a "$LOG"
  read -r P_BEFORE A_BEFORE T_BEFORE < <(count_pending)
  echo "round $i before: pending=$P_BEFORE analyzed=$A_BEFORE" | tee -a "$LOG"
  if [ "$P_BEFORE" -eq 0 ]; then
    echo "No pending left; stop." | tee -a "$LOG"
    break
  fi

  python3 scripts/weekly_analysis.py \
    --max-projects "$MAX" \
    --skip-benchmarks \
    2>&1 | tee -a "$LOG"

  echo "--- score ---" | tee -a "$LOG"
  python3 scripts/score.py 2>&1 | tee -a "$LOG" | tail -5

  echo "--- build ---" | tee -a "$LOG"
  python3 scripts/build_site.py 2>&1 | tee -a "$LOG" | tail -5

  echo "--- deploy ---" | tee -a "$LOG"
  python3 scripts/deploy_site.py --dest /var/www/ecoradar.lzpgood.online 2>&1 | tee -a "$LOG" | tail -10

  read -r P_AFTER A_AFTER T_AFTER < <(count_pending)
  echo "=== ROUND $i done $(date -Is) pending=$P_AFTER analyzed=$A_AFTER total=$T_AFTER ===" | tee -a "$LOG"
done

read -r PENDING1 ANALYZED1 TOTAL1 < <(count_pending)
echo "=== batch4 clear backlog end $(date -Is) ===" | tee -a "$LOG"
echo "AFTER pending=$PENDING1 analyzed=$ANALYZED1 total=$TOTAL1" | tee -a "$LOG"
echo "LOG=$LOG"
