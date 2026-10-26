<#
Khuration 크롤링 1회 실행 + 로그 저장. Windows 작업 스케줄러가 매일 14:00, 20:00에 부른다
(등록 방법은 backend/app/crawler/CLAUDE.md "자동 실행").

  powershell -NoProfile -ExecutionPolicy Bypass -File backend\scripts\crawl.ps1                 # 전체 크롤링 후 저장
  powershell -NoProfile -ExecutionPolicy Bypass -File backend\scripts\crawl.ps1 -DryRun -Limit 1  # 저장 없이 시험

- 로그: backend\logs\YYYY-MM-DD.log 에 이어 붙인다 (하루 2회 실행이 한 파일에). 30일 지난 로그는 지운다
- .env(ChatKHU 키 등)는 backend 폴더 기준으로 읽히므로 backend 폴더에서 실행한다
- 종료 코드: 크롤러 종료 코드 그대로 (0 = 정상)
#>
param(
    [int]$Limit = 20,
    [switch]$DryRun,
    [int]$KeepDays = 30
)

$ErrorActionPreference = 'Stop'
$backend = Split-Path -Parent $PSScriptRoot
$python = Join-Path $backend '.venv\Scripts\python.exe'
$logDir = Join-Path $backend 'logs'
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$log = Join-Path $logDir ((Get-Date -Format 'yyyy-MM-dd') + '.log')

function Write-Log([string]$line) {
    "[{0}] {1}" -f (Get-Date -Format 'HH:mm:ss'), $line | Out-File -FilePath $log -Append -Encoding utf8
}

if (-not (Test-Path $python)) {
    Write-Log "ERROR 가상환경 없음: $python (backend에서 python -m venv .venv 후 pip install -r requirements.txt)"
    exit 1
}

$crawlArgs = @('-m', 'app.crawler.run', '--limit', $Limit)
if ($DryRun) { $crawlArgs += '--dry-run' }
Write-Log ("START python {0}" -f ($crawlArgs -join ' '))

Push-Location $backend
$env:PYTHONIOENCODING = 'utf-8'
$ErrorActionPreference = 'Continue'  # 크롤러가 stderr에 쓴 경고 때문에 스크립트가 멈추지 않게
try {
    & $python @crawlArgs 2>&1 | ForEach-Object { "$_" } | Out-File -FilePath $log -Append -Encoding utf8
    $code = $LASTEXITCODE
} finally {
    Pop-Location
}
Write-Log "END exit=$code"

Get-ChildItem -Path $logDir -Filter '*.log' |
    Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-$KeepDays) } |
    Remove-Item -Force -ErrorAction SilentlyContinue

exit $code
