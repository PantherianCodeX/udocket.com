#!/usr/bin/env bash
set -euo pipefail
cd docs/build/pdf
artifacts=()
if [ -f prd.pdf ]; then
  sha256sum prd.pdf > prd.pdf.sha256
  artifacts+=("prd.pdf")
fi
if [ -f tdd.pdf ]; then
  sha256sum tdd.pdf > tdd.pdf.sha256
  artifacts+=("tdd.pdf")
fi
{
  echo "{";
  echo "  \"generated_at\": \"$(date -u +"%Y-%m-%dT%H:%M:%SZ")\",";
  echo "  \"artifacts\": [";
  first=1
  for a in "${artifacts[@]}"; do
    sum=$(cut -d' ' -f1 "$a.sha256")
    if [ $first -eq 0 ]; then echo ","; fi
    echo -n "    { \"name\": \"$a\", \"sha256\": \"$sum\" }"
    first=0
  done
  echo "\n  ]";
  echo "}";
} > manifest.json

