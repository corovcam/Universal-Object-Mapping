#!/bin/bash
/root/setup_ssh_tunnel.sh
exec /storage/entrypoint.sh "$@"
