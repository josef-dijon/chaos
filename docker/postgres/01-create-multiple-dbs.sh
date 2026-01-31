#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${POSTGRES_MULTIPLE_DATABASES:-}" ]]; then
  exit 0
fi

IFS=',' read -ra DATABASES <<< "${POSTGRES_MULTIPLE_DATABASES}"

for db in "${DATABASES[@]}"; do
  trimmed=$(echo "$db" | xargs)
  if [[ -n "$trimmed" ]]; then
    psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" <<-EOSQL
      CREATE DATABASE "$trimmed";
EOSQL
  fi
done
