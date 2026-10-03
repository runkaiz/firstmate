#!/usr/bin/env bash
set -euo pipefail
ROOT=$PWD
SCRATCH="$ROOT/.test-phase-tmp/manual"
EVIDENCE=/home/runkai/.no-mistakes/evidence/01M3ZKCQS3M27TJCN10BH53WD8
export LAB_HELPER="$ROOT/bin/fm-herdr-lab.sh" ORIGINAL_PATH="$PATH"
export LAB_SESSION
LAB_SESSION=$("$LAB_HELPER" name readiness-gate)
export FM_HERDR_LAB_STATE_DIR="$SCRATCH/lab-state" TMPDIR="$SCRATCH/tmp"
export TREEHOUSE_ROOT="$SCRATCH/pool" CALL_LOG="$EVIDENCE/herdr-calls.log"
export GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_NOSYSTEM=1
unset FM_ROOT_OVERRIDE FM_STATE_OVERRIDE FM_DATA_OVERRIDE FM_CONFIG_OVERRIDE FM_PROJECTS_OVERRIDE FM_GATE_REFUSE_BYPASS
unset HERDR_ENV HERDR_PANE_ID HERDR_TAB_ID HERDR_WORKSPACE_ID HERDR_SOCKET_PATH HERDR_SESSION TMUX
mkdir -p "$SCRATCH/bin" "$TMPDIR"
: > "$CALL_LOG"
cleanup() {
  rc=$?
  env PATH="$ORIGINAL_PATH" "$LAB_HELPER" teardown "$LAB_SESSION" || rc=1
  echo "Guarded lab teardown result=$rc"
  exit "$rc"
}
"$LAB_HELPER" provision "$LAB_SESSION"
trap cleanup EXIT
"$LAB_HELPER" viewer start "$LAB_SESSION"
lab() { env PATH="$ORIGINAL_PATH" "$LAB_HELPER" run "$LAB_SESSION" "$@"; }
drive() {
  bash -c '. "$1/bin/backends/herdr.sh"; shift; fm_backend_herdr_cli() { local session=$1; shift; [ "$session" = "$LAB_SESSION" ] || return 9; env PATH="$ORIGINAL_PATH" "$LAB_HELPER" run "$session" "$@"; }; fm_backend_herdr_prepare_shell "$@"' _ "$ROOT" "$@"
}
waitfile() { for ((i=0;i<100;i++)); do [ ! -f "$1" ] || return 0; sleep .1; done; return 1; }
lab status --json
out=$(lab workspace create --cwd "$SCRATCH" --label readiness-gate --no-focus)
ws=$(jq -r .result.workspace.workspace_id <<<"$out")
pane=$(jq -r .result.root_pane.pane_id <<<"$out")
drive "$LAB_SESSION:$pane" "touch '$SCRATCH/initial-ready'"
waitfile "$SCRATCH/initial-ready"

# A real foreground program consumes terminal input, as startup banners can.
lab pane run "$pane" "python3 '$ROOT/.test-phase-tmp/consume.py' '$SCRATCH' 2" >/dev/null
waitfile "$SCRATCH/consuming"
# Counterfactual: the old single-send behavior reports success while input is lost.
lab pane run "$pane" "touch '$SCRATCH/old-one-shot'" >/dev/null
start=$SECONDS
drive "$LAB_SESSION:$pane" "printf 'prepared\n' >> '$SCRATCH/recovered'"
waitfile "$SCRATCH/recovered"
[ "$(cat "$SCRATCH/recovered")" = prepared ]
[ ! -e "$SCRATCH/old-one-shot" ]
echo 'COUNTERFACTUAL: direct one-shot command was consumed and did not execute'
echo "RECOVERY: foreground program consumed $(wc -l < "$SCRATCH/consumed") probes; preparation=$(cat "$SCRATCH/recovered"); elapsed=$((SECONDS-start))s"
lab pane read "$pane" --lines 200 > "$EVIDENCE/recovery-pane.json"

rm "$SCRATCH/consuming"
lab pane run "$pane" "python3 '$ROOT/.test-phase-tmp/consume.py' '$SCRATCH' 3" >/dev/null
waitfile "$SCRATCH/consuming"
start=$SECONDS
set +e
FM_HERDR_SHELL_READY_POLLS=4 drive "$LAB_SESSION:$pane" "touch '$SCRATCH/forbidden-allocation'"
rc=$?
set -e
[ "$rc" -ne 0 ] && [ ! -e "$SCRATCH/forbidden-allocation" ]
echo "NEVER READY: exit=$rc; allocation absent; elapsed=$((SECONDS-start))s"
sleep 3
[ ! -e "$SCRATCH/forbidden-allocation" ]
[ -z "$(ls -A "$TMPDIR")" ]
echo 'LATE PROBES: no allocation and no readiness-directory residue'
set +e
drive "$LAB_SESSION:p999999" "touch '$SCRATCH/forbidden-allocation'"
rc=$?
set -e
[ "$rc" -ne 0 ] && [ ! -e "$SCRATCH/forbidden-allocation" ]
echo "MISSING PANE: exit=$rc; allocation absent"

# Full production spawn against a new local-file origin and private pool.
"$ROOT/bin/fm-lab-home.sh" create "$SCRATCH/home"
export FM_HOME="$SCRATCH/home" HERDR_SESSION="$LAB_SESSION"
mkdir -p "$FM_HOME/data/ready-scout" "$SCRATCH/project"
git -C "$SCRATCH/project" init -q
git -C "$SCRATCH/project" -c user.name=Test -c user.email=test@example.invalid commit --allow-empty -qm initial
git clone -q --bare "$SCRATCH/project" "$SCRATCH/origin.git"
git -C "$SCRATCH/project" remote add origin "file://$SCRATCH/origin.git"
cp "$ROOT/.test-phase-tmp/brief.md" "$FM_HOME/data/ready-scout/brief.md"
export PATH="$SCRATCH/bin:$ORIGINAL_PATH"
cp "$ROOT/.test-phase-tmp/herdr-wrapper" "$SCRATCH/bin/herdr"
chmod +x "$SCRATCH/bin/herdr"
"$ROOT/bin/fm-spawn.sh" ready-scout "$SCRATCH/project" "sh -c 'pwd > $SCRATCH/worker-cwd; sleep 30'" --scout --backend herdr
waitfile "$SCRATCH/worker-cwd"
cp "$FM_HOME/state/ready-scout.meta" "$EVIDENCE/spawn-meta.txt"
cat "$FM_HOME/state/ready-scout.meta"
cwd=$(cat "$SCRATCH/worker-cwd")
# The OS reports /var/home for the /home alias; compare within the supplied prefix.
cwd=${cwd/#\/var\/home\//\/home\/}
case "$cwd" in "$TREEHOUSE_ROOT"/*) ;; *) echo "Worker outside private pool: $cwd"; exit 1 ;; esac
[ "$(git -C "$cwd" rev-parse --show-toplevel)" != "$SCRATCH/project" ]
echo "WORKER CWD: $cwd"
echo "ISOLATION: git common-dir=$(git -C "$cwd" rev-parse --git-common-dir), git-dir=$(git -C "$cwd" rev-parse --git-dir)"
allocations=$(grep -c $'pane\trun\t.*\ttreehouse get\t' "$CALL_LOG")
[ "$allocations" -eq 1 ]
echo "ALLOCATION SUBMISSIONS: $allocations"
target=$(sed -n 's/^pane=//p' "$FM_HOME/state/ready-scout.meta")
lab workspace list > "$EVIDENCE/final-lab-workspaces.json"
echo 'FULL SPAWN: raw worker executed in isolated worktree after one allocation'
