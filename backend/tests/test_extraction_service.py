"""Unit tests for the regex-based extraction (no LLM required)."""
from datetime import date

from app.services.extraction import extract_patient_info


def test_extract_first_last_dob_labels():
    text = (
        "Patient Order Form\n"
        "First Name: Sarah\n"
        "Last Name: Connor\n"
        "Date of Birth: 05/15/1985\n"
        "Procedure: routine"
    )
    r = extract_patient_info(text)
    assert r.first_name == "Sarah"
    assert r.last_name == "Connor"
    assert r.date_of_birth == date(1985, 5, 15)


def test_extract_patient_name_inline():
    text = "Patient Name: John Q. Smith\nDOB: January 3, 1972\n"
    r = extract_patient_info(text)
    assert r.first_name == "John"
    assert r.last_name == "Smith"
    assert r.date_of_birth == date(1972, 1, 3)


def test_extract_lastname_firstname_comma():
    text = "Name: Doe, Jane\nDate of Birth: 1990-01-15"
    r = extract_patient_info(text)
    assert r.first_name == "Jane"
    assert r.last_name == "Doe"
    assert r.date_of_birth == date(1990, 1, 15)


def test_extract_handles_empty_text():
    r = extract_patient_info("")
    assert r.first_name is None
    assert r.last_name is None
    assert r.date_of_birth is None
    assert r.confidence == "low"
