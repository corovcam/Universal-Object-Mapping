<# 
    Build script for libadvisor native library on Windows
    Requires: GLPK library installed and accessible
    
    Installation options:
    1. vcpkg: vcpkg install glpk:x64-windows
    2. Manual: Download from https://sourceforge.net/projects/winglpk/ and extract to C:\glpk
#>

param(
    [switch]$Force,
    [switch]$SkipIfMissing
)

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$sourceFile = Join-Path $scriptDir "ilp.c"
$outputFile = Join-Path $scriptDir "libadvisor.dll"

# Skip if DLL already exists and is newer than source (unless Force is specified)
if (-not $Force -and (Test-Path $outputFile)) {
    $dllTime = (Get-Item $outputFile).LastWriteTime
    $srcTime = (Get-Item $sourceFile).LastWriteTime
    if ($dllTime -gt $srcTime) {
        Write-Host "libadvisor.dll is up to date, skipping build."
        exit 0
    }
}

Write-Host "Building libadvisor.dll..."

# Try to find GLPK installation
$glpkPaths = @(
    # vcpkg default locations
    "$env:VCPKG_ROOT\installed\x64-windows",
    "$env:USERPROFILE\vcpkg\installed\x64-windows",
    "C:\vcpkg\installed\x64-windows",
    # WinGLPK default locations  
    "C:\glpk",
    "C:\glpk\w64",
    "C:\Program Files\glpk",
    "C:\Program Files (x86)\glpk",
    "$env:USERPROFILE\glpk",
    "$env:USERPROFILE\glpk\w64"
)

$glpkPath = $null
$includeDir = $null
$libDir = $null

foreach ($path in $glpkPaths) {
    if (-not (Test-Path $path)) { continue }
    
    # Check for vcpkg structure (include/glpk.h)
    if (Test-Path "$path\include\glpk.h") {
        $glpkPath = $path
        $includeDir = "$path\include"
        $libDir = "$path\lib"
        break
    }
    # Check for WinGLPK structure (glpk.h directly in folder)
    if (Test-Path "$path\glpk.h") {
        $glpkPath = $path
        $includeDir = $path
        $libDir = $path
        break
    }
}

if (-not $glpkPath) {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Yellow
    Write-Host "  GLPK library not found on Windows" -ForegroundColor Yellow  
    Write-Host "========================================" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "The Advisor feature requires the GLPK (GNU Linear Programming Kit) library."
    Write-Host ""
    Write-Host "To install GLPK, choose one of these options:" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Option 1 - WinGLPK (easiest):" -ForegroundColor Green
    Write-Host "  1. Download from: https://sourceforge.net/projects/winglpk/"
    Write-Host "  2. Extract to C:\glpk (so you have C:\glpk\w64\glpk.h)"
    Write-Host ""
    Write-Host "Option 2 - vcpkg:" -ForegroundColor Green
    Write-Host "  1. Install vcpkg: git clone https://github.com/microsoft/vcpkg C:\vcpkg"
    Write-Host "  2. Run: C:\vcpkg\bootstrap-vcpkg.bat"
    Write-Host "  3. Install GLPK: C:\vcpkg\vcpkg install glpk:x64-windows"
    Write-Host "  4. Set environment variable: VCPKG_ROOT=C:\vcpkg"
    Write-Host ""
    Write-Host "After installing, rebuild the project."
    Write-Host ""
    
    if ($SkipIfMissing) {
        Write-Host "Skipping native library build (Advisor features will not work)." -ForegroundColor Yellow
        exit 0
    }
    exit 1
}

Write-Host "Found GLPK at: $glpkPath"
Write-Host "Include dir: $includeDir"
Write-Host "Library dir: $libDir"

# Try to find a C compiler

# Check for MSVC (cl.exe) via vswhere
$vsWhere = "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe"
$useVsDevCmd = $false
$vcvarsall = $null
$glpkLibFile = $null

if (Test-Path $vsWhere) {
    $vsPath = & $vsWhere -latest -property installationPath 2>$null
    if ($vsPath) {
        $vcvarsall = Join-Path $vsPath "VC\Auxiliary\Build\vcvarsall.bat"
        if (Test-Path $vcvarsall) {
            $useVsDevCmd = $true
            Write-Host "Found MSVC at: $vsPath"
            
            # Find the GLPK library file for MSVC
            $libFiles = @("glpk_4_65.lib", "glpk.lib", "libglpk.lib")
            foreach ($lib in $libFiles) {
                if (Test-Path "$libDir\$lib") {
                    $glpkLibFile = $lib
                    break
                }
            }
            
            if (-not $glpkLibFile) {
                Write-Host "Warning: Could not find GLPK .lib file in $libDir" -ForegroundColor Yellow
                $useVsDevCmd = $false
            }
        }
    }
}

if ($useVsDevCmd) {
    Write-Host "Building with MSVC..."
    
    # Build using cl.exe through cmd with vcvarsall
    $buildCmd = @"
@echo off
call "$vcvarsall" x64 > nul 2>&1
cl.exe /LD /O2 /I"$includeDir" "$sourceFile" /Fe"$outputFile" /link /LIBPATH:"$libDir" $glpkLibFile
exit /b %ERRORLEVEL%
"@
    $tempBat = Join-Path $env:TEMP "build_advisor_$([guid]::NewGuid().ToString('N')).bat"
    $buildCmd | Out-File -FilePath $tempBat -Encoding ASCII
    
    # Run the batch file and capture output without treating stderr as error
    $process = Start-Process -FilePath "cmd.exe" -ArgumentList "/c", $tempBat -NoNewWindow -Wait -PassThru -RedirectStandardOutput "$env:TEMP\build_stdout.txt" -RedirectStandardError "$env:TEMP\build_stderr.txt"
    
    # Display output
    if (Test-Path "$env:TEMP\build_stdout.txt") {
        Get-Content "$env:TEMP\build_stdout.txt" | ForEach-Object { Write-Host $_ }
        Remove-Item "$env:TEMP\build_stdout.txt" -ErrorAction SilentlyContinue
    }
    if (Test-Path "$env:TEMP\build_stderr.txt") {
        Get-Content "$env:TEMP\build_stderr.txt" | ForEach-Object { Write-Host $_ }
        Remove-Item "$env:TEMP\build_stderr.txt" -ErrorAction SilentlyContinue
    }
    
    Remove-Item -Path $tempBat -ErrorAction SilentlyContinue
    
    if ($process.ExitCode -eq 0 -and (Test-Path $outputFile)) {
        Write-Host ""
        Write-Host "Successfully built libadvisor.dll using MSVC" -ForegroundColor Green
        
        # Clean up intermediate files
        Remove-Item -Path (Join-Path $scriptDir "ilp.obj") -ErrorAction SilentlyContinue
        Remove-Item -Path (Join-Path $scriptDir "libadvisor.exp") -ErrorAction SilentlyContinue  
        Remove-Item -Path (Join-Path $scriptDir "libadvisor.lib") -ErrorAction SilentlyContinue
        exit 0
    }
    
    Write-Host "MSVC build failed (exit code: $($process.ExitCode)), trying GCC..." -ForegroundColor Yellow
}

# Try GCC (MinGW/MSYS2)
$gccPaths = @(
    "C:\msys64\mingw64\bin\gcc.exe",
    "C:\mingw64\bin\gcc.exe", 
    "C:\MinGW\bin\gcc.exe"
)

$compiler = $null
foreach ($gccPath in $gccPaths) {
    if (Test-Path $gccPath) {
        $compiler = $gccPath
        break
    }
}

# Also check PATH
if (-not $compiler) {
    $gccCmd = Get-Command gcc -ErrorAction SilentlyContinue
    if ($gccCmd) {
        $compiler = $gccCmd.Source
    }
}

if ($compiler) {
    Write-Host "Building with GCC: $compiler"
    
    $process = Start-Process -FilePath $compiler -ArgumentList "-shared", "-O2", "-o", $outputFile, $sourceFile, "-I`"$includeDir`"", "-L`"$libDir`"", "-lglpk" -NoNewWindow -Wait -PassThru
    
    if ($process.ExitCode -eq 0 -and (Test-Path $outputFile)) {
        Write-Host ""
        Write-Host "Successfully built libadvisor.dll using GCC" -ForegroundColor Green
        exit 0
    }
    
    Write-Host "GCC build failed" -ForegroundColor Red
}

Write-Host ""
Write-Host "ERROR: Failed to build libadvisor.dll" -ForegroundColor Red
Write-Host ""
Write-Host "Please ensure you have a C compiler installed:" -ForegroundColor Cyan
Write-Host "  - Visual Studio with 'Desktop development with C++' workload, OR"
Write-Host "  - MinGW-w64 / MSYS2 with GCC"
Write-Host ""

if ($SkipIfMissing) {
    Write-Host "Skipping native library build (Advisor features will not work)." -ForegroundColor Yellow
    exit 0
}
exit 1
