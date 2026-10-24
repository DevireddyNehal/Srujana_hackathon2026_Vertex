$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$frontendRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..")).Path
$cloudflaredCommand = Get-Command cloudflared -ErrorAction SilentlyContinue
$cloudflaredPath = if ($cloudflaredCommand) {
  $cloudflaredCommand.Source
} else {
  Join-Path $env:LOCALAPPDATA "CloudflareTunnel\cloudflared.exe"
}

if (-not (Test-Path -LiteralPath $cloudflaredPath -PathType Leaf)) {
  throw "cloudflared was not found. Install Cloudflare Tunnel or add cloudflared.exe to PATH."
}

$logPrefix = Join-Path ([IO.Path]::GetTempPath()) "vertex-cloudflared-$PID"
$stdoutPath = "$logPrefix.out.log"
$stderrPath = "$logPrefix.err.log"
$tunnelProcess = $null
$oldTunnelHost = $env:VERTEX_TUNNEL_HOST

Push-Location $frontendRoot
try {
  & npm.cmd run build:website
  if ($LASTEXITCODE -ne 0) {
    throw "The standalone website build failed with exit code $LASTEXITCODE."
  }

  $tunnelProcess = Start-Process `
    -FilePath $cloudflaredPath `
    -ArgumentList @("tunnel", "--no-autoupdate", "--url", "http://127.0.0.1:4173") `
    -PassThru `
    -WindowStyle Hidden `
    -RedirectStandardOutput $stdoutPath `
    -RedirectStandardError $stderrPath

  $tunnelHost = $null
  $deadline = (Get-Date).AddSeconds(60)
  while ((Get-Date) -lt $deadline) {
    if ($tunnelProcess.HasExited) {
      break
    }

    $logs = @()
    foreach ($logPath in @($stdoutPath, $stderrPath)) {
      if (Test-Path -LiteralPath $logPath) {
        $logs += Get-Content -LiteralPath $logPath -Raw
      }
    }

    $match = [regex]::Match(
      ($logs -join "`n"),
      "https://(?<hostname>[a-z0-9-]+\.trycloudflare\.com)",
      [System.Text.RegularExpressions.RegexOptions]::IgnoreCase
    )
    if ($match.Success) {
      $tunnelHost = $match.Groups["hostname"].Value
      break
    }

    Start-Sleep -Milliseconds 500
  }

  if (-not $tunnelHost) {
    $tunnelLogs = @()
    foreach ($logPath in @($stdoutPath, $stderrPath)) {
      if (Test-Path -LiteralPath $logPath) {
        $tunnelLogs += Get-Content -LiteralPath $logPath -Raw
      }
    }
    $details = ($tunnelLogs -join "`n").Trim()
    if ($details) {
      throw "Cloudflare Quick Tunnel did not provide a URL within 60 seconds.`n$details"
    }
    throw "Cloudflare Quick Tunnel did not provide a URL within 60 seconds."
  }

  $env:VERTEX_TUNNEL_HOST = $tunnelHost
  $shareUrl = "https://$tunnelHost/?page=overview"
  Write-Host ""
  Write-Host "Vertex is ready to share: $shareUrl" -ForegroundColor Green
  Write-Host "Keep this window open while your friends use the site. Press Ctrl+C to stop sharing."
  Write-Host ""

  & npm.cmd run preview:website -- --host 127.0.0.1 --strictPort
  if ($LASTEXITCODE -ne 0) {
    throw "The website preview exited with code $LASTEXITCODE."
  }
} finally {
  if ($oldTunnelHost) {
    $env:VERTEX_TUNNEL_HOST = $oldTunnelHost
  } else {
    Remove-Item Env:\VERTEX_TUNNEL_HOST -ErrorAction SilentlyContinue
  }

  if ($tunnelProcess -and -not $tunnelProcess.HasExited) {
    Stop-Process -Id $tunnelProcess.Id
  }

  foreach ($logPath in @($stdoutPath, $stderrPath)) {
    if (Test-Path -LiteralPath $logPath) {
      Remove-Item -LiteralPath $logPath
    }
  }

  Pop-Location
}
