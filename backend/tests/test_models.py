import pytest
from pydantic import ValidationError

from app.models import MAX_MESSAGE_CHARS, CandidateMessage


def test_valid_message_keeps_fields():
    msg = CandidateMessage(message_id="m1", candidate="Ana", text="Any update?")
    assert msg.message_id == "m1"
    assert msg.text == "Any update?"
    assert msg.application_status is None


@pytest.mark.parametrize("text", ["", "   ", "\n\t "])
def test_empty_or_whitespace_text_is_rejected(text):
    with pytest.raises(ValidationError):
        CandidateMessage(message_id="m1", text=text)


@pytest.mark.parametrize("message_id", ["", "   "])
def test_blank_message_id_is_rejected(message_id):
    with pytest.raises(ValidationError):
        CandidateMessage(message_id=message_id, text="hello")


def test_missing_message_id_is_rejected():
    with pytest.raises(ValidationError):
        CandidateMessage(text="hello")


def test_blank_optional_fields_become_none():
    msg = CandidateMessage(message_id="m1", text="hi", application_status="  ", context="")
    assert msg.application_status is None
    assert msg.context is None


def test_overlong_text_is_rejected():
    with pytest.raises(ValidationError):
        CandidateMessage(message_id="m1", text="a" * (MAX_MESSAGE_CHARS + 1))
