"""Multi-language verified code generation tests."""

from __future__ import annotations

import pytest

from app.chat_service import chat, is_code_question
from brain.code_catalog import CODE_TASKS, SUPPORTED_LANGUAGES, get_catalog_entry
from brain.code_languages import (
    build_multilang_prompt,
    check_code_security,
    detect_code_language,
    detect_code_task,
    evaluate_multilang,
    extract_code,
    generate_from_catalog,
    runtime_available,
)


@pytest.mark.parametrize("language", SUPPORTED_LANGUAGES)
@pytest.mark.parametrize("task", CODE_TASKS)
def test_catalog_entry_is_secure_and_passes(language: str, task: str) -> None:
    entry = get_catalog_entry(language, task)
    assert entry is not None
    security = check_code_security(entry["code"], language)
    assert security["safe"] is True
    evaluation = evaluate_multilang(entry["code"], language, entry["tests"], task=task)
    assert evaluation["passed_tests"] is True


@pytest.mark.parametrize(
    ("prompt", "language", "task"),
    [
        ("Write a JavaScript function to add two numbers.", "javascript", "add_two_numbers"),
        ("Write a TypeScript function fib(n) for Fibonacci.", "typescript", "fibonacci"),
        ("Write a Java function count_vowels(s).", "java", "count_vowels"),
        ("Write a Go function merge_sorted(a, b).", "go", "merge_sorted"),
        ("Write a Rust function is_palindrome(s).", "rust", "is_palindrome"),
        ("Write a C++ function to add two numbers.", "cpp", "add_two_numbers"),
    ],
)
def test_detect_language_and_task(prompt: str, language: str, task: str) -> None:
    assert detect_code_language(prompt) == language
    assert detect_code_task(prompt) == task


def test_is_code_question_multilang_triggers() -> None:
    assert is_code_question("Write a JavaScript function to sort an array")
    assert is_code_question("Write a Rust function fib(n)")
    assert is_code_question("Generate Java code for palindrome check")


@pytest.mark.parametrize("language", SUPPORTED_LANGUAGES)
@pytest.mark.parametrize("task", CODE_TASKS)
def test_chat_generates_verified_code(language: str, task: str) -> None:
    label = {
        "python": "Python",
        "javascript": "JavaScript",
        "typescript": "TypeScript",
        "java": "Java",
        "go": "Go",
        "rust": "Rust",
        "cpp": "C++",
    }[language]
    prompt = build_multilang_prompt(label, task)
    result = chat(prompt, session_id=f"pytest-ml-{language}-{task}")
    assert result["kind"] == "code"
    assert result.get("language") == language or language == "python"
    code = extract_code(result["reply"], language)
    entry = get_catalog_entry(language, task)
    assert code.strip() == entry["code"].strip()
    evaluation = evaluate_multilang(code, language, entry["tests"], task=task)
    assert evaluation["passed_tests"] is True
    assert check_code_security(code, language)["safe"] is True


def test_generate_from_catalog_direct() -> None:
    result = generate_from_catalog("Write a JavaScript function to add two numbers.")
    assert result is not None
    assert result["method"] == "verified_catalog"
    assert "function add" in result["answer"]
