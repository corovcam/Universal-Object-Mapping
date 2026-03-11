#!/bin/sh

# ssh requires strict permissions on the private key.
# Since it's mounted read-only, we copy it.
cp /root/.ssh/xrg13_key /tmp/xrg13_key
chmod 600 /tmp/xrg13_key

autossh -f -M 0 -gN \
    -o "ExitOnForwardFailure=yes" \
    -o "ServerAliveInterval=10" \
    -o "ServerAliveCountMax=3" \
    -i /tmp/xrg13_key \
    -L 11434:localhost:11434 $XRG13_SSH_USERNAME@xrg13.ms.mff.cuni.cz \
    -p 1302 \
    -o StrictHostKeyChecking=no \
    -o UserKnownHostsFile=/dev/null

timeout=30
while ! nc -z localhost 11434; do
    sleep 1
    timeout=$((timeout - 1))
    if [ $timeout -le 0 ]; then
        echo "SSH tunnel setup timed out."
        exit 1
    fi
done

echo "SSH tunnel established."
