import ast
import sys

files = [
    'src/algl_pdf_helper/unit_generator.py',
    'src/algl_pdf_helper/export_filters.py', 
    'src/algl_pdf_helper/learning_quality_gates.py'
]

all_ok = True
for filepath in files:
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            source = f.read()
        ast.parse(source)
        print(f'{filepath}: OK')
    except SyntaxError as e:
        print(f'{filepath}: SyntaxError at line {e.lineno}, col {e.offset}: {e.msg}')
        print(f'  Text: {e.text}')
        all_ok = False
    except Exception as e:
        print(f'{filepath}: Error: {e}')
        all_ok = False

sys.exit(0 if all_ok else 1)
