import json
from pathlib import Path
from reference_extract import ROOT, extract, evidence
from build_reference import criterion_result

# Conservative Astra reference ratings for the newly supplied CV_001..CV_025.
# Stack-only evidence is capped by the rubric; explicit work bullets may raise it.
SCORES = {
  1:[4,4,3,4,4,4,3], 2:[4,4,3,4,3,4,1], 3:[4,4,3,4,4,5,0],
  4:[4,4,4,5,3,4,0], 5:[4,4,3,4,3,4,3], 6:[4,4,3,3,4,4,1],
  7:[3,4,3,4,3,5,3], 8:[4,4,4,4,4,4,0], 9:[4,4,3,4,5,4,3],
 10:[4,4,3,4,3,4,3], 11:[3,4,3,3,3,4,3], 12:[4,4,4,5,3,5,0],
 13:[4,4,5,4,5,5,3], 14:[4,4,3,4,4,5,1], 15:[4,4,3,4,4,4,0],
 16:[4,4,5,4,5,4,0], 17:[4,4,4,4,4,5,3], 18:[3,4,3,3,3,4,1],
 19:[4,4,3,4,3,4,3], 20:[4,4,3,3,4,5,0], 21:[4,5,4,5,5,5,3],
 22:[4,4,4,4,4,5,1], 23:[4,4,5,4,4,4,0], 24:[3,4,4,4,5,4,0],
 25:[4,4,4,4,5,5,3],
}

def main():
    rubric = json.loads((ROOT/'benchmark/rubric.json').read_text(encoding='utf-8'))
    files = sorted((ROOT/'Test CV').glob('*.pdf'))[:25]
    assert len(files) == 25, len(files)
    rows=[]; quote_count=0
    for path in files:
        n=int(path.name.split('_')[1]); text=extract(path); ev=evidence(text)
        vals=SCORES[n]
        criteria=[criterion_result(c['id'],s,text,ev) for c,s in zip(rubric['criteria'],vals)]
        score=round(sum(c['weight']*s/5 for c,s in zip(rubric['criteria'],vals)),2)
        strengths=[c['name'] for c,s in zip(rubric['criteria'],vals) if s>=5]
        gaps=[c['name'] for c,s in zip(rubric['criteria'],vals) if s<=3]
        summary='Подтверждён коммерческий опыт Java/Spring backend. '
        if strengths: summary+='Сильные стороны: '+', '.join(strengths)+'. '
        if gaps: summary+='Требуют уточнения: '+', '.join(gaps)+'. '
        summary+='Итог отражает только полноту дословных свидетельств в резюме; решения о найме нет.'
        rows.append({'file':path.name,'candidate_id':path.stem,'criteria':criteria,'score':score,'summary':summary})
        quote_count += sum(len(x['quotes']) for x in criteria)
    out=ROOT/'benchmark/final_reference_gpt6_astra.json'
    out.write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    # strict validation: every quote must be a literal substring of its source PDF
    for row,path in zip(rows,files):
        text=extract(path)
        assert row['score']==round(sum(c['weight']*r['score']/5 for c,r in zip(rubric['criteria'],row['criteria'])),2)
        for r in row['criteria']:
            assert 0<=r['score']<=5
            for q in r['quotes']:
                assert q in text, (path.name,q)
    print(json.dumps({'results':len(rows),'criteria':len(rows)*7,'exact_quotes_verified':quote_count,'mean_score':round(sum(r['score'] for r in rows)/len(rows),2),'output':str(out)},ensure_ascii=False))
if __name__=='__main__': main()
