#!/bin/sh
if [ "$1" = "sh" ] || [ "$1" = "/bin/sh" ]; then
  exec "$@"
fi
if [ -n "$1" ] && [ -x "/usr/local/bin/$1" ]; then
  exec "$@"
fi
if [ -n "$SERVICE" ]; then
  exec "/usr/local/bin/$SERVICE" "$@"
fi
exec "$@"
