# Readiness verification

Validated target bc36fb74b085cc57169ff28bc11499b95a151410 with installed Herdr 0.9.3/protocol 22 and real Treehouse.

`live-check-rerun.log` is the successful final run.
The first run's `live-check.log` stopped at a test assertion comparing the host's equivalent `/home` and `/var/home` prefixes; production spawn had succeeded.
The assertion was corrected and the entire manual check rerun successfully.
No production source changes were needed.

The live lab used the guarded helper's provision, fixed-size foreground viewer, run wrapper, and teardown, with the default-session tripwire intact.
The input-loss adversary was a real foreground Python process reading terminal input for two seconds, representing the startup consumer; Herdr and Firstmate were real throughout.
A direct one-shot command was swallowed; the production readiness helper subsequently executed preparation exactly once.
The final consumed-line count includes that one counterfactual command as well as readiness probes.
A three-second consumer with a four-probe budget caused bounded refusal, no preparation, and no acknowledgement-directory residue.
A nonexistent pane also refused preparation.
The full `fm-spawn.sh --scout --backend herdr` call used a marked disposable Firstmate home, a local file origin, a private Treehouse pool, and a raw shell worker that recorded its cwd.
This proves the pre-harness allocation boundary; no vendor harness or credentials were exercised.

Targeted baseline command, with TMPDIR and FM_HERDR_LAB_STATE_DIR confined to the temporary worktree fixture:

```sh
bash bin/fm-test-run.sh --jobs 1 tests/fm-backend-herdr.test.sh tests/fm-herdr-attached-viewer-live-e2e.test.sh tests/fm-spawn-worktree-settle.test.sh tests/fm-backend.test.sh
```

All four scripts passed without skips.
The attached-viewer test exercised three fresh shells and independent exactly-once append-file oracles.
The portable tests additionally covered echoed-only probes, delivery failure, allocation delivery failure without retry, quoted temporary paths, and late probes after cleanup.
Portable fake-CLI tests are supporting evidence, not live scenarios.

The retained `live-check-driver.sh`, `consume.py`, `herdr-wrapper`, and `fixture-brief.md` reproduce the manual check when staged respectively under `.test-phase-tmp/` as `live-check.sh`, `consume.py`, `herdr-wrapper`, and `brief.md` in a disposable run worktree.
The driver's evidence directory is specific to this run and must be adjusted for another run.
`herdr-calls.log` records the full spawn's real adapter operations and exactly one `treehouse get` submission.
`spawn-meta.txt` records the allocated worktree and endpoint; `recovery-pane.json` captures the actual terminal output.

Both manual labs completed guarded teardown; all transient worktree fixtures were removed and git status was clean.
No lint, formatter, full-suite run, pipeline control, or delivery phase was performed.
No screenshot was required because this change affects command delivery and shell readiness, with no UI layout or copy change.
