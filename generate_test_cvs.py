from __future__ import annotations

import random
from datetime import date
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "Test CV"
OUTPUT.mkdir(parents=True, exist_ok=True)
RNG = random.Random(20261008)

FONT_REGULAR = Path("C:/Windows/Fonts/arial.ttf")
FONT_BOLD = Path("C:/Windows/Fonts/arialbd.ttf")
pdfmetrics.registerFont(TTFont("Resume", str(FONT_REGULAR)))
pdfmetrics.registerFont(TTFont("ResumeBold", str(FONT_BOLD)))

FIRST_NAMES = [
    "Алексей", "Антон", "Артём", "Борис", "Вадим", "Виктор", "Глеб", "Даниил", "Денис", "Егор",
    "Иван", "Илья", "Кирилл", "Лев", "Максим", "Михаил", "Никита", "Олег", "Павел", "Роман",
    "Сергей", "Тимофей", "Фёдор", "Юрий", "Алина", "Анастасия", "Валерия", "Дарья", "Екатерина", "Елена",
    "Ирина", "Ксения", "Марина", "Надежда", "Наталья", "Ольга", "Полина", "Светлана", "София", "Татьяна",
]
LAST_NAMES = [
    "Алексеев", "Беляев", "Быков", "Васильев", "Волков", "Воронов", "Гаврилов", "Громов", "Данилов", "Ершов",
    "Жуков", "Зайцев", "Иванов", "Ковалёв", "Козлов", "Комаров", "Крылов", "Кузнецов", "Лебедев", "Макаров",
    "Мельников", "Миронов", "Морозов", "Никитин", "Орлов", "Павлов", "Петров", "Романов", "Семёнов", "Соколов",
    "Тарасов", "Титов", "Фёдоров", "Фомин", "Чернов", "Шаров", "Широков", "Щербаков", "Яковлев", "Яшин",
]
PATRONYMICS = [
    "Александрович", "Алексеевич", "Андреевич", "Антонович", "Владимирович", "Дмитриевич", "Евгеньевич", "Игоревич",
    "Максимович", "Михайлович", "Николаевич", "Олегович", "Павлович", "Романович", "Сергеевич", "Александровна",
    "Алексеевна", "Андреевна", "Владимировна", "Дмитриевна", "Евгеньевна", "Игоревна", "Михайловна", "Сергеевна",
]
CITIES = ["Москва", "Санкт-Петербург", "Казань", "Екатеринбург", "Новосибирск", "Самара", "Пермь", "Уфа", "Тула", "Томск", "Омск", "Воронеж"]
COMPANIES = ["ООО Технопоток", "АО Север Софт", "ООО Кодовая Среда", "ООО ФинЛайн", "АО ДатаМост", "ООО Облако Систем", "ООО Ритейл Лаб", "АО Логика Плюс", "ООО Интегра Хаб", "ООО Платформа 24"]
UNIVERSITIES = ["МГТУ им. Н. Э. Баумана", "НИУ ИТМО", "СПбПУ Петра Великого", "КНИТУ-КАИ", "УрФУ", "НГУ", "Самарский университет", "Томский политехнический университет"]
DOMAINS = ["финтех", "электронная коммерция", "логистика", "телеком", "документооборот", "аналитическая платформа", "страхование", "HR-tech"]

CORE_TASKS = [
    "разработка и сопровождение микросервисов на Java",
    "проектирование REST API и интеграционных контрактов",
    "оптимизация запросов и схем хранения данных",
    "проведение code review и декомпозиция задач",
    "написание unit- и интеграционных тестов",
    "поиск причин инцидентов и устранение узких мест",
    "участие в проектировании архитектуры сервисов",
    "настройка CI/CD и контейнеризация приложений",
    "интеграция сервисов через брокеры сообщений",
    "подготовка технической документации",
]
ACHIEVEMENTS = [
    "сократил среднее время ответа API на 35%",
    "повысил покрытие критичных модулей тестами с 42% до 78%",
    "уменьшил количество ошибок в production на 28%",
    "перевёл модульный монолит на набор из 6 микросервисов",
    "ускорил сборку проекта с 18 до 7 минут",
    "реализовал обработку до 4 000 сообщений в секунду",
    "снизил нагрузку на базу данных на 30%",
    "автоматизировал выпуск релизов и сократил его до 20 минут",
    "подготовил библиотеку общих компонентов для 5 команд",
    "провёл техническое наставничество для 3 разработчиков",
]


def level_for(index: int):
    if index < 20:
        return "Junior Java Developer", RNG.uniform(0.5, 2.0)
    if index < 55:
        return "Java Developer", RNG.uniform(2.0, 4.5)
    if index < 88:
        return "Senior Java Developer", RNG.uniform(4.5, 8.5)
    return "Lead Java Developer", RNG.uniform(7.0, 12.0)


def profile_for(index: int):
    title, years = level_for(index)
    java_version = RNG.choice(["Java 8", "Java 11", "Java 17", "Java 21"])
    spring = RNG.sample(["Spring Boot", "Spring Core", "Spring Web", "Spring Data", "Spring Security"], k=RNG.randint(2, 5))
    databases = RNG.sample(["PostgreSQL", "MySQL", "Oracle", "MongoDB", "Redis", "ClickHouse"], k=RNG.randint(1, 3))
    messaging = []
    if index % 5 != 0:
        messaging.append(RNG.choice(["Apache Kafka", "RabbitMQ"]));
    if index % 4 == 0:
        messaging.append("Kafka Streams")
    protocols = ["REST", "JSON"]
    if index % 6 == 0:
        protocols.append("Protobuf")
    if index % 9 == 0:
        protocols.append("gRPC")
    testing = RNG.sample(["JUnit 5", "Mockito", "Testcontainers", "WireMock", "REST Assured"], k=RNG.randint(1, 4))
    tools = RNG.sample(["Git", "Maven", "Gradle", "Docker", "Kubernetes", "Jenkins", "GitLab CI", "Grafana", "Prometheus", "ELK"], k=RNG.randint(4, 7))
    ai = []
    if index % 10 == 0:
        ai = ["OpenAI API", "LangChain4j", "RAG", "AI-агенты"]
    elif index % 10 == 1:
        ai = ["OpenAI API"]
    return {
        "title": title,
        "years": round(years, 1),
        "java": java_version,
        "spring": spring,
        "databases": databases,
        "messaging": messaging,
        "protocols": protocols,
        "testing": testing,
        "tools": tools,
        "ai": ai,
    }


def styles():
    base = getSampleStyleSheet()
    return {
        "name": ParagraphStyle("Name", parent=base["Title"], fontName="ResumeBold", fontSize=19, leading=22, textColor=colors.HexColor("#111111"), spaceAfter=3),
        "title": ParagraphStyle("Title", parent=base["Normal"], fontName="ResumeBold", fontSize=11.5, leading=14, textColor=colors.HexColor("#1d3fd8"), spaceAfter=8),
        "section": ParagraphStyle("Section", parent=base["Heading2"], fontName="ResumeBold", fontSize=10.5, leading=13, textColor=colors.HexColor("#111111"), spaceBefore=9, spaceAfter=5, uppercase=True, keepWithNext=1),
        "body": ParagraphStyle("Body", parent=base["BodyText"], fontName="Resume", fontSize=8.6, leading=12.1, textColor=colors.HexColor("#242424"), spaceAfter=3),
        "small": ParagraphStyle("Small", parent=base["BodyText"], fontName="Resume", fontSize=7.4, leading=10, textColor=colors.HexColor("#686868"), spaceAfter=2),
        "job": ParagraphStyle("Job", parent=base["BodyText"], fontName="ResumeBold", fontSize=9.2, leading=12, textColor=colors.HexColor("#111111"), spaceAfter=2),
        "bullet": ParagraphStyle("Bullet", parent=base["BodyText"], fontName="Resume", fontSize=8.4, leading=11.5, leftIndent=10, firstLineIndent=-7, bulletIndent=2, spaceAfter=2),
    }


ST = styles()


def footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#d0d0d0"))
    canvas.line(18 * mm, 13 * mm, 192 * mm, 13 * mm)
    canvas.setFont("Resume", 6.8)
    canvas.setFillColor(colors.HexColor("#777777"))
    canvas.drawString(18 * mm, 8.5 * mm, "СИНТЕТИЧЕСКОЕ РЕЗЮМЕ - ТОЛЬКО ДЛЯ ТЕСТИРОВАНИЯ")
    canvas.drawRightString(192 * mm, 8.5 * mm, f"Страница {doc.page}")
    canvas.restoreState()


def p(text: str, style="body"):
    safe = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return Paragraph(safe, ST[style])


def section(title: str):
    return [Spacer(1, 2 * mm), HRFlowable(width="100%", thickness=0.7, color=colors.HexColor("#111111")), p(title.upper(), "section")]


def build_resume(index: int):
    profile = profile_for(index)
    first = FIRST_NAMES[(index * 7) % len(FIRST_NAMES)]
    last = LAST_NAMES[(index * 11) % len(LAST_NAMES)]
    patronymic = PATRONYMICS[(index * 13) % len(PATRONYMICS)]
    full_name = f"{last} {first} {patronymic}"
    city = CITIES[index % len(CITIES)]
    synthetic_id = f"SYN-JAVA-{index + 1:03d}"
    salary = RNG.randrange(90, 410, 10)
    years = profile["years"]
    total_months = max(6, round(years * 12))
    years_part, months_part = divmod(total_months, 12)
    experience_label = f"{years_part} лет {months_part} месяцев" if months_part else f"{years_part} лет"
    updated = date(2026, ((index * 3) % 9) + 1, ((index * 7) % 27) + 1)

    filename = OUTPUT / f"CV_{index + 1:03d}_{last}_{first}.pdf"
    doc = SimpleDocTemplate(
        str(filename), pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm,
        topMargin=16 * mm, bottomMargin=18 * mm, title=f"{full_name} - Java Developer",
        author="Synthetic Test Data Generator", subject="Синтетическое резюме для тестирования оценки",
    )
    story = []
    story.append(Table([[p("СИНТЕТИЧЕСКОЕ РЕЗЮМЕ", "small"), p(synthetic_id, "small")]], colWidths=[105 * mm, 69 * mm], style=TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#d7ff36")), ("BOX", (0, 0), (-1, -1), 0.8, colors.black),
        ("ALIGN", (1, 0), (1, 0), "RIGHT"), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (-1, -1), 7), ("RIGHTPADDING", (0, 0), (-1, -1), 7),
    ])))
    story += [Spacer(1, 6 * mm), p(full_name, "name"), p(profile["title"], "title")]
    story.append(p(f"Город: {city} | Формат работы: удалённо или гибрид | Готовность к командировкам: {RNG.choice(['да', 'по договорённости', 'нет'])}", "small"))
    story.append(p(f"Контакты: candidate{index + 1:03d}@example.invalid | +7 (000) 000-{index + 1:04d}", "small"))
    story += section("Желаемая должность и зарплата")
    story += [p(profile["title"], "job"), p(f"Желаемая зарплата: {salary} 000 руб. | Специализация: программист, разработчик"), p("Занятость: полная | График: полный день, удалённая работа")]
    story += section("Опыт работы")
    story.append(p(f"Общий опыт: {experience_label}", "job"))

    job_count = 1 if years < 2 else 2 if years < 5 else 3
    remaining_months = total_months
    end_year, end_month = updated.year, updated.month
    for job_index in range(job_count):
        if job_index == job_count - 1:
            duration = max(6, remaining_months)
        else:
            max_slice = max(7, remaining_months - 6 * (job_count - job_index - 1))
            duration = RNG.randint(6, max(6, min(36, max_slice)))
        remaining_months -= duration
        start_total = end_year * 12 + end_month - duration
        start_year, start_month_zero = divmod(start_total, 12)
        start_month = start_month_zero or 12
        if start_month_zero == 0:
            start_year -= 1
        period_end = "настоящее время" if job_index == 0 else f"{end_month:02d}.{end_year}"
        period = f"{start_month:02d}.{start_year} - {period_end} ({duration // 12} г. {duration % 12} мес.)"
        company = COMPANIES[(index + job_index * 3) % len(COMPANIES)]
        role = profile["title"] if job_index == 0 else RNG.choice(["Java Developer", "Junior Java Developer", "Backend Developer"])
        domain = DOMAINS[(index + job_index) % len(DOMAINS)]
        stack_parts = [profile["java"], *profile["spring"], *profile["databases"], *profile["messaging"], *profile["protocols"], *profile["testing"], *profile["tools"]]
        if job_index == 0:
            stack_parts += profile["ai"]
        tasks = RNG.sample(CORE_TASKS, k=4 if years >= 4 else 3)
        achievements = RNG.sample(ACHIEVEMENTS, k=2 if years >= 3 else 1)
        block = [p(period, "small"), p(company, "job"), p(f"{role} | Проект: {domain}", "body"), p("Обязанности:", "job")]
        block += [Paragraph(task, ST["bullet"], bulletText="-") for task in tasks]
        block += [p("Достижения:", "job")]
        block += [Paragraph(item, ST["bullet"], bulletText="-") for item in achievements]
        block += [p("Технологический стек: " + ", ".join(dict.fromkeys(stack_parts)), "body")]
        story.append(KeepTogether(block))
        story.append(Spacer(1, 4 * mm))
        end_year, end_month = start_year, start_month

    story += section("Образование")
    education_year = max(2010, 2026 - int(years) - RNG.randint(2, 6))
    story += [p(f"{education_year} | {UNIVERSITIES[index % len(UNIVERSITIES)]}", "job"), p(RNG.choice(["Прикладная информатика", "Программная инженерия", "Информатика и вычислительная техника", "Информационные системы и технологии"]))]
    if index % 3 == 0:
        story += [p("Дополнительное образование", "job"), p(RNG.choice(["Алгоритмы и структуры данных", "Архитектура высоконагруженных систем", "Spring Framework: продвинутый курс", "Kubernetes для разработчиков"]))]

    story += section("Навыки")
    all_skills = [profile["java"], *profile["spring"], *profile["databases"], *profile["messaging"], *profile["protocols"], *profile["testing"], *profile["tools"], *profile["ai"]]
    story.append(p("   •   ".join(dict.fromkeys(all_skills))))
    story += section("Языки")
    story.append(p(f"Русский - родной | Английский - {RNG.choice(['A2', 'B1', 'B2', 'C1'])}"))
    story += section("О себе")
    about = RNG.choice([
        "Java-разработчик, ориентированный на надёжность сервисов и понятный код. Предпочитаю подтверждать решения измерениями и тестами.",
        "Backend-разработчик с опытом командной разработки. Участвую в обсуждении архитектуры, провожу code review и документирую решения.",
        "Развиваюсь в направлении распределённых систем. Ценю автоматизацию, наблюдаемость и воспроизводимые процессы доставки.",
        "Специализируюсь на Java и Spring. В работе уделяю внимание качеству API, производительности баз данных и тестируемости кода.",
    ])
    story.append(p(about))
    if index % 4 == 1:
        story.append(p("Прямого опыта с Kafka Streams и Protobuf нет; изучал документацию и учебные примеры.", "body"))
    if index % 7 == 2:
        story.append(p("AI-агентов в коммерческих проектах не разрабатывал.", "body"))
    story.append(Spacer(1, 5 * mm))
    story.append(p(f"Резюме обновлено {updated.strftime('%d.%m.%Y')} | Все сведения в документе синтетические.", "small"))
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return filename


if __name__ == "__main__":
    existing = list(OUTPUT.glob("*.pdf"))
    if existing:
        raise SystemExit(f"Папка уже содержит PDF ({len(existing)}). Очистите её перед повторной генерацией.")
    paths = [build_resume(index) for index in range(100)]
    print(f"Created {len(paths)} synthetic resumes in {OUTPUT}")
