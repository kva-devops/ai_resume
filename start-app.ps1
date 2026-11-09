$ErrorActionPreference = 'Stop'
$bundledPython = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
$pythonExe = if (Test-Path $bundledPython) { $bundledPython } else { 'python' }
if (-not (Test-Path '.venv-app\Scripts\python.exe')) { & $pythonExe -m venv .venv-app }
& '.venv-app\Scripts\python.exe' -m pip install -r requirements.txt
npm install
npm run build
& '.venv-app\Scripts\python.exe' -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
