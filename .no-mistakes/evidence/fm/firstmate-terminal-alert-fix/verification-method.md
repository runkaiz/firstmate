# Watcher live verification method

Final result: the live driver exited 0 and all four focused regressions passed without skips.
Three settled display hashes generated three stale wake requests on the base and one on the target in both attended and away modes.
The final transcript proves cadence expiry, status-generation and worker-incarnation resets, new delivery/decision/blocker/failure delivery through both paths, busy-to-idle rearming, new captain-call delivery, continuing unheld-blocker/nonterminal alerts, and retry after durable queue failure.
All 17 disposable workers retained their original unlanded branch, commit, and result through supervision.
The private tmux server and all `.lv` fixtures were removed after verification; source and permanent tests were unchanged.

The product under test is the watcher CLI, its real tmux adapter, crew-state reconciliation, and durable wake drain.
`watcher-live-driver.py` creates marked disposable lab homes inside the gate worktree and a private tmux socket at `.lv/s`, with a named `fm-lab-alert` session and a 100-by-30 terminal grid.
Each completed-worker record refers to a real bash pane, a disposable Git repository with an unlanded branch, and a `done` status.
The semantic idle input is created through the production busy-event writer, representing the worker's completed turn.
No harness CLI, authentication, backend capture, crew-state executable, or watcher is replaced by a stub in these live checks.
No LLM is invoked, and no vendor-harness integration or token-cost saving is claimed.

The base watcher is extracted from commit `6407052f4c521e39401ce2305dfa45d201249827` using `git archive ... bin` into `.lv/base`.
The target watcher runs directly from this worktree at `9446664c9b1d506e1cd675da3edadf83e963d895`.
This reproduces the base version in isolation; it does not inspect or restart the operator's deployed watcher.

The driver types terminal redraws into real panes, waits for their exact capture hashes to settle and be classified, and records durable queue rows and the wake-drain presentation.
Silent checks require the watcher to stay running with an empty queue after the new hash is classified.
The cadence check ages the disposable throttle timestamp instead of waiting hours.
New-event stale checks mark only the ordinary signal as already observed through the production status-marker function, ensuring the normal signal path cannot mask a broken stale path.
Signal checks leave that path enabled.
Queue-write failure is induced by placing a directory at the disposable queue-file path, then removing it for a real retry.
The driver verifies that every case retains its original branch, commit, and result before teardown.

The first setup attempt lacked a complete worker worktree and checked the settled state too early.
The next setup attempt compared the visible viewport with the watcher's scrollback-inclusive capture and timed out.
Both were driver issues; the final driver uses a real isolated Git worktree record and exactly `tmux capture-pane -p -S -40`.
Only the final `live-transcript.log` is used for acceptance.

Four focused repository regressions run separately with `FM_TEST_ONLY=<selector> bin/fm-test-run.sh tests/fm-watch-triage.test.sh`:

- `test_terminal_delivery_redraw_bound`
- `test_terminal_delivery_new_events_remain_actionable`
- `test_terminal_delivery_resumed_activity_rearms`
- `test_terminal_delivery_failed_append_keeps_first_delivery`

Those existing tests use mocked terminal and crew-state fixtures and are supplemental, not live evidence.
In particular, active no-mistakes pipeline resumption is covered by the focused regression only: this assigned gate phase forbids starting or controlling another pipeline.
The live activity-reset scenario exercises the production semantic busy-event interface in attended and away modes.
No broad test suite, lint, format, push, PR, CI, or compaction-configuration operation is performed.
