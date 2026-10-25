# Open Source Food Truckin' - start the program (Start.bat, login shortcut, installer).
#   -Background  start hidden and return (login shortcut / installer)
param([switch]$Background, [int]$Port = 5053)

$InstallDir = $PSScriptRoot
$venvPy = Join-Path $InstallDir ".venv\Scripts\python.exe"
$serverPy = Join-Path $InstallDir "server.py"
$dataDir = Join-Path $InstallDir "data"
$Url = "http://127.0.0.1:$Port/"

if (-not (Test-Path $venvPy) -or -not (Test-Path $serverPy)) {
    Write-Host "Run Install.bat first."
    if (-not $Background) { Read-Host "Press Enter" }
    exit 1
}
New-Item -ItemType Directory -Force -Path $dataDir | Out-Null

$running = $false
try { $running = ((Invoke-WebRequest -Uri ($Url + "api/health") -UseBasicParsing -TimeoutSec 2).StatusCode -eq 200) } catch {}

if (-not $running) {
    $env:OSFT_PORT = "$Port"
    $env:PYTHONUTF8 = "1"
    $env:PYTHONIOENCODING = "utf-8"
    Start-Process -FilePath $venvPy -ArgumentList "`"$serverPy`"" -WorkingDirectory $InstallDir -WindowStyle Hidden `
        -RedirectStandardOutput (Join-Path $dataDir "osft_server.log") -RedirectStandardError (Join-Path $dataDir "osft_server.err")
}
if ($Background) { exit 0 }

for ($i = 0; $i -lt 20; $i++) {
    try {
        if ((Invoke-WebRequest -Uri ($Url + "api/health") -UseBasicParsing -TimeoutSec 2).StatusCode -eq 200) { break }
    } catch {}
    Start-Sleep -Seconds 1
}
Start-Process $Url
