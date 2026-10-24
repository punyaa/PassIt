#!/usr/bin/env bash
# Platform evaluation runs against a PassIt cloud environment (staging, never demo).
#
#   AWS_PROFILE=nus-sso scripts/loadtest/evaluate.sh <run> [pilot|full]
#
# runs: search | booking | elasticity | fault | cost | all
#   pilot  small and fast, to check the scripts and get first numbers (default)
#   full   the report runs: search 10->200 VUs over 10 min, 20 bookings/s for 5 min,
#          20->200 VU spike, fault injection mid-run
#
# Everything lands in scripts/loadtest/results/<timestamp>/ (git-ignored): k6 summaries plus an
# ECS task-count timeline, which is the autoscaling and fault-recovery figure for the report.
set -euo pipefail

RUN="${1:-}"
SCALE="${2:-pilot}"
ENV_NAME="${ENV_NAME:-staging}"
[ "$ENV_NAME" = "staging" ] || { echo "Run evaluations against staging only." >&2; exit 2; }
[ -n "$RUN" ] || { sed -n '2,13p' "$0" | sed 's/^# \{0,1\}//'; exit 2; }

export AWS_REGION="${AWS_REGION:-ap-southeast-1}" AWS_PAGER=""
CLUSTER="passit-$ENV_NAME"
HERE="$(cd "$(dirname "$0")" && pwd)"
OUT="$HERE/results/$(date +%Y%m%d-%H%M%S)-$SCALE"
mkdir -p "$OUT"

DOMAIN=$(aws cloudfront list-distributions \
  --query "DistributionList.Items[?Comment=='PassIt $ENV_NAME'].DomainName | [0]" --output text)
BASE_URL="${BASE_URL:-https://$DOMAIN}"
echo "Target: $BASE_URL   scale: $SCALE   results: $OUT"

if [ "$SCALE" = "full" ]; then
  SEARCH_ENV=(-e MAX_VUS=200 -e RAMP_MIN=10)
  BOOKING_ENV=(-e RATE=20 -e DURATION=5m)
  SPIKE_ENV=(-e PROFILE=spike -e MAX_VUS=200 -e HOLD_MIN=4)
  FAULT_ENV=(-e MAX_VUS=60 -e RAMP_MIN=5)
else
  SEARCH_ENV=(-e MAX_VUS=40 -e RAMP_MIN=1)
  BOOKING_ENV=(-e RATE=5 -e DURATION=30s)
  # Target tracking needs 3 consecutive minutes above 60% CPU, so hold the spike for 5+.
  SPIKE_ENV=(-e PROFILE=spike -e MAX_VUS=150 -e HOLD_MIN="${HOLD_MIN:-2}")
  FAULT_ENV=(-e MAX_VUS=30 -e RAMP_MIN=2)
fi

k6run() { # name, script, k6 args...
  local name="$1" script="$2"; shift 2
  k6 run --quiet -e BASE_URL="$BASE_URL" "$@" --summary-export "$OUT/$name.json" \
    "$HERE/$script" 2>&1 | tee "$OUT/$name.txt" | grep -E "checks_|http_req_duration|http_req_failed|iterations|bookings_|thresholds|✓|✗" || true
}

service_counts() { # epoch,running,desired,pending for the API service
  aws ecs describe-services --cluster "$CLUSTER" --services api \
    --query 'services[0].[runningCount,desiredCount,pendingCount]' --output text |
    awk -v t="$(date +%s)" '{print t","$1","$2","$3}'
}

timeline() { # file, interval seconds: sample until killed
  echo "epoch,running,desired,pending" > "$1"
  while true; do service_counts >> "$1"; sleep "$2"; done
}

summarise_timeline() {
  python3 - "$1" <<'PY'
import csv, sys
rows = list(csv.DictReader(open(sys.argv[1])))
if len(rows) < 2:
    sys.exit()
t0 = int(rows[0]["epoch"])
base = int(rows[0]["running"])
peak = max(int(r["running"]) for r in rows)
first_up = next((int(r["epoch"]) - t0 for r in rows if int(r["running"]) > base), None)
print(f"  tasks: start {base}, peak {peak}; first scale-out after {first_up}s" if first_up is not None
      else f"  tasks: start {base}, peak {peak}; no scale-out observed")
PY
}

run_search() { echo "== Search load"; k6run search search.js "${SEARCH_ENV[@]}"; }

run_booking() {
  echo "== Booking load (needs fresh seed: scripts/demo-reset/reset.sh $ENV_NAME)"
  k6run booking booking.js "${BOOKING_ENV[@]}" -e START_OFFSET_DAYS="${START_OFFSET_DAYS:-30}"
}

run_elasticity() {
  echo "== Elasticity spike"
  timeline "$OUT/elasticity-timeline.csv" 15 & local sampler=$!
  k6run elasticity search.js "${SPIKE_ENV[@]}"
  # Keep sampling through scale-in so the timeline shows the whole cycle.
  sleep "${COOLDOWN_SECONDS:-60}"; { kill "$sampler"; wait "$sampler"; } 2>/dev/null || true
  summarise_timeline "$OUT/elasticity-timeline.csv"
}

run_fault() {
  echo "== Fault recovery: stop one API task mid-run"
  timeline "$OUT/fault-timeline.csv" 3 & local sampler=$!
  k6 run --quiet -e BASE_URL="$BASE_URL" "${FAULT_ENV[@]}" --summary-export "$OUT/fault.json" \
    "$HERE/search.js" > "$OUT/fault.txt" 2>&1 & local load=$!
  sleep 75
  local victim; victim=$(aws ecs list-tasks --cluster "$CLUSTER" --service-name api \
    --desired-status RUNNING --query 'taskArns[0]' --output text)
  local stopped; stopped=$(date +%s)
  echo "  stopping ${victim##*/} at $(date -u +%H:%M:%S) UTC"
  aws ecs stop-task --cluster "$CLUSTER" --task "$victim" --reason "evaluation: fault recovery" >/dev/null
  local recovered=""
  for _ in $(seq 1 60); do
    sleep 3
    read -r running desired < <(aws ecs describe-services --cluster "$CLUSTER" --services api \
      --query 'services[0].[runningCount,desiredCount]' --output text)
    if [ "$running" -ge "$desired" ] && [ "$(( $(date +%s) - stopped ))" -gt 6 ]; then recovered=$(date +%s); break; fi
  done
  wait "$load" || true
  { kill "$sampler"; wait "$sampler"; } 2>/dev/null || true
  grep -E "http_req_failed|http_req_duration|checks_" "$OUT/fault.txt" || true
  [ -n "$recovered" ] && echo "  replacement running after $(( recovered - stopped )) s" \
    || echo "  replacement did not reach desired count within 3 minutes"
}

run_cost() {
  echo "== Cost (last 7 days, by service)"
  local end start; end=$(date -u +%Y-%m-%d); start=$(date -u -v-7d +%Y-%m-%d 2>/dev/null || date -u -d '-7 days' +%Y-%m-%d)
  if aws ce get-cost-and-usage --region us-east-1 --time-period "Start=$start,End=$end" --granularity DAILY \
      --metrics UnblendedCost --group-by Type=DIMENSION,Key=SERVICE > "$OUT/cost.json" 2>"$OUT/cost.err"; then
    python3 - "$OUT/cost.json" <<'PY'
import json, sys, collections
tot = collections.Counter()
for day in json.load(open(sys.argv[1]))["ResultsByTime"]:
    for g in day["Groups"]:
        tot[g["Keys"][0]] += float(g["Metrics"]["UnblendedCost"]["Amount"])
for name, cost in tot.most_common(8):
    print(f"  {name:<42} USD {cost:7.2f}")
print(f"  {'Total':<42} USD {sum(tot.values()):7.2f}")
print("  Divide by simulated rentals (bookings created in the booking run) for cost per rental.")
PY
  else
    echo "  Cost Explorer unavailable: $(head -c 200 "$OUT/cost.err")"
    echo "  This account is a linked account; ask the NUS/org owner for ce:GetCostAndUsage, or read the Billing console."
  fi
}

case "$RUN" in
  search) run_search ;;
  booking) run_booking ;;
  elasticity) run_elasticity ;;
  fault) run_fault ;;
  cost) run_cost ;;
  all) run_search; run_booking; run_elasticity; run_fault; run_cost ;;
  *) echo "unknown run: $RUN" >&2; exit 2 ;;
esac
echo "Results saved in $OUT"
