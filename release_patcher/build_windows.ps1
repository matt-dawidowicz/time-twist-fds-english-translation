$ErrorActionPreference = 'Stop'

$Root = Split-Path -Parent $PSScriptRoot
$Patcher = Join-Path $PSScriptRoot 'TimeTwistPatcher.py'
$PatchDir = Join-Path $PSScriptRoot 'patches'
$Dist = Join-Path $Root 'dist'
$Package = Join-Path $Dist 'Time-Twist-English-v1.0'

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

New-Item -ItemType Directory -Force $Package | Out-Null
Move-Item (Join-Path $Dist 'TimeTwistEnglishPatcher.exe') $Package
Copy-Item (Join-Path $PSScriptRoot 'README.md') (Join-Path $Package 'README.md')
Copy-Item (Join-Path $Root 'LICENSE') (Join-Path $Package 'LICENSE')

python (Join-Path $PSScriptRoot 'package_release.py') --package-dir $Package

Copy-Item (Join-Path $Package 'BPS-Patches\Time-Twist-English-v1.0-Zenpen.bps') $Dist
Copy-Item (Join-Path $Package 'BPS-Patches\Time-Twist-English-v1.0-Kouhen.bps') $Dist

$zip = Join-Path $Dist 'Time-Twist-English-v1.0-Windows.zip'
Compress-Archive -Path (Join-Path $Package '*') -DestinationPath $zip -Force
Get-FileHash $zip -Algorithm SHA256 | Format-List
