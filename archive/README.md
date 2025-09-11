Archive for cleanup run (2025-09-11)

This directory contains backups of duplicate and backup files that were moved during the cleanup run on 2025-09-11.

Contents
- cleanup-20250911-133932.zip : full compressed archive containing moved files and a `moved_files.txt` log listing all moved paths.

Restore instructions (Windows - PowerShell)
1. Copy the zip to a safe working location.
2. From PowerShell run:
   Expand-Archive -LiteralPath .\cleanup-20250911-133932.zip -DestinationPath .\restored
3. Inspect `restored\moved_files.txt` to find specific files to restore.
4. Move files back into the repository as needed.

Notes
- The zip is intentionally large (~1.05 GB) and was committed to the branch `cleanup/duplicates-20250911` for preservation. If you prefer not to keep large binaries in git history, move the zip to external storage and remove it from the repo.
- The moved files include many test artifacts and virtual environment directories; restoring everything into the working tree may clutter the repository. Restore only what you need.
