Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$projectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $projectRoot

Write-Host "Starting Receipt Assistant Streamlit app..."
Write-Host ""
Write-Host "Keep this terminal open while testing."
Write-Host "Open this URL in your browser:"
Write-Host "http://127.0.0.1:8501"
Write-Host ""

python -m streamlit run app/main.py --server.address 127.0.0.1 --server.port 8501 --server.headless true
