Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$projectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $projectRoot
$port = 8501

Write-Host "Checking for existing Receipt Assistant Streamlit servers on port $port..."
$existingProcessIds = @()
$netstatLines = netstat -ano | Select-String ":$port"
foreach ($line in $netstatLines) {
    $text = $line.Line.Trim()
    if ($text -notmatch "LISTENING") {
        continue
    }
    $parts = $text -split "\s+"
    $processIdText = $parts[-1]
    $processId = 0
    if ([int]::TryParse($processIdText, [ref]$processId)) {
        $existingProcessIds += $processId
    }
}

$existingProcessIds = $existingProcessIds | Sort-Object -Unique
foreach ($processId in $existingProcessIds) {
    try {
        $process = Get-Process -Id $processId -ErrorAction Stop
        if ($process.ProcessName -in @("python", "streamlit")) {
            Write-Host "Stopping stale Streamlit process $processId on port $port..."
            Stop-Process -Id $processId -Force
        }
    } catch {
        Write-Host "Process $processId is no longer running."
    }
}

Write-Host "Starting Receipt Assistant Streamlit app..."
Write-Host ""
Write-Host "Keep this terminal open while testing."
Write-Host "Open this URL in your browser:"
Write-Host "http://127.0.0.1:$port"
Write-Host ""

python -m streamlit run app/main.py --server.address 127.0.0.1 --server.port $port --server.headless true
