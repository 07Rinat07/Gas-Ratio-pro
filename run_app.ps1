param(
    [int]$Port = 8501,
    [switch]$ForceRestart,
    [switch]$Diagnostics
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ProjectRoot = (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $ProjectRoot
$EntryPoint = Join-Path $ProjectRoot "app\streamlit_app.py"

$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (Test-Path -LiteralPath $VenvPython) {
    $Python = $VenvPython
} else {
    $Python = "python"
}

function Get-PortOwnerProcess {
    param([int]$ListenPort)
    try {
        $connection = Get-NetTCPConnection -LocalPort $ListenPort -State Listen -ErrorAction Stop | Select-Object -First 1
        if ($null -eq $connection) { return $null }
        return Get-CimInstance Win32_Process -Filter "ProcessId = $($connection.OwningProcess)"
    } catch {
        return $null
    }
}

$owner = Get-PortOwnerProcess -ListenPort $Port
if ($null -ne $owner) {
    $commandLine = [string]$owner.CommandLine
    $isThisProject = $commandLine.Contains($ProjectRoot) -or $commandLine.Contains($EntryPoint)
    if ($ForceRestart -and $isThisProject) {
        Write-Host "Stopping previous Gas Ratio Pro process PID $($owner.ProcessId) on port $Port..." -ForegroundColor Yellow
        Stop-Process -Id $owner.ProcessId -Force
        Start-Sleep -Milliseconds 800
    } else {
        Write-Host "Port $Port is already occupied by PID $($owner.ProcessId)." -ForegroundColor Red
        Write-Host "Command: $commandLine" -ForegroundColor DarkYellow
        if ($isThisProject) {
            Write-Host "This is an older Gas Ratio Pro process. Restart with:" -ForegroundColor Yellow
            Write-Host "  .\run_app.ps1 -Port $Port -ForceRestart" -ForegroundColor Cyan
        } else {
            Write-Host "Use another port, for example:" -ForegroundColor Yellow
            Write-Host "  .\run_app.ps1 -Port 8502" -ForegroundColor Cyan
        }
        exit 2
    }
}

Write-Host "Starting Gas Ratio Pro v222.46" -ForegroundColor Green
Write-Host "Source: $ProjectRoot" -ForegroundColor Cyan
Write-Host "URL: http://localhost:$Port" -ForegroundColor Cyan

$env:GAS_RATIO_PRO_LEGACY_UI = ""
$env:GAS_RATIO_PRO_DIAGNOSTICS = if ($Diagnostics) { "1" } else { "" }
& $Python -m streamlit run $EntryPoint --server.port $Port --server.headless true
exit $LASTEXITCODE
