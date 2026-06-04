#!/bin/sh
# Exit immediately if a command exits with a non-zero status, 
# and treat unset variables as an error.
set -eu

log_info() { echo "[INFO] $1"; }
log_err() { echo "[ERROR] $1" >&2; }

# 1. Privilege & Writability Checks
if [ "$(id -u)" -ne 0 ]; then
    log_err "This script requires root privileges to modify /etc/hosts."
    exit 1
fi

if [ ! -w /etc/hosts ]; then
    log_err "/etc/hosts is not writable. This usually means the container is running with a read-only filesystem."
    exit 1
fi

# 2. Dependency Management
# Checks if a command exists, installs it via the available package manager if missing.
ensure_deps() {
    if command -v ip >/dev/null 2>&1 && command -v awk >/dev/null 2>&1 && command -v sed >/dev/null 2>&1; then
        return 0
    fi

    log_info "Missing required tools (ip, awk, or sed). Attempting to install..."
    
    if command -v apk >/dev/null 2>&1; then
        apk add --no-cache iproute2 awk sed
    elif command -v apt-get >/dev/null 2>&1; then
        export DEBIAN_FRONTEND=noninteractive
        apt-get update -qq && apt-get install -y -qq iproute2 gawk sed
    elif command -v dnf >/dev/null 2>&1; then
        dnf install -y -q iproute awk sed
    elif command -v yum >/dev/null 2>&1; then
        yum install -y -q iproute awk sed
    elif command -v zypper >/dev/null 2>&1; then
        zypper install -y -q iproute2 awk sed
    else
        log_err "Unsupported package manager. Please install 'iproute2', 'awk', and 'sed' manually."
        exit 1
    fi
}

# 3. Extract Gateway IP
get_gateway_ip() {
    # Extract the default gateway routing IP
    ip route show default | awk '/default/ {print $3}' | head -n 1
}

main() {
    ensure_deps

    GATEWAY_IP=$(get_gateway_ip)

    if [ -z "$GATEWAY_IP" ]; then
        log_err "Could not determine the default gateway IP from the routing table."
        exit 1
    fi
    
    log_info "Detected Host Gateway IP: $GATEWAY_IP"

    # 4. Idempotency Check
    # If the exact mapping already exists, exit cleanly.
    if grep -q "^${GATEWAY_IP}[[:space:]]*host\.docker\.internal$" /etc/hosts; then
         log_info "host.docker.internal is already correctly mapped to $GATEWAY_IP. No action needed."
         return 0
    fi

    log_info "Patching /etc/hosts..."

    # 5. Safe File Modification
    # We use a temporary file and 'cat' it back into /etc/hosts. 
    # This prevents Docker "Device or resource busy" bind-mount inode errors.
    TMP_HOSTS=$(mktemp)
    
    # Strip any existing (and potentially incorrect) host.docker.internal lines
    sed '/host\.docker\.internal/d' /etc/hosts > "$TMP_HOSTS"
    
    # Append the correct mapping
    echo "$GATEWAY_IP host.docker.internal" >> "$TMP_HOSTS"
    
    # Overwrite the original file in place
    cat "$TMP_HOSTS" > /etc/hosts
    
    # Cleanup
    rm -f "$TMP_HOSTS"

    log_info "Successfully patched /etc/hosts. host.docker.internal now points to $GATEWAY_IP."
}

# Execute
main
