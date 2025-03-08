#!/bin/bash

# Helper: netcat a given "host:port"
check_port () {
  local fulladdr="$1"
  # If "host" is 0.0.0.0, netcat to 127.0.0.1. Otherwise, use the given host.
  local host_part="$(echo "$fulladdr" | cut -d':' -f1)"
  local port_part="$(echo "$fulladdr" | cut -d':' -f2)"

  if [ -z "$host_part" ] || [ -z "$port_part" ]; then
    echo "WARN: Cannot parse $fulladdr"
    return 0
  fi

  # If host_part is 0.0.0.0, override with 127.0.0.1
  [ "$host_part" = "0.0.0.0" ] && host_part="127.0.0.1"

  if ! nc -z -w 2 "$host_part" "$port_part"; then
    echo "ERROR: Service not listening on $fulladdr"
    exit 1
  fi
}

check_port "${VIX_HOST:-127.0.0.1}:${VIX_PORT:-8288}"
