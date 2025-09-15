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

# Utility: check if a tool exists on PATH
function Test-Tool($tool) {
    $found = Get-Command $tool -ErrorAction SilentlyContinue
    return $null -ne $found
}

# Utility: run a command and throw on nonzero exit
function Run-Cmd([string]$cmd, [string[]]$args) {
    Write-Note ("$cmd " + ($args -join ' '))
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = $cmd
    $psi.Arguments = ($args -join ' ')
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $psi.UseShellExecute = $false
    $p = New-Object System.Diagnostics.Process
    $p.StartInfo = $psi
    [void]$p.Start()
    $p.WaitForExit()
    $out = $p.StandardOutput.ReadToEnd()
    $err = $p.StandardError.ReadToEnd()
    if ($out) { Write-Host $out }
    if ($p.ExitCode -ne 0) {
        if ($err) { Write-Err $err } else { Write-Err "Command failed with exit code $($p.ExitCode)" }
        throw "Command failed: $cmd $($args -join ' ')"
    }
}

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

$hasPdftoppm = Test-Tool 'pdftoppm'
$hasTesseract = Test-Tool 'tesseract'

if (-not $hasPdftoppm) { Write-Warn "pdftoppm not found in PATH. Install Poppler for Windows and add to PATH." }
if (-not $hasTesseract) { Write-Warn "tesseract not found in PATH. Install Tesseract OCR and add to PATH." }

# 3b) Ensure PoDoFo dependency via vcpkg when building C++
function Ensure-Vcpkg {
    $externalDir = Join-Path $PSScriptRoot 'external'
    if (-not (Test-Path $externalDir)) { New-Item -ItemType Directory -Path $externalDir | Out-Null }

    if (-not $env:VCPKG_ROOT) {
        $localVcpkg = Join-Path $externalDir 'vcpkg'
        if (-not (Test-Path $localVcpkg)) {
            Write-Note "Cloning vcpkg into $localVcpkg"
            try {
                git --version | Out-Null
            } catch {
                Write-Warn "Git not found; cannot auto-install vcpkg. Install Git or set VCPKG_ROOT."
                return $null
            }
            & git clone https://github.com/microsoft/vcpkg.git "$localVcpkg"
            Push-Location $localVcpkg
            try {
                Write-Note "Bootstrapping vcpkg"
                # bootstrap installs vcpkg.exe
                if (Test-Path .\bootstrap-vcpkg.bat) { & .\bootstrap-vcpkg.bat } else { & .\bootstrap-vcpkg.bat }
            } finally {
                Pop-Location
            }
        }
        $env:VCPKG_ROOT = $localVcpkg
        Write-Note "VCPKG_ROOT set to $env:VCPKG_ROOT"
    }
    return $env:VCPKG_ROOT
}

function Ensure-PoDoFo {
    param([string]$triplet = 'x64-windows')
    $root = Ensure-Vcpkg
    if (-not $root) { return $false }
    $vcpkgExe = Join-Path $root 'vcpkg.exe'
    if (-not (Test-Path $vcpkgExe)) {
        Write-Warn "vcpkg.exe not found in $root; bootstrap may have failed."
        return $false
    }
    Write-Note "Installing PoDoFo via vcpkg for triplet $triplet (this may take several minutes)"
    & "$vcpkgExe" install "podofo:$triplet"
    if ($LASTEXITCODE -eq 0) { return $true } else { Write-Warn "vcpkg failed to install PoDoFo (exit $LASTEXITCODE)"; return $false }
}

# 4) Build C++ GUI (unless user asked to skip)
$buildDir = Join-Path $PSScriptRoot 'build'
if (-not $SkipBuild -and $Backend -eq 'cpp') {
    if ([string]::IsNullOrWhiteSpace($buildDir)) { Abort-WithMessage "Internal error: buildDir was empty" }
    if (-not (Test-Path $buildDir)) { New-Item -ItemType Directory -Path $buildDir | Out-Null }
    Push-Location $buildDir
    try {
        $cfg = if ($Release) { 'Release' } else { 'Debug' }
        Write-Note "Configuring CMake (build type: $cfg) in $buildDir"
        Write-Note "Debug: PSScriptRoot=$PSScriptRoot buildDir=$buildDir"

        # Prefer Ninja if available; fallback to VS 2022
        $ninjaAvail = Test-Tool 'ninja'
        if ($ninjaAvail) {
            $generator = 'Ninja'
            $arch = ''
        } else {
            $generator = 'Visual Studio 17 2022'
            $arch = 'x64'
        }

        $cmakeArgs = @(
            "-DCMAKE_BUILD_TYPE=$cfg",
            "-G", $generator,
            $(if ($arch) { '-A' }),
            $(if ($arch) { $arch })
        )

        # Ensure PoDoFo is available via vcpkg and add toolchain to help resolve packages
        $vcpkgToolchain = $null
        if ($env:VCPKG_ROOT -and (Test-Path (Join-Path $env:VCPKG_ROOT 'scripts\buildsystems\vcpkg.cmake'))) {
            $vcpkgToolchain = Join-Path $env:VCPKG_ROOT 'scripts\buildsystems\vcpkg.cmake'
        }
        # Always attempt to ensure PoDoFo via vcpkg
        $podofoOk = Ensure-PoDoFo
        if (-not $vcpkgToolchain -and $env:VCPKG_ROOT -and (Test-Path (Join-Path $env:VCPKG_ROOT 'scripts\buildsystems\vcpkg.cmake'))) {
            $vcpkgToolchain = Join-Path $env:VCPKG_ROOT 'scripts\buildsystems\vcpkg.cmake'
        }
        Write-Note "Debug: VCPKG_ROOT=$env:VCPKG_ROOT"
        Write-Note "Debug: vcpkgToolchain=$vcpkgToolchain"
        if ($vcpkgToolchain -and (Test-Path $vcpkgToolchain)) {
            Write-Note "Using vcpkg toolchain from $env:VCPKG_ROOT"
            $cmakeArgs += @('-DCMAKE_TOOLCHAIN_FILE=' + $vcpkgToolchain, '-DVCPKG_TARGET_TRIPLET=x64-windows')
        } else {
            Write-Warn "Proceeding without vcpkg toolchain; PoDoFo must be in system paths."
        }

        # Explicitly pass PoDoFo include/lib paths from vcpkg if available
        $podofoInclude = Join-Path $env:VCPKG_ROOT 'installed/x64-windows/include'
        $podofoLib = Join-Path $env:VCPKG_ROOT 'installed/x64-windows/lib/podofo.lib'
        if ((Test-Path $podofoInclude) -and (Test-Path $podofoLib)) {
            Write-Note "Providing PoDoFo include/lib paths to CMake"
            $cmakeArgs += @("-DPODOFO_INCLUDE_DIR=$podofoInclude", "-DPODOFO_LIBRARY=$podofoLib")
        } else {
            Write-Warn "PoDoFo not found in vcpkg installed paths yet; CMake may fail to find it."
        }

        $cmakeArgs += ".."

        Write-Note "Running: cmake $($cmakeArgs -join ' ')"
        & cmake @cmakeArgs

        Write-Note "Building C++ project"
        if ($generator -eq 'Ninja') {
            & cmake --build . --config $cfg
        } else {
            if ($cfg -eq 'Release') { & cmake --build . --config Release } else { & cmake --build . }
        }
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
    # Find executable (search across config subfolders)
    $exe = Get-ChildItem -Path $buildDir -Recurse -Filter 'Textbook_Divider.exe' -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1 -ExpandProperty FullName

    if (-not $exe) {
        Write-Warn "GUI executable not found. Trying CLI executable as fallback."
        $cliExe = Get-ChildItem -Path $buildDir -Recurse -Filter 'Textbook_Divider_CLI.exe' -ErrorAction SilentlyContinue |
            Sort-Object LastWriteTime -Descending |
            Select-Object -First 1 -ExpandProperty FullName
        if ($cliExe) {
            Write-Note "Launching C++ CLI: $cliExe (prints usage if no args)"
            try { & "$cliExe" | Write-Host } catch { Abort-WithMessage "Failed to launch CLI: $_" }
        } else {
            Abort-WithMessage "No C++ executables found under $buildDir."
        }
    } else {
        Write-Note "Launching C++ GUI: $exe"
        try {
            Start-Process -FilePath $exe
        } catch {
            Abort-WithMessage "Failed to launch C++ GUI: $_"
        }
    }
}

Write-Note "Done"
Write-Host "Press Enter to exit..."; Read-Host | Out-Null
