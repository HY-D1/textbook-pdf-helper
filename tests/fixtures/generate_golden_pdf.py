"""Generate a golden PDF fixture for CI testing.

This script creates a synthetic 8-page PDF with:
- 3 SQL concepts (SELECT, WHERE, JOIN)
- 2 figures/tables
- Known structure (chapters, sections)
- Embedded text (not scanned)
"""

from __future__ import annotations

import sys
from pathlib import Path

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import (
        SimpleDocTemplate,
        Paragraph,
        Spacer,
        Table,
        TableStyle,
        PageBreak,
        ListFlowable,
        ListItem,
    )
except ImportError:
    print("reportlab is required. Install with: pip install reportlab")
    sys.exit(1)


def create_golden_pdf(output_path: Path) -> None:
    """Create the golden PDF fixture."""
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=letter,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=18,
    )

    styles = getSampleStyleSheet()
    title_style = styles["Heading1"]
    heading2_style = styles["Heading2"]
    heading3_style = styles["Heading3"]
    body_style = styles["BodyText"]
    code_style = ParagraphStyle(
        "Code",
        parent=styles["BodyText"],
        fontName="Courier",
        fontSize=9,
        leftIndent=20,
        textColor=colors.darkblue,
    )

    story = []

    # ===== Page 1: Title Page =====
    story.append(Paragraph("SQL Fundamentals: A Learning Guide", title_style))
    story.append(Spacer(1, 0.3 * inch))
    story.append(Paragraph("Golden Reference Document for Testing", heading2_style))
    story.append(Spacer(1, 0.5 * inch))
    story.append(
        Paragraph(
            "This document contains structured SQL learning content for testing "
            "the ALGL PDF Helper extraction and indexing pipeline.",
            body_style,
        )
    )
    story.append(Spacer(1, 0.3 * inch))
    story.append(Paragraph("Contents:", heading3_style))
    story.append(Spacer(1, 0.2 * inch))

    toc_items = [
        "1. SELECT Statement Basics (Page 2)",
        "2. WHERE Clause and Filtering (Page 4)",
        "3. JOIN Operations (Page 6)",
        "4. Practice Exercises (Page 8)",
    ]
    for item in toc_items:
        story.append(Paragraph(f"• {item}", body_style))

    story.append(PageBreak())

    # ===== Page 2: SELECT - Definition =====
    story.append(Paragraph("Chapter 1: SELECT Statement Basics", title_style))
    story.append(Spacer(1, 0.2 * inch))
    story.append(
        Paragraph(
            "The SELECT statement is the most fundamental SQL command. It retrieves "
            "data from one or more tables in a database. The basic syntax allows you "
            "to specify which columns you want to retrieve and from which table.",
            body_style,
        )
    )
    story.append(Spacer(1, 0.2 * inch))
    story.append(Paragraph("Basic Syntax:", heading3_style))
    story.append(Spacer(1, 0.1 * inch))
    story.append(Paragraph("SELECT column1, column2 FROM table_name;", code_style))
    story.append(Spacer(1, 0.2 * inch))
    story.append(
        Paragraph(
            "You can use the asterisk wildcard to select all columns from a table. "
            "This is useful for exploring data but should be avoided in production "
            "queries for better performance.",
            body_style,
        )
    )
    story.append(Spacer(1, 0.2 * inch))
    story.append(Paragraph("Example with all columns:", heading3_style))
    story.append(Spacer(1, 0.1 * inch))
    story.append(Paragraph("SELECT * FROM employees;", code_style))

    story.append(PageBreak())

    # ===== Page 3: SELECT - Examples and Practice =====
    story.append(Paragraph("SELECT Statement - Examples", heading2_style))
    story.append(Spacer(1, 0.2 * inch))

    # Figure 1: SELECT Examples Table
    story.append(Paragraph("Figure 1: Common SELECT Patterns", heading3_style))
    story.append(Spacer(1, 0.1 * inch))

    table_data = [
        ["Pattern", "SQL Statement", "Description"],
        [
            "All Columns",
            "SELECT * FROM users",
            "Retrieves every column",
        ],
        [
            "Specific Columns",
            "SELECT name, email FROM users",
            "Retrieves only named columns",
        ],
        [
            "Distinct Values",
            "SELECT DISTINCT dept FROM employees",
            "Removes duplicate values",
        ],
        [
            "Aliased Columns",
            "SELECT name AS username FROM users",
            "Renames output columns",
        ],
    ]

    table = Table(table_data, colWidths=[1.5 * inch, 2.5 * inch, 2.5 * inch])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 10),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
                ("GRID", (0, 0), (-1, -1), 1, colors.black),
            ]
        )
    )
    story.append(table)

    story.append(Spacer(1, 0.3 * inch))
    story.append(
        Paragraph(
            "When writing SELECT statements, consider performance implications. "
            "Selecting only the columns you need reduces network traffic and "
            "memory usage on the database server. Always specify column names "
            "explicitly in production code for better maintainability.",
            body_style,
        )
    )

    story.append(PageBreak())

    # ===== Page 4: WHERE - Definition =====
    story.append(Paragraph("Chapter 2: WHERE Clause and Filtering", title_style))
    story.append(Spacer(1, 0.2 * inch))
    story.append(
        Paragraph(
            "The WHERE clause filters rows based on specified conditions. It "
            "evaluates each row against the condition and includes only those "
            "that satisfy it in the result set. This is essential for working "
            "with large datasets where you need specific subsets of data.",
            body_style,
        )
    )
    story.append(Spacer(1, 0.2 * inch))
    story.append(Paragraph("Basic WHERE Syntax:", heading3_style))
    story.append(Spacer(1, 0.1 * inch))
    story.append(
        Paragraph(
            "SELECT column FROM table WHERE condition;", code_style
        )
    )
    story.append(Spacer(1, 0.2 * inch))
    story.append(
        Paragraph(
            "Common comparison operators include equals (=), not equals (!= or <>), "
            "greater than (>), less than (<), and their inclusive variants (>=, <=). "
            "The LIKE operator enables pattern matching with wildcards.",
            body_style,
        )
    )
    story.append(Spacer(1, 0.2 * inch))
    story.append(Paragraph("Example with comparison:", heading3_style))
    story.append(Spacer(1, 0.1 * inch))
    story.append(
        Paragraph("SELECT * FROM products WHERE price > 100;", code_style)
    )

    story.append(PageBreak())

    # ===== Page 5: WHERE - Examples and Common Mistakes =====
    story.append(Paragraph("WHERE Clause - Examples", heading2_style))
    story.append(Spacer(1, 0.2 * inch))
    story.append(
        Paragraph(
            "Multiple conditions can be combined using AND and OR operators. "
            "AND requires both conditions to be true, while OR requires at least "
            "one. Use parentheses to control evaluation order in complex queries.",
            body_style,
        )
    )
    story.append(Spacer(1, 0.2 * inch))
    story.append(Paragraph("Combined conditions:", heading3_style))
    story.append(Spacer(1, 0.1 * inch))
    story.append(
        Paragraph(
            "SELECT * FROM employees WHERE dept = 'Sales' AND salary > 50000;",
            code_style,
        )
    )
    story.append(Spacer(1, 0.3 * inch))
    story.append(Paragraph("Common Mistakes to Avoid:", heading3_style))
    story.append(Spacer(1, 0.1 * inch))

    mistakes = [
        "Using = instead of IN for multiple values",
        "Forgetting that NULL comparisons need IS NULL",
        "Not using parentheses with mixed AND/OR",
        "Case sensitivity issues with string comparisons",
    ]
    for mistake in mistakes:
        story.append(Paragraph(f"• {mistake}", body_style))

    story.append(PageBreak())

    # ===== Page 6: JOIN - Definition =====
    story.append(Paragraph("Chapter 3: JOIN Operations", title_style))
    story.append(Spacer(1, 0.2 * inch))
    story.append(
        Paragraph(
            "JOIN operations combine rows from two or more tables based on related "
            "columns. This is fundamental to relational database design, allowing "
            "data to be normalized across tables while still retrievable as unified "
            "results. The most common type is the INNER JOIN.",
            body_style,
        )
    )
    story.append(Spacer(1, 0.2 * inch))
    story.append(Paragraph("INNER JOIN Syntax:", heading3_style))
    story.append(Spacer(1, 0.1 * inch))
    story.append(
        Paragraph(
            "SELECT a.column, b.column FROM table_a a INNER JOIN table_b b "
            "ON a.id = b.foreign_id;",
            code_style,
        )
    )
    story.append(Spacer(1, 0.2 * inch))
    story.append(
        Paragraph(
            "Other join types include LEFT JOIN (all rows from left table), "
            "RIGHT JOIN (all rows from right table), and FULL OUTER JOIN "
            "(all rows from both tables). Understanding when to use each type "
            "is crucial for accurate data retrieval.",
            body_style,
        )
    )

    story.append(PageBreak())

    # ===== Page 7: JOIN - Examples and Visual Guide =====
    story.append(Paragraph("JOIN Operations - Examples", heading2_style))
    story.append(Spacer(1, 0.2 * inch))

    # Figure 2: JOIN Types Reference
    story.append(Paragraph("Figure 2: SQL JOIN Types Reference", heading3_style))
    story.append(Spacer(1, 0.1 * inch))

    join_table_data = [
        ["Join Type", "Description", "Use Case"],
        [
            "INNER JOIN",
            "Returns matching rows only",
            "When you need related data from both tables",
        ],
        [
            "LEFT JOIN",
            "Returns all left rows, matched right rows",
            "When left table data is required, right is optional",
        ],
        [
            "RIGHT JOIN",
            "Returns matched left rows, all right rows",
            "When right table data is required",
        ],
        [
            "FULL OUTER JOIN",
            "Returns all rows from both tables",
            "When you need complete data from both sources",
        ],
    ]

    join_table = Table(
        join_table_data, colWidths=[1.3 * inch, 2.3 * inch, 2.9 * inch]
    )
    join_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.navy),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 10),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                ("BACKGROUND", (0, 1), (-1, -1), colors.lightgrey),
                ("GRID", (0, 0), (-1, -1), 1, colors.black),
            ]
        )
    )
    story.append(join_table)

    story.append(Spacer(1, 0.3 * inch))
    story.append(
        Paragraph(
            "Always specify the join condition explicitly using the ON clause. "
            "While some databases support implicit joins in the WHERE clause, "
            "explicit joins are more readable and less error-prone.",
            body_style,
        )
    )

    story.append(PageBreak())

    # ===== Page 8: Practice Exercises =====
    story.append(Paragraph("Chapter 4: Practice Exercises", title_style))
    story.append(Spacer(1, 0.2 * inch))
    story.append(
        Paragraph(
            "Test your understanding with these exercises. Solutions are provided "
            "at the end of this chapter.",
            body_style,
        )
    )
    story.append(Spacer(1, 0.3 * inch))

    story.append(Paragraph("Exercise 1: Basic SELECT", heading3_style))
    story.append(
        Paragraph(
            "Write a query to retrieve the names and email addresses of all "
            "customers from the customers table.",
            body_style,
        )
    )
    story.append(Spacer(1, 0.2 * inch))

    story.append(Paragraph("Exercise 2: Filtering with WHERE", heading3_style))
    story.append(
        Paragraph(
            "Write a query to find all products with a price between 50 and 100 "
            "dollars that are currently in stock.",
            body_style,
        )
    )
    story.append(Spacer(1, 0.2 * inch))

    story.append(Paragraph("Exercise 3: JOIN Operations", heading3_style))
    story.append(
        Paragraph(
            "Write a query to display order details with customer names by joining "
            "the orders table with the customers table.",
            body_style,
        )
    )
    story.append(Spacer(1, 0.3 * inch))

    story.append(Paragraph("Summary", heading2_style))
    story.append(
        Paragraph(
            "This guide covered the three fundamental SQL concepts: SELECT for "
            "retrieving data, WHERE for filtering results, and JOIN for combining "
            "tables. Master these operations before moving on to more advanced "
            "topics like aggregation, subqueries, and window functions.",
            body_style,
        )
    )

    # Build the PDF
    doc.build(story)
    print(f"Golden PDF created: {output_path}")
    print(f"Pages: 8")
    print(f"Concepts: SELECT, WHERE, JOIN")
    print(f"Figures: 2 (SELECT patterns table, JOIN types table)")


if __name__ == "__main__":
    output_dir = Path(__file__).parent
    output_path = output_dir / "golden_chapter.pdf"
    create_golden_pdf(output_path)
