param(
    [Parameter(Mandatory=$true)][string]$Executable,
    [Parameter(Mandatory=$true)][string]$Data,
    [Parameter(Mandatory=$true)][string]$Output
)
$ErrorActionPreference = 'Stop'
$Executable = (Resolve-Path -LiteralPath $Executable).Path
$Data = (Resolve-Path -LiteralPath $Data).Path
if (Get-Process -Name wowee -ErrorAction SilentlyContinue) {
    throw 'A WoWee session is already running. Smoke test skipped to preserve it.'
}
if (Test-Path -LiteralPath $Output) {
    throw 'Choose a new output directory for a fresh smoke-test config.'
}
$Output = (New-Item -ItemType Directory -Path $Output).FullName
$names = 'WOW_DATA_PATH','WOWEE_CONFIG_ROOT','WOWEE_LOG_FILE','WOWEE_SCREENSHOT'
$previous = @{}
foreach ($name in $names) { $previous[$name] = [Environment]::GetEnvironmentVariable($name) }
try {
    $env:WOW_DATA_PATH = $Data
    $env:WOWEE_CONFIG_ROOT = Join-Path $Output 'config'
    $env:WOWEE_LOG_FILE = Join-Path $Output 'wowee.log'
    $env:WOWEE_SCREENSHOT = Join-Path $Output 'login.png'
    New-Item -ItemType Directory -Path $env:WOWEE_CONFIG_ROOT | Out-Null
    Set-Content -LiteralPath (Join-Path $env:WOWEE_CONFIG_ROOT 'settings.cfg') -Value 'check_for_updates=0'
    # The client's existing screenshot hook quits after capturing its own
    # framebuffer. No UI input, credentials, or realm login is involved.
    $process = Start-Process -FilePath $Executable -WorkingDirectory (Split-Path $Executable) `
        -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $Output 'stdout.log') `
        -RedirectStandardError (Join-Path $Output 'stderr.log')
    if (-not $process.WaitForExit(60000)) {
        # Only the process created by this invocation is terminated.
        $process.Kill()
        throw 'Review client did not finish screenshot smoke test within 60 seconds.'
    }
    $process.Refresh()
    if ($process.ExitCode -ne 0 -or -not (Test-Path -LiteralPath $env:WOWEE_SCREENSHOT)) {
        throw "Screenshot smoke test failed (exit $($process.ExitCode)); see $Output"
    }
    Get-FileHash -LiteralPath $env:WOWEE_SCREENSHOT -Algorithm SHA256 |
        ConvertTo-Json | Set-Content -LiteralPath (Join-Path $Output 'screenshot-hash.json')
    Write-Output "PASS: Login screenshot and clean exit; no in-game QA. $Output"
} finally {
    foreach ($name in $names) { [Environment]::SetEnvironmentVariable($name, $previous[$name]) }
}
