# Find all PIDs using port 11434
$pids = netstat -ano | Select-String ":11434" | ForEach-Object {
    ($_ -split '\s+')[-1]
} | Select-Object -Unique

# Kill each PID
foreach ($pid in $pids) {
    Write-Host "Killing process with PID $pid using port 11434"
    taskkill /PID $pid /F
}

# Start ollama serve
Write-Host "Starting ollama serve..."
Start-Process -NoNewWindow -FilePath "ollama" -ArgumentList "serve"
