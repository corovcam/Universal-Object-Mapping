# Copyright 2025 Daytona Platforms Inc.
# SPDX-License-Identifier: AGPL-3.0

<#
.SYNOPSIS
Setup wildcard DNS for *.proxy.localhost -> 127.0.0.1 on Windows.
Requires Acrylic DNS Proxy (installed automatically via winget if missing).
#>

# 1. Ensure the script is running as Administrator
if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Error "This script requires Administrator privileges. Please run PowerShell as Admin."
    exit 1
}

# Define paths early so we can check if it's already installed
$AcrylicDir = "${env:ProgramFiles(x86)}\Acrylic DNS Proxy"
$AcrylicHostsPath = "$AcrylicDir\AcrylicHosts.txt"

# 2. Check and Install Acrylic DNS Proxy
if (-not (Test-Path $AcrylicDir)) {
    Write-Host "Installing Acrylic DNS Proxy via Winget (Windows equivalent to dnsmasq)..."
    winget install Mayakron.AcrylicDNS --accept-package-agreements --accept-source-agreements --silent

    # Give the installer a moment to flush files to disk
    Start-Sleep -Seconds 5
} else {
    Write-Host "Acrylic DNS Proxy is already installed. Skipping installation." -ForegroundColor Cyan
}

# Verify installation was successful / exists
if (Test-Path $AcrylicHostsPath) {
    # 3. Configure the Wildcard
    Write-Host "Configuring wildcard DNS (*.proxy.localhost -> 127.0.0.1)..."
    $DnsEntry = "127.0.0.1 *.proxy.localhost"
    
    # Read current hosts to avoid appending duplicate entries on multiple runs
    $CurrentHosts = Get-Content -Path $AcrylicHostsPath -Raw
    if ($CurrentHosts -notmatch [regex]::Escape($DnsEntry)) {
        # Append to Acrylic's custom hosts file
        Add-Content -Path $AcrylicHostsPath -Value $DnsEntry
        Write-Host " -> Added wildcard entry to AcrylicHosts.txt"
    } else {
        Write-Host " -> Wildcard entry already exists. Skipping."
    }

    # 4. Restart the Service
    Write-Host "Restarting Acrylic DNS Proxy service..."
    Restart-Service -Name "AcrylicDNSProxySvc" -ErrorAction Stop

    # 5. Set Windows to use the local DNS server for BOTH IPv4 and IPv6
    Write-Host "Configuring active network adapters to use local DNS..."
    
    # Fetch only adapters actively connected to the internet (have a gateway)
    $ActiveConfigs = Get-NetIPConfiguration | Where-Object { $_.IPv4DefaultGateway -ne $null }

    foreach ($Config in $ActiveConfigs) {
        Write-Host " -> Setting DNS for adapter: $($Config.InterfaceAlias)"
        
        # Windows will automatically assign IPv4 strings to IPv4 and IPv6 strings to IPv6
        $DnsServers = @("127.0.0.1", "::1", "8.8.8.8", "2001:4860:4860::8888")
        
        Set-DnsClientServerAddress -InterfaceIndex $Config.InterfaceIndex -ServerAddresses $DnsServers
    }

    Write-Host "`nDone. Test with:"
    Write-Host "Resolve-DnsName 2280-test.proxy.localhost" -ForegroundColor Green
} else {
    Write-Error "Failed to locate AcrylicHosts.txt at $AcrylicHostsPath. Installation may have failed."
    exit 1
}