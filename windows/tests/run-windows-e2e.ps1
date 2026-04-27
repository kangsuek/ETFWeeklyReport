param(
  [ValidateSet("install", "portable")]
  [string]$PackageType = "install",
  [string]$InstallerPath = "",
  [string]$AppExePath = "",
  [int]$StartupTimeoutSec = 180,
  [switch]$SkipInstall,
  [switch]$UseDirectExe
)

$ErrorActionPreference = "Stop"

function Write-Step {
  param([string]$Message)
  Write-Host ""
  Write-Host "==> $Message" -ForegroundColor Cyan
}

function Add-Result {
  param(
    [string]$Name,
    [bool]$Passed,
    [string]$Detail
  )
  $script:Results += [PSCustomObject]@{
    Name = $Name
    Passed = $Passed
    Detail = $Detail
  }
}

function Test-HttpStatus {
  param(
    [string]$Url,
    [int]$ExpectedStatus = 200
  )
  try {
    $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 15
    if ($response.StatusCode -eq $ExpectedStatus) {
      return @{ Passed = $true; Detail = "status=$($response.StatusCode)" }
    }
    return @{ Passed = $false; Detail = "unexpected status=$($response.StatusCode)" }
  } catch {
    return @{ Passed = $false; Detail = $_.Exception.Message }
  }
}

function Find-Installer {
  param([string]$ExplicitPath)
  if ($ExplicitPath -and (Test-Path $ExplicitPath)) {
    return (Resolve-Path $ExplicitPath).Path
  }

  $repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
  $releaseDir = Join-Path $repoRoot "windows\release"
  if (-not (Test-Path $releaseDir)) {
    return $null
  }

  $candidate = Get-ChildItem -Path $releaseDir -Filter "*Setup*.exe" -File |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1

  if ($candidate) { return $candidate.FullName }
  return $null
}

function Find-DirectExe {
  param([string]$ExplicitPath)

  if ($ExplicitPath -and (Test-Path $ExplicitPath)) {
    return (Resolve-Path $ExplicitPath).Path
  }

  $repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
  $releaseDir = Join-Path $repoRoot "windows\release"
  $candidates = @(
    (Join-Path $releaseDir "win-unpacked\ETF Weekly Report.exe"),
    (Join-Path $releaseDir "ETF Weekly Report.exe")
  )

  foreach ($candidate in $candidates) {
    if (Test-Path $candidate) {
      return (Resolve-Path $candidate).Path
    }
  }

  $latest = Get-ChildItem -Path $releaseDir -Filter "*.exe" -File -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -notmatch "Setup|Uninstall" } |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1

  if ($latest) { return $latest.FullName }
  return $null
}

function Find-AppExe {
  $candidates = @(
    "$env:LOCALAPPDATA\Programs\ETF Weekly Report\ETF Weekly Report.exe",
    "$env:ProgramFiles\ETF Weekly Report\ETF Weekly Report.exe",
    "${env:ProgramFiles(x86)}\ETF Weekly Report\ETF Weekly Report.exe"
  )

  foreach ($path in $candidates) {
    if ($path -and (Test-Path $path)) {
      return $path
    }
  }
  return $null
}

function Stop-EtfProcesses {
  $targets = Get-Process -Name "ETF Weekly Report" -ErrorAction SilentlyContinue
  foreach ($p in $targets) {
    try {
      Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue
    } catch {
      # ignore
    }
  }
}

$script:Results = @()
$reportDir = Join-Path $PSScriptRoot "reports"
New-Item -Path $reportDir -ItemType Directory -Force | Out-Null
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$reportPath = Join-Path $reportDir "windows-e2e-$timestamp.json"

Write-Step "사전 정리"
Stop-EtfProcesses
Start-Sleep -Seconds 1

# 하위 호환: 기존 -UseDirectExe 사용 시 portable 모드로 강제
if ($UseDirectExe) {
  $PackageType = "portable"
}

if ($PackageType -eq "portable") {
  Write-Step "실행형 EXE 찾기"
  $directExe = Find-DirectExe -ExplicitPath $AppExePath
  if (-not $directExe) {
    Add-Result -Name "[실행형] EXE 탐색" -Passed $false -Detail "실행할 EXE를 찾을 수 없습니다."
    $Results | ConvertTo-Json -Depth 4 | Out-File -FilePath $reportPath -Encoding utf8
    Write-Host "FAILED: direct exe not found" -ForegroundColor Red
    exit 1
  }
  Add-Result -Name "[실행형] EXE 탐색" -Passed $true -Detail $directExe

  Write-Step "실행형 EXE 시작"
  try {
    Start-Process -FilePath $directExe | Out-Null
    Add-Result -Name "[실행형] EXE 실행" -Passed $true -Detail "process started"
  } catch {
    Add-Result -Name "[실행형] EXE 실행" -Passed $false -Detail $_.Exception.Message
  }
} elseif (-not $SkipInstall) {
  Write-Step "설치 파일 찾기"
  $resolvedInstaller = Find-Installer -ExplicitPath $InstallerPath
  if (-not $resolvedInstaller) {
    Add-Result -Name "[설치형] Setup EXE 탐색" -Passed $false -Detail "설치 파일(.exe)을 찾을 수 없습니다."
    $Results | ConvertTo-Json -Depth 4 | Out-File -FilePath $reportPath -Encoding utf8
    Write-Host "FAILED: installer not found" -ForegroundColor Red
    exit 1
  }
  Add-Result -Name "[설치형] Setup EXE 탐색" -Passed $true -Detail $resolvedInstaller

  Write-Step "앱 설치 실행 (무인 설치: /S)"
  try {
    $proc = Start-Process -FilePath $resolvedInstaller -ArgumentList "/S" -PassThru -Wait
    if ($proc.ExitCode -eq 0) {
      Add-Result -Name "[설치형] 무인 설치" -Passed $true -Detail "exitCode=0"
    } else {
      Add-Result -Name "[설치형] 무인 설치" -Passed $false -Detail "exitCode=$($proc.ExitCode)"
    }
  } catch {
    Add-Result -Name "[설치형] 무인 설치" -Passed $false -Detail $_.Exception.Message
  }
} else {
  Add-Result -Name "[설치형] 설치 단계" -Passed $true -Detail "skipped by -SkipInstall"
}

Write-Step "설치된 실행 파일 확인"
if ($PackageType -eq "install") {
  $appExe = Find-AppExe
  if ($appExe) {
    Add-Result -Name "[설치형] 설치 경로 실행파일 탐색" -Passed $true -Detail $appExe
  } else {
    Add-Result -Name "[설치형] 설치 경로 실행파일 탐색" -Passed $false -Detail "설치 경로에서 실행 파일을 찾지 못했습니다."
  }
} else {
  Add-Result -Name "[실행형] 설치 경로 탐색" -Passed $true -Detail "portable 모드에서는 스킵"
}

Write-Step "앱 실행 및 백엔드 준비 대기"
if ($PackageType -eq "install") {
  if ($appExe) {
    try {
      Start-Process -FilePath $appExe | Out-Null
      Add-Result -Name "[설치형] 앱 실행" -Passed $true -Detail "process started"
    } catch {
      Add-Result -Name "[설치형] 앱 실행" -Passed $false -Detail $_.Exception.Message
    }
  } else {
    Add-Result -Name "[설치형] 앱 실행" -Passed $false -Detail "실행 파일 미확인으로 스킵"
  }
}

$healthOk = $false
$deadline = (Get-Date).AddSeconds($StartupTimeoutSec)
while ((Get-Date) -lt $deadline) {
  $health = Test-HttpStatus -Url "http://localhost:18000/api/health" -ExpectedStatus 200
  if ($health.Passed) {
    $healthOk = $true
    Add-Result -Name "Health check" -Passed $true -Detail $health.Detail
    break
  }
  Start-Sleep -Seconds 2
}
if (-not $healthOk) {
  Add-Result -Name "Health check" -Passed $false -Detail "timeout=${StartupTimeoutSec}s"
}

Write-Step "핵심 API 기능 점검"
$apiChecks = @(
  @{ Name = "GET /api/etfs"; Url = "http://localhost:18000/api/etfs"; Status = 200 },
  @{ Name = "GET /api/data/scheduler-status"; Url = "http://localhost:18000/api/data/scheduler-status"; Status = 200 },
  @{ Name = "GET /api/settings/stocks"; Url = "http://localhost:18000/api/settings/stocks"; Status = 200 },
  @{ Name = "GET /api/scanner/themes"; Url = "http://localhost:18000/api/scanner/themes"; Status = 200 }
)

foreach ($check in $apiChecks) {
  $result = Test-HttpStatus -Url $check.Url -ExpectedStatus $check.Status
  Add-Result -Name $check.Name -Passed $result.Passed -Detail $result.Detail
}

Write-Step "런타임 산출물 확인"
$workspacePath = Join-Path $env:APPDATA "ETF Weekly Report"
$logPath = Join-Path $workspacePath "logs\app.log"
$venvPythonPath = Join-Path $workspacePath ".venv\Scripts\python.exe"

Add-Result -Name "Workspace path exists" -Passed (Test-Path $workspacePath) -Detail $workspacePath
Add-Result -Name "Log file exists" -Passed (Test-Path $logPath) -Detail $logPath
Add-Result -Name "Venv python exists" -Passed (Test-Path $venvPythonPath) -Detail $venvPythonPath

if (Test-Path $logPath) {
  $logContent = Get-Content -Path $logPath -Raw -ErrorAction SilentlyContinue
  Add-Result -Name "Log contains backend start" -Passed ($logContent -match "Starting backend") -Detail "keyword=Starting backend"
  Add-Result -Name "Log contains backend ready" -Passed ($logContent -match "Backend ready") -Detail "keyword=Backend ready"
}

Write-Step "앱 종료"
Stop-EtfProcesses

$Results | ConvertTo-Json -Depth 4 | Out-File -FilePath $reportPath -Encoding utf8

$failed = $Results | Where-Object { -not $_.Passed }
if ($failed.Count -gt 0) {
  Write-Host ""
  Write-Host "테스트 실패 항목: $($failed.Count)개" -ForegroundColor Red
  $failed | ForEach-Object { Write-Host " - $($_.Name): $($_.Detail)" -ForegroundColor Red }
  Write-Host "리포트: $reportPath"
  exit 1
}

Write-Host ""
Write-Host "모든 테스트 통과" -ForegroundColor Green
Write-Host "리포트: $reportPath"
exit 0
