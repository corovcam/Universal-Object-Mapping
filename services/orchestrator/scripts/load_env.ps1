$envFile = if ($args.Count -gt 0) { $args[0] } else { '.env.dev' }

Get-Content $envFile | foreach {
  $name, $value = $_.split('=')
  if ([string]::IsNullOrWhiteSpace($name) -or $name.Contains('#')) {
    # skip empty or comment line in ENV file
    return
  }
  Set-Content env:\$name $value
}
