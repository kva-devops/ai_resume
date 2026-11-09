"""Serialize the reference model's manually assigned ratings; no model/API calls.

Scores below were assigned after reading the extracted evidence for all 50 CVs.
Code attaches verbatim evidence and computes the rubric's weighted arithmetic.
"""
import json
import re
from pathlib import Path
from reference_extract import ROOT, extract, evidence

# Columns: Java, Spring/backend, data, architecture, testing, delivery, bonus.
AUTHORED_SCORES = {
    51: [4,4,5,4,3,3,3], 52: [3,4,4,5,3,4,0],
    53: [3,4,4,4,4,4,3], 54: [4,4,5,5,3,5,1],
    55: [4,4,3,5,5,3,3], 56: [4,4,4,5,4,5,0],
    57: [4,4,4,5,5,5,3], 58: [4,4,5,5,4,4,1],
    59: [4,4,4,5,5,5,0], 60: [4,4,5,4,5,5,0],
    61: [4,4,5,5,4,5,3], 62: [4,4,5,5,3,5,1],
    63: [4,4,4,4,5,5,0], 64: [4,4,5,5,4,4,3],
    65: [4,4,5,5,5,5,3], 66: [4,4,5,4,5,5,1],
    67: [4,4,3,4,5,5,3], 68: [4,4,4,4,4,5,0],
    69: [3,4,4,5,4,5,3], 70: [4,3,5,4,4,5,1],
    71: [3,4,5,5,5,4,3], 72: [4,4,4,5,4,5,0],
    73: [4,4,5,5,5,4,3], 74: [4,4,3,5,5,5,1],
    75: [4,4,5,4,5,5,0], 76: [4,4,4,5,4,3,0],
    77: [4,4,4,4,4,5,3], 78: [4,4,4,5,5,5,1],
    79: [4,4,5,5,5,5,3], 80: [4,4,5,4,5,5,0],
    81: [4,4,5,5,5,5,3], 82: [4,4,5,5,4,5,3],
    83: [4,4,4,4,5,5,0], 84: [4,4,4,5,5,4,0],
    85: [4,4,5,5,5,4,3], 86: [4,4,4,5,4,5,1],
    87: [4,4,3,5,5,5,0], 88: [4,4,4,5,5,4,0],
    89: [4,4,4,5,4,5,3], 90: [4,4,4,5,4,5,1],
    91: [4,4,4,4,4,5,3], 92: [4,4,4,5,5,5,0],
    93: [4,4,4,5,3,5,3], 94: [4,4,4,5,4,5,1],
    95: [3,4,4,4,4,5,0], 96: [4,4,4,5,4,5,0],
    97: [4,4,4,4,4,5,3], 98: [4,4,4,5,4,4,1],
    99: [4,4,5,4,4,5,0], 100: [4,4,5,4,5,5,3],
}

JAVA_DEV = 'разработка и сопровождение микросервисов на Java'
REVIEW = 'проведение code review и декомпозиция задач'
LIBRARY = 'подготовил библиотеку общих компонентов для 5 команд'
API = 'проектирование REST API и интеграционных контрактов'
API_SPEED = 'сократил среднее время ответа API на 35%'
OPTIMIZE = 'оптимизация запросов и схем хранения данных'
DB_LOAD = 'снизил нагрузку на базу данных на 30%'
ARCH = 'участие в проектировании архитектуры сервисов'
BROKER = 'интеграция сервисов через брокеры сообщений'
MIGRATION = 'перевёл модульный монолит на набор из 6 микросервисов'
THROUGHPUT = 'реализовал обработку до 4 000 сообщений в секунду'
TESTS = 'написание unit- и интеграционных тестов'
COVERAGE = 'повысил покрытие критичных модулей тестами с 42% до 78%'
CI = 'настройка CI/CD и контейнеризация приложений'
BUILD = 'ускорил сборку проекта с 18 до 7 минут'
RELEASE = 'автоматизировал выпуск релизов и сократил его до 20 минут'
STUDY = 'Прямого опыта с Kafka Streams и Protobuf нет; изучал документацию и учебные примеры.'
NO_AI = 'AI-агентов в коммерческих проектах не разрабатывал.'

TECH_PATTERNS = {
    'java_core': r'Java \d+',
    'spring_backend': r'Spring (?:Boot|Core|Web|Data|Security)',
    'data': r'PostgreSQL|MySQL|Oracle|MongoDB|ClickHouse|Redis',
    'architecture': r'Apache Kafka|RabbitMQ|Kafka\s+Streams|REST|JSON|Protobuf|gRPC',
    'testing': r'JUnit\s+5|Mockito|Testcontainers|WireMock|REST\s+Assured',
    'delivery': r'GitLab CI|Git|Maven|Gradle|Docker|Jenkins|Kubernetes|ELK|Grafana|Prometheus',
    'bonus': r'Kafka\s+Streams|Protobuf|gRPC|LangChain4j|AI-агенты',
}

def present(text, values):
    return [value for value in values if value in text]

def criterion_result(cid, score, text, ev):
    stack = ev['stacks'][0]
    tech = list(dict.fromkeys(m.group() for m in re.finditer(TECH_PATTERNS[cid], stack)))
    quotes = tech.copy()
    status = 'confirmed' if score >= 4 else 'partial'
    if cid == 'java_core':
        quotes += present(text, [JAVA_DEV, REVIEW, LIBRARY, 'провожу code review'])
        explanation = ('Java 8+ указан в стеке рабочих проектов; есть свидетельства качества разработки (review или общие компоненты). Детали JVM, concurrency и коллекций не раскрыты.' if score == 4 else 'Java 8+ указан в рабочих проектах, но конкретные приёмы Java core, JVM, concurrency и коллекций не раскрыты.')
    elif cid == 'spring_backend':
        quotes += present(text, [JAVA_DEV, API, API_SPEED, MIGRATION])
        explanation = ('Spring указан в рабочих проектах вместе с конкретной backend-работой; устройство Spring-компонентов и их реализация не детализированы.' if score == 4 else 'Spring Core/Boot указан в проектном стеке, но конкретная разработка REST API или микросервисов в обязанностях не раскрыта.')
    elif cid == 'data':
        quotes += present(text, [OPTIMIZE, DB_LOAD])
        explanation = {3: 'СУБД указана в рабочем стеке; конкретные запросы, схемы, транзакции и результаты оптимизации не раскрыты.', 4: 'Практика работы с данными подтверждена оптимизацией запросов/схем либо измеримым снижением нагрузки; подробности решений и транзакций не раскрыты.', 5: 'Указаны оптимизация запросов и схем хранения, применявшиеся СУБД и измеримое снижение нагрузки на базу на 30%.'}[score]
    elif cid == 'architecture':
        quotes += present(text, [JAVA_DEV, API, ARCH, BROKER, MIGRATION, THROUGHPUT])
        explanation = ('Есть практическая архитектурная/интеграционная работа и измеримый результат: миграция монолита на 6 сервисов или обработка 4000 сообщений/с.' if score == 5 else 'Описана практическая разработка микросервисов, API/контрактов или интеграция сервисов; сложные распределённые гарантии и архитектурные компромиссы не раскрыты.')
    elif cid == 'testing':
        quotes += present(text, [TESTS, COVERAGE])
        explanation = {3: 'Тестовые инструменты перечислены в рабочем стеке; конкретное написание тестов и измеримый результат тестирования не описаны.', 4: 'Явно указано написание unit- и интеграционных тестов и перечислены тестовые инструменты.', 5: 'Тестовые инструменты и результат подтверждены ростом покрытия критичных модулей с 42% до 78%.'}[score]
    elif cid == 'delivery':
        quotes += present(text, [CI, BUILD, RELEASE])
        explanation = {3: 'Инструменты сборки/поставки и наблюдаемости указаны в рабочем стеке, но конкретная настройка конвейера и её результат не описаны.', 4: 'Есть явная настройка CI/CD и контейнеризация; инструменты поставки/наблюдаемости перечислены, измеримые результаты не приведены.', 5: 'Практика поставки подтверждена измеримым ускорением сборки до 7 минут или автоматизацией выпуска релизов до 20 минут.'}[score]
    else:
        quotes += present(text, [STUDY, NO_AI])
        if score == 3:
            explanation = 'В стеке рабочих проектов указаны ' + ', '.join(t.replace('\n', ' ') for t in tech) + '; конкретный сценарий их реализации и результат не раскрыты. Бонус начислен один раз.'
            if NO_AI in text:
                explanation += ' Отрицание коммерческой разработки AI-агентов не отменяет другие подтверждённые технологии.'
            if STUDY in text:
                explanation += ' Kafka Streams/Protobuf упомянуты только как изучение; балл здесь основан на gRPC.'
        elif score == 1:
            explanation = 'Подтверждено только изучение Kafka Streams/Protobuf по документации и учебным примерам; прямой практический опыт явно отрицается.'
        elif NO_AI in text:
            status = 'contradiction'
            explanation = 'Коммерческая разработка AI-агентов явно отрицается; других целевых бонусных технологий не подтверждено. OpenAI API сам по себе не доказывает работу с агентами.'
        else:
            status = 'missing'
            quotes = []
            explanation = 'Kafka Streams, Protobuf/gRPC и AI-агенты не подтверждены; это недостаток сведений, а не доказанное отсутствие навыка. Обычный Kafka и OpenAI API не засчитываются сами по себе.'
    assert score == 0 or quotes
    assert all(q in text for q in quotes), (cid, quotes)
    return {'criterion_id': cid, 'score': score, 'status': status, 'explanation': explanation, 'quotes': list(dict.fromkeys(quotes))}

def main():
    rubric = json.loads((ROOT / 'benchmark/rubric.json').read_text(encoding='utf-8'))
    files = sorted((ROOT / 'Test CV').glob('*.pdf'))[:50]
    assert len(files) == 50
    rows = []
    for path in files:
        number = int(path.name.split('_')[1])
        text = extract(path)
        ev = evidence(text)
        assert ev['stacks'], path.name
        scores = AUTHORED_SCORES[number]
        criteria = [criterion_result(c['id'], s, text, ev) for c, s in zip(rubric['criteria'], scores)]
        total = round(sum(c['weight'] * s / 5 for c, s in zip(rubric['criteria'], scores)), 2)
        strengths = [c['name'] for c, s in zip(rubric['criteria'], scores) if s == 5]
        limitations = [c['name'] for c, s in zip(rubric['criteria'], scores) if s <= 3]
        summary = 'Подтверждён опыт Java/Spring backend. '
        if strengths:
            summary += 'Наиболее сильные свидетельства: ' + ', '.join(strengths) + '. '
        if limitations:
            summary += 'Требуют уточнения: ' + ', '.join(limitations) + '. '
        summary += 'JVM/concurrency/коллекции не детализированы. Итог отражает полноту свидетельств в резюме; решения о найме нет.'
        rows.append({'file': path.name, 'candidate_id': path.stem, 'criteria': criteria, 'score': total, 'summary': summary})
    out = ROOT / 'benchmark/reference_gpt6_astra.json'
    out.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    # Reopen the artifact and all source PDFs, validating the delivered data.
    saved = json.loads(out.read_text(encoding='utf-8'))
    assert len(saved) == 50
    assert len({r['file'] for r in saved}) == 50
    count = 0
    for row, path in zip(saved, files):
        assert row['file'] == path.name
        text = extract(path)
        assert len(row['criteria']) == 7
        for result, c in zip(row['criteria'], rubric['criteria']):
            assert result['criterion_id'] == c['id']
            assert 0 <= result['score'] <= 5
            assert result['status'] in {'confirmed', 'partial', 'missing', 'contradiction'}
            assert result['score'] == 0 or result['quotes']
            for quote in result['quotes']:
                assert quote in text, (path.name, quote)
                count += 1
        assert row['score'] == round(sum(c['weight'] * r['score'] / 5 for c, r in zip(rubric['criteria'], row['criteria'])), 2)
    print(json.dumps({'results': len(saved), 'criteria': len(saved)*7, 'exact_quotes_verified': count, 'min_score': min(r['score'] for r in saved), 'max_score': max(r['score'] for r in saved), 'output': str(out)}, ensure_ascii=False))

if __name__ == '__main__':
    main()
