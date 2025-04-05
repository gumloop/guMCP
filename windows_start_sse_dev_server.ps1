# start-server.ps1
# Load environment variables from .env file if it exists
if (Test-Path -Path '.env') {
    Write-Host "Loading environment variables from .env file"
    Get-Content '.env' | ForEach-Object {
        if (!$_.StartsWith('#') -and $_.Length -gt 0) {
            $key, $value = $_ -split '=', 2
            [Environment]::SetEnvironmentVariable($key, $value, 'Process')
        }
    }
} else {
    Write-Host "No .env file found, using default configuration"
    # Set default values if .env doesn't exist
    if (-not [Environment]::GetEnvironmentVariable('GUMCP_HOST', 'Process')) {
        [Environment]::SetEnvironmentVariable('GUMCP_HOST', '0.0.0.0', 'Process')
    }
    if (-not [Environment]::GetEnvironmentVariable('GUMCP_PORT', 'Process')) {
        [Environment]::SetEnvironmentVariable('GUMCP_PORT', '8000', 'Process')
    }
}

$host_value = [Environment]::GetEnvironmentVariable('GUMCP_HOST', 'Process')
$port_value = [Environment]::GetEnvironmentVariable('GUMCP_PORT', 'Process')

# Kill any process running on the specified port
Write-Host "Checking for processes running on port $port_value..."
$processes = Get-NetTCPConnection -LocalPort $port_value -ErrorAction SilentlyContinue | 
             Where-Object State -eq "Listen" | 
             Select-Object -ExpandProperty OwningProcess

if ($processes) {
    foreach ($process in $processes) {
        Write-Host "Killing process with ID $process running on port $port_value"
        Stop-Process -Id $process -Force
    }
    Start-Sleep -Seconds 1
}

Write-Host "Starting guMCP development server on $host_value`:$port_value"
python src/servers/main.py