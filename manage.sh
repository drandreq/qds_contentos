#!/bin/bash

# manage.sh - ContentOS Administrative Interface
# Physician-Programmer Standard: Verbose and Clear

path_to_env_file="./.env"

# Auto-detect docker compose v2 vs v1
if command -v docker run >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
  docker_compose_command="docker compose"
else
  docker_compose_command="docker-compose"
fi

function check_environment_file() {
  if [ ! -f "$path_to_env_file" ]; then
    echo "[!] Warning: .env file not found. Creating a template..."
    echo "GOOGLE_API_KEY=your_google_api_key_here" > "$path_to_env_file"
    echo "TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here" >> "$path_to_env_file"
    echo "TELEGRAM_WEBHOOK_URL=" >> "$path_to_env_file"
    echo "TELEGRAM_AUTHORIZED_USER_IDS=12345678,87654321" >> "$path_to_env_file"
    echo "CONTENTOS_WORDS_PER_MINUTE=150" >> "$path_to_env_file"
  fi
}

case "$1" in
  "up")
    check_environment_file
    $docker_compose_command up --build -d
    echo "[+] ContentOS is running in background."
    ;;
  "down")
    $docker_compose_command down
    echo "[-] Systems offline."
    ;;
  "rebuild")
    check_environment_file
    $docker_compose_command up --build --force-recreate -d
    echo "[+] ContentOS rebuilt and running."
    ;;
  "status")
    $docker_compose_command ps
    ;;
  "auth")
    echo "[*] Triggering Google Cloud ADC Authentication..."
    $docker_compose_command run --rm gcloud-sidecar gcloud auth application-default login
    ;;
  "logs")
    $docker_compose_command logs -f
    ;;
  *)
    echo "Usage: ./manage.sh {up|down|rebuild|status|auth|logs}"
    ;;
esac