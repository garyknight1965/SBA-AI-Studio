<#
.SYNOPSIS
Upgrades the SBA AI Studio Capture Time module structure.

.DESCRIPTION
Creates the parser and validation packages and moves
existing files into their new locations.

The script is safe to run multiple times.

Author: SBA AI Studio
#>

$ProjectRoot = Split-Path $PSScriptRoot -Parent
$CaptureRoot = Join-Path $ProjectRoot "sba_resolve\capture_time"

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host " SBA AI Studio - Capture Time Upgrade"
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

#----------------------------------------------------------
# Create folders
#----------------------------------------------------------

$Folders = @(
    "parsers",
    "validation"
)

foreach ($Folder in $Folders)
{
    $Path = Join-Path $CaptureRoot $Folder

    if (!(Test-Path $Path))
    {
        New-Item -ItemType Directory -Path $Path | Out-Null
        Write-Host "Created folder : $Folder" -ForegroundColor Green
    }
    else
    {
        Write-Host "Exists folder  : $Folder" -ForegroundColor Yellow
    }

    $Init = Join-Path $Path "__init__.py"

    if (!(Test-Path $Init))
    {
        New-Item -ItemType File -Path $Init | Out-Null
        Write-Host "Created        : $Folder\__init__.py" -ForegroundColor Green
    }
}

#----------------------------------------------------------
# Files to move
#----------------------------------------------------------

$Moves = @(
    @{
        Source      = "filename_parser.py"
        Destination = "parsers"
    },
    @{
        Source      = "filename_patterns.py"
        Destination = "parsers"
    },
    @{
        Source      = "confidence.py"
        Destination = "validation"
    },
    @{
        Source      = "validator.py"
        Destination = "validation"
    }
)

foreach ($Move in $Moves)
{
    $SourceFile = Join-Path $CaptureRoot $Move.Source
    $DestFile = Join-Path (Join-Path $CaptureRoot $Move.Destination) $Move.Source

    if ((Test-Path $SourceFile) -and !(Test-Path $DestFile))
    {
        Move-Item $SourceFile $DestFile
        Write-Host "Moved          : $($Move.Source)" -ForegroundColor Green
    }
    elseif (Test-Path $DestFile)
    {
        Write-Host "Already moved  : $($Move.Source)" -ForegroundColor Yellow
    }
    else
    {
        Write-Host "Not found      : $($Move.Source)" -ForegroundColor DarkYellow
    }
}

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host " Capture Time structure is up to date."
Write-Host "==========================================" -ForegroundColor Cyan