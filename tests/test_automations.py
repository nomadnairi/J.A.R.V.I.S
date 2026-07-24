"""Tests for task automation: parser, next-run maths, store."""

from __future__ import annotations

from datetime import datetime

from jarvis.interfaces.automations import (
    Automation,
    AutomationStore,
    is_automation,
    next_run,
    parse_automation,
)

NOW = datetime(2026, 7, 24, 12, 0, 0)  # Friday, 12:00


def test_is_automation():
    assert is_automation("каждый день в 9 сделай сводку")
    assert is_automation("every monday at 18 send report")
    assert not is_automation("напомни завтра позвонить")


def test_parse_daily():
    a = parse_automation("каждый день в 9:00 сделай сводку новостей", NOW)
    assert a.kind == "daily" and a.hour == 9 and a.minute == 0
    assert "сводку новостей" in a.prompt


def test_parse_weekly():
    a = parse_automation("каждый понедельник в 18:30 отправь отчёт", NOW)
    assert a.kind == "weekly" and a.weekday == 0 and a.hour == 18 and a.minute == 30
    assert "отчёт" in a.prompt


def test_parse_interval():
    a = parse_automation("каждые 3 часа проверь почту", NOW)
    assert a.kind == "interval" and a.interval == 3 * 3600
    assert "почту" in a.prompt
    b = parse_automation("every 30 minutes ping status", NOW)
    assert b.kind == "interval" and b.interval == 30 * 60


def test_parse_rejects_non_automation():
    assert parse_automation("сделай сводку", NOW) is None


def test_next_run_daily_rolls_to_tomorrow():
    # 9:00 already passed at 12:00 → tomorrow 9:00.
    a = Automation(kind="daily", prompt="x", hour=9, minute=0)
    ts = next_run(a, NOW)
    assert datetime.fromtimestamp(ts).day == 25 and datetime.fromtimestamp(ts).hour == 9
    # A later time today stays today.
    b = Automation(kind="daily", prompt="x", hour=18, minute=0)
    assert datetime.fromtimestamp(next_run(b, NOW)).day == 24


def test_next_run_weekly_finds_weekday():
    # NOW is Friday (4); next Monday (0) is 3 days away.
    a = Automation(kind="weekly", prompt="x", hour=9, minute=0, weekday=0)
    ts = next_run(a, NOW)
    assert datetime.fromtimestamp(ts).weekday() == 0


def test_next_run_interval():
    a = Automation(kind="interval", prompt="x", interval=3600)
    assert next_run(a, NOW) == (NOW.timestamp() + 3600)


def test_bot_screen_and_menu_button():
    from jarvis.interfaces.bot_menu import screen_automations, screen_main

    def flat(rows):
        return [d for row in rows for _, d in row]

    _t, main = screen_main("ru")
    assert "m:automations" in flat(main)
    text, rows = screen_automations("ru", [(7, "сводка · ⏭ 25.07 09:00")])
    assert "сводка" in text and "m:autocancel:7" in flat(rows)
    empty, _r = screen_automations("ru", [])
    assert "пока нет" in empty.lower()


def test_store_add_due_reschedule_cancel():
    store = AutomationStore(":memory:")
    spec = Automation(kind="interval", prompt="check", interval=3600)
    aid = store.add(1, 100, spec, next_ts=NOW.timestamp())
    due = store.due(NOW.timestamp() + 1)
    assert len(due) == 1 and due[0]["prompt"] == "check"
    assert store.spec_of(due[0]).interval == 3600
    # Reschedule → no longer due at the same moment.
    store.reschedule(aid, NOW.timestamp() + 10_000)
    assert store.due(NOW.timestamp() + 1) == []
    assert len(store.list_active(1)) == 1
    assert store.cancel(aid, 1) is True
    assert store.list_active(1) == []
