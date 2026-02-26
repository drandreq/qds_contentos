param (
    [Parameter(Position=0, Mandatory=$false)]
    [string]$Command = "help"
)

# manage.ps1 - ContentOS Administrative Interface (Windows/PowerShell)
# Physician-Programmer Standard: Verbose and Clear

$PathToEnvFile = ".\.env"

# Auto-detect docker-compose vs docker compose
$DockerComposeCmd = "docker-compose"
try {
    if (Get-Command docker -ErrorAction SilentlyContinue) {
        $result = docker compose version 2>&1
        if ($LASTEXITCODE -eq 0) {
            $DockerComposeCmd = "docker compose"
        }
    }
} catch {
    # Ignore and rely on fallback
}

function Check-EnvironmentFile {
    if (-not (Test-Path -Path $PathToEnvFile)) {
        Write-Host "[!] Warning: .env file not found. Creating a template..." -ForegroundColor Yellow
        "GOOGLE_API_KEY=your_google_api_key_here" | Out-File -FilePath $PathToEnvFile -Encoding utf8
        "TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here" | Out-File -FilePath $PathToEnvFile -Encoding utf8 -Append
        "TELEGRAM_WEBHOOK_URL=" | Out-File -FilePath $PathToEnvFile -Encoding utf8 -Append
        "TELEGRAM_AUTHORIZED_USER_IDS=12345678,87654321" | Out-File -FilePath $PathToEnvFile -Encoding utf8 -Append
        "TELEGRAM_KEEP_AUDIO=false" | Out-File -FilePath $PathToEnvFile -Encoding utf8 -Append
        "CONTENTOS_WORDS_PER_MINUTE=150" | Out-File -FilePath $PathToEnvFile -Encoding utf8 -Append
    }
}

switch ($Command) {
    "up" {
        Check-EnvironmentFile
        Invoke-Expression "$DockerComposeCmd up --build -d"
        Write-Host "[+] ContentOS is running in background." -ForegroundColor Green
    }
    "down" {
        Invoke-Expression "$DockerComposeCmd down"
        Write-Host "[-] Systems offline." -ForegroundColor Cyan
    }
    "rebuild" {
        Check-EnvironmentFile
        Invoke-Expression "$DockerComposeCmd up --build --force-recreate -d"
        Write-Host "[+] ContentOS rebuilt and running." -ForegroundColor Green
    }
    "status" {
        Invoke-Expression "$DockerComposeCmd ps"
    }
    "health" {
        Write-Host "[*] Querying ContentOS Backend Health..." -ForegroundColor Cyan
        Invoke-RestMethod http://localhost:8000/health | ConvertTo-Json -Depth 5
    }
    "auth" {
        Write-Host "[*] Triggering Google Cloud ADC Authentication..." -ForegroundColor Magenta
        Invoke-Expression "$DockerComposeCmd run --rm gcloud-sidecar gcloud auth application-default login"
    }
    "logs" {
        Invoke-Expression "$DockerComposeCmd logs -f"
    }
    default {
        Write-Host "Usage: .\manage.ps1 {up|down|rebuild|status|health|auth|logs}"
    }
}
