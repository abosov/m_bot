from pathlib import Path
import os
import subprocess


SCRIPT_PATH = (
    Path(__file__).resolve().parents[1]
    / "automation"
    / "scripts"
    / "escalate_story.sh"
)


def make_run_dir(base_dir: Path, story_id: str, run_id: str) -> Path:
    run_dir = base_dir / "automation" / "runs" / story_id / run_id
    run_dir.mkdir(parents=True)
    return run_dir


def test_escalate_story_exists() -> None:
    assert SCRIPT_PATH.exists()


def test_escalate_story_is_valid_bash() -> None:
    result = subprocess.run(
        ["bash", "-n", str(SCRIPT_PATH)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_escalate_story_resolves_pending_escalation_with_force_followup(tmp_path: Path) -> None:
    root_dir = tmp_path / "repo"
    run_dir = make_run_dir(root_dir, "US-AUTO-28", "2026-03-24_11-00-00")
    (run_dir / "manifest.md").write_text(
        "# Manifest\n"
        "- story_id: US-AUTO-28\n"
        "## Artifacts\n"
        "- manifest.md\n",
        encoding="utf-8",
    )
    (run_dir / "escalation_result.json").write_text(
        '{\n'
        '  "story_id": "US-AUTO-28",\n'
        '  "run_id": "2026-03-24_11-00-00",\n'
        '  "run_dir": "/tmp/run",\n'
        '  "gate_result": "automation/runs/US-AUTO-28/2026-03-24_11-00-00/review_gate_result.json",\n'
        '  "decision_source": "repeated_reject_stagnation",\n'
        '  "escalation_required": true,\n'
        '  "status": "pending",\n'
        '  "reason": "Repeated review_classification reject",\n'
        '  "previous_reject_run_id": "2026-03-24_10-00-00",\n'
        '  "resolution_action": "",\n'
        '  "resolved_at": ""\n'
        '}\n',
        encoding="utf-8",
    )

    env = os.environ.copy()
    env["AUTOMATION_ROOT_DIR"] = str(root_dir)
    env["AUTOMATION_RUNS_ROOT"] = str(root_dir / "automation" / "runs")
    env["AUTOMATION_RUN_DIR"] = str(run_dir)

    result = subprocess.run(
        ["bash", str(SCRIPT_PATH), "US-AUTO-28", "force-followup"],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )

    assert result.returncode == 0, result.stderr
    assert "Escalation resolved for US-AUTO-28 run 2026-03-24_11-00-00: force-followup" in result.stdout
    assert "Next command: automation/scripts/run_story.sh US-AUTO-28" in result.stdout

    escalation_result = (run_dir / "escalation_result.json").read_text(encoding="utf-8")
    assert '"status": "resolved"' in escalation_result
    assert '"resolution_action": "force-followup"' in escalation_result
    manifest_text = (run_dir / "manifest.md").read_text(encoding="utf-8")
    assert "- escalation_result.json" in manifest_text


def test_escalate_story_rejects_when_no_pending_escalation_exists(tmp_path: Path) -> None:
    root_dir = tmp_path / "repo"
    run_dir = make_run_dir(root_dir, "US-AUTO-28", "2026-03-24_11-00-00")
    (run_dir / "manifest.md").write_text(
        "# Manifest\n"
        "- story_id: US-AUTO-28\n",
        encoding="utf-8",
    )

    env = os.environ.copy()
    env["AUTOMATION_ROOT_DIR"] = str(root_dir)
    env["AUTOMATION_RUNS_ROOT"] = str(root_dir / "automation" / "runs")
    env["AUTOMATION_RUN_DIR"] = str(run_dir)

    result = subprocess.run(
        ["bash", str(SCRIPT_PATH), "US-AUTO-28", "abort"],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )

    assert result.returncode != 0
    assert "escalation artifact not found" in result.stderr

def test_escalate_story_rejects_when_status_is_not_pending(tmp_path: Path) -> None:
    root_dir = tmp_path / "repo"
    run_dir = make_run_dir(root_dir, "US-AUTO-28", "2026-03-24_11-00-01")
    (run_dir / "manifest.md").write_text(
        "# Manifest\n"
        "- story_id: US-AUTO-28\n"
        "## Artifacts\n"
        "- manifest.md\n",
        encoding="utf-8",
    )
    (run_dir / "escalation_result.json").write_text(
        '{\n'
        '  "story_id": "US-AUTO-28",\n'
        '  "run_id": "2026-03-24_11-00-01",\n'
        '  "run_dir": "/tmp/run",\n'
        '  "gate_result": "automation/runs/US-AUTO-28/2026-03-24_11-00-01/review_gate_result.json",\n'
        '  "decision_source": "repeated_reject_stagnation",\n'
        '  "escalation_required": true,\n'
        '  "status": "rejected",\n'
        '  "reason": "Repeated review_classification reject",\n'
        '  "previous_reject_run_id": "2026-03-24_10-00-00",\n'
        '  "resolution_action": "",\n'
        '  "resolved_at": ""\n'
        '}\n',
        encoding="utf-8",
    )

    env = os.environ.copy()
    env["AUTOMATION_ROOT_DIR"] = str(root_dir)
    env["AUTOMATION_RUNS_ROOT"] = str(root_dir / "automation" / "runs")
    env["AUTOMATION_RUN_DIR"] = str(run_dir)

    result = subprocess.run(
        ["bash", str(SCRIPT_PATH), "US-AUTO-28", "force-followup"],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )

    assert result.returncode != 0
    assert "status must be pending" in result.stderr


def test_escalate_story_rejects_when_decision_source_is_not_repeated_reject_stagnation(tmp_path: Path) -> None:
    root_dir = tmp_path / "repo"
    run_dir = make_run_dir(root_dir, "US-AUTO-28", "2026-03-24_11-00-02")
    (run_dir / "manifest.md").write_text(
        "# Manifest\n"
        "- story_id: US-AUTO-28\n"
        "## Artifacts\n"
        "- manifest.md\n",
        encoding="utf-8",
    )
    (run_dir / "escalation_result.json").write_text(
        '{\n'
        '  "story_id": "US-AUTO-28",\n'
        '  "run_id": "2026-03-24_11-00-02",\n'
        '  "run_dir": "/tmp/run",\n'
        '  "gate_result": "automation/runs/US-AUTO-28/2026-03-24_11-00-02/review_gate_result.json",\n'
        '  "decision_source": "manual_override",\n'
        '  "escalation_required": true,\n'
        '  "status": "pending",\n'
        '  "reason": "Repeated review_classification reject",\n'
        '  "previous_reject_run_id": "2026-03-24_10-00-00",\n'
        '  "resolution_action": "",\n'
        '  "resolved_at": ""\n'
        '}\n',
        encoding="utf-8",
    )

    env = os.environ.copy()
    env["AUTOMATION_ROOT_DIR"] = str(root_dir)
    env["AUTOMATION_RUNS_ROOT"] = str(root_dir / "automation" / "runs")
    env["AUTOMATION_RUN_DIR"] = str(run_dir)

    result = subprocess.run(
        ["bash", str(SCRIPT_PATH), "US-AUTO-28", "abort"],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )

    assert result.returncode != 0
    assert "decision_source must be repeated_reject_stagnation" in result.stderr