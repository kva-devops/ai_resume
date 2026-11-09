import json
import os
import shutil
import uuid
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .db import as_dict, connect, get_prompt, init_db
from .services import (
    api_configured,
    compute_result,
    evaluate,
    extract_csv,
    extract_pdf,
    extract_text_file,
    suggest_criteria,
)

app = FastAPI(title="Контур — оценка резюме")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "uploads"))


@app.on_event("startup")
def startup():
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    init_db()


def state_payload():
    with connect() as db:
        vacancies = [as_dict(r) for r in db.execute("SELECT * FROM vacancies ORDER BY created_at DESC").fetchall()]
        candidates = [as_dict(r) for r in db.execute("SELECT * FROM candidates ORDER BY created_at DESC").fetchall()]
        prompt = get_prompt(db)
    return {"vacancies": vacancies, "candidates": candidates, "prompt": prompt, "api_configured": api_configured()}


@app.get("/api/state")
def get_state():
    return state_payload()


@app.post("/api/vacancies")
async def create_vacancy(title: str = Form(...), text: str = Form(""), file: UploadFile | None = File(None)):
    content = text.strip()
    source_name = None
    stored_name = None
    if file and file.filename:
        data = await file.read()
        if not data:
            raise HTTPException(400, "Файл вакансии пуст.")
        ext = Path(file.filename).suffix.lower()
        try:
            content = extract_pdf(data) if ext == ".pdf" else extract_text_file(data) if ext == ".txt" else ""
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        if not content:
            raise HTTPException(400, "Для вакансии поддерживаются только PDF и TXT.")
        source_name = file.filename
        stored_name = f"{uuid.uuid4().hex}{ext}"
        (UPLOAD_DIR / stored_name).write_bytes(data)
    if not content:
        raise HTTPException(400, "Добавьте текст вакансии или загрузите файл.")
    with connect() as db:
        cursor = db.execute("INSERT INTO vacancies(title, source_name, stored_name, content) VALUES(?,?,?,?)", (title.strip() or "Новая вакансия", source_name, stored_name, content))
        vacancy_id = cursor.lastrowid
    return {"id": vacancy_id}


@app.post("/api/vacancies/{vacancy_id}/suggest")
def create_suggestion(vacancy_id: int):
    with connect() as db:
        row = db.execute("SELECT * FROM vacancies WHERE id=?", (vacancy_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Вакансия не найдена.")
        try:
            criteria, source = suggest_criteria(row["content"])
        except RuntimeError as exc:
            raise HTTPException(502, str(exc)) from exc
        db.execute("UPDATE vacancies SET criteria_json=?, confirmed=0 WHERE id=?", (json.dumps(criteria, ensure_ascii=False), vacancy_id))
    return {"criteria": criteria, "source": source}


class CriteriaBody(BaseModel):
    criteria: list[dict]


@app.put("/api/vacancies/{vacancy_id}/criteria")
def save_criteria(vacancy_id: int, body: CriteriaBody):
    criteria = body.criteria
    if not criteria:
        raise HTTPException(400, "Добавьте хотя бы один критерий.")
    total = sum(int(c.get("weight", 0)) for c in criteria)
    bonus = sum(int(c.get("weight", 0)) for c in criteria if c.get("type") == "bonus")
    if total != 100:
        raise HTTPException(400, f"Сумма весов должна быть 100, сейчас {total}.")
    if bonus > 10:
        raise HTTPException(400, f"Сумма весов критериев «будет плюсом» не должна превышать 10, сейчас {bonus}.")
    if any(not str(c.get("name", "")).strip() or int(c.get("weight", 0)) <= 0 for c in criteria):
        raise HTTPException(400, "У каждого критерия должны быть название и положительный вес.")
    normalized = [{**c, "id": str(c.get("id") or f"c{uuid.uuid4().hex[:8]}"), "weight": int(c["weight"])} for c in criteria]
    with connect() as db:
        if not db.execute("SELECT 1 FROM vacancies WHERE id=?", (vacancy_id,)).fetchone():
            raise HTTPException(404, "Вакансия не найдена.")
        db.execute("UPDATE vacancies SET criteria_json=?, confirmed=1 WHERE id=?", (json.dumps(normalized, ensure_ascii=False), vacancy_id))
    return {"criteria": normalized, "confirmed": True}


@app.post("/api/vacancies/{vacancy_id}/candidates")
async def upload_candidates(vacancy_id: int, files: list[UploadFile] = File(...)):
    with connect() as db:
        vacancy = db.execute("SELECT * FROM vacancies WHERE id=?", (vacancy_id,)).fetchone()
        if not vacancy:
            raise HTTPException(404, "Вакансия не найдена.")
        if not vacancy["confirmed"]:
            raise HTTPException(400, "Сначала подтвердите критерии вакансии.")
    created, errors = [], []
    for file in files:
        try:
            data = await file.read()
            if not data:
                raise ValueError("Файл пуст.")
            ext = Path(file.filename or "").suffix.lower()
            fields, display = {}, None
            if ext == ".pdf":
                content = extract_pdf(data)
                source_type = "pdf"
            elif ext == ".csv":
                content, fields, display = extract_csv(data)
                source_type = "csv"
            else:
                raise ValueError("Поддерживаются только PDF и CSV.")
            stored = f"{uuid.uuid4().hex}{ext}"
            (UPLOAD_DIR / stored).write_bytes(data)
            name = display or Path(file.filename or "Кандидат").stem
            with connect() as db:
                cur = db.execute(
                    "INSERT INTO candidates(vacancy_id,name,source_name,stored_name,source_type,content,fields_json) VALUES(?,?,?,?,?,?,?)",
                    (vacancy_id, name, file.filename, stored, source_type, content, json.dumps(fields, ensure_ascii=False)),
                )
                created.append(cur.lastrowid)
        except ValueError as exc:
            errors.append({"file": file.filename, "error": str(exc)})
    if not created and errors:
        raise HTTPException(400, errors[0]["error"])
    return {"created": created, "errors": errors}


@app.post("/api/candidates/{candidate_id}/evaluate")
def evaluate_candidate(candidate_id: int):
    with connect() as db:
        row = db.execute("SELECT * FROM candidates WHERE id=?", (candidate_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Кандидат не найден.")
        vacancy = db.execute("SELECT * FROM vacancies WHERE id=?", (row["vacancy_id"],)).fetchone()
        prompt = get_prompt(db)
        criteria = json.loads(vacancy["criteria_json"])
        db.execute("UPDATE candidates SET status='evaluating', error=NULL WHERE id=?", (candidate_id,))
    try:
        result, mode = evaluate(row["content"], criteria, prompt["value"])
        result = compute_result(result, criteria)
        result["mode"] = mode
        with connect() as db:
            db.execute("UPDATE candidates SET evaluation_json=?, status='done', prompt_version=?, error=NULL WHERE id=?", (json.dumps(result, ensure_ascii=False), prompt["version"], candidate_id))
        return result
    except RuntimeError as exc:
        with connect() as db:
            db.execute("UPDATE candidates SET status='error', error=? WHERE id=?", (str(exc), candidate_id))
        raise HTTPException(502, str(exc)) from exc


class PromptBody(BaseModel):
    value: str


@app.put("/api/settings/prompt")
def update_prompt(body: PromptBody):
    if len(body.value.strip()) < 80:
        raise HTTPException(400, "Промпт слишком короткий: добавьте правила оценки и работы с доказательствами.")
    with connect() as db:
        db.execute("INSERT INTO settings(key,value,updated_at) VALUES('system_prompt',?,CURRENT_TIMESTAMP) ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=CURRENT_TIMESTAMP", (body.value.strip(),))
    return {"saved": True}


@app.delete("/api/candidates/{candidate_id}")
def delete_candidate(candidate_id: int):
    with connect() as db:
        row = db.execute("SELECT stored_name FROM candidates WHERE id=?", (candidate_id,)).fetchone()
        db.execute("DELETE FROM candidates WHERE id=?", (candidate_id,))
    if row and row["stored_name"]:
        (UPLOAD_DIR / row["stored_name"]).unlink(missing_ok=True)
    return {"deleted": True}


@app.delete("/api/vacancies/{vacancy_id}")
def delete_vacancy(vacancy_id: int):
    with connect() as db:
        vacancy = db.execute("SELECT stored_name FROM vacancies WHERE id=?", (vacancy_id,)).fetchone()
        files = [row["stored_name"] for row in db.execute("SELECT stored_name FROM candidates WHERE vacancy_id=?", (vacancy_id,)).fetchall() if row["stored_name"]]
        db.execute("DELETE FROM vacancies WHERE id=?", (vacancy_id,))
    if vacancy and vacancy["stored_name"]:
        files.append(vacancy["stored_name"])
    for stored_name in files:
        (UPLOAD_DIR / stored_name).unlink(missing_ok=True)
    return {"deleted": True}


DIST = Path(__file__).resolve().parents[1] / "dist"
if DIST.exists():
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")

    @app.get("/{path:path}")
    def spa(path: str):
        target = DIST / path
        return FileResponse(target if target.is_file() else DIST / "index.html")
