param(
    [Parameter(Mandatory = $true)]
    [string]$Message,

    [switch]$SkipChecks
)

$ErrorActionPreference = "Stop"

function Stop-WithMessage {
    param([string]$Text)
    Write-Host "ERROR: $Text" -ForegroundColor Red
    exit 1
}

# Always run from repository root, even when the script is launched from scripts/.
$repoRoot = git rev-parse --show-toplevel 2>$null
if (-not $repoRoot) {
    Stop-WithMessage "This folder is not a Git repository. Run the script inside C:\OSPanel\home\gas-ratio-pro."
}
Set-Location $repoRoot

$currentBranch = (git branch --show-current).Trim()
if ($currentBranch -ne "main") {
    Write-Host "Switching branch: $currentBranch -> main" -ForegroundColor Yellow
    git checkout main
}

# Keep origin/main as the only upstream for the working branch.
git branch --set-upstream-to=origin/main main 2>$null | Out-Null

# Do not allow accidental commits to master.
$localMaster = git branch --list master
if ($localMaster) {
    Write-Host "Local branch 'master' exists but is not used by this project." -ForegroundColor Yellow
    Write-Host "Delete it after your working tree is clean: git branch -D master" -ForegroundColor Yellow
}

if (-not $SkipChecks) {
    Write-Host "Running tests..." -ForegroundColor Cyan
    python -m pytest

    Write-Host "Running preflight..." -ForegroundColor Cyan
    if (Test-Path "tools/preflight.py") {
        python tools/preflight.py
    }
    else {
        python scripts/preflight.py
    }
}

$status = git status --porcelain
if (-not $status) {
    Write-Host "Nothing to commit. Working tree is clean." -ForegroundColor Green
    git status
    exit 0
}

git add .
git commit -m $Message

Write-Host "Local commit created on main." -ForegroundColor Green
Write-Host "Push manually with: git push origin main" -ForegroundColor Cyan
git status
