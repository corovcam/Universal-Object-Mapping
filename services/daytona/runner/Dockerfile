FROM daytonaio/daytona-runner

COPY set-host-docker-internal.sh /usr/local/bin/set-host-docker-internal.sh
RUN chmod +x /usr/local/bin/set-host-docker-internal.sh

# Override the entrypoint to run the patch script FIRST, then start the original services
ENTRYPOINT ["sh", "-c", "/usr/local/bin/set-host-docker-internal.sh && /usr/local/bin/dockerd-entrypoint.sh & exec daytona-runner"]
