#!/usr/bin/env bash

BASE_URL="${BASE_URL:-http://192.168.178.72:8001}"
AUTH_HEADER="${AUTH_HEADER:-}"

declare -a endpoints=(
    "system/ping:/system/ping"
    "system/health:/system/health"
    "feeds/list:/feeds/list"
    "feeds/add:/feeds/add"
    "feeds/update:/feeds/update"
    "feeds/delete:/feeds/delete"
    "feeds/test:/feeds/test"
    "feeds/refresh:/feeds/refresh"
    "feeds/performance:/feeds/performance"
    "feeds/diagnostics:/feeds/diagnostics"
    "articles/latest:/articles/latest"
    "articles/search:/articles/search"
    "templates/assign:/templates/assign"
    "data/export:/data/export"
    "health:/health"
    "mcp:/mcp"
    "openapi:/openapi.json"
)

echo "Testing endpoints against $BASE_URL"
echo "================================="

for item in "${endpoints[@]}"; do
    IFS=':' read -r label path <<< "$item"
    url="$BASE_URL$path"

    printf "\n[%s] Testing %s\n" "$label" "$url"

    # Test POST first
    if [ -n "$AUTH_HEADER" ]; then
        status_post=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$url" -H "Content-Type: application/json" -H "Authorization: $AUTH_HEADER" -d '{}')
    else
        status_post=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$url" -H "Content-Type: application/json" -d '{}')
    fi

    # Test GET as fallback
    if [ -n "$AUTH_HEADER" ]; then
        status_get=$(curl -s -o /dev/null -w "%{http_code}" -X GET "$url" -H "Authorization: $AUTH_HEADER")
    else
        status_get=$(curl -s -o /dev/null -w "%{http_code}" -X GET "$url")
    fi

    echo "  POST: $status_post | GET: $status_get"

    # Color-code results
    if [ "$status_post" = "200" ] || [ "$status_get" = "200" ]; then
        echo "  ✅ SUCCESS"
    elif [ "$status_post" = "405" ] && [ "$status_get" = "200" ]; then
        echo "  ⚠️  GET only"
    elif [ "$status_post" = "200" ] && [ "$status_get" = "405" ]; then
        echo "  ⚠️  POST only"
    elif [ "$status_post" = "404" ] && [ "$status_get" = "404" ]; then
        echo "  ❌ NOT FOUND"
    else
        echo "  ⚠️  Mixed results"
    fi
done

echo ""
echo "================================="
echo "Test completed for $BASE_URL"