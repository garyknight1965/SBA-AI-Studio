<#
.SYNOPSIS
Creates the Capture Time module for SBA AI Studio.

.DESCRIPTION
Creates the production folder structure and starter files
for the CORE-003 Capture Time Resolver.

Author : SBA AI Studio
#>

$ProjectRoot = Split-Path $PSScriptRoot -Parent
$ModuleRoot  = Join-Path $ProjectRoot "sba_resolve\capture_time"

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host " SBA AI Studio - Capture Time Module"
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

#---------------------------------------------------
# Create folder
#---------------------------------------------------

New-Item `
    -ItemType Directory `
    -Force `
    -Path $ModuleRoot | Out-Null

#---------------------------------------------------
# Files
#---------------------------------------------------

$Files = @(
    "__init__.py",
    "models.py",
    "confidence.py",
    "validator.py",
    "filename_parser.py",
    "resolver.py",
    "exceptions.py"
)

foreach ($File in $Files)
{
    $Path = Join-Path $ModuleRoot $File

    if (!(Test-Path $Path))
    {
        New-Item `
            -ItemType File `
            -Path $Path | Out-Null

        Write-Host "Created $File" -ForegroundColor Green
    }
    else
    {
        Write-Host "Exists  $File" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "Capture Time module ready." -ForegroundColor Green