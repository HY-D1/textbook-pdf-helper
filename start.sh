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
    if [[ -z "${VIRTUAL_ENV}" ]]; then
        if [[ -d "$SCRIPT_DIR/.venv" ]]; then
            print_info "Activating virtual environment..."
            source "$SCRIPT_DIR/.venv/bin/activate"
        else
            print_warning "Virtual environment not found. Creating one..."
            python3 -m venv "$SCRIPT_DIR/.venv"
            source "$SCRIPT_DIR/.venv/bin/activate"
        fi
    fi
    
    # Always ensure package is installed
    if ! python3 -c "import algl_pdf_helper" 2>/dev/null; then
        print_info "Installing algl-pdf-helper package..."
        pip install -q -e "$SCRIPT_DIR"
    fi
    
    # Verify installation
    if ! python3 -c "import algl_pdf_helper" 2>/dev/null; then
        print_error "Failed to install algl-pdf-helper package"
        exit 1
    fi
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
    echo "6) ⚙️  Advanced Options"
    echo "7) 🚪 Exit"
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
    if [[ -z "${VIRTUAL_ENV}" ]] || ! python3 -c "import algl_pdf_helper" 2>/dev/null; then
        if [[ -f "$SCRIPT_DIR/.venv/bin/activate" ]]; then
            source "$SCRIPT_DIR/.venv/bin/activate"
        fi
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
    
    print_info "Command: algl-pdf index $pdf_path --out $output_dir $cmd_args"
    echo ""
    
    # Run processing - use full path to ensure we use venv version
    local algl_pdf_cmd
    if [[ -n "$VIRTUAL_ENV" ]] && [[ -f "$VIRTUAL_ENV/bin/algl-pdf" ]]; then
        algl_pdf_cmd="$VIRTUAL_ENV/bin/algl-pdf"
    else
        algl_pdf_cmd="algl-pdf"
    fi
    
    if "$algl_pdf_cmd" index "$pdf_path" --out "$output_dir" $cmd_args; then
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

# Main loop
main() {
    # Check/create directories
    mkdir -p "$RAW_PDF_DIR" "$READ_USE_DIR"
    
    # Check virtual environment
    check_venv
    
    # Check OCR dependencies
    check_ocr_deps
    
    # Welcome message
    print_header "ALGL PDF Helper v$(python3 -c "from algl_pdf_helper import __version__; print(__version__)" 2>/dev/null || echo "0.1.0")"
    print_info "Raw PDF folder:  $RAW_PDF_DIR"
    print_info "Output folder:   $READ_USE_DIR"
    
    while true; do
        show_main_menu
        read -p "Select option [1-7]: " choice
        
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
                show_options_menu
                ;;
            7)
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
