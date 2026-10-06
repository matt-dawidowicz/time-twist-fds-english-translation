$ErrorActionPreference = 'Stop'

$Root = Split-Path -Parent $PSScriptRoot
$Patcher = Join-Path $PSScriptRoot 'TimeTwistPatcher.py'
$PatchDir = Join-Path $PSScriptRoot 'patches'
$Dist = Join-Path $Root 'dist'
$Package = Join-Path $Dist 'Time-Twist-English-v1.1'
$Exe = Join-Path $Package 'TimeTwistEnglishPatcher.exe'

python -m pip install --upgrade pip
python -m pip install pyinstaller

Remove-Item -Recurse -Force -ErrorAction SilentlyContinue (Join-Path $Root 'build-pyinstaller')
Remove-Item -Recurse -Force -ErrorAction SilentlyContinue $Dist

python -m PyInstaller `
  --noconfirm `
  --clean `
  --onefile `
  --windowed `
  --name TimeTwistEnglishPatcher `
  --distpath $Dist `
  --workpath (Join-Path $Root 'build-pyinstaller') `
  --specpath (Join-Path $Root 'build-pyinstaller') `
  --add-data "$PatchDir;patches" `
  $Patcher
if ($LASTEXITCODE -ne 0) { throw 'PyInstaller build failed' }

New-Item -ItemType Directory -Force $Package | Out-Null
Move-Item (Join-Path $Dist 'TimeTwistEnglishPatcher.exe') $Exe
Copy-Item (Join-Path $PSScriptRoot 'README.md') (Join-Path $Package 'README.md')
Copy-Item (Join-Path $Root 'LICENSE') (Join-Path $Package 'LICENSE')
Copy-Item (Join-Path $Root 'docs/WALKTHROUGH.txt') (Join-Path $Package 'WALKTHROUGH.txt')
Copy-Item (Join-Path $PSScriptRoot 'CHANGELOG.md') (Join-Path $Package 'CHANGELOG.md')

python (Join-Path $PSScriptRoot 'package_release.py') --package-dir $Package
if ($LASTEXITCODE -ne 0) { throw 'Release packaging failed' }

# Smoke-test the frozen executable without opening the GUI.
$process = Start-Process -FilePath $Exe -ArgumentList '--version' -Wait -PassThru
if ($process.ExitCode -ne 0) {
  throw "Frozen patcher smoke test failed with exit code $($process.ExitCode)"
}
$process = Start-Process -FilePath $Exe -ArgumentList '--verify-resources' -Wait -PassThru
if ($process.ExitCode -ne 0) {
  throw "Frozen patch resources failed verification with exit code $($process.ExitCode)"
}

# Expose public and playtest upgrade patches as top-level artifacts.
Copy-Item (Join-Path $Package 'BPS-Patches\*.bps') $Dist

$zip = Join-Path $Dist 'Time-Twist-English-v1.1-Windows.zip'
Compress-Archive -Path (Join-Path $Package '*') -DestinationPath $zip -Force

Write-Host 'Release artifacts:'
Get-FileHash $Exe -Algorithm SHA256 | Format-Table -AutoSize
Get-FileHash (Join-Path $Dist 'Time-Twist-English-v1.1-Zenpen.bps') -Algorithm SHA256 | Format-Table -AutoSize
Get-FileHash (Join-Path $Dist 'Time-Twist-English-v1.1-Kouhen.bps') -Algorithm SHA256 | Format-Table -AutoSize
Get-FileHash $zip -Algorithm SHA256 | Format-Table -AutoSize
