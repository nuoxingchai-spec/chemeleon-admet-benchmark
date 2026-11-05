param([string]$Python = 'python', [string]$Tectonic = 'tectonic')
$ErrorActionPreference = 'Stop'
$env:ADMET_EXPERIMENT_ROOT = Join-Path $PSScriptRoot 'evidence'
$env:ADMET_BIB_SOURCE = Join-Path $PSScriptRoot 'paper'
$texCommand = Get-Command $Tectonic -ErrorAction Stop
$env:TECTONIC_EXE = $texCommand.Source
& $Python -X utf8 -B (Join-Path $PSScriptRoot 'scripts\build_paper.py')
if ($LASTEXITCODE -ne 0) { throw 'Paper build failed' }
