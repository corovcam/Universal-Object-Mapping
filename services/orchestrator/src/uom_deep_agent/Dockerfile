FROM mcr.microsoft.com/dotnet/sdk:10.0

RUN apt-get update && apt-get install -y --no-install-recommends wget gnupg ca-certificates maven && rm -rf /var/lib/apt/lists/*

RUN wget -qO /etc/apt/trusted.gpg.d/bellsoft.asc https://download.bell-sw.com/pki/GPG-KEY-bellsoft

RUN echo 'deb [arch=amd64] https://apt.bell-sw.com/ stable main' > /etc/apt/sources.list.d/bellsoft.list

RUN apt-get update && apt-get install -y --no-install-recommends bellsoft-java25 && rm -rf /var/lib/apt/lists/*
