"""Windows launcher checks with synthetic processes and temporary state only."""

import base64
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess

import pytest


LAUNCHER = Path(__file__).resolve().parents[1] / "scripts" / "local_app.ps1"
POWERSHELL = shutil.which("powershell.exe")
pytestmark = pytest.mark.skipif(os.name != "nt" or not POWERSHELL, reason="Windows launcher")


def run_ps(tmp_path, body, *, action="Start", runtime="default", timeout=20):
    project = tmp_path / "synthetic project with spaces"
    project.mkdir(exist_ok=True)
    env = dict(os.environ, LAUNCHER_PATH=str(LAUNCHER), LAUNCHER_ROOT=str(project))
    script = (
        f". $env:LAUNCHER_PATH -LibraryOnly -ProjectRoot $env:LAUNCHER_ROOT -Action {action} "
        f"-Runtime {runtime} -NoBrowser -NoDialogs -StartupTimeoutSeconds 1\n"
        "[void][IO.Directory]::CreateDirectory($script:StateDirectory)\n"
        + body
    )
    encoded = base64.b64encode(script.encode("utf-16le")).decode("ascii")
    result = subprocess.run(
        [POWERSHELL, "-NoProfile", "-ExecutionPolicy", "Bypass", "-EncodedCommand", encoded],
        env=env, capture_output=True, timeout=timeout,
    )
    # Avoid echoing process commands or absolute paths on test failure.
    assert result.returncode == 0, "Launcher check failed"
    return json.loads(result.stdout.decode("utf-8-sig").strip())


def test_repeated_start_reuses_verified_app(tmp_path):
    result = run_ps(tmp_path, """
function Read-AppState { return @{ port = 8510 } }
function Get-OwnedProcess($State) { return @{ Id = 42 } }
function Test-AppHealth([int]$CandidatePort) { return $CandidatePort -eq 8510 }
function Start-AppProcess { throw 'duplicate_start' }
Invoke-AppAction | ConvertTo-Json -Compress
""")
    assert result == {"status": "reused", "port": 8510}


def test_unready_existing_app_is_not_replaced(tmp_path):
    result = run_ps(tmp_path, """
function Read-AppState { return @{ port = 8510 } }
function Get-OwnedProcess($State) { return @{ Id = 42 } }
function Test-AppHealth { return $false }
function Start-AppProcess { throw 'duplicate_start' }
try { Invoke-AppAction } catch { @{ code = $_.Exception.Message } | ConvertTo-Json -Compress }
""")
    assert result == {"code": "existing_app_unready"}


def test_busy_port_is_skipped_without_stopping_its_listener(tmp_path):
    with socket.socket() as occupied:
        occupied.bind(("127.0.0.1", 0))
        occupied.listen()
        port = occupied.getsockname()[1]
        if port > 65525:
            pytest.skip("Ephemeral port outside launcher range")
        result = run_ps(tmp_path, f"""
$Port = {port}
function Stop-OwnedProcess {{ throw 'must_not_stop_other_app' }}
@{{ port = (Find-FreePort) }} | ConvertTo-Json -Compress
""")
        assert port < result["port"] <= port + 10
        assert occupied.getsockname()[1] == port


@pytest.mark.parametrize("wrong_start,wrong_command", [(True, False), (False, True)])
def test_stop_rejects_reused_pid_or_foreign_command(tmp_path, wrong_start, wrong_command):
    ticks = "0" if wrong_start else "638000000000000000"
    command = "python.exe -m http.server" if wrong_command else "python.exe -m streamlit run"
    result = run_ps(tmp_path, f"""
function Get-Process {{ return [pscustomobject]@{{ StartTime = [DateTime]::new(638000000000000000) }} }}
function Get-CimInstance {{ return [pscustomobject]@{{ CommandLine = '{command}' }} }}
$state = @{{ process_id = 42; started_ticks = '{ticks}' }}
@{{ stopped = (Stop-OwnedProcess $state) }} | ConvertTo-Json -Compress
""")
    assert result == {"stopped": False}


def test_stop_only_verified_process_and_clear_state(tmp_path):
    result = run_ps(tmp_path, """
$script:killed = $false
$fake = [pscustomobject]@{ Id = 42 }
$fake | Add-Member ScriptMethod Kill { $script:killed = $true }
$fake | Add-Member ScriptMethod WaitForExit { param($Timeout) return $true }
function Get-OwnedProcess($State) { return $fake }
Save-AppState @{ version = 1; process_id = 42; started_ticks = '123'; port = 8501 }
$result = Invoke-AppAction
@{ status = $result.status; killed = $script:killed; state_exists = (Test-Path $script:StateFile) } | ConvertTo-Json -Compress
""", action="Stop")
    assert result == {"status": "stopped", "killed": True, "state_exists": False}


def test_missing_environment_does_not_install_or_start(tmp_path):
    result = run_ps(tmp_path, """
function Start-AppProcess { throw 'must_not_start' }
try { Invoke-AppAction } catch { @{ code = $_.Exception.Message } | ConvertTo-Json -Compress }
""")
    assert result == {"code": "environment_missing"}


@pytest.mark.parametrize("with_ocr", [False, True])
def test_runtime_prefers_ocr_environment_and_checks_its_imports(tmp_path, with_ocr):
    setup_ocr = """
[void][IO.Directory]::CreateDirectory((Join-Path $script:Root '.venv-ocr/Scripts'))
[void](New-Item -ItemType File -Path (Join-Path $script:Root '.venv-ocr/Scripts/python.exe'))
""" if with_ocr else ""
    result = run_ps(tmp_path, """
[void][IO.Directory]::CreateDirectory((Join-Path $script:Root '.venv/Scripts'))
[void](New-Item -ItemType File -Path (Join-Path $script:Root '.venv/Scripts/python.exe'))
""" + setup_ocr + """
$script:paddleChecked = $false
function Test-AppPython($Python, $RequirePaddle) {
    $script:paddleChecked = $RequirePaddle
    return $true
}
$selected = Get-AppPython
@{ selected = $selected.Substring($script:Root.Length + 1); paddle_checked = $script:paddleChecked } | ConvertTo-Json -Compress
""")
    folder = ".venv-ocr" if with_ocr else ".venv"
    assert result == {"selected": str(Path(folder) / "Scripts" / "python.exe"), "paddle_checked": with_ocr}


def test_broken_ocr_environment_does_not_silently_use_non_ocr_python(tmp_path):
    result = run_ps(tmp_path, """
foreach ($folder in @('.venv', '.venv-ocr')) {
    [void][IO.Directory]::CreateDirectory((Join-Path $script:Root ($folder + '/Scripts')))
    [void](New-Item -ItemType File -Path (Join-Path $script:Root ($folder + '/Scripts/python.exe')))
}
function Test-AppPython { return $false }
try { Get-AppPython | Out-Null } catch { @{ code = $_.Exception.Message } | ConvertTo-Json -Compress }
""")
    assert result == {"code": "ocr_environment_invalid"}


def test_startup_timeout_cleans_up_only_verified_identities(tmp_path):
    result = run_ps(tmp_path, """
$script:stopped = @()
function Get-AppPython { return 'synthetic-python' }
function Find-FreePort { return 8510 }
function Start-AppProcess { return [pscustomobject]@{ Id = 41; StartTime = [DateTime]::UtcNow } }
function Get-ListenerState { return @{ process_id = 42; started_ticks = '123'; port = 8510 } }
function Test-AppHealth { return $false }
function Stop-OwnedProcess($State) { $script:stopped += $State.process_id; return $true }
try { Invoke-AppAction } catch {
    @{ code = $_.Exception.Message; stopped = $script:stopped; state_exists = (Test-Path $script:StateFile) } | ConvertTo-Json -Compress
}
""")
    assert result == {"code": "startup_failed", "stopped": [42, 41], "state_exists": False}


def test_command_identity_and_quoted_entrypoint_with_spaces(tmp_path):
    result = run_ps(tmp_path, r"""
@{
    own = (Test-AppCommand ('python.exe -m streamlit run "' + $script:EntryPoint + '" --server.port 8501'))
    foreign = (Test-AppCommand 'python.exe -m streamlit run "C:\other\app\main.py"')
    suffix = (Test-AppCommand ('python.exe -m streamlit run "' + $script:EntryPoint + '.other"'))
} | ConvertTo-Json -Compress
""")
    assert result == {"own": True, "foreign": False, "suffix": False}


def test_launch_arguments_keep_project_path_quoted_and_server_local(tmp_path):
    result = run_ps(tmp_path, """
function Start-Process {
    param($FilePath, $ArgumentList, $WorkingDirectory, $WindowStyle, [switch]$PassThru)
    return @{
        quoted = $ArgumentList.Contains(('run "' + $script:EntryPoint + '" '))
        loopback = $ArgumentList.Contains('--server.address 127.0.0.1')
        hidden = $WindowStyle -eq 'Hidden'
        cwd = $WorkingDirectory -eq $script:Root
    }
}
Start-AppProcess 'synthetic-python' 8510 | ConvertTo-Json -Compress
""")
    assert result == {"quoted": True, "loopback": True, "hidden": True, "cwd": True}


def test_state_contains_only_process_metadata_and_handles_corruption(tmp_path):
    result = run_ps(tmp_path, """
Save-AppState @{ version = 1; process_id = 42; started_ticks = '123'; port = 8501 }
$valid = Read-AppState
Set-Content -LiteralPath $script:StateFile -Value '{broken'
@{ keys = @($valid.PSObject.Properties.Name | Sort-Object); corrupt_is_null = ($null -eq (Read-AppState)) } | ConvertTo-Json -Compress
""")
    assert result == {"keys": ["port", "process_id", "started_ticks", "version"], "corrupt_is_null": True}


def test_second_launcher_cannot_take_the_lock(tmp_path):
    result = run_ps(tmp_path, """
$lockPath = Join-Path $script:StateDirectory 'launcher.lock'
$first = [IO.File]::Open($lockPath, 'OpenOrCreate', 'ReadWrite', 'None')
$blocked = $false
try { $second = [IO.File]::Open($lockPath, 'OpenOrCreate', 'ReadWrite', 'None'); $second.Dispose() }
catch { $blocked = $true }
finally { $first.Dispose() }
@{ blocked = $blocked } | ConvertTo-Json -Compress
""")
    assert result == {"blocked": True}


def test_v5_runtime_has_separate_python_state_and_port(tmp_path):
    result = run_ps(tmp_path, """
[void][IO.Directory]::CreateDirectory((Join-Path $script:Root '.venv-paddle-v5/Scripts'))
[void](New-Item -ItemType File -Path (Join-Path $script:Root '.venv-paddle-v5/Scripts/python.exe'))
function Test-AppPython($Python, $RequirePaddle) { return $RequirePaddle }
$selected = Get-AppPython
@{ selected = $selected.Substring($script:Root.Length + 1); port = $Port;
   separate = $script:StateDirectory.EndsWith('local_app_v5') } | ConvertTo-Json -Compress
""", runtime="v5")
    assert result == {"selected": str(Path('.venv-paddle-v5')/'Scripts'/'python.exe'),
                      "port": 8502, "separate": True}


def test_v5_child_uses_local_paddle_and_isolated_data_and_restores_environment(tmp_path):
    result = run_ps(tmp_path, """
$oldProvider = [Environment]::GetEnvironmentVariable('OCR_PROVIDER', 'Process')
function Start-Process {
    param($FilePath, $ArgumentList, $WorkingDirectory, $WindowStyle, [switch]$PassThru)
    return @{ provider = $env:OCR_PROVIDER; gpu = $env:PADDLE_USE_GPU;
              isolated_db = $env:APP_DB_PATH -eq 'data/paddle_v5/app.db'; hidden = $WindowStyle -eq 'Hidden';
              shared_lookup = $env:MERCHANT_LOOKUP_DB_PATH -eq 'data/app.db' }
}
$child = Start-AppProcess 'synthetic-python' 8502
$child.restored = [Environment]::GetEnvironmentVariable('OCR_PROVIDER', 'Process') -eq $oldProvider
$child | ConvertTo-Json -Compress
""", runtime="v5")
    assert result == {"provider": "paddle", "gpu": "true", "isolated_db": True,
                      "hidden": True, "restored": True, "shared_lookup": True}


@pytest.mark.parametrize('exit_code,valid', [(0, True), (1, False)])
def test_import_check_uses_exit_code_instead_of_native_stderr(tmp_path, exit_code, valid):
    result = run_ps(tmp_path, f"""
$fake = Join-Path $script:Root 'synthetic.cmd'
Set-Content -LiteralPath $fake -Value "@echo off`r`necho synthetic warning 1>&2`r`nexit /b {exit_code}"
$before = $ErrorActionPreference
@{{ valid = (Test-AppPython $fake $false); restored = $ErrorActionPreference -eq $before }} | ConvertTo-Json -Compress
""")
    assert result == {"valid": valid, "restored": True}
