param([string]$Modele = '9eg', [ValidateSet('auto','word','reportlab')][string]$PdfMoteur = 'auto')
$ErrorActionPreference = 'Stop'
$taskRoot = $PSScriptRoot
$bundledPython = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
$pythonCommand = $null
if (Test-Path -LiteralPath $bundledPython) { $pythonCommand = $bundledPython }
elseif (Get-Command py.exe -ErrorAction SilentlyContinue) { $pythonCommand = 'py.exe' }
elseif (Get-Command python.exe -ErrorAction SilentlyContinue) { $pythonCommand = 'python.exe' }
else { throw 'Python est requis. Installez Python 3, puis relancez ce fichier.' }
$arguments = @((Join-Path $taskRoot 'generer-documents.py'), '--modele', $Modele, '--pdf-moteur', $PdfMoteur)
& $pythonCommand @arguments
if ($LASTEXITCODE -ne 0) { throw 'La génération a échoué. Consultez le message ci-dessus.' }
