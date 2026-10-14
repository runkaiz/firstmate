"""Execute selected existing behavioral tests; no real Pi SDK is used."""
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path.cwd()
EVIDENCE = Path(__file__).parent
source = (ROOT / "tests/fm-pi-branch-extension.test.sh").read_text()
definitions = source.split("\ntest_outcomes_tool_call_headers_follow_the_loaded_pi_version\n", 1)[0]
definitions = definitions.replace(
    '. "$(dirname "${BASH_SOURCE[0]}")/lib.sh"', '. "$PWD/tests/lib.sh"', 1
)
selectors = [
    "test_idle_custom_before_agent_start_never_reads_prompt",
    "test_branch_mirror_filters_order_and_cursor",
    "test_captain_outcome_processing_turn_is_sequence_keyed_and_re_presented",
    "test_away_record_parks_main_and_presents_after_archive",
]
results = []
with tempfile.TemporaryDirectory(prefix=".phase-test-", dir=ROOT) as temporary:
    env = dict(os.environ, TMPDIR=temporary)
    for selector in selectors:
        result = subprocess.run(
            ["bash"], input=definitions + "\n" + selector + "\n", text=True,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env,
        )
        results.append((selector, result.returncode, result.stdout))
        print(f"{selector}: exit {result.returncode}", flush=True)
    before = subprocess.run(
        ["bash"], input=definitions + '\ngit show 8c9c67de^:.pi/extensions/fm-branch-supervision.ts > "$TMP_ROOT/pre-repair.ts"\nEXT="$TMP_ROOT/pre-repair.ts"\ntest_idle_custom_before_agent_start_never_reads_prompt\n',
        text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env,
    )
    results.append(("new regression against 8c9c67de^ extension", before.returncode, before.stdout))
    print(f"pre-repair regression: exit {before.returncode}; trim TypeError reproduced: {chr(39) + 'trim' + chr(39) in before.stdout}", flush=True)
log = "These are behavioral tests with a stubbed Pi SDK, not live product validation.\n\n"
for name, status, output in results:
    log += f"TEST: {name}\nEXIT: {status}\n{output}\n"
(EVIDENCE / "targeted-regression.log").write_text(log)
assert all(status == 0 for _, status, _ in results[:-1]), log
assert before.returncode != 0 and "reading 'trim'" in before.stdout, log
