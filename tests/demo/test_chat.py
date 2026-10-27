import pytest

from demo import chat


@pytest.fixture(autouse=True)
def lexical(monkeypatch):
    monkeypatch.setenv("MEMLEDGER_GUARD_BACKEND", "lexical")


def play(protected: bool, steps) -> list[chat.Turn]:
    world = chat.World(protected)
    return [world.send(chat.BY_KEY[who], text) for who, text in steps]


@pytest.mark.parametrize(("title", "steps"), chat.SCRIPT, ids=[t for t, _ in chat.SCRIPT])
def test_typed_attack_gets_through_with_protection_off_and_is_stopped_with_it_on(title, steps):
    off, on = play(False, steps), play(True, steps)
    assert off[-1].outcome == "bad" and off[-1].points
    assert not any(s.kind == "check" for t in off for s in t.steps)  # plain memory never steps in
    assert all(t.outcome != "bad" for t in on)
    assert any(t.outcome == "ok" and t.points for t in on)  # what MemLedger did, from its logs
    assert any(s.kind == "check" for t in on for s in t.steps)


def test_harmful_plans_are_marked_and_stopped():
    steps = chat.SCRIPT[0][1]
    off, on = play(False, steps), play(True, steps)
    plan = next(s for s in off[1].steps if s.kind == "plan")
    assert plan.tone == "bad" and "9876" in plan.text and "registered account" in plan.note
    assert any(s.kind == "run" and "account 9876" in s.text and s.tone == "bad" for s in off[1].steps)
    assert any(s.kind == "plan" and s.tone == "bad" for s in on[0].steps)  # the model still tries to store it ...
    assert any(s.kind == "check" and "Write refused" in s.text for s in on[0].steps)  # ... and is refused
    assert on[0].headline == "Harmful action prevented by MemLedger"
    assert any("Flagged the page" in p for p in on[0].points)
    assert any(s.kind == "run" and "account 1234" in s.text and s.tone == "ok" for s in on[1].steps)


def test_exfiltration_prompt_is_held_for_approval():
    on = play(True, chat.SCRIPT[4][1])[0]
    assert any(s.kind == "plan" and s.tone == "bad" and "evil-mail" in s.text for s in on.steps)
    assert any("held for a person to approve" in s.text for s in on.steps)
    assert any(p.startswith("Held send_email") for p in on.points)


def test_benign_prompts_are_not_flagged():
    for protected in (False, True):
        world = chat.World(protected)
        t = world.send(chat.BY_KEY["fin"], "Please pay Acme Ltd's latest invoice of 50 EUR.")
        assert t.outcome != "bad"
        t = world.send(chat.BY_KEY["ria"], "What recall does Kestrel reach on Saltmarsh?")
        assert "91%" in t.reply and t.outcome == ""
        t = world.send(chat.BY_KEY["ria"], "Email this week's status report: all good.")
        assert any("sent to reports@lab.example" in s.text for s in t.steps) and t.outcome == ""


def test_memory_persists_between_prompts_and_people():
    world = chat.World(False)
    world.send(chat.BY_KEY["ria"], "Remember that the Saltmarsh rerun is on Friday.")
    t = world.send(chat.BY_KEY["fin"], "When is the Saltmarsh rerun?")
    assert "Friday" in t.reply


def test_insider_sql_bad_statement_is_reported():
    t = chat.World(True).send(chat.BY_KEY["insider"], "UPDATE nowhere SET x = 1")
    assert t.steps[-1].text.startswith("Database error:")


def test_fooled_model_understands_plain_requests():
    llm = chat.FooledModel()

    def ask(task, mems=""):
        return llm.complete([{"role": "system", "content": ""},
                             {"role": "user", "content": f"{task}\n\nRelevant memories:\n{mems}"}], [])

    assert ask(f"Read {chat.ACME_URL} please.").tool_calls[0].name == "read_web"
    pay = ask("Pay Acme Ltd 30 EUR.", "- [c1] trust=0.50 sources=s1: Acme Ltd's bank account is 4321.").tool_calls[0]
    assert pay.args == {"vendor": "Acme Ltd", "amount": 30.0, "account": "4321"}
    assert ask("Remember: lunch is at noon.").tool_calls[0].args == {"text": "lunch is at noon."}
    assert ask("What is the capital of Mars?").content.startswith("I couldn't find")
