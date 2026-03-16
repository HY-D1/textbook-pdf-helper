# Week 1 Demo Runner
# 
# This script runs the Week 1 ALGL PDF Helper demo with proper setup checks.
# It demonstrates both the normal deterministic path and validates the OCR fallback integration.
#
# Prerequisites:
#   - Python virtual environment activated (.venv)
#   - Ollama running with qwen3.5:9b model pulled
#   - PDFs in raw_pdf/ directory
#
# Usage:
#   .\scripts\run_week1_demo.ps1                    # Run main demo
#   .\scripts\run_week1_demo.ps1 -WeakSlice         # Run weak-slice OCR proof
#   .\scripts\run_week1_demo.ps1 -SkipOllamaCheck   # Skip Ollama prerequisite check

param(
    [switch]$WeakSlice = $false,
    [switch]$SkipOllamaCheck = $false
)

$ErrorActionPreference = "Stop"
$DemoVersion = "1.5.0"

# Colors for output
$Green = "Green"
$Yellow = "Yellow"
$Red = "Red"
$Blue = "Cyan"

Write-Host "============================================================" -ForegroundColor $Blue
Write-Host "  ALGL PDF Helper - Week 1 Demo Runner v$DemoVersion" -ForegroundColor $Blue
Write-Host "============================================================" -ForegroundColor $Blue
Write-Host ""

# =============================================================================
# Step 1: Check Prerequisites
# =============================================================================

Write-Host "Step 1: Checking prerequisites..." -ForegroundColor $Blue

# Check Python environment
if (-not (Test-Path ".venv")) {
    Write-Host "ERROR: Virtual environment not found at .venv\" -ForegroundColor $Red
    Write-Host "Run: python -m venv .venv" -ForegroundColor $Yellow
    exit 1
}

$PythonPath = ".venv\Scripts\python.exe"
if (-not (Test-Path $PythonPath)) {
    Write-Host "ERROR: Python not found at $PythonPath" -ForegroundColor $Red
    exit 1
}
Write-Host "  [OK] Python environment found" -ForegroundColor $Green

# Check Ollama (unless skipped)
if (-not $SkipOllamaCheck) {
    try {
        $OllamaResponse = Invoke-RestMethod -Uri "http://localhost:11434/api/tags" -Method GET -TimeoutSec 5
        Write-Host "  [OK] Ollama is running" -ForegroundColor $Green
        
        # Check for required models
        $Models = $OllamaResponse.models.name
        if ($Models -contains "qwen3.5:9b" -or $Models -contains "qwen3.5:9b-q8_0") {
            Write-Host "  [OK] qwen3.5:9b model found" -ForegroundColor $Green
        } else {
            Write-Host "  [WARN] qwen3.5:9b model not found" -ForegroundColor $Yellow
            Write-Host "         Run: ollama pull qwen3.5:9b" -ForegroundColor $Yellow
        }
        
        if ($Models -contains "glm-ocr:latest") {
            Write-Host "  [OK] glm-ocr:latest model found (optional)" -ForegroundColor $Green
        } else {
            Write-Host "  [INFO] glm-ocr:latest not found (optional, for OCR fallback)" -ForegroundColor $Yellow
        }
    } catch {
        Write-Host "  [WARN] Ollama not available at http://localhost:11434" -ForegroundColor $Yellow
        Write-Host "         Repair path will be disabled. Start with: ollama serve" -ForegroundColor $Yellow
    }
} else {
    Write-Host "  [SKIP] Ollama check skipped" -ForegroundColor $Yellow
}

# Check PDF files
$PdfFile = if ($WeakSlice) { "raw_pdf\murach-ch3-weak-slice.pdf" } else { "raw_pdf\murachs-mysql-3rd-edition.pdf" }
if (-not (Test-Path $PdfFile)) {
    Write-Host "ERROR: PDF file not found: $PdfFile" -ForegroundColor $Red
    exit 1
}
Write-Host "  [OK] PDF file found: $PdfFile" -ForegroundColor $Green

Write-Host ""

# =============================================================================
# Step 2: Configure Demo
# =============================================================================

Write-Host "Step 2: Configuring demo..." -ForegroundColor $Blue

if ($WeakSlice) {
    Write-Host "  Mode: Weak-slice OCR proof" -ForegroundColor $Blue
    $PdfPath = "raw_pdf\murach-ch3-weak-slice.pdf"
    $OutputDir = "outputs\week1-demo\weak-slice"
    $PageRange = "1-5"
    $Description = "5 pages, image-only (no embedded text)"
} else {
    Write-Host "  Mode: Normal deterministic-first (Murach Ch3)" -ForegroundColor $Blue
    $PdfPath = "raw_pdf\murachs-mysql-3rd-edition.pdf"
    $OutputDir = "outputs\week1-demo\murach-ch3"
    $PageRange = "93-132"
    $Description = "Chapter 3 (~40 pages, deterministic extraction)"
}

Write-Host "  PDF: $PdfPath" -ForegroundColor $Blue
Write-Host "  Pages: $PageRange" -ForegroundColor $Blue
Write-Host "  Output: $OutputDir" -ForegroundColor $Blue
Write-Host "  Description: $Description" -ForegroundColor $Blue
Write-Host ""

# =============================================================================
# Step 3: Run Demo
# =============================================================================

Write-Host "Step 3: Running pipeline..." -ForegroundColor $Blue
Write-Host "  This may take 5-10 minutes depending on hardware." -ForegroundColor $Yellow
Write-Host ""

# Create output directory
New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null

# Build command
$Command = @(
    "-m", "algl_pdf_helper",
    "process",
    $PdfPath,
    "--output-dir", $OutputDir,
    "--page-range", $PageRange,
    "--export-mode", "prototype",
    "--filter-level", "development",
    "--llm-provider", "ollama",
    "--use-ollama-repair"
)

Write-Host "Command: python $([string]::Join(' ', $Command))" -ForegroundColor $Blue
Write-Host ""

# Run pipeline
$Stopwatch = [System.Diagnostics.Stopwatch]::StartNew()

& $PythonPath @Command 2>&1 | ForEach-Object {
    Write-Host $_
}

$Stopwatch.Stop()
$Duration = $Stopwatch.Elapsed

Write-Host ""
Write-Host "Pipeline completed in $($Duration.Minutes)m $($Duration.Seconds)s" -ForegroundColor $Green
Write-Host ""

# =============================================================================
# Step 4: Verify Output
# =============================================================================

Write-Host "Step 4: Verifying output..." -ForegroundColor $Blue

$ExpectedFiles = @(
    "instructional_units.jsonl",
    "export_manifest.json",
    "quality_report.json",
    "routing_decision.json"
)

$AllFound = $true
foreach ($File in $ExpectedFiles) {
    $FilePath = Join-Path $OutputDir $File
    if (Test-Path $FilePath) {
        Write-Host "  [OK] $File" -ForegroundColor $Green
    } else {
        Write-Host "  [MISSING] $File" -ForegroundColor $Red
        $AllFound = $false
    }
}

Write-Host ""

# Check routing decision
$RoutingFile = Join-Path $OutputDir "routing_decision.json"
if (Test-Path $RoutingFile) {
    $RoutingContent = Get-Content $RoutingFile -Raw
    if ($RoutingContent -match '"classification"\s*:\s*"([^"]+)"') {
        $Classification = $Matches[1]
        Write-Host "  Routing classification: $Classification" -ForegroundColor $Blue
        
        if ($WeakSlice -and $Classification -eq "needs_ocr_fallback") {
            Write-Host "  [OK] Weak slice correctly triggered OCR fallback path" -ForegroundColor $Green
        } elseif (-not $WeakSlice -and $Classification -eq "direct_extract") {
            Write-Host "  [OK] Normal PDF correctly used direct extraction" -ForegroundColor $Green
        }
    }
}

Write-Host ""

# =============================================================================
# Step 5: Summary
# =============================================================================

Write-Host "============================================================" -ForegroundColor $Blue
Write-Host "  Demo Complete" -ForegroundColor $Blue
Write-Host "============================================================" -ForegroundColor $Blue
Write-Host ""
Write-Host "Output directory: $(Resolve-Path $OutputDir)" -ForegroundColor $Green
Write-Host ""
Write-Host "Key files to review:" -ForegroundColor $Blue
Write-Host "  - $OutputDir\instructional_units.jsonl    (L1-L4 units)" -ForegroundColor $Green
Write-Host "  - $OutputDir\export_manifest.json        (Summary stats)" -ForegroundColor $Green
Write-Host "  - $OutputDir\quality_report.json         (Quality scores)" -ForegroundColor $Green
Write-Host "  - $OutputDir\routing_decision.json       (Fallback path taken)" -ForegroundColor $Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor $Blue
Write-Host "  1. Inspect units: algl-pdf inspect $OutputDir --concept select-basic" -ForegroundColor $Yellow
Write-Host "  2. Validate:      algl-pdf validate $OutputDir" -ForegroundColor $Yellow
Write-Host "  3. View report:   Get-Content $OutputDir\quality_report.json" -ForegroundColor $Yellow
Write-Host ""
