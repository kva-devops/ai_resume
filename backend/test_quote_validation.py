import unittest

from backend.services import find_source_evidence, locate_source_quote, validate_evaluation


class QuoteValidationTests(unittest.TestCase):
    content = "[Страница 1]\nJava — разработчик\nSpring   Boot и PostgreSQL"
    criteria = [{"id": "c1"}]

    def test_safe_pdf_formatting_is_matched_to_exact_source(self):
        data = {"criteria": [{
            "criterion_id": "c1",
            "score": 4,
            "status": "confirmed",
            "explanation": "Подтверждено",
            "quotes": ["java – разработчик Spring Boot"],
        }]}
        valid, error = validate_evaluation(data, self.criteria, self.content)
        self.assertTrue(valid, error)
        self.assertEqual(data["criteria"][0]["quotes"], ["Java — разработчик\nSpring   Boot"])

    def test_ellipsis_is_not_accepted_as_exact_quote(self):
        self.assertIsNone(locate_source_quote(self.content, "Java ... PostgreSQL"))

    def test_reformatted_model_quote_is_retrieved_from_source(self):
        criterion = {"id": "c1", "name": "Java и PostgreSQL", "description": "Стек Java, Spring Boot и PostgreSQL"}
        evidence = find_source_evidence(self.content, "Стек: Java, Spring Boot, PostgreSQL", criterion)
        self.assertEqual(evidence, "Java — разработчик\nSpring   Boot и PostgreSQL")

    def test_unverifiable_quote_downgrades_criterion_instead_of_failing_candidate(self):
        data = {"criteria": [{
            "criterion_id": "c1",
            "score": 5,
            "status": "confirmed",
            "explanation": "Указан Kubernetes",
            "quotes": ["Kubernetes в production"],
        }]}
        valid, error = validate_evaluation(data, self.criteria, self.content)
        self.assertTrue(valid, error)
        self.assertEqual(data["criteria"][0]["status"], "missing")
        self.assertEqual(data["criteria"][0]["score"], 0)
        self.assertEqual(data["criteria"][0]["quotes"], [])

    def test_missing_status_discards_model_evidence(self):
        data = {"criteria": [{
            "criterion_id": "c1",
            "score": 0,
            "status": "missing",
            "explanation": "Нет сведений",
            "quotes": ["Java"],
        }]}
        valid, error = validate_evaluation(data, self.criteria, self.content)
        self.assertTrue(valid, error)
        self.assertEqual(data["criteria"][0]["quotes"], [])

    def test_missing_quote_downgrades_instead_of_failing_candidate(self):
        data = {"criteria": [{
            "criterion_id": "c1",
            "score": 4,
            "status": "confirmed",
            "explanation": "Подтверждено без цитаты",
            "quotes": [],
        }]}
        valid, error = validate_evaluation(data, self.criteria, self.content)
        self.assertTrue(valid, error)
        self.assertEqual(data["criteria"][0]["status"], "missing")
        self.assertEqual(data["criteria"][0]["score"], 0)


if __name__ == "__main__":
    unittest.main()
