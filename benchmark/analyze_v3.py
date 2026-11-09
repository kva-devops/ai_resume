import json
from pathlib import Path

p = Path(__file__).resolve().parent
r = json.loads((p / 'v3_reference_gpt6_astra.json').read_text(encoding='utf8'))
c = json.loads((p / 'v3_current_gpt4o_mini.json').read_text(encoding='utf8'))
avg = lambda x: sum(float(a['score']) for a in x) / len(x)
out = {
    'sample_size': len(r),
    'reference_mean': round(avg(r), 2),
    'v3_mean': round(avg(c), 2),
    'delta': round(avg(c) - avg(r), 2),
    'reference_range': [min(x['score'] for x in r), max(x['score'] for x in r)],
    'v3_range': [min(x['score'] for x in c), max(x['score'] for x in c)],
    'over_5': sum(a['score'] > b['score'] + 5 for a, b in zip(c, r)),
    'under_5': sum(a['score'] < b['score'] - 5 for a, b in zip(c, r)),
}
(p / 'v3_comparison_report.json').write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding='utf8')
print(json.dumps(out, ensure_ascii=False, indent=2))
