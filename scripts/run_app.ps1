param(
    [ValidateSet('Start', 'Stop', 'Status')][string]$Action = 'Start',
    [switch]$NoBrowser,
    [switch]$NoDialogs
)

& (Join-Path $PSScriptRoot 'local_app.ps1') -Action $Action -NoBrowser:$NoBrowser -NoDialogs:$NoDialogs
exit $LASTEXITCODE
