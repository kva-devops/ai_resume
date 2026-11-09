"""Read-only PDF extraction helper for the independently authored reference ratings."""
import json
import re
import sys
from pathlib import Path
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]

def extract(path):
    return '\n'.join(page.extract_text() or '' for page in PdfReader(path).pages)

def evidence(text):
    stacks = re.findall(r'Технологический стек: ([\s\S]*?)(?=\n(?:\d{2}\.\d{4}|ОБРАЗОВАНИЕ|\n|СИНТЕТИЧЕСКОЕ))', text)
    bullets = list(dict.fromkeys(re.findall(r'^- [^\n]*', text, re.M)))
    about = text.split('О СЕБЕ\n')[-1].split('Резюме обновлено')[0].strip()
    return {'stacks': list(dict.fromkeys(stacks)), 'bullets': bullets, 'about': about}

if __name__ == '__main__':
    start, end = map(int, sys.argv[1:3])
    for path in sorted((ROOT / 'Test CV').glob('*.pdf'))[start:end]:
        print(path.name)
        print(json.dumps(evidence(extract(path)), ensure_ascii=False, indent=2))
