from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal


@dataclass
class TableCell:
    """Represents a single cell in a table."""
    content: str
    rowspan: int = 1
    colspan: int = 1
    align: Literal["left", "center", "right"] = "left"
    is_header: bool = False


@dataclass
class TableRow:
    """Represents a row in a table."""
    cells: list[TableCell]


@dataclass
class TableData:
    """Represents structured table data."""
    headers: list[TableCell] | None = None
    rows: list[TableRow] = None
    caption: str = ""
    
    def __post_init__(self):
        if self.rows is None:
            self.rows = []


class TableConverter:
    """Converts PDF tables to HTML or Markdown format with proper formatting."""
    
    def __init__(self):
        self._table_count = 0
    
    def reset_counter(self) -> None:
        """Reset the table counter."""
        self._table_count = 0
    
    def _get_next_table_num(self) -> int:
        """Get the next table number."""
        self._table_count += 1
        return self._table_count
    
    def convert_to_html(
        self,
        data: TableData,
        table_id: str | None = None,
        add_figure_wrap: bool = True,
    ) -> str:
        """Convert table data to HTML.
        
        Args:
            data: Structured table data
            table_id: Optional ID for the table element
            add_figure_wrap: Whether to wrap in figure element with caption
            
        Returns:
            HTML string
        """
        table_num = self._get_next_table_num()
        
        html_parts: list[str] = []
        
        # Start table
        id_attr = f' id="{table_id}"' if table_id else ""
        html_parts.append(f'<table class="pdf-table"{id_attr}>')
        
        # Add header row
        if data.headers:
            html_parts.append("<thead>")
            html_parts.append("<tr>")
            for cell in data.headers:
                html_parts.append(self._render_header_cell(cell))
            html_parts.append("</tr>")
            html_parts.append("</thead>")
        
        # Add body rows
        if data.rows:
            html_parts.append("<tbody>")
            for row in data.rows:
                html_parts.append("<tr>")
                for cell in row.cells:
                    html_parts.append(self._render_body_cell(cell))
                html_parts.append("</tr>")
            html_parts.append("</tbody>")
        
        html_parts.append("</table>")
        
        table_html = "\n".join(html_parts)
        
        # Wrap in figure if requested
        if add_figure_wrap:
            caption_text = data.caption or f"Table {table_num}"
            table_html = f"""<figure class="table-figure">
{table_html}
<figcaption>{caption_text}</figcaption>
</figure>"""
        
        return table_html
    
    def _render_header_cell(self, cell: TableCell) -> str:
        """Render a header cell as HTML."""
        attrs: list[str] = []
        
        if cell.rowspan > 1:
            attrs.append(f'rowspan="{cell.rowspan}"')
        if cell.colspan > 1:
            attrs.append(f'colspan="{cell.colspan}"')
        if cell.align != "left":
            attrs.append(f'align="{cell.align}"')
        
        attr_str = " ".join(attrs)
        if attr_str:
            attr_str = " " + attr_str
        
        content = self._escape_html(cell.content)
        return f"<th{attr_str}>{content}</th>"
    
    def _render_body_cell(self, cell: TableCell) -> str:
        """Render a body cell as HTML."""
        attrs: list[str] = []
        
        if cell.rowspan > 1:
            attrs.append(f'rowspan="{cell.rowspan}"')
        if cell.colspan > 1:
            attrs.append(f'colspan="{cell.colspan}"')
        if cell.align != "left":
            attrs.append(f'align="{cell.align}"')
        
        # Add alignment class for styling
        if cell.align != "left":
            attrs.append(f'class="align-{cell.align}"')
        
        attr_str = " ".join(attrs)
        if attr_str:
            attr_str = " " + attr_str
        
        content = self._escape_html(cell.content)
        return f"<td{attr_str}>{content}</td>"
    
    def _escape_html(self, text: str) -> str:
        """Escape HTML special characters."""
        return (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
        )
    
    def convert_to_markdown(
        self,
        data: TableData,
        add_caption: bool = True,
    ) -> str:
        """Convert table data to Markdown.
        
        Args:
            data: Structured table data
            add_caption: Whether to add caption
            
        Returns:
            Markdown string
        """
        table_num = self._get_next_table_num()
        md_parts: list[str] = []
        
        # Determine column count
        col_count = 0
        if data.headers:
            col_count = len(data.headers)
        elif data.rows:
            col_count = max(len(row.cells) for row in data.rows) if data.rows else 0
        
        if col_count == 0:
            return ""
        
        # Add header row
        if data.headers:
            header_cells = [cell.content for cell in data.headers]
            md_parts.append("| " + " | ".join(header_cells) + " |")
        else:
            # No headers, use empty headers
            md_parts.append("| " + " | ".join([""] * col_count) + " |")
        
        # Add separator
        md_parts.append("| " + " | ".join(["---" for _ in range(col_count)]) + " |")
        
        # Add data rows
        for row in data.rows:
            # Handle colspan by duplicating content
            cells: list[str] = []
            for cell in row.cells:
                cells.append(cell.content)
                # Add empty cells for colspan
                for _ in range(cell.colspan - 1):
                    cells.append("")
            
            # Pad to match column count
            while len(cells) < col_count:
                cells.append("")
            cells = cells[:col_count]  # Truncate if too many
            
            md_parts.append("| " + " | ".join(cells) + " |")
        
        table_md = "\n".join(md_parts)
        
        # Add caption if requested
        if add_caption:
            caption_text = data.caption or f"Table {table_num}"
            table_md += f"\n\n*{caption_text}*"
        
        return table_md
    
    def parse_pymupdf_table(self, table) -> TableData:
        """Parse a PyMuPDF table into TableData.
        
        Args:
            table: PyMuPDF table object
            
        Returns:
            Structured table data
        """
        try:
            import pandas as pd
            df = table.to_pandas()
            
            # Convert DataFrame to TableData
            headers = None
            rows: list[TableRow] = []
            
            # Check if first row should be header
            if not df.empty:
                # Create header cells
                headers = [
                    TableCell(content=str(col), is_header=True)
                    for col in df.columns
                ]
                
                # Create data rows
                for _, row_data in df.iterrows():
                    cells = [
                        TableCell(content=str(val) if pd.notna(val) else "")
                        for val in row_data
                    ]
                    rows.append(TableRow(cells=cells))
            
            return TableData(headers=headers, rows=rows)
            
        except ImportError:
            # Fallback without pandas
            return self._parse_table_without_pandas(table)
    
    def _parse_table_without_pandas(self, table) -> TableData:
        """Parse table without pandas dependency."""
        # Access table cells directly from PyMuPDF table
        headers = None
        rows: list[TableRow] = []
        
        # Try to get table content as nested list
        try:
            # PyMuPDF tables have extract() method
            cells = table.extract()
            if cells:
                # First row as header
                if len(cells) > 0:
                    headers = [TableCell(content=str(cell) if cell else "", is_header=True) 
                              for cell in cells[0]]
                
                # Remaining rows as data
                for row_cells in cells[1:]:
                    cells_list = [TableCell(content=str(cell) if cell else "")
                                 for cell in row_cells]
                    rows.append(TableRow(cells=cells_list))
        except Exception:
            pass
        
        return TableData(headers=headers, rows=rows)
    
    def parse_markdown_table(self, markdown: str) -> TableData:
        """Parse a Markdown table into TableData.
        
        Args:
            markdown: Markdown table string
            
        Returns:
            Structured table data
        """
        lines = markdown.strip().split("\n")
        if len(lines) < 2:
            return TableData()
        
        headers = None
        rows: list[TableRow] = []
        
        # Parse header
        header_line = lines[0]
        header_cells = [cell.strip() for cell in header_line.split("|") if cell.strip()]
        if header_cells:
            headers = [TableCell(content=cell, is_header=True) for cell in header_cells]
        
        # Skip separator line (line 1)
        # Parse data rows
        for line in lines[2:]:
            if "|" in line:
                cells = [cell.strip() for cell in line.split("|") if cell.strip()]
                if cells:
                    row_cells = [TableCell(content=cell) for cell in cells]
                    rows.append(TableRow(cells=row_cells))
        
        return TableData(headers=headers, rows=rows)
    
    def detect_alignment(self, separator_line: str) -> list[Literal["left", "center", "right"]]:
        """Detect column alignment from markdown separator line.
        
        Args:
            separator_line: The markdown separator line (e.g., |---|:---:|---:|
            
        Returns:
            List of alignment values for each column
        """
        alignments: list[Literal["left", "center", "right"]] = []
        
        # Split by | and filter empty strings
        parts = [p.strip() for p in separator_line.split("|") if p.strip()]
        
        for part in parts:
            if part.startswith(":") and part.endswith(":"):
                alignments.append("center")
            elif part.endswith(":"):
                alignments.append("right")
            else:
                alignments.append("left")
        
        return alignments
    
    def infer_alignment(self, content: str) -> Literal["left", "center", "right"]:
        """Infer cell alignment based on content.
        
        Args:
            content: Cell content
            
        Returns:
            Inferred alignment
        """
        content = content.strip()
        
        # Numbers and currency typically right-aligned
        if re.match(r"^[\d\s,.$%€£¥]+$", content):
            return "right"
        
        # Center short content or headers
        if len(content) < 10:
            return "center"
        
        return "left"
    
    def save_html_table(
        self,
        data: TableData,
        output_path: Path,
        include_styles: bool = True,
    ) -> None:
        """Save table as HTML file.
        
        Args:
            data: Table data
            output_path: Path to save HTML file
            include_styles: Whether to include CSS styles
        """
        html = self.convert_to_html(data, add_figure_wrap=True)
        
        if include_styles:
            html = self._wrap_with_styles(html)
        
        output_path.write_text(html, encoding="utf-8")
    
    def _wrap_with_styles(self, table_html: str) -> str:
        """Wrap table HTML with CSS styles."""
        styles = """<style>
.pdf-table {
    border-collapse: collapse;
    width: 100%;
    margin: 1em 0;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}
.pdf-table th,
.pdf-table td {
    border: 1px solid #ddd;
    padding: 8px 12px;
    text-align: left;
}
.pdf-table th {
    background-color: #f5f5f5;
    font-weight: 600;
    color: #333;
}
.pdf-table tr:nth-child(even) {
    background-color: #fafafa;
}
.pdf-table tr:hover {
    background-color: #f0f0f0;
}
.pdf-table td.align-center,
.pdf-table th.align-center {
    text-align: center;
}
.pdf-table td.align-right,
.pdf-table th.align-right {
    text-align: right;
}
.table-figure {
    margin: 1.5em 0;
}
.table-figure figcaption {
    text-align: center;
    font-style: italic;
    color: #666;
    margin-top: 0.5em;
    font-size: 0.9em;
}
</style>
"""
        return styles + table_html


def convert_table_for_concept(
    table_data: list[list[str]],
    caption: str = "",
    table_num: int = 1,
) -> str:
    """Convert raw table data to HTML for concept markdown.
    
    Args:
        table_data: 2D list of cell values
        caption: Optional caption
        table_num: Table number for default caption
        
    Returns:
        HTML string for the table
    """
    if not table_data or not table_data[0]:
        return ""
    
    converter = TableConverter()
    
    # First row as headers
    headers = [TableCell(content=cell, is_header=True) for cell in table_data[0]]
    
    # Remaining rows as data
    rows: list[TableRow] = []
    for row_data in table_data[1:]:
        cells = [TableCell(content=cell) for cell in row_data]
        rows.append(TableRow(cells=cells))
    
    data = TableData(
        headers=headers,
        rows=rows,
        caption=caption or f"Table {table_num}",
    )
    
    return converter.convert_to_html(data, add_figure_wrap=True)
