param(
    [string]$TaskName = "CycleQuant Daily Paper Evaluation",
    [string]$DailyAt = "06:45"
)

$ErrorActionPreference = "Stop"
$runScript = Join-Path $PSScriptRoot "run_daily.ps1"
if (-not (Test-Path -LiteralPath $runScript)) {
    throw "Daily runner not found at $runScript"
}

$parsedTime = [DateTime]::ParseExact(
    $DailyAt,
    "HH:mm",
    [Globalization.CultureInfo]::InvariantCulture
)
$action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-NoProfile -File `"$runScript`""
$trigger = New-ScheduledTaskTrigger -Daily -At $parsedTime
$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 20)

Register-ScheduledTask `
    -TaskName $TaskName `
    -Description "Runs the CycleQuant paper-only daily evaluation." `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Force

Write-Host "Registered '$TaskName' for $DailyAt local time."
