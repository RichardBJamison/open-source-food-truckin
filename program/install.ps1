# Open Source Food Truckin' - Windows installer (run by Install.bat)
# ASCII only on purpose: Windows PowerShell 5.1 misreads UTF-8 without a BOM.
# Copies the program to %USERPROFILE%\osft-program, sets it up, starts it at login, opens the browser.
# Re-run any time to update: your data in osft-program\data is kept.
#   -Silent       no prompts (testing)
#   -SkipBrowser  do not open the browser

param(
    [switch]$Silent,
    [switch]$SkipBrowser,
    [string]$InstallDir = "",
    [int]$Port = 5053
)

# Continue, not Stop: Windows PowerShell 5.1 turns pip warnings on stderr into fatal errors under Stop.
$ErrorActionPreference = "Continue"
if (-not $InstallDir) { $InstallDir = Join-Path $env:USERPROFILE "osft-program" }
$SourceDir = $PSScriptRoot
$Url = "http://127.0.0.1:$Port/"

function Step([string]$msg) { Write-Host "  $msg" }

function Fail([string]$msg) {
    Write-Host ""
    Write-Host "  ERROR: $msg"
    if (-not $Silent) { Read-Host "  Press Enter to close" }
    exit 1
}

function Find-Python {
    # "py -3" is the python.org launcher; "python" may be the Microsoft Store stub, so test it really runs.
    $candidates = @(
        @{ Cmd = "py"; Args = @("-3") },
        @{ Cmd = "python"; Args = @() },
        @{ Cmd = "python3"; Args = @() }
    )
    foreach ($c in $candidates) {
        try {
            $exe = Get-Command $c.Cmd -ErrorAction Stop
            $check = $c.Args + @("-c", "import sys; print(1 if sys.version_info >= (3, 9) else 0)")
            $ok = & $exe.Source @check 2>$null
            if ($ok -eq "1") { return @{ Exe = $exe.Source; Args = $c.Args } }
        } catch {}
    }
    return $null
}

function Test-Health {
    # Invoke-WebRequest fails on some Windows setups; curl.exe ships with Windows 10+ (same fallback as Barware)
    try {
        $r = Invoke-WebRequest -Uri ($Url + "api/health") -UseBasicParsing -TimeoutSec 3
        if ($r.StatusCode -eq 200) { return $true }
    } catch {}
    try {
        $code = (& curl.exe -s -o NUL -w "%{http_code}" ($Url + "api/health") 2>$null)
        if ($code -eq "200") { return $true }
    } catch {}
    return $false
}

function Show-Logs {
    foreach ($name in @("osft_server.err", "osft_server.log")) {
        $path = Join-Path $InstallDir "data\$name"
        if (Test-Path $path) {
            Write-Host "  --- $path ---"
            Get-Content $path -ErrorAction SilentlyContinue | Select-Object -Last 30 | ForEach-Object { Write-Host "  $_" }
        }
    }
}

function Stop-Port([int]$p) {
    try {
        Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue | ForEach-Object {
            Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue
        }
    } catch {}
}

if (-not $Silent) { Clear-Host }
Write-Host ""
Write-Host "  Open Source Food Truckin' - Windows Install"
Write-Host "  -------------------------------------------"
Write-Host ""

Step "[1/6] Checking Python 3.9+..."
$py = Find-Python
if (-not $py) {
    Write-Host ""
    Write-Host "  Python 3 is not installed yet."
    Write-Host "  1. Get it from https://www.python.org/downloads/ (the big yellow button)."
    Write-Host "  2. In the installer, CHECK 'Add python.exe to PATH', then Install Now."
    Write-Host "  3. Double-click Install.bat again."
    if (-not $Silent) { Start-Process "https://www.python.org/downloads/" }
    Fail "Python 3.9 or newer not found."
}
$ver = & $py.Exe @($py.Args + @("--version"))
Step "OK $ver"

Step "[2/6] Copying the program to $InstallDir..."
Stop-Port $Port   # an older copy may be running; stop it before replacing its files
New-Item -ItemType Directory -Force -Path (Join-Path $InstallDir "data") | Out-Null
if ((Resolve-Path $SourceDir).Path.TrimEnd("\") -ne (Resolve-Path $InstallDir).Path.TrimEnd("\")) {
    & robocopy.exe $SourceDir $InstallDir /E /XD (Join-Path $SourceDir "data") (Join-Path $SourceDir ".venv") __pycache__ .pytest_cache /NFL /NDL /NJH /NJS /NP | Out-Null
    if ($LASTEXITCODE -ge 8) { Fail "Could not copy the program files (robocopy code $LASTEXITCODE)." }
    $global:LASTEXITCODE = 0
}
Step "OK Program files in place (your data folder is untouched)"

Step "[3/6] Setting up Python..."
$venvPy = Join-Path $InstallDir ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPy)) {
    & $py.Exe @($py.Args + @("-m", "venv", (Join-Path $InstallDir ".venv")))
    if (-not (Test-Path $venvPy)) { Fail "Could not create the Python environment." }
}
Step "OK Python environment ready"

Step "[4/6] Installing Flask (first time needs internet)..."
& $venvPy -m pip install --upgrade pip --quiet --disable-pip-version-check 2>$null | Out-Null
& $venvPy -m pip install -r (Join-Path $InstallDir "requirements.txt") --quiet --disable-pip-version-check
& $venvPy -c "import flask" 2>$null
if ($LASTEXITCODE -ne 0) { Fail "Could not install Flask. Check the internet connection and run Install.bat again." }
Step "OK Ready"

Step "[5/6] Starting the program (and at every login)..."
$startScript = Join-Path $InstallDir "start-server.ps1"
try {
    $startup = [Environment]::GetFolderPath("Startup")
    $wsh = New-Object -ComObject WScript.Shell
    $lnk = $wsh.CreateShortcut((Join-Path $startup "Open Source Food Truckin.lnk"))
    $lnk.TargetPath = "powershell.exe"
    $lnk.Arguments = "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$startScript`" -Background -Port $Port"
    $lnk.WorkingDirectory = $InstallDir
    $lnk.Description = "Open Source Food Truckin' local program"
    $lnk.Save()
} catch {
    Step "WARN Could not add the login shortcut ($($_.Exception.Message)). Use Start.bat after a restart."
}
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $startScript -Background -Port $Port
$ok = $false
for ($i = 0; $i -lt 30; $i++) {
    if (Test-Health) { $ok = $true; break }
    Start-Sleep -Seconds 1
}
if (-not $ok) { Show-Logs; Fail "The program didn't start. Logs are in $(Join-Path $InstallDir 'data')" }
Step "OK Running at $Url"

Step "[6/6] Opening your browser..."
if (-not $SkipBrowser -and -not $Silent) { Start-Process $Url }

Write-Host ""
Write-Host "  All set!"
Write-Host "  Program:  $Url  <- bookmark this. That bookmark is the software."
Write-Host "  It starts by itself when you log in. Stop it with Stop.bat in $InstallDir."
Write-Host "  Your data: $(Join-Path $InstallDir 'data')"
Write-Host ""
if (-not $Silent) { Read-Host "  Press Enter to close this window" }
exit 0
