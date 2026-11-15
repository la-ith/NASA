param([ValidateRange(1,65535)][int]$Port=8000)
$ErrorActionPreference='Stop'
$projectPath=$PSScriptRoot
$pythonPath=$null
foreach($candidate in @('backend/.venv/Scripts/python.exe','outputs/review-venv/Scripts/python.exe')){
    $candidatePath=Join-Path $projectPath $candidate
    if(Test-Path -LiteralPath $candidatePath){$pythonPath=$candidatePath;break}
}
if(-not $pythonPath){
    throw 'Create backend/.venv and install backend/requirements.txt using the root README, then run this script again.'
}
Push-Location (Join-Path $projectPath 'backend')
try{
    Write-Host "Field Shift: http://127.0.0.1:$Port/"
    Write-Host 'Press Ctrl+C to stop. Private settings load from backend/.env.'
    & $pythonPath -m uvicorn app.main:app --host 127.0.0.1 --port $Port --workers 1
}finally{Pop-Location}
