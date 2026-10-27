"""Seed synthetic tickets and notes. All data is fictional.

Usage: python scripts/seed_data.py [data_dir]
"""
import random
import sqlite3
import sys
from pathlib import Path

DATA = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent / "data"

TEMPLATES = [
    ("VPN keeps disconnecting", "VPN drops every few minutes on home Wi-Fi", "network"),
    ("Cannot connect to VPN", "Client shows error 809 after the update", "network"),
    ("Laptop battery draining fast", "Battery lasts under 2 hours", "hardware"),
    ("Request access to analytics dashboard", "Need viewer access for Q4 reporting", "access"),
    ("Password reset not working", "Reset email never arrives", "access"),
    ("Monitor flickering", "External monitor flickers on docking station", "hardware"),
    ("Payroll shows wrong tax code", "Tax code on payslip looks incorrect", "payroll"),
    ("Software install request", "Please install the design tool licence", "software"),
    ("Printer offline on floor 2", "Nobody can print since Monday", "hardware"),
    ("Phishing email reported", "Received suspicious invoice email", "security"),
]
NAMES = ["Priya", "Marcus", "Chen", "Sofia", "Omar", "Lena", "Diego", "Aiko"]
NOTES = [
    ("Q4 planning sync", "Decided to freeze scope by Nov 15. Owner: Marcus. Action: finalise budget.", "planning"),
    ("VPN incident review", "Root cause: expired certificate on gateway. Action: add expiry monitoring.", "incident,vpn"),
    ("Onboarding feedback", "New hires want a clearer week-1 checklist. Owner: Sofia.", "hr,onboarding"),
    ("Security training", "Phishing simulation scheduled for December. Owner: Omar.", "security"),
]


def main() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    random.seed(16)
    for name in ("tickets.db", "notes.db"):
        (DATA / name).unlink(missing_ok=True)

    t = sqlite3.connect(DATA / "tickets.db")
    t.execute("""CREATE TABLE tickets (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, description TEXT,
        category TEXT, status TEXT DEFAULT 'open', priority TEXT DEFAULT 'medium', assignee TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP)""")
    for i in range(60):
        title, desc, cat = random.choice(TEMPLATES)
        t.execute("INSERT INTO tickets (title, description, category, status, priority, assignee, created_at) "
                  "VALUES (?,?,?,?,?,?,?)",
                  (title, desc, cat, random.choice(["open", "open", "in_progress", "closed"]),
                   random.choice(["low", "medium", "high"]), random.choice(NAMES),
                   f"2026-{random.randint(8, 10):02d}-{random.randint(1, 28):02d}"))
    t.commit()

    n = sqlite3.connect(DATA / "notes.db")
    n.execute("""CREATE TABLE notes (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, body TEXT, tags TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP)""")
    n.executemany("INSERT INTO notes (title, body, tags) VALUES (?,?,?)", NOTES)
    n.commit()
    print(f"seeded {DATA}: 60 tickets, {len(NOTES)} notes")


if __name__ == "__main__":
    main()
