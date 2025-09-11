<#
cleanup_duplicates.ps1

Safely archive duplicate and backup files found by the earlier scan.
Usage (from repo root):
  powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\cleanup_duplicates.ps1 [-Root <path>] [-IncludeEnv] [-Commit] [-DryRun]

Options:
  -Root: root folder (defaults to current directory)
  -IncludeEnv: include `.env` and `tests\.env` directories in the archive (off by default)
  -Commit: run `git add` and `git commit` after moving files (off by default)
  -DryRun: list actions but do not move files

Behavior summary (default):
  - Create timestamped archive folder under `archive/cleanup-<timestamp>`
  - Move all `*.bak` files (excluding `.git`) into the archive, preserving relative paths
  - Move files under `tests/` and `data/` whose names contain `(2)` into the archive
  - Move `tests` logs named `*(2).log`
  - Do NOT touch `.git` internals or `src/` files
  - Optionally move `.env` and `tests/.env` if `-IncludeEnv` is supplied
  - Optionally commit the changes if `-Commit` is supplied

This script is conservative by default. Inspect the generated archive and `moved_files.txt` before deleting anything else.
#>

param(
    [string]$Root = (Get-Location).Path,
    [switch]$IncludeEnv,
    [switch]$Commit,
    [switch]$DryRun
)

function Normalize-Root {
    param($r)
    $p = (Get-Item -LiteralPath $r -ErrorAction Stop).FullName
    return $p.TrimEnd('\')
}

try {
    $Root = Normalize-Root -r $Root
} catch {
    Write-Error "Root path '$Root' not found or inaccessible."
    exit 1
}

$timestamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$archiveRel = "archive\cleanup-$timestamp"
$ArchivePath = Join-Path $Root $archiveRel

if(-not $DryRun) {
    New-Item -ItemType Directory -Path $ArchivePath -Force | Out-Null
} else {
    Write-Output "DRY RUN: would create archive at: $ArchivePath"
}

 # We'll use a single pass over files but apply conservative path restrictions
 $excludedPathRegex = '\\.git\\'  # exclude any files inside .git
 $excludedArchiveRegex = [regex]::Escape($archiveRel)

 $movedList = New-Object System.Collections.Generic.List[string]
 $movedCount = 0

 Write-Output "Starting scan from root: $Root"

 # Helper to compute relative path and destination
 function Get-RelativePath {
     param([string]$Full, [string]$RootPath)
     return $Full.Substring($RootPath.Length).TrimStart('\\')
 }

 # Find candidate files
 $allCandidates = @()

 # 1. All .bak files (excluding .git)
 $allBak = Get-ChildItem -Path $Root -Recurse -File -Force -ErrorAction SilentlyContinue | Where-Object { ($_.Extension -ieq '.bak') -and ($_.FullName -notmatch $excludedPathRegex) -and ($_.FullName -notmatch $excludedArchiveRegex) }
 $allCandidates += $allBak

 # 2. Files under tests/ and data/ with (2) in name (exclude .git and archive)
 $testsAndData = Get-ChildItem -Path $Root -Recurse -File -Force -ErrorAction SilentlyContinue | Where-Object { ($_.FullName -match '\\(tests|data)\\') -and ($_.Name -match '\(2\)') -and ($_.FullName -notmatch $excludedPathRegex) -and ($_.FullName -notmatch $excludedArchiveRegex) }
 $allCandidates += $testsAndData

 # 3. test logs matching (2).log (already mostly covered but keep safe)
 $testLogs = @()
 if(Test-Path (Join-Path $Root 'tests')) {
     $testLogs = Get-ChildItem -Path (Join-Path $Root 'tests') -Recurse -File -Force -ErrorAction SilentlyContinue | Where-Object { $_.Name -match '\(2\)\.log$' -and ($_.FullName -notmatch $excludedArchiveRegex) }
 }
 $allCandidates += $testLogs

 # Deduplicate
 $allCandidates = $allCandidates | Select-Object -Unique

 # If IncludeEnv requested, gather .env and tests/.env
 $envDirs = @()
 if($IncludeEnv) {
     $possible = @(Join-Path $Root '.env', Join-Path $Root 'tests\\.env')
     foreach($p in $possible) {
         if(Test-Path $p) { $envDirs += $p }
     }
 }

 Write-Output "Found $($allCandidates.Count) candidate files to archive (plus $($envDirs.Count) env directories)."
 if($allCandidates.Count -eq 0 -and $envDirs.Count -eq 0) {
     Write-Output "No candidates found. Exiting."
     exit 0
 }

 if($DryRun) {
     Write-Output "DRY RUN: listing candidates (first 200):"
     $allCandidates | Select-Object -First 200 | ForEach-Object { $_.FullName }
     if($envDirs.Count -gt 0) {
         Write-Output "DRY RUN: env directories that would be archived:"
         $envDirs | ForEach-Object { $_ }
     }
     Write-Output "To actually perform archival, re-run without -DryRun."
     exit 0
 }

 # Move files preserving relative path
 foreach($f in $allCandidates) {
     try {
         $rel = Get-RelativePath -Full $f.FullName -RootPath $Root
         $dest = Join-Path $ArchivePath $rel
         $destDir = Split-Path $dest
         if(-not (Test-Path $destDir)) { New-Item -ItemType Directory -Path $destDir -Force | Out-Null }
         Move-Item -LiteralPath $f.FullName -Destination $dest -Force -ErrorAction Stop
         $movedList.Add($dest)
         $movedCount = $movedCount + 1
     } catch {
         Write-Warning "Failed to move $($f.FullName): $($_.Exception.Message)"
     }
 }

 # Move env dirs if requested
 foreach($d in $envDirs) {
     try {
         $rel = Get-RelativePath -Full $d -RootPath $Root
         $dest = Join-Path $ArchivePath $rel
         $destDir = Split-Path $dest
         if(-not (Test-Path $destDir)) { New-Item -ItemType Directory -Path $destDir -Force | Out-Null }
         Move-Item -LiteralPath $d -Destination $dest -Force -ErrorAction Stop
         $movedList.Add($dest)
         $movedCount = $movedCount + 1
    } catch {
        Write-Warning "Failed to move directory $($d): $($_.Exception.Message)"
    }
 }

 # Write moved files list
 $movedLog = Join-Path $ArchivePath 'moved_files.txt'
 $movedList | Out-File -FilePath $movedLog -Encoding UTF8

 Write-Output "Moved $movedCount items into $ArchivePath"
 Write-Output "Moved items listed in: $movedLog"

 # Optionally commit
 if($Commit) {
     if(Test-Path (Join-Path $Root '.git')) {
         Write-Output "Running git add/commit..."
         Push-Location -LiteralPath $Root
         try {
             git add -A
             $msg = "cleanup: archive duplicate and backup files (automated) - $timestamp"
             git commit -m $msg
             Write-Output "Git commit created."
         } catch {
             Write-Warning "Git commit failed: $($_.Exception.Message)"
         } finally {
             Pop-Location
         }
     } else {
         Write-Warning "No .git folder found under root; skipping commit."
     }
 }

 Write-Output "Done. Please inspect the archive before removing anything permanently."
