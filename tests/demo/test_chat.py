import pytest

from demo import chat


@pytest.fixture(autouse=True)
def lexical(monkeypatch):
    monkeypatch.setenv("MEMLEDGER_GUARD_BACKEND", "lexical")


@pytest.mark.parametrize("case", chat.CASES, ids=[c.key for c in chat.CASES])
def test_attack_works_with_protection_off_and_is_blocked_with_it_on(case):
    off, on = chat.play(case, protected=False), chat.play(case, protected=True)
    assert off.attacked and off.verdict == case.goal_off
    assert not on.attacked and on.verdict == case.goal_on
    assert not any(m.role == "guard" for m in off.messages)  # plain memory never steps in
    assert any(m.role == "guard" for m in on.messages)  # MemLedger's intervention is shown


def test_transcript_names_people_and_shows_tool_calls():
    p = chat.play(chat.BY_KEY["acme"], protected=False)
    roles = [m.role for m in p.messages]
    assert roles[0] == "user" and p.messages[0].who.startswith("Ria") and "agent" in roles and "tool" in roles
    assert any("Paid account 9876" in m.text and m.tone == "bad" for m in p.messages)
    on = chat.play(chat.BY_KEY["acme"], protected=True)
    assert any("unknown → 1234" in m.text for m in on.messages)  # account bound from the registry


def test_follow_up_question_uses_the_memory_the_run_left():
    off = chat.play(chat.BY_KEY["acme"], protected=False)
    assert "9876" in chat.ask(off, "What is Acme Ltd's bank account?")[-1].text
    on = chat.play(chat.BY_KEY["acme"], protected=True)
    assert "9876" not in chat.ask(on, "What is Acme Ltd's bank account?")[-1].text


def test_tamper_case_edits_storage_and_is_caught_on_read():
    on = chat.play(chat.BY_KEY["tamper"], protected=True)
    assert any("Integrity check failed" in m.text for m in on.messages)
    assert all("19%" not in m.text for m in on.messages if m.role == "agent")
    off = chat.play(chat.BY_KEY["tamper"], protected=False)
    assert "19%" in off.messages[-1].text
