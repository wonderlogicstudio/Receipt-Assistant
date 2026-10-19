"""Check the project hook contract without starting Codex or reading receipt data."""

import json
from pathlib import Path
import shutil
import subprocess

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "ponytail_hook.js"
NODE = shutil.which("node")
pytestmark = pytest.mark.skipif(not NODE, reason="Node.js is required for Codex hooks")


@pytest.mark.parametrize("event", ["SessionStart", "UserPromptSubmit", "SubagentStart"])
def test_hook_injects_skill_and_preflight_without_echoing_prompt(event):
    result = subprocess.run(
        [NODE, str(SCRIPT), event], cwd=ROOT, input='{"prompt":"SYNTHETIC_PRIVATE_MARKER"}',
        text=True, capture_output=True, timeout=5,
    )
    assert result.returncode == 0
    output = json.loads(result.stdout)["hookSpecificOutput"]
    assert output["hookEventName"] == event
    context = output["additionalContext"]
    assert "# Ponytail" in context and "Receipt Assistant project preflight:" in context
    assert "working Python" in context and "CPU/GPU" in context
    assert "AGENTS.md" in context and "latest Ponytail mode/off instruction" in context
    assert "SYNTHETIC_PRIVATE_MARKER" not in result.stdout + result.stderr


def test_hook_is_silent_outside_this_project(tmp_path):
    result = subprocess.run(
        [NODE, str(SCRIPT), "SessionStart"], cwd=tmp_path,
        input="{}", text=True, capture_output=True, timeout=5,
    )
    assert result.returncode == 0 and not result.stdout and not result.stderr


def test_missing_skill_reports_safe_failure(tmp_path):
    script = tmp_path / "scripts" / SCRIPT.name
    script.parent.mkdir()
    shutil.copyfile(SCRIPT, script)
    result = subprocess.run(
        [NODE, str(script), "SessionStart"], cwd=tmp_path,
        input="{}", text=True, capture_output=True, timeout=5,
    )
    assert result.returncode == 1 and not result.stdout
    assert result.stderr == "Project Ponytail instructions are unavailable or invalid.\n"


@pytest.mark.parametrize("event", ["SessionStart", "UserPromptSubmit", "SubagentStart"])
def test_registered_command_runs_from_project_subdirectory(event):
    config = json.loads((ROOT / ".codex" / "hooks.json").read_text(encoding="utf-8"))
    handler = config["hooks"][event][0]["hooks"][0]
    result = subprocess.run(
        handler["command"], cwd=ROOT / "app", shell=True,
        input="{}", text=True, capture_output=True, timeout=5,
    )
    assert result.returncode == 0
    assert json.loads(result.stdout)["hookSpecificOutput"]["hookEventName"] == event
