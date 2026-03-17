param(
    [switch]$SkipOllamaCheck = $false,
    [switch]$FullBook = $false
)

$ErrorActionPreference = "Stop"

# -----------------------------------------------------------------------------
# Resolve repo root safely:
# - if run as a saved script: use $PSScriptRoot
# - if pasted into an interactive shell: use current directory
# -----------------------------------------------------------------------------
if ($PSScriptRoot) {
    # script is inside scripts\ ; repo root is parent of scripts\
    $RepoRoot = Split-Path -Parent $PSScriptRoot
}
elseif ($MyInvocation.MyCommand.Path) {
    $RepoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
}
else {
    $RepoRoot = (Get-Location).Path
}

Set-Location $RepoRoot

$Python = Join-Path $RepoRoot ".venv\Scripts\python.exe"

$MurachPdf = Join-Path $RepoRoot "raw_pdf\murachs-mysql-3rd-edition.pdf"

$RamakrishnanCandidates = @(
    (Join-Path $RepoRoot "raw_pdf\ramakrishnan-dbms-3rd-edition.pdf"),
    (Join-Path $RepoRoot "raw_pdf\dbms-ramakrishnan-3rd-edition.pdf")
)

$RamakrishnanPdf = $null
foreach ($candidate in $RamakrishnanCandidates) {
    if (Test-Path $candidate) {
        $RamakrishnanPdf = $candidate
        break
    }
}

$OutputRoot = Join-Path $RepoRoot "outputs\ollama-both-textbooks"

function Write-Section($text) {
    Write-Host ""
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host " $text" -ForegroundColor Cyan
    Write-Host "============================================================" -ForegroundColor Cyan
}

function Assert-FileExists($path, $label) {
    if ([string]::IsNullOrWhiteSpace($path) -or -not (Test-Path $path)) {
        throw "$label not found: $path"
    }
}

function Check-Ollama {
    Write-Host "Checking Ollama..." -ForegroundColor Yellow
    try {
        $resp = Invoke-RestMethod -Uri "http://localhost:11434/api/tags" -Method GET -TimeoutSec 5
    } catch {
        throw "Ollama is not reachable at http://localhost:11434 . Start it with: ollama serve"
    }

    $models = @()
    if ($resp.models) {
        $models = $resp.models | ForEach-Object { $_.name }
    }

    Write-Host "Available models:" -ForegroundColor Green
    $models | ForEach-Object { Write-Host "  - $_" }

    if (-not ($models -contains "qwen3.5:9b")) {
        Write-Warning "qwen3.5:9b not found. Pull it with: ollama pull qwen3.5:9b"
    }

    if (-not ($models -contains "glm-ocr:latest")) {
        Write-Warning "glm-ocr:latest not found. Pull it with: ollama pull glm-ocr:latest"
    }
}

function Run-ProcessCommand {
    param(
        [string]$PdfPath,
        [string]$OutputDir,
        [string]$Label,
        [string]$ChapterRange,
        [switch]$UseFullBook
    )

    Write-Section "Running: $Label"

    New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null

    $args = @(
        "-m", "algl_pdf_helper",
        "process",
        $PdfPath,
        "--output-dir", $OutputDir,
        "--export-mode", "student_ready",
        "--filter-level", "production",
        "--llm-provider", "ollama",
        "--use-ollama-repair",
        "--ollama-model", "qwen3.5:9b"
    )

    if (-not $UseFullBook) {
        $args += @("--chapter-range", $ChapterRange)
    }

    Write-Host "Command:" -ForegroundColor Yellow
    Write-Host "$Python $($args -join ' ')" -ForegroundColor Gray
    Write-Host ""

    & $Python @args

    Write-Host ""
    Write-Host "Finished: $Label" -ForegroundColor Green
    Write-Host "Output: $OutputDir" -ForegroundColor Green

    $expectedFiles = @(
        "instructional_units.jsonl",
        "quality_report.json",
        "export_manifest.json",
        "routing_decision.json"
    )

    foreach ($file in $expectedFiles) {
        $full = Join-Path $OutputDir $file
        if (Test-Path $full) {
            Write-Host "  [OK] $file" -ForegroundColor Green
        } else {
            Write-Warning "Missing expected file: $full"
        }
    }

    $ocrArtifact = Join-Path $OutputDir "ocr_fallback_result.json"
    if (Test-Path $ocrArtifact) {
        Write-Host "  [INFO] OCR fallback artifact present: ocr_fallback_result.json" -ForegroundColor Yellow
    } else {
        Write-Host "  [INFO] OCR fallback artifact not present (likely deterministic path was sufficient)" -ForegroundColor DarkYellow
    }
}

Write-Section "ALGL PDF Helper - Process Both Textbooks with Ollama"

Assert-FileExists $Python "Virtualenv Python"
Assert-FileExists $MurachPdf "Murach PDF"

if (-not $RamakrishnanPdf) {
    throw "Ramakrishnan PDF not found. Checked:`n - $($RamakrishnanCandidates -join "`n - ")"
}

if (-not $SkipOllamaCheck) {
    Check-Ollama
} else {
    Write-Warning "Skipping Ollama check."
}

Write-Host ""
Write-Host "Repo root: $RepoRoot" -ForegroundColor Cyan
Write-Host "Mode: $($(if ($FullBook) { 'FULL BOOK' } else { 'CHAPTER SLICES' }))" -ForegroundColor Cyan

$murachOut = Join-Path $OutputRoot "murach-ch3"
Run-ProcessCommand `
    -PdfPath $MurachPdf `
    -OutputDir $murachOut `
    -Label "Murach MySQL 3e" `
    -ChapterRange "3" `
    -UseFullBook:$FullBook

$ramOut = Join-Path $OutputRoot "ramakrishnan-ch2"
Run-ProcessCommand `
    -PdfPath $RamakrishnanPdf `
    -OutputDir $ramOut `
    -Label "Ramakrishnan DBMS 3e" `
    -ChapterRange "2" `
    -UseFullBook:$FullBook

Write-Section "Done"

Write-Host "Murach output:       $murachOut" -ForegroundColor Green
Write-Host "Ramakrishnan output: $ramOut" -ForegroundColor Green
Write-Host ""
Write-Host "Check these files in each output folder:" -ForegroundColor Yellow
Write-Host "  - instructional_units.jsonl"
Write-Host "  - quality_report.json"
Write-Host "  - export_manifest.json"
Write-Host "  - routing_decision.json"
Write-Host "  - ocr_fallback_result.json (only if OCR fallback triggered)"