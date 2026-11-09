import csv
import io
import json
import os
import re
import unicodedata
from pathlib import Path

import httpx
from pypdf import PdfReader


def extract_pdf(data: bytes) -> str:
    try:
        reader = PdfReader(io.BytesIO(data))
        pages = []
        for number, page in enumerate(reader.pages, 1):
            text = (page.extract_text() or "").strip()
            if text:
                pages.append(f"[Страница {number}]\n{text}")
        if not pages:
            raise ValueError("В PDF нет извлекаемого текстового слоя. OCR в этой версии не поддерживается.")
        return "\n\n".join(pages)
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError("Не удалось прочитать PDF. Проверьте, что файл не повреждён.") from exc


def extract_text_file(data: bytes) -> str:
    for encoding in ("utf-8-sig", "cp1251"):
        try:
            text = data.decode(encoding).strip()
            if not text:
                raise ValueError("Файл пуст.")
            return text
        except UnicodeDecodeError:
            continue
    raise ValueError("Не удалось распознать кодировку TXT-файла.")


def extract_csv(data: bytes):
    text = extract_text_file(data)
    try:
        rows = list(csv.DictReader(io.StringIO(text)))
    except csv.Error as exc:
        raise ValueError("CSV содержит ошибку разметки.") from exc
    if not rows or not rows[0]:
        raise ValueError("CSV должен содержать заголовок и одну строку кандидата.")
    if len(rows) != 1:
        raise ValueError("Один CSV должен содержать ровно одного кандидата.")
    fields = {str(k).strip(): str(v or "").strip() for k, v in rows[0].items() if k}
    content = "\n".join(f"[{key}] {value}" for key, value in fields.items() if value)
    if not content:
        raise ValueError("В строке кандидата нет заполненных полей.")
    display = next((fields.get(k) for k in ("Имя", "имя", "name", "ФИО") if fields.get(k)), None)
    return content, fields, display


def suggest_criteria_locally(text: str):
    lower = text.lower()
    library = [
        ("Java", ["java"], "Коммерческая разработка на Java"),
        ("Spring", ["spring"], "Опыт со Spring Framework / Spring Boot"),
        ("Базы данных", ["sql", "postgres", "баз данных"], "Работа с реляционными базами данных"),
        ("Брокеры сообщений", ["kafka", "rabbitmq", "брокер"], "Опыт с брокерами сообщений"),
        ("Тестирование", ["тест", "junit", "mockito"], "Автоматизированное тестирование"),
        ("Инструменты разработки", ["git", "docker", "maven", "gradle"], "Git, сборка и контейнеризация"),
        ("Kafka Streams", ["kafka streams"], "Практический опыт Kafka Streams"),
        ("Protobuf", ["protobuf", "protocol buffers"], "Опыт с Protocol Buffers"),
        ("AI-агенты", ["ai-агент", "ai агент", "llm"], "Опыт разработки AI-агентов"),
    ]
    found = [(name, desc) for name, words, desc in library if any(w in lower for w in words)]
    if not found:
        found = [
            ("Релевантный опыт", "Опыт в задачах и роли из описания вакансии"),
            ("Ключевые навыки", "Подтверждённые профильные навыки"),
            ("Результаты", "Измеримые достижения и вклад"),
            ("Образование", "Соответствующее образование или подготовка"),
        ]
    found = found[:8]
    bonus_names = {"Kafka Streams", "Protobuf", "AI-агенты"}
    bonus_count = sum(name in bonus_names for name, _ in found)
    bonus_total = min(10, bonus_count * 3) if bonus_count else 0
    required = [pair for pair in found if pair[0] not in bonus_names]
    required_total = 100 - bonus_total
    result = []
    for i, (name, desc) in enumerate(required):
        weight = required_total // len(required) + (1 if i < required_total % len(required) else 0)
        result.append({"id": f"c{i+1}", "name": name, "description": desc, "type": "required", "weight": weight})
    for j, (name, desc) in enumerate(pair for pair in found if pair[0] in bonus_names):
        weight = bonus_total // bonus_count + (1 if j < bonus_total % bonus_count else 0)
        result.append({"id": f"c{len(result)+1}", "name": name, "description": desc, "type": "bonus", "weight": weight})
    return result


def _api_settings():
    local_key_file = Path("ProxyApiKey.txt")
    local_key = local_key_file.read_text(encoding="utf-8").strip() if local_key_file.exists() else ""
    return (
        os.getenv("OPENAI_BASE_URL", "https://api.proxyapi.ru/openai/v1").rstrip("/"),
        os.getenv("OPENAI_API_KEY", "") or local_key,
        os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
    )


def api_configured():
    return bool(_api_settings()[1])


def call_model(messages, schema_hint: str):
    base_url, key, model = _api_settings()
    if not key:
        raise RuntimeError("Proxy API не настроен. Добавьте OPENAI_API_KEY в .env и перезапустите сервер.")
    payload = {
        "model": model,
        "temperature": 0,
        "response_format": {"type": "json_object"},
        "messages": messages + [{"role": "user", "content": schema_hint}],
    }
    try:
        with httpx.Client(timeout=90) as client:
            response = client.post(f"{base_url}/chat/completions", headers={"Authorization": f"Bearer {key}"}, json=payload)
            response.raise_for_status()
            return json.loads(response.json()["choices"][0]["message"]["content"])
    except httpx.HTTPStatusError as exc:
        code = exc.response.status_code
        if code == 429:
            raise RuntimeError("Лимит запросов к модели исчерпан. Попробуйте позже.") from exc
        raise RuntimeError(f"Proxy API вернул ошибку {code}.") from exc
    except (httpx.HTTPError, KeyError, json.JSONDecodeError) as exc:
        raise RuntimeError("Не удалось получить корректный ответ от модели.") from exc


def suggest_criteria(text: str):
    if not api_configured():
        return suggest_criteria_locally(text), "local"
    schema = "Верни JSON: {\"criteria\":[{\"id\":\"c1\",\"name\":\"...\",\"description\":\"...\",\"type\":\"required|bonus\",\"weight\":число}]}. Сумма весов ровно 100, bonus не более 10."
    data = call_model([
        {"role": "system", "content": "Извлеки из вакансии краткую проверяемую шкалу критериев. Личные данные не включай."},
        {"role": "user", "content": text},
    ], schema)
    return data.get("criteria", []), "model"


def _find_quote(content: str, keywords):
    for line in content.splitlines():
        clean = line.strip()
        if clean and any(k.lower() in clean.lower() for k in keywords):
            return clean[:350]
    return None


def demo_evaluation(content, criteria):
    items = []
    for criterion in criteria:
        words = [w for w in re.findall(r"[A-Za-zА-Яа-яЁё0-9+#.]+", criterion["name"]) if len(w) > 2]
        quote = _find_quote(content, words)
        if quote:
            items.append({"criterion_id": criterion["id"], "score": 4, "status": "confirmed", "explanation": "В резюме найдено прямое упоминание по критерию.", "quotes": [quote]})
        else:
            items.append({"criterion_id": criterion["id"], "score": 0, "status": "missing", "explanation": "Нет сведений в предоставленном резюме.", "quotes": []})
    return {"criteria": items, "summary": "Предварительная локальная оценка по прямым совпадениям. Для смыслового анализа подключите proxy API."}


_TYPOGRAPHY_MAP = str.maketrans({
    "–": "-", "—": "-", "−": "-", "‑": "-",
    "“": '"', "”": '"', "„": '"', "«": '"', "»": '"',
    "’": "'", "‘": "'", "`": "'",
})


def _canonical_with_map(value: str):
    """Normalize PDF formatting while retaining positions in the original text."""
    canonical, positions = [], []
    pending_space_at = None
    for index, char in enumerate(value):
        normalized = unicodedata.normalize("NFKC", char).translate(_TYPOGRAPHY_MAP)
        for part in normalized:
            if part == "\u00ad":
                continue
            if part.isspace():
                if canonical and pending_space_at is None:
                    pending_space_at = index
                continue
            if pending_space_at is not None:
                canonical.append(" ")
                positions.append(pending_space_at)
                pending_space_at = None
            for folded in part.casefold():
                canonical.append(folded)
                positions.append(index)
    return "".join(canonical), positions


def locate_source_quote(content: str, quote: str):
    """Return the exact source slice for a quote that only differs in safe formatting."""
    if not isinstance(quote, str) or not quote.strip():
        return None
    canonical_content, positions = _canonical_with_map(content)
    canonical_quote, _ = _canonical_with_map(quote)
    if not canonical_quote or "..." in canonical_quote or "…" in quote:
        return None
    start = canonical_content.find(canonical_quote)
    if start < 0:
        return None
    end = start + len(canonical_quote) - 1
    if end >= len(positions):
        return None
    return content[positions[start]:positions[end] + 1].strip()


_EVIDENCE_STOP_WORDS = {
    "опыт", "работа", "работы", "работал", "работала", "знание", "знания", "навык", "навыки",
    "разработка", "разработки", "использование", "уверенная", "уверенный", "практический", "глубокое",
    "с", "и", "в", "на", "по", "для", "или", "из", "от", "до", "как", "к", "а", "но",
    "the", "and", "with", "for", "from", "using", "experience", "knowledge", "development",
}


def _evidence_tokens(value: str):
    canonical, _ = _canonical_with_map(value)
    return [token for token in re.findall(r"[a-zа-яё0-9+#.]+", canonical) if token not in _EVIDENCE_STOP_WORDS and (len(token) >= 2 or token.isdigit())]


def find_source_evidence(content: str, quote: str, criterion: dict):
    """Find a conservative exact source fragment when the model reformatted its quote."""
    lines = [line.strip() for line in content.splitlines() if line.strip() and not re.fullmatch(r"\[Страница \d+\]", line.strip())]
    fragments = list(lines)
    fragments.extend(f"{lines[i]}\n{lines[i + 1]}" for i in range(len(lines) - 1))
    quote_tokens = set(_evidence_tokens(quote))
    criterion_tokens = set(_evidence_tokens(f"{criterion.get('name', '')} {criterion.get('description', '')}"))
    if not quote_tokens and not criterion_tokens:
        return None

    best_fragment, best_score = None, 0.0
    for fragment in fragments:
        if len(fragment) > 700:
            continue
        fragment_tokens = set(_evidence_tokens(fragment))
        quote_matches = len(quote_tokens & fragment_tokens)
        criterion_matches = len(criterion_tokens & fragment_tokens)
        quote_ratio = quote_matches / max(len(quote_tokens), 1)
        criterion_ratio = criterion_matches / max(min(len(criterion_tokens), 6), 1)
        score = quote_ratio * 0.75 + min(criterion_ratio, 1.0) * 0.25
        strong_enough = (
            (quote_matches >= 2 and quote_ratio >= 0.5)
            or (0 < len(quote_tokens) <= 3 and quote_ratio == 1.0)
            or (quote_matches >= 1 and criterion_matches >= 2 and score >= 0.45)
        )
        if strong_enough and score > best_score:
            best_fragment, best_score = fragment, score
    return best_fragment


def validate_evaluation(data, criteria, content):
    criteria_by_id = {str(c["id"]): c for c in criteria}
    ids = set(criteria_by_id)
    items = data.get("criteria")
    if not isinstance(items, list) or {str(x.get("criterion_id")) for x in items} != ids:
        return False, "Ответ содержит неполный набор критериев."
    for item in items:
        if item.get("status") not in {"confirmed", "partial", "missing", "contradiction"}:
            return False, "Получен неизвестный статус."
        score = item.get("score")
        if not isinstance(score, (int, float)) or not 0 <= score <= 5:
            return False, "Оценка должна быть от 0 до 5."
        if item["status"] == "missing" and score != 0:
            return False, "Статус «нет сведений» должен иметь нулевую оценку."
        raw_quotes = item.get("quotes", [])
        if isinstance(raw_quotes, str):
            quotes = [raw_quotes]
        elif isinstance(raw_quotes, list):
            quotes = [quote for quote in raw_quotes if isinstance(quote, str) and quote.strip()]
        else:
            quotes = []
        if item["status"] == "missing":
            item["quotes"] = []
            continue
        source_quotes = []
        for quote in quotes:
            source_quote = locate_source_quote(content, quote)
            if source_quote is None:
                source_quote = find_source_evidence(content, quote, criteria_by_id[str(item["criterion_id"])])
            if source_quote and source_quote not in source_quotes:
                source_quotes.append(source_quote)
        if item["status"] in {"confirmed", "partial", "contradiction"} and not source_quotes:
            item["score"] = 0
            item["status"] = "missing"
            item["explanation"] = "Нет проверяемого подтверждения в предоставленном резюме."
            item["quotes"] = []
        else:
            item["quotes"] = source_quotes
    return True, ""


def evaluate(content, criteria, system_prompt):
    if not api_configured():
        return demo_evaluation(content, criteria), "local"
    schema = "Верни JSON: {\"criteria\":[{\"criterion_id\":\"id\",\"score\":0..5,\"status\":\"confirmed|partial|missing|contradiction\",\"explanation\":\"...\",\"quotes\":[\"дословная цитата\"]}],\"summary\":\"обоснованный вывод\"}. Для missing quotes=[]. Каждая цитата должна быть одним непрерывным фрагментом исходного резюме длиной 3–30 слов. Копируй символы дословно: не используй многоточия, не склеивай разные предложения и не добавляй номер страницы внутрь цитаты."
    prompt = f"КРИТЕРИИ:\n{json.dumps(criteria, ensure_ascii=False)}\n\nРЕЗЮМЕ:\n{content}"
    last_error = ""
    for attempt in range(2):
        extra = f"\nПредыдущий ответ отклонён сервером: {last_error}. Скопируй более короткую непрерывную цитату прямо из текста резюме, без пересказа, многоточий и добавленных символов." if attempt else ""
        data = call_model([{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt + extra}], schema)
        valid, last_error = validate_evaluation(data, criteria, content)
        if valid:
            return data, "model"
    raise RuntimeError(f"Ответ модели не прошёл проверку цитат: {last_error}")


def compute_result(evaluation, criteria):
    by_id = {str(c["id"]): c for c in criteria}
    total = sum(by_id[str(item["criterion_id"])]["weight"] * item["score"] / 5 for item in evaluation["criteria"])
    evaluation["score"] = round(total)
    evaluation["strengths"] = [by_id[str(i["criterion_id"])]["name"] for i in evaluation["criteria"] if i["score"] >= 4]
    evaluation["gaps"] = [by_id[str(i["criterion_id"])]["name"] for i in evaluation["criteria"] if i["status"] in {"missing", "contradiction"}]
    return evaluation
