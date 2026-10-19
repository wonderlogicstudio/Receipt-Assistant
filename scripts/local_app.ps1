param(
    [ValidateSet('Start', 'Stop', 'Status')][string]$Action = 'Start',
    [ValidateSet('default', 'v5')][string]$Runtime = 'default',
    [string]$ProjectRoot = (Join-Path $PSScriptRoot '..'),
    [ValidateRange(1024, 65525)][int]$Port = 8501,
    [ValidateRange(1, 120)][int]$StartupTimeoutSeconds = 45,
    [switch]$NoBrowser,
    [switch]$NoDialogs,
    [switch]$LibraryOnly
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$script:Root = [IO.Path]::GetFullPath($ProjectRoot)
$script:EntryPoint = Join-Path $script:Root 'app\main.py'
$script:StateDirectory = Join-Path $script:Root 'output\local_app'
if ($Runtime -eq 'v5') {
    $script:StateDirectory = Join-Path $script:Root 'output\local_app_v5'
    if (!$PSBoundParameters.ContainsKey('Port')) { $Port = 8502 }
}
$script:StateFile = Join-Path $script:StateDirectory 'state.json'

function Read-AppState {
    if (!(Test-Path -LiteralPath $script:StateFile)) { return $null }
    try {
        $state = Get-Content -LiteralPath $script:StateFile -Raw -Encoding UTF8 | ConvertFrom-Json
        if ($state.version -ne 1 -or [int]$state.process_id -le 0 -or
            [int]$state.port -lt 1024 -or [int]$state.port -gt 65535) { return $null }
        return $state
    } catch { return $null }
}

function Save-AppState($State) {
    $State | ConvertTo-Json -Compress | Set-Content -LiteralPath $script:StateFile -Encoding UTF8
}

function Clear-AppState {
    if (Test-Path -LiteralPath $script:StateFile) { Remove-Item -LiteralPath $script:StateFile -Force }
}

function Test-AppCommand([string]$CommandLine) {
    if ([string]::IsNullOrWhiteSpace($CommandLine)) { return $false }
    $entry = [regex]::Escape($script:EntryPoint)
    return $CommandLine -match ('(?i)\s-m\s+streamlit\s+run\s+(?:"' + $entry + '"|' + $entry + ')(?=\s|$)')
}

function Get-OwnedProcess($State) {
    if ($null -eq $State) { return $null }
    try {
        $process = Get-Process -Id ([int]$State.process_id) -ErrorAction Stop
        if ($process.StartTime.ToUniversalTime().Ticks.ToString() -ne [string]$State.started_ticks) { return $null }
        $details = Get-CimInstance Win32_Process -Filter ('ProcessId = ' + [int]$State.process_id)
        if (!(Test-AppCommand $details.CommandLine)) { return $null }
        return $process
    } catch { return $null }
}

function Stop-OwnedProcess($State) {
    $process = Get-OwnedProcess $State
    if ($null -eq $process) { return $false }
    $process.Kill()
    [void]$process.WaitForExit(5000)
    return $true
}

function Get-ListenerId([int]$CandidatePort) {
    # Never print the machine's network inventory.
    foreach ($line in (netstat -ano -p tcp)) {
        if ($line -match ('^\s*TCP\s+\S+:' + $CandidatePort + '\s+\S+\s+LISTENING\s+(\d+)\s*$')) {
            return [int]$Matches[1]
        }
    }
    return 0
}

function Test-AppHealth([int]$CandidatePort) {
    $response = $null
    $reader = $null
    try {
        $request = [Net.HttpWebRequest]::Create("http://127.0.0.1:$CandidatePort/_stcore/health")
        $request.Proxy = $null
        $request.Timeout = 1000
        $request.ReadWriteTimeout = 1000
        $response = $request.GetResponse()
        $reader = New-Object IO.StreamReader($response.GetResponseStream())
        return $response.StatusCode -eq 200 -and $reader.ReadToEnd().Trim() -eq 'ok'
    } catch { return $false }
    finally {
        if ($null -ne $reader) { $reader.Dispose() }
        if ($null -ne $response) { $response.Dispose() }
    }
}

function Find-FreePort {
    foreach ($candidate in $Port..($Port + 10)) {
        $listener = $null
        try {
            $listener = New-Object Net.Sockets.TcpListener([Net.IPAddress]::Loopback, $candidate)
            $listener.Start()
            return $candidate
        } catch { continue }
        finally { if ($null -ne $listener) { $listener.Stop() } }
    }
    throw 'ports_busy'
}

function Test-AppPython([string]$Python, [bool]$RequirePaddle) {
    $check = 'import sys; assert sys.version_info >= (3, 11); import streamlit, pandas, openpyxl, pydantic, dotenv, requests'
    if ($RequirePaddle) { $check += '; import paddle; from paddleocr import PaddleOCR' }
    # Import only: no provider execution, package installation, or model download.
    $previousErrorAction = $ErrorActionPreference
    try {
        # PowerShell 5 treats native stderr warnings as errors; use the exit code.
        $ErrorActionPreference = 'Continue'
        & $Python -c $check 2>$null | Out-Null
        return $LASTEXITCODE -eq 0
    } catch { return $false }
    finally { $ErrorActionPreference = $previousErrorAction }
}

function Get-AppPython {
    $ocrPython = Join-Path $script:Root '.venv-ocr\Scripts\python.exe'
    if ($Runtime -eq 'v5') { $ocrPython = Join-Path $script:Root '.venv-paddle-v5\Scripts\python.exe' }
    $requirePaddle = Test-Path -LiteralPath $ocrPython -PathType Leaf
    $python = Join-Path $script:Root '.venv\Scripts\python.exe'
    if ($requirePaddle) { $python = $ocrPython }
    if ($Runtime -eq 'v5' -and !$requirePaddle) { throw 'ocr_environment_invalid' }
    if (!(Test-Path -LiteralPath $python -PathType Leaf)) { throw 'environment_missing' }
    if (!(Test-AppPython $python $requirePaddle)) {
        if ($requirePaddle) { throw 'ocr_environment_invalid' }
        throw 'environment_missing'
    }
    return $python
}

function Start-AppProcess([string]$Python, [int]$CandidatePort) {
    $arguments = '-m streamlit run "' + $script:EntryPoint + '" --server.address 127.0.0.1 --server.port ' +
        $CandidatePort + ' --server.headless true --browser.gatherUsageStats false'
    $overrides = @{}
    if ($Runtime -eq 'v5') {
        $overrides = @{
            OCR_PROVIDER = 'paddle'; PADDLE_USE_GPU = 'true'; PADDLE_LANG = 'korean'
            PADDLE_PDX_CACHE_HOME = (Join-Path $script:Root '.venv-paddle-v5\model-cache')
            PADDLE_PDX_MODEL_SOURCE = 'BOS'; PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK = 'True'
            APP_DB_PATH = 'data/paddle_v5/app.db'; UPLOAD_DIR = 'data/paddle_v5/uploads'
            MERCHANT_LOOKUP_DB_PATH = 'data/app.db'
            OUTPUT_DIR = 'data/paddle_v5/outputs'
        }
    }
    $previous = @{}
    try {
        foreach ($key in $overrides.Keys) {
            $previous[$key] = [Environment]::GetEnvironmentVariable($key, 'Process')
            [Environment]::SetEnvironmentVariable($key, $overrides[$key], 'Process')
        }
        return Start-Process -FilePath $Python -ArgumentList $arguments -WorkingDirectory $script:Root -WindowStyle Hidden -PassThru
    } finally {
        foreach ($key in $previous.Keys) { [Environment]::SetEnvironmentVariable($key, $previous[$key], 'Process') }
    }
}

function Get-ListenerState([int]$CandidatePort) {
    $listenerId = Get-ListenerId $CandidatePort
    if ($listenerId -le 0) { return $null }
    try {
        $process = Get-Process -Id $listenerId -ErrorAction Stop
        $state = [pscustomobject]@{
            version = 1
            process_id = $listenerId
            started_ticks = $process.StartTime.ToUniversalTime().Ticks.ToString()
            port = $CandidatePort
        }
        if ($null -ne (Get-OwnedProcess $state)) { return $state }
    } catch { }
    return $null
}

function Open-AppBrowser([int]$CandidatePort) {
    if (!$NoBrowser) { Start-Process "http://127.0.0.1:$CandidatePort" }
}

function Invoke-AppAction {
    $state = Read-AppState
    $owned = Get-OwnedProcess $state
    if ($Action -eq 'Status') {
        if ($null -ne $owned -and (Test-AppHealth ([int]$state.port))) {
            return @{ status = 'running'; port = [int]$state.port }
        }
        return @{ status = 'stopped' }
    }
    if ($Action -eq 'Stop') {
        $stopped = Stop-OwnedProcess $state
        Clear-AppState
        if ($stopped) { return @{ status = 'stopped' } }
        return @{ status = 'already_stopped' }
    }
    if ($null -ne $owned) {
        if (!(Test-AppHealth ([int]$state.port))) { throw 'existing_app_unready' }
        Open-AppBrowser ([int]$state.port)
        return @{ status = 'reused'; port = [int]$state.port }
    }
    Clear-AppState
    $python = Get-AppPython
    $selectedPort = Find-FreePort
    $started = Start-AppProcess $python $selectedPort
    $startedState = [pscustomobject]@{
        process_id = $started.Id
        started_ticks = $started.StartTime.ToUniversalTime().Ticks.ToString()
    }
    $deadline = [DateTime]::UtcNow.AddSeconds($StartupTimeoutSeconds)
    $listenerState = $null
    try {
        do {
            $listenerState = Get-ListenerState $selectedPort
            if ($null -ne $listenerState -and (Test-AppHealth $selectedPort)) {
                Save-AppState $listenerState
                Open-AppBrowser $selectedPort
                return @{ status = 'started'; port = $selectedPort }
            }
            Start-Sleep -Milliseconds 300
        } while ([DateTime]::UtcNow -lt $deadline)
        throw 'startup_failed'
    } catch {
        # A venv redirector may spawn a child: verify both identities before stopping.
        if ($null -ne $listenerState) { [void](Stop-OwnedProcess $listenerState) }
        [void](Stop-OwnedProcess $startedState)
        Clear-AppState
        throw 'startup_failed'
    }
}

function Show-AppMessage([string]$Message, [bool]$IsError = $false) {
    if ($NoDialogs) { return }
    $shell = New-Object -ComObject WScript.Shell
    $icon = 64
    if ($IsError) { $icon = 16 }
    [void]$shell.Popup($Message, 0, 'Receipt Assistant', $icon)
}

if ($LibraryOnly) { return }
$lock = $null
$exitCode = 0
try {
    [void][IO.Directory]::CreateDirectory($script:StateDirectory)
    try {
        $lock = [IO.File]::Open((Join-Path $script:StateDirectory 'launcher.lock'), 'OpenOrCreate', 'ReadWrite', 'None')
    } catch { throw 'launcher_busy' }
    $result = Invoke-AppAction
    if ($NoDialogs -or $Action -eq 'Status') { $result | ConvertTo-Json -Compress }
    elseif ($Action -eq 'Stop') { Show-AppMessage '영수증 비서가 종료되었습니다. 실행 중인 앱이 없으면 아무 작업도 하지 않습니다.' }
} catch {
    $code = $_.Exception.Message
    $messages = @{
        environment_missing = '실행 환경이 없습니다. README의 설치 방법으로 .venv를 먼저 준비해 주세요.'
        ocr_environment_invalid = 'OCR 실행 환경을 불러오지 못했습니다. README의 PaddleOCR 실행 환경 안내를 확인해 주세요.'
        ports_busy = '로컬 포트가 사용 중입니다. 다른 앱을 확인한 뒤 다시 실행해 주세요.'
        launcher_busy = '앱을 실행하거나 종료하는 중입니다. 잠시 후 다시 눌러 주세요.'
        existing_app_unready = '실행 중인 앱이 응답하지 않습니다. 영수증 비서 종료 파일을 누른 뒤 다시 실행해 주세요.'
        startup_failed = '앱을 시작하지 못했습니다. 실행 환경을 확인한 뒤 다시 시도해 주세요.'
    }
    if (!$messages.ContainsKey($code)) { $code = 'startup_failed' }
    if ($NoDialogs) { @{ status = 'error'; code = $code } | ConvertTo-Json -Compress }
    else { Show-AppMessage $messages[$code] $true }
    $exitCode = 1
} finally {
    if ($null -ne $lock) { $lock.Dispose() }
}
exit $exitCode
