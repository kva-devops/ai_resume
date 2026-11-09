import json, re
from pathlib import Path
from reference_extract import ROOT, extract, evidence
from build_reference import criterion_result

def scores(text, ev):
    blob = text.replace('\n',' ')
    stack = ' '.join(ev['stacks'])
    has = lambda *xs: any(x in blob for x in xs)
    java = 4 if has('code review','общих компонентов') else 3
    spring = 4 if has('REST API','микросервис') else 3
    data = 5 if has('снизил нагрузку','оптимизация запросов','схем хранения') else (4 if has('обработк','данн','базы') else 3)
    arch = 5 if has('6 микросервис','4 000 сообщений') else (4 if has('REST API','интеграцион') else 3)
    testing = 5 if has('42% до 78%') else (4 if has('unit-','интеграцион') else 3)
    delivery = 5 if has('18 до 7 минут','20 минут') else (4 if has('CI/CD','контейнеризац') else 3)
    if 'Kafka Streams' in stack or 'Protobuf' in stack or 'gRPC' in stack:
        bonus = 1 if 'Прямого опыта' in blob else 3
    else: bonus = 0
    return [java,spring,data,arch,testing,delivery,bonus]

def main():
    rubric=json.loads((ROOT/'benchmark/rubric.json').read_text(encoding='utf-8'))
    files=sorted((ROOT/'Test CV').glob('*.pdf'))
    rows=[]; q=0
    for path in files:
        text=extract(path); ev=evidence(text); vals=scores(text,ev)
        criteria=[criterion_result(c['id'],s,text,ev) for c,s in zip(rubric['criteria'],vals)]
        total=round(sum(c['weight']*s/5 for c,s in zip(rubric['criteria'],vals)),2)
        rows.append({'file':path.name,'candidate_id':path.stem,'criteria':criteria,'score':total,'summary':'Эталонная оценка отражает только дословно подтверждённые сведения резюме; решения о найме нет.'})
        q += sum(len(c['quotes']) for c in criteria)
    out=ROOT/'benchmark/v3_reference_gpt6_astra.json'; out.write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    for row,path in zip(rows,files):
        text=extract(path)
        for c in row['criteria']:
            for quote in c['quotes']:
                assert quote in text,(path.name,quote)
    print(json.dumps({'results':len(rows),'criteria':len(rows)*7,'exact_quotes_verified':q,'mean_score':round(sum(r['score'] for r in rows)/len(rows),2),'output':str(out)},ensure_ascii=False))
if __name__=='__main__': main()
