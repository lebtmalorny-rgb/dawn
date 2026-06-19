#!/usr/bin/env bash
set -euo pipefail

pattern_file="$(mktemp)"
allow_file="$(mktemp)"
match_file="$(mktemp)"
trap 'rm -f "$pattern_file" "$allow_file" "$match_file"' EXIT

{
  printf '%s\n' 'admin[[:digit:]]{3}'
  printf '%s\n' 'OS_''PASSWORD=.*'
  printf '%s\n' '(^|[^[:alnum:]_])(MYSQL_PASSWORD|MYSQL_ROOT_PASSWORD|RABBITMQ_DEFAULT_PASS)[[:space:]]*[:=][[:space:]]*(\$\{[A-Z0-9_]+:-)?[^[:space:]#}]+'
  printf '%s\n' 'CLOUD_UI_DATABASE_URL[[:space:]]*[:=][[:space:]]*(\$\{CLOUD_UI_DATABASE_URL:-)?mysql\+pymysql://[^:[:space:]/}]+:[^@[:space:]}]+@'
  printf '%s\n' 'CLOUD_UI_RABBITMQ_URL[[:space:]]*[:=][[:space:]]*(\$\{CLOUD_UI_RABBITMQ_URL:-)?amqps?://[^:[:space:]/}]+:[^@[:space:]}]+@'
  printf '%s\n' '(^|[[:space:]])[A-Z0-9_]*(AMQP|RABBITMQ|BROKER|CELERY|MQ)[A-Z0-9_]*(URL|URI)?[[:space:]]*[:=][[:space:]]*(\$\{[A-Z0-9_]+:-)?amqps?://[^:[:space:]/}]+:[^@[:space:]}]+@'
  printf '%s\n' '^[[:space:]]*[[:alnum:]_]*([Pp][Aa][Ss][Ss][Ww][Oo][Rr][Dd]|[Tt][Oo][Kk][Ee][Nn]|[Ss][Ee][Cc][Rr][Ee][Tt])[[:space:]]*[:=][[:space:]]*(\$\{[[:alnum:]_]+:-)?[^$[:space:]#}][^[:space:]#}]*'
  printf '%s\n' 'BEGIN ([[:alnum:]]+ )*PRIVATE KEY'
  printf '%s\n' 'application_credential_''secret\s*='
  printf '%s\n' 'auth_''token\s*='
  printf '%s\n' 'X-Auth-''Token'
} > "$pattern_file"

{
  printf '%s\n' '^\./compose\.yaml:[[:digit:]]+:[[:space:]]+MYSQL_PASSWORD: \$\{MYSQL_PASSWORD:-cloud_ui_dev\}$'
  printf '%s\n' '^\./compose\.yaml:[[:digit:]]+:[[:space:]]+MYSQL_ROOT_PASSWORD: \$\{MYSQL_ROOT_PASSWORD:-cloud_ui_root_dev\}$'
  printf '%s\n' '^\./compose\.yaml:[[:digit:]]+:[[:space:]]+RABBITMQ_DEFAULT_PASS: \$\{RABBITMQ_DEFAULT_PASS:-cloud_ui_dev\}$'
  printf '%s\n' '^\./compose\.yaml:[[:digit:]]+:[[:space:]]+CLOUD_UI_DATABASE_URL: \$\{CLOUD_UI_DATABASE_URL:-mysql\+pymysql://cloud_ui:cloud_ui_dev@db:3306/cloud_ui\}$'
  printf '%s\n' '^\./compose\.yaml:[[:digit:]]+:[[:space:]]+CLOUD_UI_RABBITMQ_URL: \$\{CLOUD_UI_RABBITMQ_URL:-amqp://cloud_ui:cloud_ui_dev@rabbitmq:5672/%2Fcloud-ui\}$'
  printf '%s\n' '^\./deploy/env\.example:[[:digit:]]+:CLOUD_UI_DATABASE_URL=mysql\+pymysql://cloud_ui:cloud_ui_dev@db:3306/cloud_ui$'
  printf '%s\n' '^\./deploy/env\.example:[[:digit:]]+:CLOUD_UI_RABBITMQ_URL=amqp://cloud_ui:cloud_ui_dev@rabbitmq:5672/%2Fcloud-ui$'
  printf '%s\n' '^\./deploy/env\.example:[[:digit:]]+:MYSQL_PASSWORD=cloud_ui_dev$'
  printf '%s\n' '^\./deploy/env\.example:[[:digit:]]+:MYSQL_ROOT_PASSWORD=cloud_ui_root_dev$'
  printf '%s\n' '^\./deploy/env\.example:[[:digit:]]+:RABBITMQ_DEFAULT_PASS=cloud_ui_dev$'
} > "$allow_file"

report_matches() {
  set +e
  grep -Ev -f "$allow_file" "$match_file"
  status=$?
  set -e
  if [ "$status" -eq 1 ]; then
    exit 0
  fi
  if [ "$status" -eq 0 ]; then
    exit 1
  fi
  exit "$status"
}

if command -v rg >/dev/null 2>&1; then
  set +e
  rg --hidden --no-ignore -n -f "$pattern_file" \
    . \
    --glob '!backend/.venv/**' \
    --glob '!frontend/node_modules/**' \
    --glob '!.git/**' \
    --glob '!scripts/secret-scan.sh' \
    --glob '!docs/superpowers/plans/**' \
    --glob '!frontend/package-lock.json' \
    > "$match_file"
  status=$?
  set -e
  if [ "$status" -eq 1 ]; then
    exit 0
  fi
  if [ "$status" -eq 0 ]; then
    report_matches
  fi
  exit "$status"
fi

matched=1
error_status=0
while IFS= read -r -d '' file_path; do
  set +e
  grep -HEn -f "$pattern_file" "$file_path" >> "$match_file"
  status=$?
  set -e
  if [ "$status" -eq 0 ]; then
    matched=0
  elif [ "$status" -gt 1 ]; then
    error_status=$status
  fi
done < <(
  find . \
    \( -path './backend/.venv' \
    -o -path './frontend/node_modules' \
    -o -path './.git' \
    -o -path './docs/superpowers/plans' \) -prune \
    -o -type f \
    ! -path './scripts/secret-scan.sh' \
    ! -path './frontend/package-lock.json' \
    -print0
)

if [ "$error_status" -ne 0 ]; then
  exit "$error_status"
fi
if [ "$matched" -eq 1 ]; then
  exit 0
fi
report_matches
