from __future__ import annotations

import json
import re
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Literal

import fitz  # PyMuPDF

if TYPE_CHECKING:
    from .models import AssetManifest, ExtractedAsset


ASSET_TYPES = Literal["image", "table"]


@dataclass
class ExtractedAsset:
    """Represents an extracted asset (image or table) from a PDF."""
    
    id: str  # e.g., "page-001-fig-01" or "page-001-table-01"
    type: ASSET_TYPES  # "image" or "table"
    page: int
    bbox: tuple[float, float, float, float]  # (x0, y0, x1, y1)
    doc_id: str
    format: str  # e.g., "png" for images, "html" for tables
    caption: str = ""
    content: bytes | str = field(default=b"")  # Image bytes or table HTML/markdown
    metadata: dict = field(default_factory=dict)

    def get_relative_path(self) -> str:
        """Get the relative path for this asset following naming conventions."""
        return f"{self.get_asset_dir()}/{self.get_filename()}"
    
    def get_asset_dir(self) -> str:
        """Get the asset directory (without filename)."""
        if self.type == "image":
            return f"assets/images/{self.doc_id}"
        else:  # table
            return f"assets/tables/{self.doc_id}"

    def get_filename(self) -> str:
        """Get the filename for this asset."""
        page_str = f"page-{self.page:03d}"
        
        if self.type == "image":
            # Parse figure number from id (e.g., "fig-01" from "page-001-fig-01")
            parts = self.id.split("-")
            if len(parts) >= 4 and parts[-2] == "fig":
                fig_num = parts[-1]
                return f"{page_str}-fig-{fig_num}.png"
            return f"{page_str}-{self.id}.png"
        else:  # table
            # Parse table number from id (e.g., "table-01" from "page-001-table-01")
            parts = self.id.split("-")
            if len(parts) >= 4 and parts[-2] == "table":
                table_num = parts[-1]
                return f"{page_str}-table-{table_num}.html"
            return f"{page_str}-{self.id}.html"
    
    def to_asset_reference(self) -> "AssetReference":
        """Convert this extracted asset to an AssetReference for manifests."""
        from .models import AssetReference
        
        ref = AssetReference(
            id=self.id,
            type=self.type,
            path=self.get_relative_path(),
            pageNumber=self.page,
            caption=self.caption,
        )
        
        # Add dimensions if available in metadata
        if self.metadata:
            if "width" in self.metadata:
                ref.width = self.metadata["width"]
            if "height" in self.metadata:
                ref.height = self.metadata["height"]
            if "extracted_text" in self.metadata:
                ref.extractedText = self.metadata["extracted_text"]
        
        return ref


class AssetExtractor:
    """Extracts images and tables from PDFs using PyMuPDF or Marker backends."""
    
    def __init__(self, backend: Literal["pymupdf", "marker"] = "pymupdf"):
        """Initialize the asset extractor.
        
        Args:
            backend: The extraction backend to use ("pymupdf" or "marker")
        """
        self.backend = backend
        self._image_counter: dict[int, int] = {}
        self._table_counter: dict[int, int] = {}
    
    def _reset_counters(self) -> None:
        """Reset page counters for a new extraction."""
        self._image_counter = {}
        self._table_counter = {}
    
    def _generate_image_id(self, page: int) -> str:
        """Generate a unique image ID for the page."""
        self._image_counter[page] = self._image_counter.get(page, 0) + 1
        return f"page-{page:03d}-fig-{self._image_counter[page]:02d}"
    
    def _generate_table_id(self, page: int) -> str:
        """Generate a unique table ID for the page."""
        self._table_counter[page] = self._table_counter.get(page, 0) + 1
        return f"page-{page:03d}-table-{self._table_counter[page]:02d}"
    
    def extract_images(
        self,
        pdf_path: Path,
        doc_id: str,
        min_width: int = 50,
        min_height: int = 50,
    ) -> list[ExtractedAsset]:
        """Extract images from a PDF file.
        
        Args:
            pdf_path: Path to the PDF file
            doc_id: Document ID for asset naming
            min_width: Minimum image width to extract (filters out icons)
            min_height: Minimum image height to extract
            
        Returns:
            List of extracted image assets
        """
        self._reset_counters()
        
        if self.backend == "pymupdf":
            return self._extract_images_pymupdf(pdf_path, doc_id, min_width, min_height)
        elif self.backend == "marker":
            return self._extract_images_marker(pdf_path, doc_id, min_width, min_height)
        else:
            raise ValueError(f"Unknown backend: {self.backend}")
    
    def _extract_images_pymupdf(
        self,
        pdf_path: Path,
        doc_id: str,
        min_width: int,
        min_height: int,
    ) -> list[ExtractedAsset]:
        """Extract images using PyMuPDF."""
        assets: list[ExtractedAsset] = []
        doc = fitz.open(pdf_path)
        
        try:
            for page_num in range(doc.page_count):
                page = doc.load_page(page_num)
                page_number = page_num + 1  # 1-indexed
                
                # Get image list
                image_list = page.get_images(full=True)
                
                for img_index, img in enumerate(image_list):
                    xref = img[0]
                    
                    try:
                        # Extract image
                        base_image = doc.extract_image(xref)
                        image_bytes = base_image["image"]
                        image_ext = base_image["ext"]
                        
                        # Get image dimensions from the page
                        # Try to find the bbox for this image
                        bbox = self._find_image_bbox(page, xref)
                        
                        # Skip small images (likely icons)
                        if bbox:
                            width = bbox[2] - bbox[0]
                            height = bbox[3] - bbox[1]
                            if width < min_width or height < min_height:
                                continue
                        
                        # Convert to PNG if needed
                        if image_ext != "png":
                            image_bytes = self._convert_to_png(image_bytes)
                        
                        asset_id = self._generate_image_id(page_number)
                        
                        # Try to find caption
                        caption = self._find_caption(page, bbox) if bbox else ""
                        
                        asset = ExtractedAsset(
                            id=asset_id,
                            type="image",
                            page=page_number,
                            bbox=bbox or (0, 0, 0, 0),
                            doc_id=doc_id,
                            format="png",
                            caption=caption,
                            content=image_bytes,
                            metadata={
                                "original_ext": image_ext,
                                "xref": xref,
                            },
                        )
                        assets.append(asset)
                        
                    except Exception as e:
                        # Skip problematic images
                        continue
                        
        finally:
            doc.close()
        
        return assets
    
    def _find_image_bbox(
        self,
        page: fitz.Page,
        xref: int,
    ) -> tuple[float, float, float, float] | None:
        """Find the bounding box of an image on a page."""
        # Get all drawings and images on the page
        rect = None
        
        # Check for images in page content
        for img in page.get_images(full=True):
            if img[0] == xref:
                # Try to find the bbox from page blocks
                blocks = page.get_text("dict")["blocks"]
                for block in blocks:
                    if block.get("type") == 1:  # Image block
                        # This is an image block
                        bbox = block.get("bbox")
                        if bbox:
                            return (bbox[0], bbox[1], bbox[2], bbox[3])
        
        # Fallback: use page rect
        return None
    
    def _convert_to_png(self, image_bytes: bytes) -> bytes:
        """Convert image bytes to PNG format.
        
        Handles various image modes including CMYK, RGBA, and palette-based images.
        CMYK images are converted to RGB since PNG doesn't support CMYK.
        """
        try:
            from PIL import Image
            import io
            
            img = Image.open(io.BytesIO(image_bytes))
            
            # Convert to RGB if necessary (PNG only supports RGB/RGBA/L modes)
            # CMYK must be converted to RGB since PNG doesn't support CMYK
            if img.mode == "RGBA":
                # Preserve transparency by creating RGB with white background
                background = Image.new("RGB", img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[3])  # 3 is alpha channel
                img = background
            elif img.mode in ("CMYK", "P", "LA", "L"):
                # Convert all other modes to RGB
                img = img.convert("RGB")
            
            output = io.BytesIO()
            img.save(output, format="PNG")
            return output.getvalue()
        except Exception:
            # If conversion fails for any reason, return original bytes
            # This ensures we don't lose data even if conversion fails
            return image_bytes
    
    def _find_caption(
        self,
        page: fitz.Page,
        bbox: tuple[float, float, float, float] | None,
    ) -> str:
        """Try to find a caption for an image/table near the given bbox."""
        if not bbox:
            return ""
        
        # Look for text below the image
        caption_area = fitz.Rect(
            bbox[0],
            bbox[3],
            bbox[2],
            bbox[3] + 30,  # 30 points below
        )
        
        caption_text = page.get_text("text", clip=caption_area)
        caption_text = caption_text.strip()
        
        # Look for common caption patterns
        caption_patterns = [
            r"^(Figure|Fig\.?|Table)\s+\d+[.:]?\s*(.+)$",
            r"^(Figure|Fig\.?|Table)\s+\d+$",
        ]
        
        for pattern in caption_patterns:
            match = re.match(pattern, caption_text, re.IGNORECASE)
            if match:
                return caption_text
        
        # If no pattern match, return first line if it looks like a caption
        first_line = caption_text.split("\n")[0] if caption_text else ""
        if len(first_line) < 200 and ("figure" in first_line.lower() or "table" in first_line.lower()):
            return first_line
        
        return ""
    
    def _extract_images_marker(
        self,
        pdf_path: Path,
        doc_id: str,
        min_width: int,
        min_height: int,
    ) -> list[ExtractedAsset]:
        """Extract images using Marker backend."""
        # Marker integration - requires marker library
        try:
            from marker.convert import convert_single_pdf
            from marker.models import load_all_models
        except ImportError:
            raise RuntimeError(
                "Marker backend requested but marker is not installed. "
                "Install with: pip install marker-pdf"
            )
        
        assets: list[ExtractedAsset] = []
        
        # Load models (this is slow, so ideally cached)
        model_dict = load_all_models()
        
        # Convert PDF
        full_text, images, out_meta = convert_single_pdf(
            str(pdf_path),
            model_dict,
        )
        
        # Process extracted images
        for img_name, img_bytes in images.items():
            try:
                # Try to determine page from image metadata or name
                page_num = self._extract_page_from_image_name(img_name)
                
                # Convert to PNG if needed
                img_bytes = self._convert_to_png(img_bytes)
                
                asset_id = self._generate_image_id(page_num)
                
                asset = ExtractedAsset(
                    id=asset_id,
                    type="image",
                    page=page_num,
                    bbox=(0, 0, 0, 0),  # Marker doesn't provide bbox
                    doc_id=doc_id,
                    format="png",
                    content=img_bytes,
                    metadata={
                        "original_name": img_name,
                        "source": "marker",
                    },
                )
                assets.append(asset)
                
            except Exception:
                continue
        
        return assets
    
    def _extract_page_from_image_name(self, img_name: str) -> int:
        """Try to extract page number from Marker image name."""
        # Marker names images like "page_001_img_001.png"
        match = re.search(r"page[_-](\d+)", img_name, re.IGNORECASE)
        if match:
            return int(match.group(1))
        return 1  # Default to page 1
    
    def extract_tables(
        self,
        pdf_path: Path,
        doc_id: str,
    ) -> list[ExtractedAsset]:
        """Extract tables from a PDF file.
        
        Args:
            pdf_path: Path to the PDF file
            doc_id: Document ID for asset naming
            
        Returns:
            List of extracted table assets
        """
        self._reset_counters()
        
        if self.backend == "pymupdf":
            return self._extract_tables_pymupdf(pdf_path, doc_id)
        elif self.backend == "marker":
            return self._extract_tables_marker(pdf_path, doc_id)
        else:
            raise ValueError(f"Unknown backend: {self.backend}")
    
    def _extract_tables_pymupdf(
        self,
        pdf_path: Path,
        doc_id: str,
    ) -> list[ExtractedAsset]:
        """Extract tables using PyMuPDF."""
        assets: list[ExtractedAsset] = []
        doc = fitz.open(pdf_path)
        
        try:
            for page_num in range(doc.page_count):
                page = doc.load_page(page_num)
                page_number = page_num + 1
                
                # Find tables
                tables = page.find_tables()
                
                if tables and tables.tables:
                    for table_idx, table in enumerate(tables.tables):
                        try:
                            # Extract table data
                            df = table.to_pandas()
                            
                            # Convert to HTML
                            html_content = self._dataframe_to_html(df, table_idx + 1)
                            
                            asset_id = self._generate_table_id(page_number)
                            
                            # Try to find caption
                            bbox = table.bbox
                            caption = self._find_caption(page, bbox) if bbox else ""
                            
                            asset = ExtractedAsset(
                                id=asset_id,
                                type="table",
                                page=page_number,
                                bbox=bbox if bbox else (0, 0, 0, 0),
                                doc_id=doc_id,
                                format="html",
                                caption=caption,
                                content=html_content,
                                metadata={
                                    "rows": len(df),
                                    "cols": len(df.columns),
                                    "source": "pymupdf",
                                },
                            )
                            assets.append(asset)
                            
                        except Exception:
                            continue
                            
        finally:
            doc.close()
        
        return assets
    
    def _dataframe_to_html(self, df: "pandas.DataFrame", table_num: int) -> str:
        """Convert a pandas DataFrame to styled HTML table."""
        # Handle multi-index if present
        html = df.to_html(
            index=False,
            border=1,
            classes=["pdf-table"],
            escape=False,
        )
        
        # Wrap with figure element for styling
        wrapped_html = f"""<figure class="table-figure">
{html}
<figcaption>Table {table_num}</figcaption>
</figure>"""
        
        return wrapped_html
    
    def _extract_tables_marker(
        self,
        pdf_path: Path,
        doc_id: str,
    ) -> list[ExtractedAsset]:
        """Extract tables using Marker backend."""
        try:
            from marker.convert import convert_single_pdf
            from marker.models import load_all_models
        except ImportError:
            raise RuntimeError(
                "Marker backend requested but marker is not installed."
            )
        
        assets: list[ExtractedAsset] = []
        
        # Marker includes tables in the markdown output
        model_dict = load_all_models()
        full_text, images, out_meta = convert_single_pdf(
            str(pdf_path),
            model_dict,
        )
        
        # Parse markdown for tables
        # Marker outputs tables in markdown format
        table_pattern = r'\|[^\n]+\|\n\|[-:\| ]+\|\n(?:\|[^\n]+\|\n?)+'
        
        for match in re.finditer(table_pattern, full_text):
            table_md = match.group(0)
            
            # Convert markdown table to HTML
            html_content = self._markdown_table_to_html(table_md)
            
            # Try to determine page (Marker doesn't provide this directly)
            page_number = 1
            
            asset_id = self._generate_table_id(page_number)
            
            asset = ExtractedAsset(
                id=asset_id,
                type="table",
                page=page_number,
                bbox=(0, 0, 0, 0),
                doc_id=doc_id,
                format="html",
                content=html_content,
                metadata={
                    "source": "marker",
                },
            )
            assets.append(asset)
        
        return assets
    
    def _markdown_table_to_html(self, markdown_table: str) -> str:
        """Convert a markdown table to HTML."""
        lines = markdown_table.strip().split("\n")
        if len(lines) < 2:
            return ""
        
        # Parse header
        headers = [cell.strip() for cell in lines[0].split("|") if cell.strip()]
        
        # Skip separator line
        # Parse rows
        rows = []
        for line in lines[2:]:
            cells = [cell.strip() for cell in line.split("|") if cell.strip()]
            if cells:
                rows.append(cells)
        
        # Build HTML
        html_parts = ['<table class="pdf-table">', "<thead>", "<tr>"]
        for header in headers:
            html_parts.append(f"<th>{header}</th>")
        html_parts.extend(["</tr>", "</thead>", "<tbody>"])
        
        for row in rows:
            html_parts.append("<tr>")
            for cell in row[:len(headers)]:
                html_parts.append(f"<td>{cell}</td>")
            html_parts.append("</tr>")
        
        html_parts.extend(["</tbody>", "</table>"])
        
        return "".join(html_parts)
    
    def save_assets(
        self,
        assets: list[ExtractedAsset],
        output_dir: Path,
    ) -> list[Path]:
        """Save extracted assets to the output directory.
        
        Args:
            assets: List of assets to save
            output_dir: Base output directory
            
        Returns:
            List of paths to saved files
        """
        saved_paths: list[Path] = []
        
        for asset in assets:
            # Determine subdirectory based on type
            if asset.type == "image":
                asset_dir = output_dir / "assets" / "images" / asset.doc_id
            else:  # table
                asset_dir = output_dir / "assets" / "tables" / asset.doc_id
            
            asset_dir.mkdir(parents=True, exist_ok=True)
            
            # Get filename
            filename = asset.get_filename()
            file_path = asset_dir / filename
            
            # Save content
            if isinstance(asset.content, bytes):
                file_path.write_bytes(asset.content)
            else:
                file_path.write_text(str(asset.content), encoding="utf-8")
            
            saved_paths.append(file_path)
        
        return saved_paths


def extract_assets_from_pdf(
    pdf_path: Path,
    doc_id: str,
    output_dir: Path,
    backend: Literal["pymupdf", "marker"] = "pymupdf",
    extract_images: bool = True,
    extract_tables: bool = True,
) -> dict[str, list[ExtractedAsset]]:
    """Convenience function to extract and save all assets from a PDF.
    
    Args:
        pdf_path: Path to the PDF file
        doc_id: Document ID for asset naming
        output_dir: Base output directory
        backend: Extraction backend to use
        extract_images: Whether to extract images
        extract_tables: Whether to extract tables
        
    Returns:
        Dictionary with "images" and "tables" keys containing extracted assets
    """
    extractor = AssetExtractor(backend=backend)
    result: dict[str, list[ExtractedAsset]] = {
        "images": [],
        "tables": [],
    }
    
    if extract_images:
        images = extractor.extract_images(pdf_path, doc_id)
        extractor.save_assets(images, output_dir)
        result["images"] = images
    
    if extract_tables:
        tables = extractor.extract_tables(pdf_path, doc_id)
        extractor.save_assets(tables, output_dir)
        result["tables"] = tables
    
    return result
