<#
PowerShell build_and_launch.ps1

Usage:
  .\build_and_launch.ps1 -Backend cpp    # build & run C++ GUI
  .\build_and_launch.ps1 -Backend py     # prepare venv & run Python GUI

What it does (Windows):
 - Creates/activates a Python venv at ./venv
 - Installs Python requirements from requirements.txt and editable package
 - Checks for Poppler's pdftoppm and Tesseract; warns if missing
 - Configures and builds the C++ GUI with CMake (out-of-source build in ./build)
 - Launches either the built C++ executable or the Python GUI

Requires: PowerShell 5.1 or newer, CMake, Visual Studio (MSVC) or other C++ toolchain on PATH for CMake, Git, pip
#>
param(
    [ValidateSet("cpp","py")] 
    [string]$Backend = "cpp",

    [switch]$SkipBuild,
    [switch]$Release
)

$ErrorActionPreference = 'Stop'

function Abort-WithMessage($msg) {
    Write-Err $msg
    Write-Host "Press Enter to exit..."; Read-Host | Out-Null
    exit 1
}

function Write-Note($msg) { Write-Host "[INFO] $msg" -ForegroundColor Cyan }
function Write-Warn($msg) { Write-Host "[WARN] $msg" -ForegroundColor Yellow }
function Write-Err($msg) { Write-Host "[ERROR] $msg" -ForegroundColor Red }

# 1) Prepare Python venv
$venvDir = Join-Path $PSScriptRoot 'venv'
if (-not (Test-Path $venvDir)) {
    Write-Note "Creating virtual environment at $venvDir"
    python -m venv $venvDir
} else {
    Write-Note "Virtual environment already exists at $venvDir"
}

$activate = Join-Path $venvDir 'Scripts\Activate.ps1'
if (-not (Test-Path $activate)) {
    Write-Warn "Activate script not found at $activate. Ensure Python venv creation succeeded."
} else {
    Write-Note "Activating virtual environment (dot-sourcing activation script)"
    try {
        . $activate
    } catch {
        Write-Warn "Failed to activate venv using dot-sourcing: $_"
    }
}

# 2) Install Python dependencies (if not already)
if (-not $SkipBuild) {
    Write-Note "Installing Python requirements"
    if (Test-Path (Join-Path $PSScriptRoot 'requirements.txt')) {
        pip install -r "$PSScriptRoot\requirements.txt"
    }
    Write-Note "Installing package in editable mode"
    pip install -e "$PSScriptRoot"
}

# 3) Check external tools: pdftoppm (Poppler) and tesseract
function Test-Tool($tool) {
    $found = Get-Command $tool -ErrorAction SilentlyContinue
    return $null -ne $found
}

$hasPdftoppm = Test-Tool 'pdftoppm'
$hasTesseract = Test-Tool 'tesseract'

if (-not $hasPdftoppm) { Write-Warn "pdftoppm not found in PATH. Install Poppler for Windows and add to PATH." }
if (-not $hasTesseract) { Write-Warn "tesseract not found in PATH. Install Tesseract OCR and add to PATH." }

# 4) Build C++ GUI (unless user asked to skip)
$buildDir = Join-Path $PSScriptRoot 'build'
if (-not $SkipBuild -and $Backend -eq 'cpp') {
    if (-not (Test-Path $buildDir)) { New-Item -ItemType Directory -Path $buildDir | Out-Null }
    Push-Location $buildDir
    try {
        $cfg = if ($Release) { 'Release' } else { 'Debug' }
        Write-Note "Configuring CMake (build type: $cfg) in $buildDir"

        # Choose generator depending on environment (adjust if different VS version)
        $generator = 'Visual Studio 17 2022'
        $arch = 'x64'

        $cmakeArgs = @(
            "-DCMAKE_BUILD_TYPE=$cfg",
            "-G", $generator,
            "-A", $arch,
            ".."
        )

        Write-Note "Running: cmake $($cmakeArgs -join ' ')"
        & cmake @cmakeArgs

        Write-Note "Building C++ project"
        if ($cfg -eq 'Release') { & cmake --build . --config Release } else { & cmake --build . }
    } catch {
        Pop-Location
        Abort-WithMessage "CMake configuration/build failed: $_"
    }

    Pop-Location
}

# 5) Launch the requested backend
if ($Backend -eq 'py') {
    Write-Note "Launching Python GUI"
    try {
        textbook-divider-gui
    } catch {
        Abort-WithMessage "Failed to launch Python GUI: $_"
    }
} else {
    # Find executable
    $exe = Join-Path $buildDir 'Textbook_Divider.exe'
    if (-not (Test-Path $exe)) {
        Abort-WithMessage "C++ executable not found at $exe. Build may have failed."
    }

    Write-Note "Launching C++ GUI: $exe"
    try {
        Start-Process -FilePath $exe
    } catch {
        Abort-WithMessage "Failed to launch C++ GUI: $_"
    }
}

Write-Note "Done"
Write-Host "Press Enter to exit..."; Read-Host | Out-Null
