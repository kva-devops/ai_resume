import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ref = json.loads((ROOT / 'final_reference_gpt6_astra.json').read_text(encoding='utf-8'))
cur = json.loads((ROOT / 'final_current_gpt4o_mini_v2.json').read_text(encoding='utf-8'))

def mean(rows):
    return sum(float(x['score']) for x in rows) / len(rows)

report = {
    'sample_size': len(ref),
    'reference_mean': round(mean(ref), 2),
    'current_mean': round(mean(cur), 2),
    'delta_current_minus_reference': round(mean(cur) - mean(ref), 2),
    'reference_range': [min(x['score'] for x in ref), max(x['score'] for x in ref)],
    'current_range': [min(x['score'] for x in cur), max(x['score'] for x in cur)],
    'over_scored': sum(x['score'] > y['score'] + 5 for x, y in zip(cur, ref)),
    'under_scored': sum(x['score'] < y['score'] - 5 for x, y in zip(cur, ref)),
}
report['criterion_deltas'] = {}
for i, criterion in enumerate(ref[0]['criteria']):
    name = criterion['criterion_id']
    a = [r['criteria'][i]['score'] for r in ref]
    b = [r['criteria'][i]['score'] for r in cur]
    report['criterion_deltas'][name] = round(sum(b) / len(b) - sum(a) / len(a), 2)
(ROOT / 'final_comparison_report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(report, ensure_ascii=False, indent=2))
