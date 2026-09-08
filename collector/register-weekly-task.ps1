# Register a weekly Windows task that runs collector\pull.cmd.
# Default: every Monday at 21:00 (after a typical Premier League weekend).
# Requires that .env has SOFASCORE_SESSION and SOFASCORE_* URLs.

param(
    [string]$Day = "MON",
    [string]$Time = "21:00",
    [string]$TaskName = "FantasyFootballTrackerPull"
)

$script = Join-Path $PSScriptRoot "pull.cmd"
if (-not (Test-Path $script)) {
    throw "Missing $script"
}

$command = "schtasks /Create /TN `"$TaskName`" /TR `"$script`" /SC WEEKLY /D $Day /ST $Time /RL LIMITED /F"
Write-Host $command
cmd /c $command
if ($LASTEXITCODE -ne 0) {
    throw "schtasks failed with exit code $LASTEXITCODE"
}
Write-Host "Registered weekly task '$TaskName' ($Day $Time)."
Write-Host "Logs: $(Join-Path $PSScriptRoot 'cache\pull.log')"
Write-Host "When SofaScore returns 401, refresh SOFASCORE_SESSION in .env."
