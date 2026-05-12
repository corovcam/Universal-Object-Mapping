# 1. Ensure the script is running as Administrator
if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Error "This script requires Administrator privileges."
    exit 1
}

# 2. Get active internet-connected adapters
$ActiveAdapters = Get-NetIPConfiguration | Where-Object { $_.IPv4DefaultGateway -ne $null }

Write-Host "`n=== RESTORING ORIGINAL DNS (DHCP) ===" -ForegroundColor Cyan

# 3. Restore DNS to Automatic (DHCP)
foreach ($Adapter in $ActiveAdapters) {
    Write-Host "Resetting $($Adapter.InterfaceAlias) to Automatic DNS..."
    # -ResetServerAddresses removes the static IPs and defaults back to DHCP
    Set-DnsClientServerAddress -InterfaceIndex $Adapter.InterfaceIndex -ResetServerAddresses
}

Write-Host "Done. Your system is back to normal." -ForegroundColor Green
