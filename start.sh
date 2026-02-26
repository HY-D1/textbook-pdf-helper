#!/bin/bash

# ALGL PDF Helper - Interactive Processing Script
# Usage: ./start.sh

# Don't use set -e as it interferes with error handling in loops

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RAW_PDF_DIR="$SCRIPT_DIR/raw_pdf"
READ_USE_DIR="$SCRIPT_DIR/read_use"

# Function to print colored output
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "\n${CYAN}========================================${NC}"
    echo -e "${CYAN}$1${NC}"
    echo -e "${CYAN}========================================${NC}\n"
}

# Function to check if virtual environment is activated
check_venv() {
    local venv_python="$SCRIPT_DIR/.venv/bin/python"
    local venv_pip="$SCRIPT_DIR/.venv/bin/pip"
    
    # Create venv if it doesn't exist
    if [[ ! -d "$SCRIPT_DIR/.venv" ]]; then
        print_warning "Virtual environment not found. Creating one..."
        python3 -m venv "$SCRIPT_DIR/.venv"
    fi
    
    # Ensure package is installed using venv python directly
    if ! "$venv_python" -c "import algl_pdf_helper" 2>/dev/null; then
        print_info "Installing algl-pdf-helper package..."
        "$venv_pip" install "$SCRIPT_DIR" 2>&1 | tail -5
    fi
    
    # Verify installation
    if ! "$venv_python" -c "import algl_pdf_helper" 2>/dev/null; then
        print_error "Failed to install algl-pdf-helper package"
        exit 1
    fi
    
    print_success "Package installed successfully"
}

# Function to check OCR system dependencies
check_ocr_deps() {
    local missing=()
    
    if ! command -v tesseract &> /dev/null; then
        missing+=("tesseract")
    fi
    
    if ! command -v gs &> /dev/null && ! command -v gswin64c &> /dev/null; then
        missing+=("ghostscript")
    fi
    
    if [[ ${#missing[@]} -gt 0 ]]; then
        print_warning "OCR system dependencies missing: ${missing[*]}"
        echo ""
        echo "To use OCR features, install:"
        if [[ "$OSTYPE" == "darwin"* ]]; then
            echo "  brew install tesseract ghostscript"
        elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
            echo "  sudo apt-get install tesseract-ocr ghostscript"
        else
            echo "  - Tesseract: https://github.com/UB-Mannheim/tesseract/wiki"
            echo "  - Ghostscript: https://www.ghostscript.com/download/gsdnld.html"
        fi
        echo ""
        read -p "Continue without OCR? (Y/n): " confirm
        [[ "$confirm" =~ ^[Nn]$ ]] && exit 1
        OCR_MODE="skip"
    fi
}

# Function to check educational pipeline dependencies
check_edu_deps() {
    local venv_python="$SCRIPT_DIR/.venv/bin/python"
    local missing_deps=()
    
    if ! "$venv_python" -c "import marker" 2>/dev/null; then
        missing_deps+=("marker-pdf")
    fi
    
    if ! "$venv_python" -c "import openai" 2>/dev/null; then
        missing_deps+=("openai")
    fi
    
    if [[ ${#missing_deps[@]} -gt 0 ]]; then
        echo ""
        print_info "Optional: For educational note generation (option 7), install:"
        echo "  pip install ${missing_deps[*]}"
        echo ""
        echo "Educational notes feature:"
        echo "  ✅ High-quality PDF extraction (Marker)"
        echo "  ✅ LLM-enhanced learning content (OpenAI)"
        echo "  ✅ Student-ready study materials"
        echo ""
    fi
}

# Function to get PDF name without extension
get_pdf_basename() {
    local pdf_path="$1"
    local name
    name=$(basename "$pdf_path")
    # Remove .pdf or .PDF extension (case insensitive)
    name="${name%.pdf}"
    name="${name%.PDF}"
    name="${name%.Pdf}"
    name="${name%.pDf}"
    echo "$name"
}

# Function to sanitize folder name
sanitize_folder_name() {
    local name="$1"
    # Fallback if empty
    if [[ -z "$name" ]]; then
        name="unnamed-pdf"
    fi
    # Replace spaces and special chars with hyphens, lowercase
    local sanitized
    sanitized=$(echo "$name" | tr '[:upper:]' '[:lower:]' | tr -cs 'a-z0-9' '-' | sed 's/^-//;s/-$//')
    # Fallback if sanitization resulted in empty string
    if [[ -z "$sanitized" ]]; then
        sanitized="pdf-$(date +%s)"
    fi
    echo "$sanitized"
}

# Function to list available PDFs
list_pdfs() {
    local pdfs=()
    while IFS= read -r -d '' pdf; do
        pdfs+=("$pdf")
    done < <(find "$RAW_PDF_DIR" -maxdepth 1 -type f \( -iname "*.pdf" \) -print0 2>/dev/null || true)
    
    if [[ ${#pdfs[@]} -eq 0 ]]; then
        echo ""
        return 1
    fi
    
    printf '%s\n' "${pdfs[@]}"
}

# Function to show main menu
show_main_menu() {
    print_header "ALGL PDF Helper - Main Menu"
    
    local pdf_count
    pdf_count=$(find "$RAW_PDF_DIR" -maxdepth 1 -type f -iname "*.pdf" 2>/dev/null | wc -l)
    
    echo -e "${CYAN}Raw PDFs available:${NC} $pdf_count"
    echo -e "${CYAN}Output directory:${NC} $READ_USE_DIR"
    echo ""
    echo "1) 📄 Process Single PDF"
    echo "2) 📁 Process All PDFs"
    echo "3) 🔄 Re-process Existing PDF"
    echo "4) 📋 List Raw PDFs"
    echo "5) 📂 Open Output Folder"
    echo "6) 📤 Export to SQL-Adapt (Standard)"
    echo "7) 🎓 Export to SQL-Adapt (Educational)"
    echo "8) ⚙️  Advanced Options"
    echo "9) 🚪 Exit"
    echo ""
}

# Function to show PDF selection menu
show_pdf_menu() {
    print_header "Select PDF to Process"
    
    local pdfs=()
    local i=1
    
    while IFS= read -r -d '' pdf; do
        pdfs+=("$pdf")
        local basename
        basename=$(get_pdf_basename "$pdf")
        local size
        size=$(du -h "$pdf" 2>/dev/null | cut -f1 || echo "?")
        printf "  %2d) %-40s (%s)\n" "$i" "$basename" "$size"
        ((i++))
    done < <(find "$RAW_PDF_DIR" -maxdepth 1 -type f \( -iname "*.pdf" \) -print0 2>/dev/null | sort -z)
    
    if [[ ${#pdfs[@]} -eq 0 ]]; then
        print_error "No PDFs found in $RAW_PDF_DIR"
        return 1
    fi
    
    echo ""
    echo "  0) Go Back"
    echo ""
    
    read -p "Select PDF [0-${#pdfs[@]}]: " choice
    
    if [[ "$choice" == "0" ]]; then
        return 2
    fi
    
    if [[ "$choice" =~ ^[0-9]+$ ]] && (( choice >= 1 && choice <= ${#pdfs[@]} )); then
        SELECTED_PDF="${pdfs[$((choice-1))]}"
        return 0
    else
        print_error "Invalid selection"
        return 1
    fi
}

# Function to show processing options
show_options_menu() {
    print_header "Processing Options"
    
    echo "Current settings:"
    echo "  OCR Mode:        ${OCR_MODE:-auto}"
    echo "  Use Aliases:     ${USE_ALIASES:-yes}"
    echo "  Strip Headers:   ${STRIP_HEADERS:-yes}"
    echo "  Chunk Words:     ${CHUNK_WORDS:-180}"
    echo "  Overlap Words:   ${OVERLAP_WORDS:-30}"
    echo ""
    echo "1) Toggle OCR (current: ${OCR_MODE:-auto})"
    echo "   - auto: OCR only when needed"
    echo "   - force: Always OCR"
    echo "   - skip: Never OCR"
    echo ""
    echo "2) Toggle Aliases (current: ${USE_ALIASES:-yes})"
    echo "   - yes: Use stable names like 'sql-textbook'"
    echo "   - no: Use SHA-based IDs"
    echo ""
    echo "3) Toggle Header Stripping (current: ${STRIP_HEADERS:-yes})"
    echo ""
    echo "4) Set Chunk Size (current: ${CHUNK_WORDS:-180})"
    echo ""
    echo "5) Set Overlap (current: ${OVERLAP_WORDS:-30})"
    echo ""
    echo "6) Back to Main Menu"
    echo ""
    
    read -p "Select option [1-6]: " opt
    
    case $opt in
        1)
            case "${OCR_MODE:-auto}" in
                auto) OCR_MODE="force" ;;
                force) OCR_MODE="skip" ;;
                skip) OCR_MODE="auto" ;;
            esac
            ;;
        2)
            if [[ "${USE_ALIASES:-yes}" == "yes" ]]; then
                USE_ALIASES="no"
            else
                USE_ALIASES="yes"
            fi
            ;;
        3)
            if [[ "${STRIP_HEADERS:-yes}" == "yes" ]]; then
                STRIP_HEADERS="no"
            else
                STRIP_HEADERS="yes"
            fi
            ;;
        4)
            read -p "Enter chunk size in words [180]: " CHUNK_WORDS
            CHUNK_WORDS=${CHUNK_WORDS:-180}
            ;;
        5)
            read -p "Enter overlap in words [30]: " OVERLAP_WORDS
            OVERLAP_WORDS=${OVERLAP_WORDS:-30}
            ;;
    esac
}

# Function to build algl-pdf command arguments
build_args() {
    local args=""
    
    # OCR option
    case "${OCR_MODE:-auto}" in
        force) args="$args --ocr" ;;
        skip) args="$args --auto-ocr=false" ;;
        *) ;; # auto is default
    esac
    
    # Aliases
    if [[ "${USE_ALIASES:-yes}" == "yes" ]]; then
        args="$args --use-aliases"
    fi
    
    # Strip headers
    if [[ "${STRIP_HEADERS:-yes}" == "no" ]]; then
        args="$args --strip-headers=false"
    fi
    
    # Chunk and overlap
    args="$args --chunk-words ${CHUNK_WORDS:-180}"
    args="$args --overlap-words ${OVERLAP_WORDS:-30}"
    
    echo "$args"
}

# Function to ensure venv is active
ensure_venv() {
    local venv_python="$SCRIPT_DIR/.venv/bin/python"
    local venv_pip="$SCRIPT_DIR/.venv/bin/pip"
    
    # Verify module is accessible, install if not
    if ! "$venv_python" -c "import algl_pdf_helper" 2>/dev/null; then
        print_info "Installing package in venv..."
        "$venv_pip" install "$SCRIPT_DIR" 2>&1 | tail -5
    fi
}

# Function to process a single PDF
process_pdf() {
    local pdf_path="$1"
    local pdf_name
    pdf_name=$(get_pdf_basename "$pdf_path")
    local folder_name
    folder_name=$(sanitize_folder_name "$pdf_name")
    local output_dir="$READ_USE_DIR/$folder_name"
    
    # Debug output
    if [[ -z "$pdf_name" ]] || [[ "$pdf_name" == "-" ]]; then
        print_error "Could not extract valid PDF name from: $pdf_path"
        return 1
    fi
    
    # Ensure venv is active before each PDF
    ensure_venv
    
    print_header "Processing: $pdf_name"
    
    # Check if already processed
    if [[ -d "$output_dir" ]] && [[ -f "$output_dir/index.json" ]]; then
        print_warning "Already processed: $pdf_name"
        read -p "Re-process? (y/N): " confirm
        if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
            return 0
        fi
        rm -rf "$output_dir"
    fi
    
    mkdir -p "$output_dir"
    
    # Build command
    local cmd_args
    cmd_args=$(build_args)
    
    # First check quality
    print_info "Checking extraction quality..."
    local venv_python="$SCRIPT_DIR/.venv/bin/python"
    local quality_output
    quality_output=$("$venv_python" -m algl_pdf_helper check-quality "$pdf_path" 2>&1)
    
    # Check if OCR is recommended
    if echo "$quality_output" | grep -q "OCR recommended"; then
        print_warning "Low quality text detected - OCR will be used automatically"
        # Force OCR mode temporarily for this PDF
        local saved_ocr_mode="${OCR_MODE:-auto}"
        OCR_MODE="force"
        cmd_args=$(build_args)
        OCR_MODE="$saved_ocr_mode"
    fi
    
    echo ""
    print_info "Command: $venv_python -m algl_pdf_helper index $pdf_path --out $output_dir $cmd_args"
    echo ""
    
    # Run processing using venv Python directly to ensure module is found
    if "$venv_python" -m algl_pdf_helper index "$pdf_path" --out "$output_dir" $cmd_args; then
        print_success "Processing complete!"
        print_info "Output location: $output_dir"
        
        # Show what was generated
        echo ""
        echo "Generated files:"
        ls -1 "$output_dir" | sed 's/^/  - /'
        
        if [[ -d "$output_dir/concepts" ]]; then
            local concept_count
            concept_count=$(find "$output_dir/concepts" -name "*.md" | wc -l)
            print_success "Concepts generated: $concept_count"
        fi
        
        return 0
    else
        print_error "Processing failed!"
        return 1
    fi
}

# Function to process all PDFs
process_all_pdfs() {
    print_header "Processing All PDFs"
    
    local pdfs=()
    while IFS= read -r -d '' pdf; do
        pdfs+=("$pdf")
    done < <(find "$RAW_PDF_DIR" -maxdepth 1 -type f \( -iname "*.pdf" \) -print0 2>/dev/null | sort -z)
    
    if [[ ${#pdfs[@]} -eq 0 ]]; then
        print_error "No PDFs found in $RAW_PDF_DIR"
        return 1
    fi
    
    print_info "Found ${#pdfs[@]} PDF(s) to process"
    echo ""
    
    local success_count=0
    local fail_count=0
    
    for pdf in "${pdfs[@]}"; do
        if process_pdf "$pdf"; then
            ((success_count++))
        else
            ((fail_count++))
        fi
        echo ""
    done
    
    print_header "Batch Processing Complete"
    print_success "Successful: $success_count"
    if [[ $fail_count -gt 0 ]]; then
        print_error "Failed: $fail_count"
    fi
}

# Function to re-process existing
reprocess_existing() {
    print_header "Re-process Existing PDFs"
    
    local folders=()
    local i=1
    
    while IFS= read -r -d '' folder; do
        local folder_name
        folder_name=$(basename "$folder")
        folders+=("$folder")
        
        # Check if source PDF still exists
        local pdf_name
        pdf_name=$(echo "$folder_name" | tr '-' ' ')
        local found_pdf=""
        
        for ext in pdf PDF; do
            if [[ -f "$RAW_PDF_DIR/$pdf_name.$ext" ]]; then
                found_pdf="$RAW_PDF_DIR/$pdf_name.$ext"
                break
            fi
        done
        
        local status="${GREEN}✓${NC}"
        [[ -z "$found_pdf" ]] && status="${RED}✗ Source PDF missing${NC}"
        
        printf "  %2d) %-30s %b\n" "$i" "$folder_name" "$status"
        ((i++))
    done < <(find "$READ_USE_DIR" -maxdepth 1 -type d ! -path "$READ_USE_DIR" -print0 2>/dev/null | sort -z)
    
    if [[ ${#folders[@]} -eq 0 ]]; then
        print_warning "No processed PDFs found"
        return 1
    fi
    
    echo ""
    echo "  A) Re-process All"
    echo "  0) Go Back"
    echo ""
    
    read -p "Select [0-${#folders[@]}/A]: " choice
    
    if [[ "$choice" == "0" ]]; then
        return 0
    fi
    
    if [[ "$choice" =~ ^[Aa]$ ]]; then
        for folder in "${folders[@]}"; do
            local folder_name
            folder_name=$(basename "$folder")
            local pdf_name
            pdf_name=$(echo "$folder_name" | tr '-' ' ')
            
            # Find source PDF
            local pdf_path=""
            for ext in pdf PDF; do
                if [[ -f "$RAW_PDF_DIR/$pdf_name.$ext" ]]; then
                    pdf_path="$RAW_PDF_DIR/$pdf_name.$ext"
                    break
                fi
            done
            
            if [[ -n "$pdf_path" ]]; then
                rm -rf "$folder"
                process_pdf "$pdf_path"
            fi
        done
        return 0
    fi
    
    if [[ "$choice" =~ ^[0-9]+$ ]] && (( choice >= 1 && choice <= ${#folders[@]} )); then
        local folder="${folders[$((choice-1))]}"
        local folder_name
        folder_name=$(basename "$folder")
        local pdf_name
        pdf_name=$(echo "$folder_name" | tr '-' ' ')
        
        # Find source PDF
        local pdf_path=""
        for ext in pdf PDF; do
            if [[ -f "$RAW_PDF_DIR/$pdf_name.$ext" ]]; then
                pdf_path="$RAW_PDF_DIR/$pdf_name.$ext"
                break
            fi
        done
        
        if [[ -z "$pdf_path" ]]; then
            print_error "Source PDF not found for: $folder_name"
            return 1
        fi
        
        rm -rf "$folder"
        process_pdf "$pdf_path"
    fi
}

# Function to list raw PDFs
list_raw_pdfs() {
    print_header "Raw PDFs in $RAW_PDF_DIR"
    
    local pdfs=()
    local total_size=0
    
    while IFS= read -r -d '' pdf; do
        pdfs+=("$pdf")
        local size
        size=$(stat -f%z "$pdf" 2>/dev/null || stat -c%s "$pdf" 2>/dev/null || echo "0")
        ((total_size += size))
    done < <(find "$RAW_PDF_DIR" -maxdepth 1 -type f \( -iname "*.pdf" \) -print0 2>/dev/null | sort -z)
    
    if [[ ${#pdfs[@]} -eq 0 ]]; then
        print_warning "No PDFs found"
        echo ""
        echo "Place PDF files in: $RAW_PDF_DIR"
        return 1
    fi
    
    printf "  %-5s %-40s %10s %15s\n" "No." "Filename" "Size" "Processed"
    echo "  $(printf '%*s' 75 '' | tr ' ' '-')"
    
    local i=1
    for pdf in "${pdfs[@]}"; do
        local basename
        basename=$(get_pdf_basename "$pdf")
        local size
        size=$(du -h "$pdf" 2>/dev/null | cut -f1 || echo "?")
        
        local folder_name
        folder_name=$(sanitize_folder_name "$basename")
        local processed="${RED}No${NC}"
        [[ -d "$READ_USE_DIR/$folder_name" ]] && processed="${GREEN}Yes${NC}"
        
        printf "  %-5d %-40s %10s %15b\n" "$i" "$basename" "$size" "$processed"
        ((i++))
    done
    
    echo ""
    local total_mb
    total_mb=$(echo "scale=2; $total_size / 1024 / 1024" | bc 2>/dev/null || echo "$((total_size / 1024 / 1024))")
    print_info "Total: ${#pdfs[@]} PDF(s), ${total_mb} MB"
}

# Function to open output folder
open_output_folder() {
    print_info "Opening: $READ_USE_DIR"
    
    if [[ "$OSTYPE" == "darwin"* ]]; then
        open "$READ_USE_DIR"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        xdg-open "$READ_USE_DIR" 2>/dev/null || nautilus "$READ_USE_DIR" 2>/dev/null || print_info "Please open: $READ_USE_DIR"
    else
        print_info "Please open: $READ_USE_DIR"
    fi
}

# Function to export to SQL-Adapt
export_to_sqladapt_menu() {
    print_header "Export to SQL-Adapt"
    
    # Show current export status
    local sqladapt_dir="/Users/harrydai/Desktop/Personal Portfolio/adaptive-instructional-artifacts/apps/web/public/textbook-static"
    local current_concepts=0
    local current_pdfs=0
    
    if [[ -f "$sqladapt_dir/concept-map.json" ]]; then
        current_concepts=$(grep -o '"sourceDocId"' "$sqladapt_dir/concept-map.json" 2>/dev/null | wc -l)
        current_pdfs=$(grep -o '"sourceDocIds"' "$sqladapt_dir/concept-map.json" 2>/dev/null | wc -l)
        print_info "Current export status:"
        echo "  📚 PDFs exported: $current_pdfs"
        echo "  📖 Total concepts: $current_concepts"
        echo ""
    fi
    
    # Find processed PDFs with concept manifests
    local folders=()
    local exported_pdfs=()
    
    while IFS= read -r -d '' folder; do
        if [[ -f "$folder/concept-manifest.json" ]]; then
            local folder_name
            folder_name=$(basename "$folder")
            folders+=("$folder")
            
            # Check if already exported
            if [[ -d "$sqladapt_dir/concepts/$folder_name" ]]; then
                exported_pdfs+=("✓")
            else
                exported_pdfs+=(" ")
            fi
        fi
    done < <(find "$READ_USE_DIR" -maxdepth 1 -type d ! -path "$READ_USE_DIR" -print0 2>/dev/null | sort -z)
    
    if [[ ${#folders[@]} -eq 0 ]]; then
        print_error "No processed PDFs with concept manifests found"
        print_info "Process a PDF with a concepts.yaml file first"
        return 1
    fi
    
    echo "Available for export:"
    echo "  (✓ = already exported, will be updated)"
    echo ""
    
    local i=1
    for idx in "${!folders[@]}"; do
        local folder="${folders[$idx]}"
        local folder_name
        folder_name=$(basename "$folder")
        local concept_count
        concept_count=$(find "$folder/concepts" -name "*.md" 2>/dev/null | wc -l)
        local status="${exported_pdfs[$idx]}"
        printf "  %2d) [%s] %-30s (%s concepts)\n" "$i" "$status" "$folder_name" "$concept_count"
        ((i++))
    done
    
    echo ""
    echo "  A) Export/Update All"
    echo "  0) Go Back"
    echo ""
    
    read -p "Select PDF to export [0-${#folders[@]}/A]: " choice
    
    if [[ "$choice" == "0" ]]; then
        return 0
    fi
    
    # Export all
    if [[ "$choice" =~ ^[Aa]$ ]]; then
        for folder in "${folders[@]}"; do
            local folder_name
            folder_name=$(basename "$folder")
            
            print_header "Exporting: $folder_name"
            
            local venv_python_export="$SCRIPT_DIR/.venv/bin/python"
            if "$venv_python_export" -m algl_pdf_helper export "$folder"; then
                print_success "Exported: $folder_name"
            else
                print_error "Failed: $folder_name"
            fi
            echo ""
        done
        
        print_header "Export Summary"
        print_info "Output: $sqladapt_dir"
        if [[ -f "$sqladapt_dir/concept-map.json" ]]; then
            local total_concepts
            total_concepts=$(grep -c '"title"' "$sqladapt_dir/concept-map.json" 2>/dev/null || echo "0")
            print_info "Total concepts exported: $total_concepts"
        fi
        echo ""
        read -p "Press Enter to continue..."
        return 0
    fi
    
    # Export single
    if [[ "$choice" =~ ^[0-9]+$ ]] && (( choice >= 1 && choice <= ${#folders[@]} )); then
        local folder="${folders[$((choice-1))]}"
        local folder_name
        folder_name=$(basename "$folder")
        
        print_info "Exporting $folder_name to SQL-Adapt..."
        
        local venv_python_export="$SCRIPT_DIR/.venv/bin/python"
        if "$venv_python_export" -m algl_pdf_helper export "$folder"; then
            print_success "Export complete!"
            print_info "Output: $sqladapt_dir"
            
            # Show current status
            if [[ -f "$sqladapt_dir/concept-map.json" ]]; then
                local total_concepts
                total_concepts=$(grep -c '"title"' "$sqladapt_dir/concept-map.json" 2>/dev/null || echo "0")
                print_info "Total concepts in export: $total_concepts"
            fi
        else
            print_error "Export failed!"
        fi
        
        echo ""
        read -p "Press Enter to continue..."
    fi
}

# Function to export educational notes to SQL-Adapt
export_educational_to_sqladapt_menu() {
    print_header "Export Educational Notes to SQL-Adapt"
    
    local sqladapt_dir="/Users/harrydai/Desktop/Personal Portfolio/adaptive-instructional-artifacts/apps/web/public/textbook-static"
    
    # Check dependencies
    local venv_python="$SCRIPT_DIR/.venv/bin/python"
    local has_marker=false
    local has_openai=false
    
    if "$venv_python" -c "import marker" 2>/dev/null; then
        has_marker=true
    fi
    
    if "$venv_python" -c "import openai" 2>/dev/null; then
        has_openai=true
    fi
    
    print_info "Pipeline Status:"
    if [[ "$has_marker" == "true" ]]; then
        echo "  ✅ Marker (PDF extraction): Available"
    else
        echo "  ⚠️  Marker (PDF extraction): Not installed"
        echo "      Install: pip install marker-pdf"
    fi
    
    if [[ "$has_openai" == "true" ]]; then
        echo "  ✅ OpenAI SDK: Available"
    else
        echo "  ⚠️  OpenAI SDK: Not installed"
        echo "      Install: pip install openai"
    fi
    
    # Check API keys
    if [[ -n "$OPENAI_API_KEY" ]]; then
        echo "  ✅ OPENAI_API_KEY: Set"
    fi
    
    if [[ -n "$KIMI_API_KEY" ]] || [[ -n "$MOONSHOT_API_KEY" ]]; then
        echo "  ✅ KIMI_API_KEY: Set"
    fi
    
    # Show cost comparison
    echo ""
    echo "💰 Cost Comparison (per concept, RMB):"
    echo "  Kimi (moonshot-v1-8k):  ¥0.066  ⭐ Cheapest"
    echo "  OpenAI (gpt-4o-mini):   ¥1.100  (~17x more)"
    echo ""
    
    if [[ -z "$KIMI_API_KEY" ]] && [[ -z "$MOONSHOT_API_KEY" ]] && [[ -z "$OPENAI_API_KEY" ]]; then
        print_warning "No LLM API key set!"
        echo ""
        echo "Recommend: Use Kimi (cheapest, China-based)"
        echo "  1. Get key: https://platform.moonshot.cn/"
        echo "  2. Set key: export KIMI_API_KEY='sk-your-key'"
        echo ""
    fi
    
    # List raw PDFs (can process directly without pre-processing)
    local pdfs=()
    while IFS= read -r -d '' pdf; do
        pdfs+=("$pdf")
    done < <(find "$RAW_PDF_DIR" -maxdepth 1 -type f \( -iname "*.pdf" \) -print0 2>/dev/null | sort -z)
    
    if [[ ${#pdfs[@]} -eq 0 ]]; then
        print_error "No PDFs found in $RAW_PDF_DIR"
        return 1
    fi
    
    print_info "Available PDFs for educational export:"
    echo ""
    
    local i=1
    for pdf in "${pdfs[@]}"; do
        local basename
        basename=$(get_pdf_basename "$pdf")
        local size
        size=$(du -h "$pdf" 2>/dev/null | cut -f1 || echo "?")
        printf "  %2d) %-40s (%s)\n" "$i" "$basename" "$size"
        ((i++))
    done
    
    echo ""
    echo "  0) Go Back"
    echo ""
    
    read -p "Select PDF to export [0-${#pdfs[@]}]: " choice
    
    if [[ "$choice" == "0" ]]; then
        return 0
    fi
    
    if [[ "$choice" =~ ^[0-9]+$ ]] && (( choice >= 1 && choice <= ${#pdfs[@]} )); then
        local pdf_path="${pdfs[$((choice-1))]}"
        local pdf_name
        pdf_name=$(get_pdf_basename "$pdf_path")
        
        print_header "Exporting Educational Notes: $pdf_name"
        
        # Choose LLM provider
        local llm_provider="kimi"
        local llm_key_set=false
        
        if [[ -n "$KIMI_API_KEY" ]] || [[ -n "$MOONSHOT_API_KEY" ]]; then
            llm_key_set=true
            llm_provider="kimi"
        elif [[ -n "$OPENAI_API_KEY" ]]; then
            llm_key_set=true
            llm_provider="openai"
        fi
        
        # If both keys available, let user choose
        if [[ -n "$KIMI_API_KEY" ]] && [[ -n "$OPENAI_API_KEY" ]]; then
            echo ""
            echo "Select LLM Provider:"
            echo "  1) Kimi (Moonshot) - ¥0.066/concept ⭐ Cheapest"
            echo "  2) OpenAI (GPT-4o-mini) - ¥1.100/concept"
            echo ""
            read -p "Select [1-2, default=1]: " provider_choice
            
            if [[ "$provider_choice" == "2" ]]; then
                llm_provider="openai"
            else
                llm_provider="kimi"
            fi
            echo ""
        fi
        
        # Show cost estimate
        echo "💰 Estimated Cost:"
        if [[ "$llm_provider" == "kimi" ]]; then
            echo "  Kimi (moonshot-v1-8k): ~¥2.00 for 30 concepts"
            echo "  (~¥0.07 per concept)"
        else
            echo "  OpenAI (gpt-4o-mini): ~¥33.00 for 30 concepts"
            echo "  (~¥1.10 per concept)"
        fi
        echo ""
        
        print_info "This will:"
        echo "  1. Extract PDF content using Marker (high quality)"
        echo "  2. Generate educational notes with $llm_provider LLM"
        echo "  3. Export to SQL-Adapt format"
        echo ""
        
        read -p "Continue? [Y/n]: " confirm
        if [[ "$confirm" =~ ^[Nn]$ ]]; then
            return 0
        fi
        echo ""
        
        print_info "Command: algl-pdf export-edu $pdf_path --output-dir $sqladapt_dir"
        echo ""
        
        # Set provider environment variable for the command
        export EDUCATIONAL_LLM_PROVIDER="$llm_provider"
        
        if "$venv_python" -m algl_pdf_helper export-edu "$pdf_path" --output-dir "$sqladapt_dir"; then
            print_success "Educational export complete!"
            print_info "Output: $sqladapt_dir"
            
            # Show generated files
            if [[ -d "$sqladapt_dir" ]]; then
                echo ""
                echo "Generated files:"
                ls -1 "$sqladapt_dir" | grep "$(echo "$pdf_name" | tr '[:upper:]' '[:lower:]' | tr -cs 'a-z0-9' '-')" | head -10 | sed 's/^/  - /'
            fi
        else
            print_error "Export failed!"
            print_info "Check that dependencies are installed:"
            echo "  pip install marker-pdf openai"
            echo ""
            print_info "For Kimi (cheapest):"
            echo "  1. Get API key: https://platform.moonshot.cn/"
            echo "  2. Set: export KIMI_API_KEY='sk-your-key'"
        fi
        
        echo ""
        read -p "Press Enter to continue..."
    fi
}

# Main loop
main() {
    # Check/create directories
    mkdir -p "$RAW_PDF_DIR" "$READ_USE_DIR"
    
    # Check virtual environment
    check_venv
    
    # Check OCR dependencies
    check_ocr_deps
    
    # Check educational pipeline dependencies (optional)
    check_edu_deps
    
    # Welcome message
    print_header "ALGL PDF Helper v$(python3 -c "from algl_pdf_helper import __version__; print(__version__)" 2>/dev/null || echo "0.1.0")"
    print_info "Raw PDF folder:  $RAW_PDF_DIR"
    print_info "Output folder:   $READ_USE_DIR"
    
    while true; do
        show_main_menu
        read -p "Select option [1-9]: " choice
        
        case $choice in
            1)
                if show_pdf_menu; then
                    process_pdf "$SELECTED_PDF"
                    echo ""
                    read -p "Press Enter to continue..."
                fi
                ;;
            2)
                process_all_pdfs
                echo ""
                read -p "Press Enter to continue..."
                ;;
            3)
                reprocess_existing
                echo ""
                read -p "Press Enter to continue..."
                ;;
            4)
                list_raw_pdfs
                echo ""
                read -p "Press Enter to continue..."
                ;;
            5)
                open_output_folder
                sleep 1
                ;;
            6)
                export_to_sqladapt_menu
                ;;
            7)
                export_educational_to_sqladapt_menu
                ;;
            8)
                show_options_menu
                ;;
            9)
                print_info "Goodbye!"
                exit 0
                ;;
            *)
                print_error "Invalid option"
                sleep 1
                ;;
        esac
    done
}

# Run main
main "$@"
