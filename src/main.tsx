import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  AlertCircle, BriefcaseBusiness, Check, ChevronRight, CircleGauge, ClipboardCheck,
  FileCheck2, FileText, Loader2, Plus, RefreshCw, Search, Settings2, Sparkles,
  Trash2, Upload, Users, X
} from "lucide-react";
import "./styles.css";

type Criterion = { id: string; name: string; description: string; type: "required" | "bonus"; weight: number };
type CriterionResult = { criterion_id: string; score: number; status: "confirmed" | "partial" | "missing" | "contradiction"; explanation: string; quotes: string[] };
type Evaluation = { score: number; criteria: CriterionResult[]; summary: string; strengths: string[]; gaps: string[]; mode?: string };
type Vacancy = { id: number; title: string; content: string; source_name?: string; criteria: Criterion[]; confirmed: boolean; created_at: string };
type Candidate = { id: number; vacancy_id: number; name: string; source_name: string; source_type: string; content: string; status: string; error?: string; evaluation?: Evaluation; created_at: string };
type AppState = { vacancies: Vacancy[]; candidates: Candidate[]; prompt: { value: string; version: string }; api_configured: boolean };
type Tab = "setup" | "description" | "candidates" | "compare" | "prompt";

const api = async (path: string, init?: RequestInit) => {
  const response = await fetch(path, init);
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail || "Не удалось выполнить запрос.");
  return data;
};

const statusLabels = { confirmed: "Подтверждено", partial: "Частично", missing: "Нет сведений", contradiction: "Есть противоречие" };

function App() {
  const [data, setData] = useState<AppState | null>(null);
  const [activeId, setActiveId] = useState<number | null>(null);
  const [tab, setTab] = useState<Tab>("setup");
  const [modal, setModal] = useState(false);
  const [busy, setBusy] = useState("");
  const [toast, setToast] = useState<{ kind: "ok" | "error"; text: string } | null>(null);

  const load = async () => {
    try {
      const next = await api("/api/state");
      setData(next);
      setActiveId(current => current ?? next.vacancies[0]?.id ?? null);
    } catch (error) { setToast({ kind: "error", text: (error as Error).message }); }
  };
  useEffect(() => { load(); }, []);
  useEffect(() => { if (toast) { const id = setTimeout(() => setToast(null), 4500); return () => clearTimeout(id); } }, [toast]);

  const vacancy = data?.vacancies.find(v => v.id === activeId) ?? null;
  const candidates = data?.candidates.filter(c => c.vacancy_id === activeId) ?? [];
  const run = async (key: string, action: () => Promise<unknown>, success?: string) => {
    setBusy(key);
    try { await action(); await load(); if (success) setToast({ kind: "ok", text: success }); }
    catch (error) { setToast({ kind: "error", text: (error as Error).message }); }
    finally { setBusy(""); }
  };

  if (!data) return <div className="loading-screen"><Loader2 className="spin" /><span>Открываем рабочее пространство</span></div>;

  return <div className="app-shell">
    <aside className="sidebar">
      <div className="brand"><div className="brand-mark"><ClipboardCheck size={22}/></div><div><strong>Контур</strong><span>оценка резюме</span></div></div>
      <button className="new-vacancy" onClick={() => setModal(true)}><Plus size={17}/> Новая вакансия</button>
      <div className="side-label">Вакансии</div>
      <div className="vacancy-list">
        {data.vacancies.map(v => <button key={v.id} className={`vacancy-item ${v.id === activeId ? "active" : ""}`} onClick={() => { setActiveId(v.id); setTab("setup"); }}>
          <span className="vacancy-icon"><BriefcaseBusiness size={17}/></span>
          <span><strong>{v.title}</strong><small>{data.candidates.filter(c => c.vacancy_id === v.id).length} кандидатов</small></span>
          {v.confirmed && <Check size={15} className="side-check"/>}
        </button>)}
        {!data.vacancies.length && <div className="side-empty">Создайте первую вакансию, чтобы начать оценку.</div>}
      </div>
      <button className={`admin-nav ${tab === "prompt" ? "active" : ""}`} onClick={() => setTab("prompt")}>
        <span className="vacancy-icon"><Settings2 size={17}/></span>
        <span><strong>Системный промпт</strong><small>Администрирование</small></span>
      </button>
      <div className="privacy-note"><span className={`status-light ${data.api_configured ? "on" : ""}`}/><div><strong>{data.api_configured ? "Proxy API подключён" : "Локальный режим"}</strong><small>{data.api_configured ? "Токен хранится на сервере" : "Без отправки данных наружу"}</small></div></div>
    </aside>

    <main className="main">
      {tab === "prompt" ? <>
        <header className="topbar admin-topbar">
          <div><div className="eyebrow">АДМИНИСТРИРОВАНИЕ</div><h1>Системный промпт</h1></div>
          <span className="admin-badge"><Settings2 size={14}/> Общий для приложения</span>
        </header>
        <div className="content admin-content">
          <PromptPanel initial={data.prompt.value} busy={busy} run={run}/>
        </div>
      </> : vacancy ? <>
        <header className="topbar">
          <div><div className="eyebrow">ВАКАНСИЯ</div><h1>{vacancy.title}</h1></div>
          <div className="top-actions"><span className={`phase-pill ${vacancy.confirmed ? "ready" : "draft"}`}>{vacancy.confirmed ? <><Check size={14}/> Критерии подтверждены</> : "Черновик критериев"}</span><button className="icon-btn danger" title="Удалить вакансию" onClick={() => { if (confirm("Удалить вакансию и всех кандидатов?")) run("delete-v", () => api(`/api/vacancies/${vacancy.id}`, { method: "DELETE" })).then(() => setActiveId(null)); }}><Trash2 size={18}/></button></div>
        </header>
        <nav className="tabs">
          <TabButton active={tab === "description"} onClick={() => setTab("description")} icon={<FileText/>} label="Полное описание вакансии" />
          <TabButton active={tab === "setup"} onClick={() => setTab("setup")} icon={<CircleGauge/>} label="Критерии" />
          <TabButton active={tab === "candidates"} onClick={() => setTab("candidates")} icon={<Users/>} label="Кандидаты" count={candidates.length}/>
          <TabButton active={tab === "compare"} onClick={() => setTab("compare")} icon={<FileCheck2/>} label="Сравнение" />
        </nav>
        <div className="content">
          {tab === "description" && <VacancyDescription vacancy={vacancy}/>} 
          {tab === "setup" && <CriteriaPanel vacancy={vacancy} busy={busy} run={run}/>} 
          {tab === "candidates" && <CandidatesPanel vacancy={vacancy} candidates={candidates} busy={busy} run={run}/>} 
          {tab === "compare" && <ComparePanel vacancy={vacancy} candidates={candidates}/>} 
        </div>
      </> : <EmptyHome onCreate={() => setModal(true)}/>} 
    </main>
    {modal && <NewVacancyModal onClose={() => setModal(false)} onCreated={async (id) => { setModal(false); await load(); setActiveId(id); }}/>} 
    {toast && <div className={`toast ${toast.kind}`}><span>{toast.kind === "ok" ? <Check/> : <AlertCircle/>}</span>{toast.text}<button onClick={() => setToast(null)}><X/></button></div>}
  </div>;
}

function TabButton({ active, onClick, icon, label, count }: { active: boolean; onClick: () => void; icon: React.ReactNode; label: string; count?: number }) {
  return <button className={active ? "active" : ""} onClick={onClick}>{React.cloneElement(icon as React.ReactElement<{size:number}>, {size:17})}{label}{count !== undefined && <span>{count}</span>}</button>;
}

function EmptyHome({ onCreate }: { onCreate: () => void }) {
  return <div className="empty-home"><div className="empty-visual"><FileText size={34}/></div><div className="eyebrow">РАБОЧЕЕ ПРОСТРАНСТВО РЕКРУТЕРА</div><h1><span>Сравнивайте кандидатов</span><span>по одной шкале</span></h1><p>Добавьте вакансию, проверьте предложенные критерии и загрузите резюме. Каждый балл будет связан с цитатой из исходного файла.</p><button className="primary" onClick={onCreate}><Plus size={18}/> Создать вакансию</button><div className="steps"><span><b>1</b> Вакансия</span><ChevronRight/><span><b>2</b> Критерии</span><ChevronRight/><span><b>3</b> Резюме</span><ChevronRight/><span><b>4</b> Сравнение</span></div></div>;
}

function NewVacancyModal({ onClose, onCreated }: { onClose: () => void; onCreated: (id: number) => void }) {
  const [title, setTitle] = useState(""); const [text, setText] = useState(""); const [file, setFile] = useState<File | null>(null); const [error, setError] = useState(""); const [busy, setBusy] = useState(false);
  const submit = async (e: React.FormEvent) => { e.preventDefault(); setBusy(true); setError(""); const form = new FormData(); form.append("title", title); form.append("text", text); if (file) form.append("file", file); try { const result = await api("/api/vacancies", {method:"POST", body:form}); onCreated(result.id); } catch (err) { setError((err as Error).message); setBusy(false); } };
  return <div className="modal-backdrop" onMouseDown={e => e.target === e.currentTarget && onClose()}><form className="modal" onSubmit={submit}><div className="modal-head"><div><div className="eyebrow">НОВАЯ ВАКАНСИЯ</div><h2>Что будем оценивать?</h2></div><button type="button" className="icon-btn" onClick={onClose}><X/></button></div><label>Название вакансии<input value={title} onChange={e=>setTitle(e.target.value)} placeholder="Например, Senior Java Developer" required autoFocus/></label><label>Текст вакансии<textarea value={text} onChange={e=>setText(e.target.value)} placeholder="Вставьте требования, задачи и условия..." disabled={!!file}/></label><div className="or"><span>или</span></div><label className={`dropzone ${file ? "has-file" : ""}`}><input type="file" accept=".pdf,.txt" onChange={e=>{setFile(e.target.files?.[0]||null); setText("");}}/><Upload/><strong>{file ? file.name : "Загрузить PDF или TXT"}</strong><small>{file ? "Файл выбран" : "PDF должен содержать текстовый слой"}</small></label>{error && <div className="inline-error"><AlertCircle/>{error}</div>}<div className="modal-actions"><button type="button" className="secondary" onClick={onClose}>Отмена</button><button className="primary" disabled={busy || (!text.trim() && !file)}>{busy ? <Loader2 className="spin"/> : <Plus/>} Создать вакансию</button></div></form></div>;
}

function parseVacancySections(content: string) {
  const headingMap: Array<[RegExp,string]> = [
    [/^(обязанности|задачи|чем предстоит заниматься|что предстоит делать)/i,"Обязанности"],
    [/^(требования|что мы ожидаем|что для нас важно|наш идеальный кандидат)/i,"Требования"],
    [/^(условия|что мы предлагаем|мы предлагаем|преимущества работы)/i,"Условия"],
    [/^(будет плюсом|желательно|дополнительные требования)/i,"Будет плюсом"],
    [/^(о компании|о нас|описание вакансии)/i,"О вакансии"],
  ];
  const sections: Array<{title:string;items:string[]}> = [];
  let current = {title:"О вакансии",items:[] as string[]};
  const push = () => { if (current.items.length) sections.push(current); };
  content.replace(/^\[Страница \d+\]\s*/gm,"").split(/\r?\n/).map(line=>line.trim()).filter(Boolean).forEach(line=>{
    const clean = line.replace(/^[-–—•*\d.)\s]+/,"").trim();
    const match = headingMap.find(([pattern])=>pattern.test(clean.replace(/:$/,"")));
    if (match && clean.length < 80) { push(); current={title:match[1],items:[]}; }
    else current.items.push(clean);
  });
  push();
  return sections.length ? sections : [{title:"О вакансии",items:[content]}];
}

function VacancyDescription({ vacancy }: { vacancy: Vacancy }) {
  const sections = useMemo(()=>parseVacancySections(vacancy.content),[vacancy.content]);
  return <section className="vacancy-description"><div className="eyebrow">ПОЛНОЕ ОПИСАНИЕ ВАКАНСИИ</div><h2>{vacancy.title}</h2><div className="vacancy-description-grid">{sections.map((section,i)=><article className={`vacancy-section section-${section.title.toLowerCase().replaceAll(" ","-")}`} key={`${section.title}-${i}`}><h3>{section.title}</h3><ul>{section.items.map((item,n)=><li key={n}>{item}</li>)}</ul></article>)}</div></section>;
}

function CriteriaPanel({ vacancy, busy, run }: { vacancy: Vacancy; busy: string; run: Function }) {
  const [criteria, setCriteria] = useState<Criterion[]>(vacancy.criteria || []);
  useEffect(() => setCriteria(vacancy.criteria || []), [vacancy.id, vacancy.criteria]);
  const total = criteria.reduce((s,c)=>s+Number(c.weight||0),0); const bonus = criteria.filter(c=>c.type==="bonus").reduce((s,c)=>s+Number(c.weight||0),0);
  const update = (index:number, patch:Partial<Criterion>) => setCriteria(items=>items.map((c,i)=>i===index?{...c,...patch}:c));
  const add = () => setCriteria(c=>[...c,{id:`c${Date.now()}`,name:"",description:"",type:"required",weight:1}]);
  return <div className="panel-wrap"><section className="section-head"><div><h2>Шкала оценки</h2><p>Кандидаты будут оцениваться только по этому списку. Проверьте формулировки и веса до загрузки резюме.</p></div><button className="secondary accent" onClick={()=>run("suggest",()=>api(`/api/vacancies/${vacancy.id}/suggest`,{method:"POST"}),"Критерии сформированы. Проверьте и подтвердите их.")} disabled={busy==="suggest"}>{busy==="suggest"?<Loader2 className="spin"/>:<Sparkles/>}{criteria.length?"Предложить заново":"Предложить критерии"}</button></section>
  {!criteria.length ? <div className="empty-block"><Sparkles/><h3>Сформируйте первую шкалу</h3><p>Система выделит проверяемые требования из текста вакансии и распределит веса.</p></div> : <>
    <div className="criteria-summary"><div><span>Общий вес</span><strong className={total===100?"good":"bad"}>{total}<small>/100</small></strong></div><div><span>«Будет плюсом»</span><strong className={bonus<=10?"good":"bad"}>{bonus}<small>/10 макс.</small></strong></div><div className="rule-note"><Check/> Личные данные кандидата не входят в шкалу</div></div>
    <div className="criteria-list">{criteria.map((c,i)=><div className="criterion" key={c.id}><div className="criterion-index">{String(i+1).padStart(2,"0")}</div><div className="criterion-main"><input className="name-input" value={c.name} onChange={e=>update(i,{name:e.target.value})} placeholder="Название критерия"/><input className="desc-input" value={c.description} onChange={e=>update(i,{description:e.target.value})} placeholder="Что именно подтверждает соответствие"/></div><select value={c.type} onChange={e=>update(i,{type:e.target.value as Criterion["type"]})}><option value="required">Обязательный</option><option value="bonus">Будет плюсом</option></select><div className="weight"><input type="number" min="1" max="100" value={c.weight} onChange={e=>update(i,{weight:Number(e.target.value)})}/><span>вес</span></div><button className="icon-btn" title="Удалить критерий" onClick={()=>setCriteria(x=>x.filter((_,n)=>n!==i))}><Trash2/></button></div>)}</div>
    <div className="criteria-footer"><button className="text-btn" onClick={add}><Plus/> Добавить критерий</button><button className="primary" disabled={busy==="confirm"||total!==100||bonus>10} onClick={()=>run("confirm",()=>api(`/api/vacancies/${vacancy.id}/criteria`,{method:"PUT",headers:{"Content-Type":"application/json"},body:JSON.stringify({criteria})}),"Шкала подтверждена — теперь можно загрузить резюме.")}>{busy==="confirm"?<Loader2 className="spin"/>:<Check/>} Подтвердить шкалу</button></div>
  </>}</div>;
}

function CandidatesPanel({ vacancy, candidates, busy, run }: { vacancy: Vacancy; candidates: Candidate[]; busy: string; run: Function }) {
  const [files,setFiles]=useState<File[]>([]); const [selected,setSelected]=useState<number|null>(null); const active=candidates.find(c=>c.id===selected)||null;
  const upload=()=>{const form=new FormData();files.forEach(f=>form.append("files",f));return run("upload",()=>api(`/api/vacancies/${vacancy.id}/candidates`,{method:"POST",body:form}),"Резюме загружены и готовы к проверке.").then(()=>setFiles([]));};
  if (!vacancy.confirmed) return <div className="gate"><AlertCircle/><h2>Сначала подтвердите критерии</h2><p>Это защищает шкалу от изменений во время оценки кандидатов.</p></div>;
  return <div className="panel-wrap"><section className="section-head"><div><h2>Кандидаты</h2><p>Загрузите PDF с текстовым слоем или CSV — один файл на одного кандидата.</p></div><a className="text-link" href="data:text/csv;charset=utf-8,%EF%BB%BFИмя%2CЖелаемая%20должность%2CОпыт%2CОбязанности%2CДостижения%2CСтек%2CОбразование%2CЯзыки%2CНавыки%2CО%20себе%0A" download="resume-template.csv">Скачать CSV-шаблон</a></section>
  <div className="upload-row"><label className="upload-compact"><input type="file" multiple accept=".pdf,.csv" onChange={e=>setFiles(Array.from(e.target.files||[]))}/><Upload/><span><strong>{files.length?`${files.length} файл(а) выбрано`:"Выберите резюме"}</strong><small>PDF или CSV, можно несколько</small></span></label><button className="primary" disabled={!files.length||busy==="upload"} onClick={upload}>{busy==="upload"?<Loader2 className="spin"/>:<FileCheck2/>} Добавить кандидатов</button></div>
  {!candidates.length?<div className="empty-block slim"><Users/><h3>Здесь появятся кандидаты</h3><p>После загрузки сначала проверьте извлечённый текст, затем запустите оценку.</p></div>:<div className="candidate-grid">{candidates.map(c=><article className="candidate-card" key={c.id}><div className="candidate-head"><div className="avatar">{c.name.slice(0,2).toUpperCase()}</div><div><h3>{c.name}</h3><span>{c.source_name}</span></div><button className="icon-btn" onClick={()=>{if(confirm("Удалить кандидата и его оценку?"))run(`del-${c.id}`,()=>api(`/api/candidates/${c.id}`,{method:"DELETE"}))}}><Trash2/></button></div><div className="candidate-state">{c.status==="done"?<><div className="score-mini">{c.evaluation?.score}</div><span><strong>Оценка завершена</strong><small>{c.evaluation?.mode==="local"?"Локальная предварительная":"Проверена моделью"}</small></span></>:c.status==="error"?<><AlertCircle className="red"/><span><strong>Ошибка оценки</strong><small>{c.error}</small></span></>:<><FileText/><span><strong>Текст извлечён</strong><small>{c.content.length.toLocaleString("ru-RU")} знаков</small></span></>}</div><div className="candidate-actions"><button className="secondary" onClick={()=>setSelected(c.id)}><Search/> Проверить текст</button><button className="primary small" disabled={busy===`eval-${c.id}`} onClick={()=>run(`eval-${c.id}`,()=>api(`/api/candidates/${c.id}/evaluate`,{method:"POST"}),`Оценка ${c.name} завершена.`)}>{busy===`eval-${c.id}`?<Loader2 className="spin"/>:<RefreshCw/>}{c.status==="done"?"Оценить заново":"Оценить"}</button></div></article>)}</div>}
  {active&&<div className="drawer-backdrop" onMouseDown={e=>e.target===e.currentTarget&&setSelected(null)}><aside className="drawer"><div className="modal-head"><div><div className="eyebrow">ИЗВЛЕЧЁННОЕ РЕЗЮМЕ</div><h2>{active.name}</h2></div><button className="icon-btn" onClick={()=>setSelected(null)}><X/></button></div><div className="source-meta"><FileText/> {active.source_name} · {active.source_type.toUpperCase()}</div><pre>{active.content}</pre></aside></div>}</div>;
}

function ComparePanel({ vacancy, candidates }: { vacancy: Vacancy; candidates: Candidate[] }) {
  const done=useMemo(()=>candidates.filter(c=>c.status==="done"&&c.evaluation).sort((a,b)=>(b.evaluation?.score||0)-(a.evaluation?.score||0)),[candidates]); const [open,setOpen]=useState<number|null>(null);
  if(!done.length)return <div className="gate"><CircleGauge/><h2>Пока нечего сравнивать</h2><p>Завершите оценку хотя бы одного кандидата. Здесь появится рейтинг без автоматического решения о найме.</p></div>;
  return <div className="panel-wrap compare"><section className="section-head"><div><h2>Сравнение кандидатов</h2><p>Итог рассчитан сервером по подтверждённым весам. Нажмите строку, чтобы увидеть доказательства.</p></div><div className="no-decision"><AlertCircle/> Решение остаётся за рекрутером</div></section><div className="table-wrap"><table><thead><tr><th>Кандидат</th><th>Итог</th>{vacancy.criteria.map(c=><th key={c.id}>{c.name}<small>{c.weight}%</small></th>)}</tr></thead><tbody>{done.map((c,index)=><React.Fragment key={c.id}><tr className="result-row" onClick={()=>setOpen(open===c.id?null:c.id)}><td><span className="rank">{index+1}</span><strong>{c.name}</strong><small>{c.source_name}</small></td><td><ScoreRing score={c.evaluation!.score}/></td>{vacancy.criteria.map(cr=>{const r=c.evaluation!.criteria.find(x=>x.criterion_id===cr.id);return <td key={cr.id}><span className={`cell-score ${r?.status}`}>{r?.score??0}<small>/5</small></span></td>})}</tr>{open===c.id&&<tr className="detail-row"><td colSpan={vacancy.criteria.length+2}><CandidateDetail candidate={c} vacancy={vacancy}/></td></tr>}</React.Fragment>)}</tbody></table></div></div>;
}

function ScoreRing({score}:{score:number}){return <div className="score-ring" style={{"--score":`${score*3.6}deg`} as React.CSSProperties}><span>{score}</span><small>/100</small></div>}
function CandidateDetail({candidate, vacancy}:{candidate:Candidate;vacancy:Vacancy}){return <div className="candidate-detail"><div className="detail-summary"><div><div className="eyebrow">ВЫВОД</div><p>{candidate.evaluation?.summary}</p></div><div className="tag-groups"><span><b>Сильные стороны</b>{candidate.evaluation?.strengths.map(x=><em key={x}>{x}</em>)}</span><span><b>Пробелы и нет сведений</b>{candidate.evaluation?.gaps.map(x=><em className="gap" key={x}>{x}</em>)}</span></div></div><div className="evidence-list">{candidate.evaluation?.criteria.map(r=>{const c=vacancy.criteria.find(x=>x.id===r.criterion_id);return <div className="evidence" key={r.criterion_id}><div><strong>{c?.name}</strong><span className={`status ${r.status}`}>{statusLabels[r.status]}</span><b>{r.score}/5</b></div><p>{r.explanation}</p>{r.quotes.map((q,i)=><blockquote key={i}>«{q}»</blockquote>)}</div>})}</div></div>}

function PromptPanel({initial,busy,run}:{initial:string;busy:string;run:Function}){const[value,setValue]=useState(initial);useEffect(()=>setValue(initial),[initial]);return <div className="panel-wrap prompt-page"><section className="section-head"><div><h2>Состав и правила</h2><p>Это единая инструкция для модели. Здесь можно увидеть её целиком, скорректировать формулировки и сохранить новую версию. Уже завершённые оценки не изменятся.</p></div><button className="primary" disabled={busy==="prompt"||value===initial} onClick={()=>run("prompt",()=>api("/api/settings/prompt",{method:"PUT",headers:{"Content-Type":"application/json"},body:JSON.stringify({value})}),"Системный промпт сохранён.")}>{busy==="prompt"?<Loader2 className="spin"/>:<Check/>} Сохранить изменения</button></section><div className="prompt-principles"><span><b>01</b> Шкала от 0 до 5</span><span><b>02</b> Только дословные цитаты</span><span><b>03</b> Нет сведений — 0 баллов</span><span><b>04</b> Личные данные исключены</span></div><div className="prompt-card"><div className="prompt-meta"><span><Settings2/> Полный текст системного промпта</span><span>{value.length.toLocaleString("ru-RU")} знаков</span></div><textarea aria-label="Полный текст системного промпта" value={value} onChange={e=>setValue(e.target.value)} spellCheck={false}/><div className="prompt-hint"><AlertCircle/> Критерии конкретной вакансии передаются модели отдельно. Токен API никогда не попадает в браузер.</div></div></div>}

createRoot(document.getElementById("root")!).render(<React.StrictMode><App/></React.StrictMode>);
