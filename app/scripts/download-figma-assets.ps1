# Figma 아이콘/이미지를 app/assets 아래로 내려받습니다. (Figma 임시 URL은 7일 뒤 만료)
# 실행: cd C:\dev\Khuration\app ; powershell -ExecutionPolicy Bypass -File scripts\download-figma-assets.ps1
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$manifest = Get-Content (Join-Path $PSScriptRoot "figma-assets.json") -Raw -Encoding UTF8 | ConvertFrom-Json
$fail = 0
foreach ($a in $manifest) {
  $out = Join-Path $root $a.path
  New-Item -ItemType Directory -Force -Path (Split-Path $out) | Out-Null
  try {
    Invoke-WebRequest -Uri $a.url -OutFile $out -UseBasicParsing
    if ($out.EndsWith(".svg")) {
      # 모바일 SVG 렌더러는 CSS 변수(var(--fill-0, #8A1538))를 못 읽으므로 기본값으로 풀어 줍니다. 색·모양은 그대로입니다.
      $svg = [System.IO.File]::ReadAllText($out)
      $svg = [regex]::Replace($svg, 'var\(--[\w-]+,\s*([^)]+)\)', '$1')
      [System.IO.File]::WriteAllText($out, $svg)
    }
    $size = (Get-Item $out).Length
    if ($size -lt 60) { throw "too small ($size bytes)" }
    Write-Host ("OK   {0} ({1} bytes)" -f $a.path, $size)
  } catch {
    $fail++
    Write-Host ("FAIL {0} : {1}" -f $a.path, $_) -ForegroundColor Red
  }
}
if ($fail -gt 0) { Write-Host "$fail 개 실패. URL이 만료됐으면 Claude에게 다시 받아 달라고 하세요." -ForegroundColor Red; exit 1 }
Write-Host "완료: $($manifest.Count)개" -ForegroundColor Green
