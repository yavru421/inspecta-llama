# Double-click to launch Inspectallama Suite (GUI)

# Load API key from .env file
$envFile = ".\.env"
if (Test-Path $envFile) {
    $envContent = Get-Content $envFile | Where-Object { $_ -match "^LLAMA_API_KEY=" }
    if ($envContent) {
        $apiKey = $envContent -replace "LLAMA_API_KEY=", ""
        $env:LLAMA_API_KEY = $apiKey
    }
}

python .\cumulative_app.py
# Ensure the script runs in the correct directory
Set-Location -Path (Split-Path -Parent $MyInvocation.MyCommand.Path)