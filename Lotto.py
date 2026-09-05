import tkinter as tk
from tkinter import ttk, messagebox
import random
import sqlite3
import csv
import io
import configparser
from pathlib import Path
import urllib.request
import urllib.error
import re
import os
import shutil
import subprocess
import tempfile
import wave
import math
from pathlib import Path
from datetime import datetime, timedelta

VERSION = "0.4.41"
DB_FILE = Path(__file__).with_name("lotto.db")
WESTLOTTO_URL = "https://www.westlotto.de/spielgemeinschaft/gewinnzahlen/gewinnzahlen.html"
LOTTOZAHLEN_HOME = "https://lottozahlen.de/"
LOTTOZAHLEN_DRAW = "https://lottozahlen.de/lotto/{date}/"
EXTERNAL_DB_URL = "https://raw.githubusercontent.com/lotto-aktuell/lotto-daten-feed/main/docs/lotto6aus49.json"


def db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def create_tables():
    conn = db()
    conn.execute("""CREATE TABLE IF NOT EXISTS lotto_numbers (
        id INTEGER PRIMARY KEY AUTOINCREMENT, number INTEGER NOT NULL)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS super_numbers (
        id INTEGER PRIMARY KEY AUTOINCREMENT, number INTEGER NOT NULL)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS official_draws (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        draw_date TEXT UNIQUE NOT NULL,
        draw_day TEXT NOT NULL,
        n1 INTEGER NOT NULL, n2 INTEGER NOT NULL, n3 INTEGER NOT NULL,
        n4 INTEGER NOT NULL, n5 INTEGER NOT NULL, n6 INTEGER NOT NULL,
        superzahl INTEGER NOT NULL)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS tickets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        draw_day TEXT NOT NULL,
        n1 INTEGER NOT NULL, n2 INTEGER NOT NULL, n3 INTEGER NOT NULL,
        n4 INTEGER NOT NULL, n5 INTEGER NOT NULL, n6 INTEGER NOT NULL,
        superzahl INTEGER NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP)""")
    cols = [r[1] for r in conn.execute("PRAGMA table_info(tickets)").fetchall()]
    if "draw_date" not in cols:
        conn.execute("ALTER TABLE tickets ADD COLUMN draw_date TEXT")
        rows = conn.execute("SELECT id, draw_day, created_at FROM tickets").fetchall()
        for r in rows:
            try:
                d = datetime.strptime((r["created_at"] or "")[:10], "%Y-%m-%d")
            except Exception:
                d = datetime.now()
            target = 2 if r["draw_day"] == "Mittwoch" else 5
            delta = (d.weekday() - target) % 7
            d = d.replace(hour=0, minute=0, second=0, microsecond=0)
            d = d.fromordinal(d.toordinal() - delta)
            conn.execute("UPDATE tickets SET draw_date=? WHERE id=?",
                         (d.strftime("%d.%m.%Y"), r["id"]))
    # A saved tip always gets its weekday from its concrete draw date.
    # This repairs older tips that may have been saved with the wrong
    # Wednesday/Saturday selection.
    ticket_rows = conn.execute(
        "SELECT id, draw_date FROM tickets WHERE draw_date IS NOT NULL AND draw_date<>''"
    ).fetchall()
    for r in ticket_rows:
        try:
            d = datetime.strptime(r["draw_date"], "%d.%m.%Y")
            if d.weekday() == 2:
                conn.execute("UPDATE tickets SET draw_day='Mittwoch' WHERE id=?", (r["id"],))
            elif d.weekday() == 5:
                conn.execute("UPDATE tickets SET draw_day='Samstag' WHERE id=?", (r["id"],))
        except Exception:
            pass

    conn.execute("""CREATE TABLE IF NOT EXISTS winning_quotas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        draw_date TEXT NOT NULL,
        draw_day TEXT NOT NULL,
        class_no INTEGER NOT NULL,
        winners INTEGER,
        quota REAL,
        UNIQUE(draw_date, class_no))""")
    conn.execute("""CREATE TABLE IF NOT EXISTS notified_wins (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ticket_id INTEGER NOT NULL,
        draw_date TEXT NOT NULL,
        class_no INTEGER NOT NULL,
        UNIQUE(ticket_id, draw_date, class_no))""")
    conn.execute("""CREATE TABLE IF NOT EXISTS external_database_meta (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL)""")
    conn.commit()
    conn.close()


def date_key(s):
    try:
        return datetime.strptime(s, "%d.%m.%Y")
    except Exception:
        return datetime.min


def money(value):
    if value is None:
        return "–"
    return f"{value:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")

def draw_day_from_date(date_str):
    """Return the official Lotto draw weekday for a concrete date."""
    d = datetime.strptime(date_str, "%d.%m.%Y")
    if d.weekday() == 2:
        return "Mittwoch"
    if d.weekday() == 5:
        return "Samstag"
    return None


def quota_label(row):
    if row is None:
        return "–"
    if row["quota"] is None:
        return "unbesetzt"
    return money(row["quota"])


def get_win_class(ticket, draw):
    winning = {draw[f"n{i}"] for i in range(1, 7)}
    own = {ticket[f"n{i}"] for i in range(1, 7)}
    correct = len(winning & own)
    super_match = ticket["superzahl"] == draw["superzahl"]
    if correct == 6 and super_match: return 1
    if correct == 6: return 2
    if correct == 5 and super_match: return 3
    if correct == 5: return 4
    if correct == 4 and super_match: return 5
    if correct == 4: return 6
    if correct == 3 and super_match: return 7
    if correct == 3: return 8
    if correct == 2 and super_match: return 9
    return None


def save_official_draw(date_str, numbers, sz):
    """Save a draw once; repair an existing record only when its data differ.

    This prevents duplicates while also fixing records created by the older
    parser that accidentally picked numbers from the surrounding page text.
    """
    dt = datetime.strptime(date_str, "%d.%m.%Y")
    day = "Mittwoch" if dt.weekday() == 2 else "Samstag" if dt.weekday() == 5 else dt.strftime("%A")
    numbers = tuple(sorted(int(n) for n in numbers))
    if len(numbers) != 6 or len(set(numbers)) != 6 or not all(1 <= n <= 49 for n in numbers):
        raise ValueError("Ungültige sechs Lottozahlen.")
    sz = int(sz)
    conn = db()
    row = conn.execute("SELECT * FROM official_draws WHERE draw_date=?", (date_str,)).fetchone()
    if row:
        old = tuple(row[f"n{i}"] for i in range(1, 7))
        if old != numbers or row["superzahl"] != sz or row["draw_day"] != day:
            conn.execute(
                "UPDATE official_draws SET draw_day=?, n1=?, n2=?, n3=?, n4=?, n5=?, n6=?, superzahl=? WHERE draw_date=?",
                (day, *numbers, sz, date_str))
            conn.commit()
            conn.close()
            return "repaired"
        conn.close()
        return False
    conn.execute("""INSERT INTO official_draws
        (draw_date,draw_day,n1,n2,n3,n4,n5,n6,superzahl)
        VALUES(?,?,?,?,?,?,?,?,?)""", (date_str, day, *numbers, sz))
    conn.commit()
    conn.close()
    return True


def save_quotas(date_str, day, rows):
    """Store quotas without creating duplicates.

    Existing identical rows are left untouched. If an already stored value is
    demonstrably wrong, it is repaired in place; no second record is created.
    """
    if not rows:
        return
    conn = db()
    for cls, winners, quota in rows:
        old = conn.execute(
            "SELECT draw_day,winners,quota FROM winning_quotas "
            "WHERE draw_date=? AND class_no=?",
            (date_str, cls)).fetchone()
        if old is None:
            conn.execute(
                "INSERT INTO winning_quotas(draw_date,draw_day,class_no,winners,quota) "
                "VALUES(?,?,?,?,?)",
                (date_str, day, cls, winners, quota))
        elif (old["draw_day"], old["winners"], old["quota"]) != (day, winners, quota):
            conn.execute(
                "UPDATE winning_quotas SET draw_day=?,winners=?,quota=? "
                "WHERE draw_date=? AND class_no=?",
                (day, winners, quota, date_str, cls))
    conn.commit()
    conn.close()


def parse_quota_rows(text):
    """Parse only the LOTTO 6aus49 winning-quota table.

    Important: the archive pages also contain other euro amounts nearby,
    such as the total paid-out sum and carried-over jackpot amounts. Those
    are NOT the quote per winner. We therefore parse each ``Klasse N`` row
    from its table structure and only accept a euro amount when it belongs
    to that row. An ``unbesetzt`` class deliberately keeps quota=None.
    """
    text = re.sub(r"\s+", " ", text).replace("\xa0", " ").strip()
    rows = {}

    # Prefer the explicit 6aus49 quota-table area and stop before Spiel 77.
    header = re.search(
        r"Gewinnklasse\s+.*?Gewinner\s+.*?Quote\s+je\s+Gewinn",
        text, re.I)
    if header:
        text = text[header.end():]
    stop = re.search(r"(?:\b(?:Gewinnquoten\s+Spiel\s*77|Spiel\s*77\s+und\s+SUPER\s*6|Gewinnquoten\s+SUPER\s*6)\b|\bIn\s+\d+\s+Gewinnklassen\s+gab\s+es\b|\bDie\s+Tabelle\s+nennt\b|\bAusgespielte\s+Gewinnsumme\b|\bAusgezahlte\s+Gewinnsumme\b)", text, re.I)
    if stop:
        text = text[:stop.start()]

    # The archive's actual table rows are of the form:
    # Klasse 3 ... 40 ... 13.490,90 €
    # or Klasse 1 ... 0 ... unbesetzt
    chunks = list(re.finditer(
        r"Klasse\s*([1-9])\b(.*?)(?=Klasse\s*[1-9]\b|$)",
        text, re.I))

    for m in chunks:
        cls = int(m.group(1))
        chunk = m.group(2)

        # A row that explicitly says unbesetzt has no quote per winner.
        if re.search(r"\bunbesetzt\b|\bliegt nicht vor\b", chunk, re.I):
            # If a later amount in the same row is actually a jackpot/carryover
            # mentioned in prose, it must not be shown as the quote.
            rows[cls] = (cls, None, None)
            continue

        # Find the quote amount in the row. There should be one amount only
        # in a real table row. Do not accept amounts from following prose.
        # IMPORTANT: do not allow whitespace inside the euro amount.
        # A flattened table may contain e.g. "512 3.141,60 €" where
        # 512 is the winner count and 3.141,60 € is the actual quote.
        # The old pattern joined both numbers into 5123.141,60 €.
        amount_pattern = r"((?:\d{1,3}(?:\.\d{3})+|\d+),\d{2})\s*(?:€|EUR)"
        amounts = re.findall(amount_pattern, chunk, re.I)
        amount = None
        if amounts:
            raw = amounts[-1].replace(" ", "")
            amount = float(raw.replace(".", "").replace(",", "."))

        # Winner count is the last integer before the quote, excluding the
        # class number and description. This also handles 2.792 / 22.979 etc.
        prefix = chunk
        if amounts:
            pos = re.search(amount_pattern, chunk, re.I)
            if pos:
                prefix = chunk[:pos.start()]
        counts = re.findall(r"(?<![\d.])(\d[\d.]*)\b", prefix)
        winners = None
        if counts:
            try:
                winners = int(counts[-1].replace(".", ""))
            except ValueError:
                pass

        if amount is not None:
            rows[cls] = (cls, winners, amount)

    # Safety fallback for pages where table cells are flattened without a
    # detectable header. This pattern requires the class description and
    # keeps "unbesetzt" as a missing quote.
    if len(rows) < 9:
        pat = re.compile(
            r"Klasse\s*([1-9])\s*[^K]{0,180}?"
            r"(?:\b(unbesetzt|liegt nicht vor)\b|"
            r"(\d[\d.\s]*)\s+(\d[\d.\s]*,\d{2})\s*(?:€|EUR))",
            re.I)
        for m in pat.finditer(text):
            cls = int(m.group(1))
            if m.group(2):
                rows[cls] = (cls, None, None)
            elif m.group(4):
                winners = int(m.group(3).replace(" ", "").replace(".", ""))
                amount = float(m.group(4).replace(" ", "").replace(".", "").replace(",", "."))
                rows[cls] = (cls, winners, amount)

    return [rows[k] for k in sorted(rows)]

def parse_westlotto_page(html):
    plain = re.sub(r"<script.*?</script>|<style.*?</style>", " ", html,
                   flags=re.I | re.S)
    plain = re.sub(r"<[^>]+>", " ", plain)
    plain = re.sub(r"&nbsp;|&#160;|&#xA0;", " ", plain, flags=re.I)
    plain = re.sub(r"\s+", " ", plain).strip()

    headings = list(re.finditer(
        r"Ergebnisse\s+vom\s+(Mittwoch|Samstag),\s+den\s+"
        r"(\d{2}\.\d{2}\.\d{4})", plain, re.I))
    if not headings:
        raise ValueError("Keine Mittwoch-/Samstag-Ziehungen gefunden.")

    results = []
    for idx, h in enumerate(headings):
        day = h.group(1).capitalize()
        date_str = h.group(2)
        block_end = headings[idx + 1].start() if idx + 1 < len(headings) else len(plain)
        block = plain[h.end():block_end]

        # Search only the first result area, before the quota table.
        sm = re.search(r"Superzahl\s*(\d)", block, re.I)
        if not sm:
            continue
        before = block[:sm.start()]

        # Look for six distinct 1..49 values and choose the first plausible run.
        candidates = [int(x) for x in re.findall(r"(?<!\d)([1-9]|[1-4]\d)(?!\d)", before)]
        nums = None
        for i in range(0, max(0, len(candidates) - 5)):
            cand = candidates[i:i+6]
            if len(cand) == 6 and len(set(cand)) == 6 and all(1 <= n <= 49 for n in cand):
                nums = sorted(cand)
                break
        if nums is None:
            continue

        sz = int(sm.group(1))

        # Restrict quota parsing to the LOTTO 6aus49 section. The current
        # WestLotto page has a header followed by nine rows; "Spiel 77"
        # marks the end of this section.
        after = block[sm.end():]
        qmatch = re.search(r"\bQuoten\b", after, re.I)
        qtext = after[qmatch.end():] if qmatch else after
        stop = re.search(r"\b(?:Spiel\s*77|SUPER\s*6)\b", qtext, re.I)
        if stop:
            qtext = qtext[:stop.start()]

        quotas = parse_quota_rows(qtext[:8000])
        results.append((date_str, day, nums, sz, quotas))
    return results


def fetch_historical_draw(date_str):
    """Fetch one completed historical draw and its final 6aus49 quotas.

    The WestLotto page is the primary source for current data. For an older
    saved tip, its individual archive page is used because the current
    WestLotto page normally shows only the latest Wednesday/Saturday results.
    """
    dt = datetime.strptime(date_str, "%d.%m.%Y")
    url = f"https://lottozahlen.de/lotto/{dt:%Y-%m-%d}/"
    req = urllib.request.Request(
        url, headers={"User-Agent": f"Mozilla/5.0 Lotto-Simulator/{VERSION}"})
    with urllib.request.urlopen(req, timeout=15) as r:
        html = r.read().decode("utf-8", "ignore")

    plain = re.sub(r"<script.*?</script>|<style.*?</style>", " ", html,
                   flags=re.I | re.S)
    plain = re.sub(r"<[^>]+>", " ", plain)
    plain = re.sub(r"&nbsp;|&#160;|&#xA0;", " ", plain, flags=re.I)
    plain = re.sub(r"\s+", " ", plain).strip()

    dm = re.search(
        r"(?:Ziehung vom|Lottozahlen vom)\s+"
        r"(?:Mittwoch|Samstag),\s*(?:den\s*)?"
        r"(\d{2}\.\d{2}\.\d{4})", plain, re.I)
    if not dm:
        raise ValueError("Historische Ziehung konnte nicht erkannt werden.")
    real_date = dm.group(1)
    if real_date != date_str:
        raise ValueError(f"Archivseite lieferte {real_date} statt {date_str}.")

    day = "Mittwoch" if dt.weekday() == 2 else "Samstag" if dt.weekday() == 5 else None
    if not day:
        raise ValueError("Das Tippdatum ist kein Mittwoch oder Samstag.")

    # Parse only the explicit Gewinnzahlen area; never the digits between the
    # date heading and that area (which may contain metadata and 6aus49).
    six, sz_value = extract_six_lotto_numbers(plain[dm.end():])

    # The archive text has an explicit "Gewinnquoten LOTTO 6aus49" section.
    qmatch = re.search(r"Gewinnquoten\s+LOTTO\s*6\s*aus\s*49", plain, re.I)
    if not qmatch:
        raise ValueError("Historische Gewinnquoten konnten nicht gefunden werden.")
    qtext = plain[qmatch.end():qmatch.end()+7000]
    quotas = parse_quota_rows(qtext)
    if len(quotas) < 9:
        raise ValueError(f"Nur {len(quotas)} von 9 Gewinnklassen gefunden.")

    return real_date, day, six, sz_value, quotas

def _plain_html(html):
    text = re.sub(r"<script.*?</script>|<style.*?</style>", " ", html, flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"&nbsp;|&#160;|&#xA0;", " ", text, flags=re.I)
    return re.sub(r"\s+", " ", text).strip()


def extract_six_lotto_numbers(text):
    """Extract the six main numbers from the explicit Gewinnzahlen area.

    Never scan from the date heading: archive pages contain other digits such
    as the date, ``6 aus 49`` and metadata before the actual winning numbers.
    """
    m = re.search(r"Gewinnzahlen(?:\s+LOTTO\s*6\s*aus\s*49)?", text, re.I)
    if not m:
        raise ValueError("Bereich Gewinnzahlen nicht gefunden.")
    tail = text[m.end():]
    sm = re.search(r"Superzahl\s*(?:\(Superzahl\))?\s*(\d)", tail, re.I)
    if not sm:
        sm = re.search(r"(\d)\s+(?:SZ\s*)?(?:\(Superzahl\)\s*)?Superzahl\b", tail, re.I)
    if not sm:
        raise ValueError("Superzahl fehlt.")
    before = tail[:sm.start()]
    candidates = [int(x) for x in re.findall(r"(?<!\d)([1-9]|[1-4]\d)(?!\d)", before)]
    # The six actual numbers are the first six numbers in this explicit area.
    # If formatting inserts harmless labels/digits, try consecutive unique runs.
    for i in range(max(0, len(candidates) - 5)):
        cand = candidates[i:i+6]
        if len(cand) == 6 and len(set(cand)) == 6:
            return sorted(cand), int(sm.group(1))
    raise ValueError("Die sechs Lottozahlen konnten nicht erkannt werden.")


def parse_lottozahlen_home(html):
    """Read the newest Wednesday and Saturday draws from the explicit result areas."""
    plain = _plain_html(html)
    heads = list(re.finditer(
        r"Lottozahlen\s+vom\s+(Mittwoch|Samstag),\s*(?:den\s*)?(\d{2}\.\d{2}\.\d{4})",
        plain, re.I))
    results = []
    for idx, h in enumerate(heads):
        day = h.group(1).capitalize()
        date_str = h.group(2)
        block_end = heads[idx + 1].start() if idx + 1 < len(heads) else len(plain)
        block = plain[h.end():block_end]
        try:
            nums, sz = extract_six_lotto_numbers(block)
        except ValueError:
            continue
        results.append((date_str, day, nums, sz))
    chosen = {}
    for r in results:
        chosen[r[1]] = max(chosen.get(r[1], r), key=lambda x: date_key(x[0]))
    return [chosen[d] for d in ("Mittwoch", "Samstag") if d in chosen]


def fetch_lottozahlen_draw_page(date_str):
    dt = datetime.strptime(date_str, "%d.%m.%Y")
    url = LOTTOZAHLEN_DRAW.format(date=dt.strftime("%Y-%m-%d"))
    req = urllib.request.Request(url, headers={"User-Agent": f"Mozilla/5.0 Lotto-Simulator/{VERSION}"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return _plain_html(r.read().decode("utf-8", "ignore"))


def parse_lottozahlen_draw_page(plain, date_str):
    """Parse one dated archive page: six numbers, Superzahl and quotas."""
    dm = re.search(
        r"(?:Lottozahlen\s+vom|Ziehung\s+vom)\s+(?:Mittwoch|Samstag),\s*(?:den\s*)?"
        r"(\d{2}\.\d{2}\.\d{4})", plain, re.I)
    if not dm:
        raise ValueError("Ziehung konnte auf der Archivseite nicht erkannt werden.")
    real_date = dm.group(1)
    if real_date != date_str:
        raise ValueError(f"Archivseite lieferte {real_date} statt {date_str}.")

    nums, sz = extract_six_lotto_numbers(plain[dm.end():])

    qmatch = re.search(r"Gewinnquoten\s+LOTTO\s*6\s*aus\s*49", plain, re.I)
    if not qmatch:
        raise ValueError("Gewinnquoten nicht gefunden.")
    qtext = plain[qmatch.end():qmatch.end() + 14000]
    quotas = parse_quota_rows(qtext)

    # Do not reject a page merely because one fixed/empty class is rendered
    # differently. The explicit rows are still useful for tip checking.
    if not quotas:
        raise ValueError("Keine Gewinnquoten konnten erkannt werden.")

    dt = datetime.strptime(date_str, "%d.%m.%Y")
    day = "Mittwoch" if dt.weekday() == 2 else "Samstag" if dt.weekday() == 5 else dt.strftime("%A")
    return real_date, day, sorted(nums), sz, quotas


def fetch_completed_draw_date(day_name, today=None):
    """Return the most recent completed Wednesday/Saturday on or before today."""
    today = today or datetime.now()
    target = 2 if day_name == "Mittwoch" else 5
    delta = (today.weekday() - target) % 7
    candidate = today.replace(hour=23, minute=59, second=59, microsecond=0)
    candidate = candidate.fromordinal(candidate.toordinal() - delta)
    # On Saturday, before the normal 19:25 draw, today's Saturday is not completed.
    if day_name == "Samstag" and today.weekday() == 5 and today.hour < 20:
        candidate = candidate.fromordinal(candidate.toordinal() - 7)
    return candidate.strftime("%d.%m.%Y")


def fetch_current_draws_from_archive(show_message=True):
    """Load the newest completed Wednesday and Saturday separately.

    This deliberately does not rely on the homepage showing both draws.  The
    homepage often shows the latest Wednesday and the *next* Saturday.  Each
    dated archive page is therefore fetched directly, so the main page always
    has one completed Wednesday and one completed Saturday.
    """
    targets = [
        ("Mittwoch", fetch_completed_draw_date("Mittwoch")),
        ("Samstag", fetch_completed_draw_date("Samstag")),
    ]
    saved = []
    errors = []

    for expected_day, date_str in targets:
        try:
            page = fetch_lottozahlen_draw_page(date_str)
            real_date, day, nums, sz, quotas = parse_lottozahlen_draw_page(page, date_str)
            if day != expected_day:
                raise ValueError(f"Erwartet {expected_day}, Archiv meldet {day}.")
            new = save_official_draw(real_date, nums, sz)
            if quotas:
                save_quotas(real_date, day, quotas)
            saved.append((real_date, day, nums, sz, quotas, new))
        except Exception as e:
            errors.append(f"{expected_day} {date_str}: {e}")

    if not saved:
        raise ValueError("Keine aktuellen Mittwoch-/Samstag-Daten konnten geladen werden. " + "; ".join(errors))

    update_home_cards()
    check_all_saved_tips(show_message=True)

    if show_message:
        lines = []
        for date_str, day, nums, sz, quotas, new in saved:
            quota_lines = []
            for cls, winners, quota in sorted(quotas, key=lambda item: item[0]):
                betrag = "unbesetzt" if quota is None else money(quota)
                quota_lines.append(f"{cls}: {betrag}")
            quota_text = "\n".join(quota_lines) if quota_lines else "Keine Quoten vorhanden"
            lines.append(
                f"{day}, {date_str}\n"
                f"Zahlen: {'  '.join(f'{n:02d}' for n in nums)}\n"
                f"Superzahl: {sz}\n"
                f"Gewinnquoten:\n{quota_text}\n"
                f"{'Neu gespeichert' if new else 'Bereits vorhanden – nicht doppelt gespeichert'}"
            )
        if errors:
            lines.append("Nicht geladen:\n" + "\n".join(errors))
        messagebox.showinfo("Lotto-Daten aktualisiert", "\n\n".join(lines) + "\n\nQuelle: lottozahlen.de", parent=root)
    return saved

def fetch_current_draws(show_message=True):
    """Fetch current Wednesday and Saturday data. Archive source is primary; WestLotto is fallback."""
    try:
        return fetch_current_draws_from_archive(show_message)
    except Exception as archive_error:
        try:
            return _fetch_current_draws_westlotto(show_message)
        except Exception as west_error:
            raise ValueError(f"Lotto-Daten konnten nicht geladen werden. Archiv: {archive_error}; WestLotto: {west_error}")

def _fetch_current_draws_westlotto(show_message=True):
    req = urllib.request.Request(
        WESTLOTTO_URL,
        headers={"User-Agent": f"Mozilla/5.0 Lotto-Simulator/{VERSION}"})
    with urllib.request.urlopen(req, timeout=15) as r:
        html = r.read().decode("utf-8", "ignore")

    results = parse_westlotto_page(html)
    # Keep the newest Wednesday and newest Saturday only for the main page.
    chosen = {}
    for item in results:
        chosen[item[1]] = max(chosen.get(item[1], item), key=lambda x: date_key(x[0]))

    saved = []
    for day in ("Mittwoch", "Samstag"):
        if day not in chosen:
            continue
        date_str, draw_day, nums, sz, quotas = chosen[day]
        new = save_official_draw(date_str, nums, sz)
        save_quotas(date_str, draw_day, quotas)
        saved.append((date_str, draw_day, nums, sz, quotas, new))

    if not saved:
        raise ValueError("Es konnte keine aktuelle Mittwoch- oder Samstag-Ziehung gespeichert werden.")

    update_home_cards()
    check_all_saved_tips(show_message=True)

    if show_message:
        text = []
        for date_str, day, nums, sz, quotas, new in saved:
            qcount = len(quotas)
            text.append(
                f"{day}, {date_str}\n"
                f"Zahlen: {'  '.join(f'{n:02d}' for n in nums)}\n"
                f"Superzahl: {sz}\n"
                f"Quoten: {qcount} Gewinnklassen gespeichert\n"
                f"{'Neu gespeichert' if new else 'Bereits vorhanden – nicht doppelt gespeichert'}")
        messagebox.showinfo("Lotto-Daten aktualisiert", "\n\n".join(text) +
                            "\n\nQuelle: WestLotto", parent=root)
    return saved


def _external_meta_get(key):
    conn = db()
    row = conn.execute("SELECT value FROM external_database_meta WHERE key=?", (key,)).fetchone()
    conn.close()
    return row["value"] if row else None


def _external_meta_set(key, value):
    conn = db()
    conn.execute("INSERT OR REPLACE INTO external_database_meta(key,value) VALUES(?,?)", (key, str(value)))
    conn.commit()
    conn.close()


def external_database_loaded():
    return _external_meta_get("loaded") == "1"


MODERN_QUOTA_START = "01.01.2020"  # Vollständiges Quotenarchiv der gewählten externen Quelle


def _quota_complete(date_str):
    """Return True when all nine modern LOTTO 6aus49 quota classes exist."""
    conn = db()
    row = conn.execute(
        "SELECT COUNT(*) AS c FROM winning_quotas WHERE draw_date=? AND class_no BETWEEN 1 AND 9",
        (date_str,),
    ).fetchone()
    conn.close()
    return int(row["c"] or 0) == 9


def sync_missing_external_quotas(progress_cb=None):
    """Fill missing final quotas for imported draws efficiently.

    The large history feed supplies the complete draw history with numbers and
    Superzahl. Final 6aus49 quotas are published on dated archive pages.
    Existing complete quota sets are skipped. Missing quota pages are fetched
    concurrently in a small worker pool so the first full import does not
    take many hours on a Raspberry Pi.

    The current external quota archive is complete for the 2020-present
    9-class format, so only that range is bulk-synchronised here. Older draw
    numbers remain available in the historical database and can still be
    fetched individually when a saved tip needs them.
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    conn = db()
    rows = conn.execute(
        "SELECT draw_date FROM official_draws ORDER BY draw_date"
    ).fetchall()
    conn.close()

    candidates = []
    start_dt = datetime.strptime(MODERN_QUOTA_START, "%d.%m.%Y")
    for row in rows:
        date_str = row["draw_date"]
        try:
            dt = datetime.strptime(date_str, "%d.%m.%Y")
        except Exception:
            continue
        if dt >= start_dt and dt.weekday() in (2, 5) and not _quota_complete(date_str):
            candidates.append(date_str)

    total = len(candidates)
    if total == 0:
        if progress_cb:
            progress_cb(0, 0, "", 0)
        return 0, []

    done = 0
    errors = []

    def load_one(date_str):
        try:
            real_date, real_day, nums, sz, quotas = fetch_historical_draw(date_str)
            if len(quotas) < 9:
                raise ValueError(f"Nur {len(quotas)} von 9 Gewinnklassen gefunden")
            save_official_draw(real_date, nums, sz)
            save_quotas(real_date, real_day, quotas)
            return date_str, None
        except Exception as e:
            return date_str, str(e)

    # Eight workers are fast enough for a Pi while avoiding an aggressive
    # request burst against the public archive.
    with ThreadPoolExecutor(max_workers=8, thread_name_prefix="LottoQuota") as pool:
        futures = [pool.submit(load_one, date_str) for date_str in candidates]
        processed = 0
        for future in as_completed(futures):
            date_str, error = future.result()
            processed += 1
            if error:
                errors.append((date_str, error))
            else:
                done += 1
            if progress_cb:
                # The UI counter represents pages already processed, while
                # ``done`` remains the number of successfully imported quota sets.
                progress_cb(processed, total, date_str, len(errors))

    return done, errors


def download_external_database_async(force=False, on_complete=None):
    """Synchronise the complete LOTTO-6aus49 history from the live JSON feed.

    The external feed is maintained automatically after the Wednesday and
    Saturday draws.  On the first activation the complete available history
    is imported.  Later checks compare the feed with the local database and
    only add/repair changed draws.  Local data is never deleted.
    """
    if getattr(root, "_external_download_running", False):
        return

    root._external_download_running = True
    win = tk.Toplevel(root)
    win.title("Externe Lotto-Datenbank")
    win.geometry("560x270")
    win.resizable(False, False)
    ttk.Label(win, text="Externe Lotto-Datenbank", style="Title.TLabel").pack(pady=(18, 6))
    status = ttk.Label(win, text="Verbindung zur aktuellen Datenbank wird hergestellt …", justify="center")
    status.pack(pady=4)
    progress = ttk.Progressbar(win, mode="determinate", length=450, maximum=100)
    progress.pack(pady=12)
    count_label = ttk.Label(win, text="Noch keine Ziehungen verarbeitet")
    count_label.pack(pady=4)
    ttk.Label(win, text="Die Datenbank wird automatisch nach neuen Ziehungen geprüft.\n"
                       "Bereits vorhandene lokale Daten bleiben erhalten.", justify="center").pack(pady=5)

    def ui(done, total, saved, message=None):
        if not win.winfo_exists():
            return
        if total:
            progress["value"] = min(100, done * 100 / total)
        count_label.config(text=f"{saved:,} neue/geänderte Ziehungen verarbeitet".replace(",", "."))
        if message:
            status.config(text=message)

    def worker():
        conn = None
        try:
            headers = {
                "User-Agent": f"Mozilla/5.0 Lotto-Simulator/{VERSION}",
                "Accept": "application/json",
            }
            # GitHub/Pages supports validators. This makes the normal startup
            # check cheap when the weekly database has not changed.
            etag = _external_meta_get("etag")
            last_modified = _external_meta_get("last_modified")
            if etag:
                headers["If-None-Match"] = etag
            if last_modified:
                headers["If-Modified-Since"] = last_modified

            req = urllib.request.Request(EXTERNAL_DB_URL, headers=headers)
            try:
                response = urllib.request.urlopen(req, timeout=30)
                raw = response.read()
                response_etag = response.headers.get("ETag")
                response_last_modified = response.headers.get("Last-Modified")
            except urllib.error.HTTPError as e:
                if e.code == 304:
                    root.after(0, ui, 0, 1, 0,
                               "Ziehungsdaten sind bereits aktuell – fehlende Gewinnquoten werden geprüft …")
                    qdone, qerrors = sync_missing_external_quotas(
                        lambda done, total, date_str, err_count: root.after(
                            0, ui, done, max(total, 1), done,
                            f"Gewinnquoten: {done} von {total} Ziehungen geprüft …"
                            if total else "Alle Gewinnquoten sind bereits vorhanden."
                        )
                    )
                    _external_meta_set("quota_sync_done", datetime.now().strftime("%d.%m.%Y %H:%M:%S"))
                    msg = ("Externe Datenbank ist bereits aktuell."
                           if not qerrors else
                           f"Externe Datenbank ist aktuell; {len(qerrors)} Gewinnquoten konnten nicht geladen werden.")
                    root.after(0, finish, True, qdone, qdone, msg, True)
                    return
                raise

            root.after(0, ui, 0, 1, 0, "Aktueller Datenfeed geladen – Daten werden geprüft …")
            payload = json.loads(raw.decode("utf-8-sig", "replace"))
            draws = payload.get("draws")
            if not isinstance(draws, list) or not draws:
                raise ValueError("Der externe Datenfeed enthält keine gültigen Ziehungen.")

            valid = []
            for item in draws:
                try:
                    d = datetime.strptime(str(item["d"]).strip(), "%Y-%m-%d")
                    nums = [int(n) for n in item["n"]]
                    if d.weekday() not in (2, 5):
                        continue
                    if len(nums) != 6 or len(set(nums)) != 6 or not all(1 <= n <= 49 for n in nums):
                        continue
                    sz_raw = item.get("sz")
                    sz = 0 if sz_raw in (None, "") else int(sz_raw)
                    if not 0 <= sz <= 9:
                        continue
                    valid.append((d.strftime("%d.%m.%Y"), d.weekday(), sorted(nums), sz))
                except Exception:
                    continue

            total = len(valid)
            if total < 1000:
                raise ValueError(
                    f"Der externe Datenfeed ist unvollständig ({total} gültige Ziehungen). "
                    "Der vorhandene lokale Datenbestand bleibt unverändert."
                )

            conn = db()
            changed = 0
            for pos, (date_str, weekday, nums, sz) in enumerate(valid, 1):
                day = "Mittwoch" if weekday == 2 else "Samstag"
                existing = conn.execute(
                    "SELECT n1,n2,n3,n4,n5,n6,superzahl,draw_day FROM official_draws WHERE draw_date=?",
                    (date_str,)
                ).fetchone()
                incoming = tuple(nums) + (sz, day)
                if not existing or tuple(existing[f"n{i}"] for i in range(1, 7)) + (existing["superzahl"], existing["draw_day"]) != incoming:
                    conn.execute("""INSERT OR REPLACE INTO official_draws
                        (draw_date,draw_day,n1,n2,n3,n4,n5,n6,superzahl)
                        VALUES(?,?,?,?,?,?,?,?,?)""", (date_str, day, *nums, sz))
                    changed += 1
                if pos % 100 == 0 or pos == total:
                    conn.commit()
                    root.after(0, ui, pos, total, changed,
                               f"{pos:,} von {total:,} Ziehungen geprüft …".replace(",", "."))
            conn.commit()
            conn.close()
            conn = None

            root.after(0, ui, 0, 1, changed,
                       "Ziehungen übernommen – jetzt werden die endgültigen Gewinnquoten geladen …")
            qdone, qerrors = sync_missing_external_quotas(
                lambda done, total, date_str, err_count: root.after(
                    0, ui, done, max(total, 1), done,
                    f"Gewinnquoten: {done} von {total} Ziehungen geprüft …"
                    if total else "Alle Gewinnquoten sind bereits vorhanden."
                )
            )

            _external_meta_set("loaded", 1)
            _external_meta_set("source", "Ziehungsfeed + lottozahlen.de Gewinnquotenarchiv")
            _external_meta_set("draw_count", total)
            _external_meta_set("feed_stand", str(payload.get("meta", {}).get("stand", "")))
            _external_meta_set("last_loaded", datetime.now().strftime("%d.%m.%Y %H:%M:%S"))
            if response_etag:
                _external_meta_set("etag", response_etag)
            if response_last_modified:
                _external_meta_set("last_modified", response_last_modified)

            feed_stand = str(payload.get("meta", {}).get("stand", "")).strip()
            msg = f"Datenbank aktuell geprüft – {changed} neue/geänderte Ziehungen; Gewinnquoten geprüft: {qdone}." if changed else f"Datenbank ist bereits aktuell; Gewinnquoten geprüft: {qdone}."
            if qerrors:
                msg += f" {len(qerrors)} Gewinnquoten konnten nicht geladen werden."
            if feed_stand:
                msg += f" Datenstand: {feed_stand}."
            root.after(0, finish, True, changed, total, msg, False)
        except Exception as e:
            if conn is not None:
                try:
                    conn.rollback()
                    conn.close()
                except Exception:
                    pass
            root.after(0, finish, False, 0, 0, str(e), False)

    def finish(ok, changed, total, message, not_modified=False):
        root._external_download_running = False
        if win.winfo_exists():
            win.destroy()
        if ok:
            update_home_cards()
            if not_modified:
                set_status("Externe Lotto-Datenbank: bereits aktuell.")
            else:
                set_status(message)
            try:
                sync_historical_ticket_data()
                check_all_saved_tips(show_message=True)
            except Exception:
                pass
            if on_complete:
                root.after(100, on_complete)
        else:
            set_status("Externe Lotto-Datenbank konnte nicht aktualisiert werden – lokale Daten bleiben erhalten.")
            messagebox.showerror("Externe Lotto-Datenbank",
                                 "Der automatische Datenbank-Abgleich ist fehlgeschlagen.\n\n" + message +
                                 "\n\nDie bereits lokal gespeicherten Daten bleiben erhalten.", parent=root)

    import threading
    import json
    threading.Thread(target=worker, name="LottoExternalDB", daemon=True).start()

def fetch_current_lotto_numbers():
    try:
        fetch_current_draws(True)
        # Der Abruf speichert Zahlen und Gewinnquoten bereits in der Datenbank.
        # Danach müssen die sichtbaren Karten aber ebenfalls neu aufgebaut werden.
        update_home_cards()
        check_all_saved_tips(show_message=True)
        set_status("Aktuelle Zahlen und Gewinnquoten wurden aktualisiert.")
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        messagebox.showerror("Internetfehler",
            "Die aktuellen Lottozahlen konnten nicht abgerufen werden.\n\n" + str(e),
            parent=root)
        set_status("Internetfehler beim Aktualisieren.")
    except Exception as e:
        messagebox.showerror("Lotto-Abruf",
            "Die Lotto-Daten konnten nicht verarbeitet werden.\n\n" + str(e),
            parent=root)
        set_status("Abruf fehlgeschlagen – Details siehe Fehlermeldung.")


def refresh_all_data(show_message=True):
    """Refresh external history (if enabled), then official current data and saved tips."""
    if external_database:
        set_status("Externe Datenbank aktiviert – Datenbestand wird aktualisiert …")

        def after_external():
            try:
                fetch_current_draws(show_message=True)
                hist_done, hist_errors = sync_historical_ticket_data()
                update_home_cards()
                check_all_saved_tips(show_message=True)
                if hist_errors:
                    set_status(
                        f"Aktualisierung abgeschlossen. Historisch nachgeladen: {hist_done}; "
                        f"{len(hist_errors)} konnten nicht geladen werden.")
                else:
                    set_status(f"Aktualisierung abgeschlossen. Historisch nachgeladen: {hist_done}.")
            except Exception as e:
                update_home_cards()
                set_status(f"Aktualisierung teilweise abgeschlossen: {e}")

        download_external_database_async(force=True, on_complete=after_external)
        return None

    try:
        saved = fetch_current_draws(show_message=show_message)
        hist_done, hist_errors = sync_historical_ticket_data()
        update_home_cards()
        check_all_saved_tips(show_message=True)
        if hist_errors:
            set_status(
                f"Aktualisierung abgeschlossen. Historisch nachgeladen: {hist_done}; "
                f"{len(hist_errors)} konnten nicht geladen werden.")
        else:
            set_status(f"Aktualisierung abgeschlossen. Historisch nachgeladen: {hist_done}.")
        return saved
    except Exception as e:
        try:
            hist_done, hist_errors = sync_historical_ticket_data()
            update_home_cards()
            check_all_saved_tips(show_message=True)
            set_status(
                f"Aktuelle Daten konnten nicht vollständig geladen werden; "
                f"historisch nachgeladen: {hist_done}.")
            if show_message:
                messagebox.showwarning(
                    "Aktualisierung",
                    "Die aktuellen Daten konnten nicht vollständig geladen werden.\n\n"
                    + str(e),
                    parent=root)
        except Exception:
            set_status("Aktualisierung fehlgeschlagen – vorhandene Daten bleiben erhalten.")
            if show_message:
                messagebox.showerror("Aktualisierung", str(e), parent=root)


def draw_numbers():
    numbers = sorted(random.sample(range(1, 50), 6))
    sz = random.randint(0, 9)
    conn = db()
    conn.executemany("INSERT INTO lotto_numbers(number) VALUES(?)", [(n,) for n in numbers])
    conn.execute("INSERT INTO super_numbers(number) VALUES(?)", (sz,))
    conn.commit()
    conn.close()
    simulated_label.config(
        text=f"{'  '.join(f'{n:02d}' for n in numbers)}   |   Superzahl {sz}")
    set_status("Neue Zufallsziehung erzeugt.")



class CalendarPopup(tk.Toplevel):
    """Small dependency-free calendar popup used for date selection."""
    def __init__(self, parent, initial_date=None, callback=None):
        super().__init__(parent)
        self.callback = callback
        self.transient(parent)
        self.title("Datum auswählen")
        self.resizable(False, False)
        self.grab_set()
        try:
            self.current = datetime.strptime(initial_date or "", "%d.%m.%Y")
        except Exception:
            self.current = datetime.now()
        self.current = self.current.replace(day=1)
        self._build()
        self._render()

    def _build(self):
        top = ttk.Frame(self, padding=6)
        top.pack(fill="x")
        ttk.Button(top, text="◀", width=3, command=self._prev).pack(side="left")
        self.month_label = ttk.Label(top, anchor="center", font=("Arial", 11, "bold"))
        self.month_label.pack(side="left", fill="x", expand=True)
        ttk.Button(top, text="▶", width=3, command=self._next).pack(side="right")
        self.grid_frame = ttk.Frame(self, padding=(6, 0, 6, 6))
        self.grid_frame.pack()

    def _render(self):
        for child in self.grid_frame.winfo_children():
            child.destroy()
        months = ["Januar", "Februar", "März", "April", "Mai", "Juni",
                  "Juli", "August", "September", "Oktober", "November", "Dezember"]
        self.month_label.config(text=f"{months[self.current.month-1]} {self.current.year}")
        for col, name in enumerate(["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]):
            ttk.Label(self.grid_frame, text=name, width=4, anchor="center").grid(row=0, column=col, padx=1, pady=2)
        import calendar as _calendar
        first_weekday, days = _calendar.monthrange(self.current.year, self.current.month)
        for day in range(1, days + 1):
            pos = first_weekday + day - 1
            r, c = 1 + pos // 7, pos % 7
            btn = ttk.Button(self.grid_frame, text=str(day), width=4,
                             command=lambda d=day: self._choose(d))
            btn.grid(row=r, column=c, padx=1, pady=1)

    def _prev(self):
        year, month = self.current.year, self.current.month - 1
        if month == 0:
            year, month = year - 1, 12
        self.current = self.current.replace(year=year, month=month, day=1)
        self._render()

    def _next(self):
        year, month = self.current.year, self.current.month + 1
        if month == 13:
            year, month = year + 1, 1
        self.current = self.current.replace(year=year, month=month, day=1)
        self._render()

    def _choose(self, day):
        selected = self.current.replace(day=day)
        if self.callback:
            self.callback(selected.strftime("%d.%m.%Y"))
        self.destroy()


def attach_calendar(parent, entry, callback=None):
    """Add a calendar button and call the supplied date callback directly.

    The callback receives the selected date as TT.MM.JJJJ.  This avoids relying
    on synthetic keyboard events, which can be unreliable with Tk grab/focus
    handling in a modal calendar window.
    """
    def open_calendar():
        def apply_date(value):
            entry.delete(0, tk.END)
            entry.insert(0, value)
            entry.icursor(tk.END)
            if callback is not None:
                entry.after_idle(lambda: callback(value))
        CalendarPopup(parent, entry.get().strip(), apply_date)
    return ttk.Button(parent, text="📅", width=4, command=open_calendar)


def show_database_manager():
    """Browse the local Lotto database by any date.

    A date that is not itself a draw date is assigned to the next official
    Wednesday or Saturday, exactly like the Lotto-Tipp date field.
    """
    win = tk.Toplevel(root)
    win.title("Lotto-Datenbank Manager")
    win.geometry("760x620")
    win.minsize(700, 560)

    ttk.Label(win, text="Lotto-Datenbank Manager", style="Title.TLabel").pack(pady=(16, 4))
    ttk.Label(win, text="Datum auswählen – die gespeicherten Zahlen, Superzahl und Gewinnquoten werden angezeigt.").pack(pady=(0, 10))

    search = ttk.Frame(win)
    search.pack(fill="x", padx=22, pady=8)
    ttk.Label(search, text="Ziehungsdatum:").pack(side="left", padx=(0, 8))
    date_entry = ttk.Entry(search, width=15, justify="center")
    date_entry.pack(side="left")
    cal_btn = attach_calendar(search, date_entry, lambda _value: load_date())
    cal_btn.pack(side="left", padx=5)
    ttk.Button(search, text="Anzeigen", command=lambda: load_date()).pack(side="left", padx=5)

    info = tk.StringVar(value="Bitte ein Datum eingeben oder den Kalender verwenden.")
    ttk.Label(win, textvariable=info, justify="center", wraplength=680).pack(pady=8)

    result = ttk.LabelFrame(win, text="  Ziehungsdaten  ", padding=14)
    result.pack(fill="both", expand=True, padx=22, pady=8)
    result.columnconfigure(0, weight=1)

    def load_date():
        date_str = date_entry.get().strip()
        try:
            d = datetime.strptime(date_str, "%d.%m.%Y")
        except ValueError:
            info.set("Bitte ein gültiges Datum im Format TT.MM.JJJJ eingeben.")
            for child in result.winfo_children(): child.destroy()
            return
        # Use the same date-to-draw rule as the Lotto-Tipp window:
        # exact Wednesday/Saturday stays unchanged; every other date maps
        # to the next official draw. This also makes calendar-selected
        # dates behave exactly like manually entered dates.
        draw_date_obj = d
        if d.weekday() not in (2, 5):
            for offset in range(1, 7):
                candidate = d + timedelta(days=offset)
                if candidate.weekday() in (2, 5):
                    draw_date_obj = candidate
                    break
        draw_date_str = draw_date_obj.strftime("%d.%m.%Y")
        draw_day = "Mittwoch" if draw_date_obj.weekday() == 2 else "Samstag"

        conn = db()
        draw = conn.execute("SELECT * FROM official_draws WHERE draw_date=?", (draw_date_str,)).fetchone()
        quotas = conn.execute("SELECT * FROM winning_quotas WHERE draw_date=? ORDER BY class_no", (draw_date_str,)).fetchall()
        conn.close()
        for child in result.winfo_children(): child.destroy()
        if not draw:
            if draw_date_str != date_str:
                info.set(f"{date_str} → nächste Ziehung: {draw_day}, {draw_date_str}. Für diese Ziehung sind noch keine Daten gespeichert.")
            else:
                info.set(f"Für den {date_str} ist keine Ziehung in der lokalen Datenbank gespeichert.")
            ttk.Label(result, text="Keine Daten vorhanden.", style="CardMuted.TLabel").pack(pady=35)
            return
        if draw_date_str != date_str:
            info.set(f"{date_str} → {draw_day}, {draw_date_str} – Daten aus der lokalen Lotto-Datenbank")
        else:
            info.set(f"{draw['draw_day']}, {draw['draw_date']} – Daten aus der lokalen Lotto-Datenbank")
        ttk.Label(result, text="Lottozahlen", style="CardHead.TLabel").pack(pady=(6, 4))
        ttk.Label(result, text="  ".join(f"{draw[f'n{i}']:02d}" for i in range(1, 7)), style="Numbers.TLabel").pack(pady=2)
        ttk.Label(result, text=f"Superzahl: {draw['superzahl']}", style="Super.TLabel").pack(pady=(5, 12))
        ttk.Separator(result).pack(fill="x", pady=5)
        ttk.Label(result, text="Gewinnquoten", style="CardHead.TLabel").pack(pady=(7, 4))
        if not quotas:
            ttk.Label(result, text="Keine Gewinnquoten für diese Ziehung gespeichert.", style="CardMuted.TLabel").pack(pady=12)
        else:
            grid = ttk.Frame(result)
            grid.pack(fill="x", padx=15, pady=4)
            for i, q in enumerate(quotas):
                text = f"Klasse {q['class_no']}: {quota_label(q)}"
                ttk.Label(grid, text=text, style="Quota.TLabel").grid(row=i // 3, column=i % 3, padx=8, pady=4, sticky="w")

    conn = db()
    latest_row = conn.execute("SELECT draw_date FROM official_draws ORDER BY draw_date DESC LIMIT 1").fetchone()
    conn.close()
    date_entry.insert(0, latest_row["draw_date"] if latest_row else datetime.now().strftime("%d.%m.%Y"))
    ttk.Button(win, text="Schließen", command=win.destroy).pack(pady=12)
    load_date()

def add_ticket(ticket=None):
    win = tk.Toplevel(root)
    editing = ticket is not None
    win.title("Lotto-Tipp bearbeiten" if editing else "Mein Lotto-Tipp")
    win.geometry("560x620")
    win.transient(root)
    win.grab_set()

    ttk.Label(win, text=("Lotto-Tipp bearbeiten" if editing else "Eigenen Lotto-Tipp eingeben"),
              style="Title.TLabel").pack(pady=(20, 4))
    ttk.Label(win, text="Beliebig viele Tipps • Mittwoch und Samstag getrennt").pack(pady=(0, 12))

    form = ttk.LabelFrame(win, text="Tipp", padding=14)
    form.pack(fill="x", padx=25, pady=8)

    entries = []
    for i in range(6):
        ttk.Label(form, text=f"Zahl {i+1}:").grid(row=i, column=0, padx=8, pady=5, sticky="w")
        e = ttk.Entry(form, width=12, justify="center")
        e.grid(row=i, column=1, padx=8, pady=5)
        entries.append(e)

    ttk.Label(form, text="Superzahl:").grid(row=6, column=0, padx=8, pady=6, sticky="w")
    se = ttk.Entry(form, width=12, justify="center")
    se.grid(row=6, column=1, padx=8, pady=6)

    ttk.Label(form, text="Tippdatum:").grid(row=7, column=0, padx=8, pady=6, sticky="w")
    de = ttk.Entry(form, width=14, justify="center")
    de.grid(row=7, column=1, padx=8, pady=6)
    attach_calendar(form, de, lambda _value: update_draw_from_date()).grid(row=7, column=2, padx=(0, 8), pady=6)

    ttk.Label(form, text="Zugeordnete Ziehung:").grid(row=8, column=0, padx=8, pady=6, sticky="w")
    day = tk.StringVar(value="–")
    draw_info = ttk.Label(form, textvariable=day, width=28, anchor="center")
    draw_info.grid(row=8, column=1, padx=8, pady=6)

    def next_valid_draw_date():
        base = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        for offset in range(8):
            candidate = base + timedelta(days=offset)
            if candidate.weekday() in (2, 5):
                return candidate.strftime("%d.%m.%Y")
        return base.strftime("%d.%m.%Y")

    def find_draw_for_date(date_str):
        """Find the concrete draw belonging to a tip date.

        An exact Wednesday/Saturday is always used. For any other date the
        next official draw is selected. This is deliberately date-based and
        does not depend on the newest row in the database, so old dates work
        exactly like current dates.
        """
        d = datetime.strptime(date_str, "%d.%m.%Y")
        for offset in range(7):
            candidate = d + timedelta(days=offset)
            if candidate.weekday() == 2:
                return candidate, "Mittwoch"
            if candidate.weekday() == 5:
                return candidate, "Samstag"
        raise ValueError("Keine Mittwoch-/Samstag-Ziehung gefunden.")

    def update_draw_from_date(*_):
        try:
            entered = datetime.strptime(de.get().strip(), "%d.%m.%Y")
            draw_date_obj, draw_day = find_draw_for_date(entered.strftime("%d.%m.%Y"))
            draw_date = draw_date_obj.strftime("%d.%m.%Y")

            # Always show the concrete draw selected from the entered date.
            # If it is already in the local database, also show its numbers
            # immediately. This makes historical tips work without relying on
            # the currently displayed Wednesday/Saturday cards.
            conn = db()
            draw = conn.execute(
                "SELECT * FROM official_draws WHERE draw_date=?", (draw_date,)
            ).fetchone()
            conn.close()
            if draw:
                nums = "  ".join(f"{draw[f'n{i}']:02d}" for i in range(1, 7))
                day.set(f"{draw_day}-Ziehung • {draw_date} • {nums} • SZ {draw['superzahl']}")
            else:
                day.set(f"{draw_day}-Ziehung • {draw_date} • Daten werden bei Bedarf geladen")
        except ValueError:
            day.set("Datum prüfen")

    de.insert(0, next_valid_draw_date())
    update_draw_from_date()
    de.bind("<KeyRelease>", update_draw_from_date)

    ttk.Label(form, text="Name:").grid(row=9, column=0, padx=8, pady=6, sticky="w")
    ne = ttk.Entry(form, width=28)
    ne.insert(0, ticket["name"] if editing else "Mein Tipp")
    ne.grid(row=9, column=1, padx=8, pady=6)

    if editing:
        for idx, e in enumerate(entries, 1):
            e.insert(0, str(ticket[f"n{idx}"]))
        se.delete(0, tk.END)
        se.insert(0, str(ticket["superzahl"]))
        de.delete(0, tk.END)
        # Der gespeicherte Ziehungstag ist das maßgebliche historische Datum.
        de.insert(0, ticket["draw_date"] or datetime.now().strftime("%d.%m.%Y"))
        update_draw_from_date()

    def save():
        try:
            nums = [int(e.get()) for e in entries]
            sz = int(se.get())
        except ValueError:
            messagebox.showerror("Eingabe", "Bitte nur ganze Zahlen eingeben.", parent=win)
            return
        if len(set(nums)) != 6 or not all(1 <= n <= 49 for n in nums):
            messagebox.showerror("Eingabe", "Bitte 6 verschiedene Zahlen von 1 bis 49 eingeben.", parent=win)
            return
        if not 0 <= sz <= 9:
            messagebox.showerror("Eingabe", "Die Superzahl muss 0 bis 9 sein.", parent=win)
            return
        try:
            tip_date = datetime.strptime(de.get().strip(), "%d.%m.%Y")
            draw_date_obj, detected_day = find_draw_for_date(tip_date.strftime("%d.%m.%Y"))
            draw_date = draw_date_obj.strftime("%d.%m.%Y")
        except ValueError:
            messagebox.showerror(
                "Datum",
                "Bitte ein gültiges Datum im Format TT.MM.JJJJ eingeben.",
                parent=win)
            return

        day.set(f"{detected_day}-Ziehung • {draw_date}")

        nums.sort()
        name = ne.get().strip() or "Mein Tipp"
        conn = db()
        if editing:
            conn.execute("""UPDATE tickets SET
                name=?, draw_day=?, draw_date=?,
                n1=?, n2=?, n3=?, n4=?, n5=?, n6=?, superzahl=?
                WHERE id=?""",
                (name, detected_day, draw_date, *nums, sz, ticket["id"]))
            # Eine Änderung des Tipps darf eine alte Gewinnbenachrichtigung
            # nicht fälschlich weiterverwenden.
            conn.execute("DELETE FROM notified_wins WHERE ticket_id=?", (ticket["id"],))
        else:
            conn.execute("""INSERT INTO tickets
                (name,draw_day,draw_date,n1,n2,n3,n4,n5,n6,superzahl)
                VALUES(?,?,?,?,?,?,?,?,?,?)""",
                (name, detected_day, draw_date, *nums, sz))
        conn.commit()
        conn.close()

        # Den gerade gespeicherten Tipp sofort mit GENAU seiner Ziehung
        # verbinden. Falls die Ziehung noch nicht lokal vorhanden ist, wird
        # sie direkt aus dem Archiv geladen. Danach kann der nächste Tipp
        # eingegeben werden, ohne vorher „Aktualisieren“ zu drücken.
        try:
            conn = db()
            draw = conn.execute(
                "SELECT * FROM official_draws WHERE draw_date=?", (draw_date,)
            ).fetchone()
            conn.close()
            if draw is None:
                real_date, real_day, hist_nums, hist_sz, hist_quotas = fetch_historical_draw(draw_date)
                save_official_draw(real_date, hist_nums, hist_sz)
                save_quotas(real_date, real_day, hist_quotas)
        except Exception:
            # Der Tipp bleibt trotzdem gespeichert; ein späterer Start oder
            # „Aktualisieren“ kann fehlende historische Daten nachladen.
            pass
        try:
            sync_historical_ticket_data()
        except Exception:
            pass

        if editing:
            win.destroy()
            check_all_saved_tips(show_message=True)
            set_status(f"Tipp „{name}“ geändert.")
        else:
            # Bei einem neuen Tipp bleibt das Eingabefenster geöffnet,
            # damit direkt der nächste Tipp eingegeben werden kann.
            for entry in entries:
                entry.delete(0, tk.END)
            se.delete(0, tk.END)
            se.insert(0, "")
            ne.delete(0, tk.END)
            ne.insert(0, "Mein Tipp")
            de.delete(0, tk.END)
            de.insert(0, datetime.now().strftime("%d.%m.%Y"))
            update_draw_from_date()
            check_all_saved_tips(show_message=True)
            set_status("Tipp gespeichert – bereit für den nächsten Tipp.")
            entries[0].focus_set()

    bf = ttk.Frame(win)
    bf.pack(pady=18)
    ttk.Button(bf, text="✓ Tipp speichern", command=save).pack(side="left", padx=6, ipadx=12, ipady=5)
    ttk.Button(bf, text="Abbrechen", command=win.destroy).pack(side="left", padx=6, ipadx=12, ipady=5)


def show_tickets():
    win = tk.Toplevel(root)
    win.title("Meine Lotto-Tipps")
    win.geometry("1120x600")
    ttk.Label(win, text="Meine Lotto-Tipps", style="Title.TLabel").pack(pady=(15, 4))
    ttk.Label(win, text="Jeder Tipp bleibt seiner konkreten Ziehung zugeordnet.").pack(pady=(0, 8))

    tree = ttk.Treeview(win, columns=("id","name","day","date","numbers","sz"),
                        show="headings")
    for col, head, width in [
        ("id","Nr.",55),("name","Name",170),("day","Ziehung",95),
        ("date","Datum",110),("numbers","Lottozahlen",420),("sz","Superzahl",90)]:
        tree.heading(col, text=head)
        tree.column(col, width=width, anchor="center")
    tree.pack(fill="both", expand=True, padx=18, pady=10)

    conn = db()
    rows = conn.execute("SELECT * FROM tickets ORDER BY id").fetchall()
    conn.close()
    for r in rows:
        tree.insert("", "end", iid=str(r["id"]),
                    values=(r["id"], r["name"], r["draw_day"], r["draw_date"] or "–",
                            " – ".join(str(r[f"n{i}"]) for i in range(1,7)), r["superzahl"]))

    bf = ttk.Frame(win)
    bf.pack(pady=10)

    def selected():
        s = tree.selection()
        if not s:
            messagebox.showwarning("Auswahl", "Bitte einen Tipp auswählen.", parent=win)
            return None
        conn = db()
        r = conn.execute("SELECT * FROM tickets WHERE id=?", (int(s[0]),)).fetchone()
        conn.close()
        return r

    def check():
        r = selected()
        if r:
            check_ticket(r, win)

    def edit():
        r = selected()
        if r:
            win.destroy()
            add_ticket(r)

    def delete():
        r = selected()
        if r and messagebox.askyesno("Löschen", f"„{r['name']}“ löschen?", parent=win):
            conn = db()
            conn.execute("DELETE FROM tickets WHERE id=?", (r["id"],))
            conn.execute("DELETE FROM notified_wins WHERE ticket_id=?", (r["id"],))
            conn.commit()
            conn.close()
            win.destroy()
            show_tickets()

    ttk.Button(bf, text="Ausgewählten Tipp prüfen", command=check).pack(side="left", padx=5, ipadx=8, ipady=4)
    ttk.Button(bf, text="Tipp bearbeiten", command=edit).pack(side="left", padx=5, ipadx=8, ipady=4)
    ttk.Button(bf, text="Tipp löschen", command=delete).pack(side="left", padx=5, ipadx=8, ipady=4)
    ttk.Button(bf, text="Neuen Tipp", command=add_ticket).pack(side="left", padx=5, ipadx=8, ipady=4)
    ttk.Button(bf, text="Schließen", command=win.destroy).pack(side="left", padx=5, ipadx=8, ipady=4)


def check_ticket(ticket, parent=None):
    # Zuerst exakt die zum Tipp gehörende historische Ziehung verwenden.
    # Fehlt sie, wird sie automatisch aus dem Archiv nachgeladen.
    draw_date = ticket["draw_date"]
    conn = db()
    if draw_date:
        d = conn.execute(
            "SELECT * FROM official_draws WHERE draw_date=?",
            (draw_date,)).fetchone()
    else:
        d = None
    conn.close()

    if d is None and draw_date:
        try:
            real_date, real_day, nums, sz, quotas = fetch_historical_draw(draw_date)
            save_official_draw(real_date, nums, sz)
            save_quotas(real_date, real_day, quotas)
            conn = db()
            d = conn.execute(
                "SELECT * FROM official_draws WHERE draw_date=?",
                (draw_date,)).fetchone()
            conn.close()
        except Exception as e:
            messagebox.showinfo(
                "Tipp prüfen",
                f"Die historische Ziehung am {draw_date} konnte nicht geladen werden.\n\n"
                f"Fehler: {e}",
                parent=parent)
            return

    if d is None:
        conn = db()
        draws = conn.execute(
            "SELECT * FROM official_draws WHERE draw_day=? ORDER BY id DESC",
            (ticket["draw_day"],)).fetchall()
        conn.close()
        if draws:
            d = draws[0]

    if d is None:
        messagebox.showinfo(
            "Tipp prüfen",
            f"Für die Ziehung am {ticket['draw_date']} sind noch keine "
            "offiziellen Gewinnzahlen gespeichert und konnten nicht automatisch "
            "geladen werden.",
            parent=parent)
        return
    winning = {d[f"n{i}"] for i in range(1, 7)}
    own = {ticket[f"n{i}"] for i in range(1, 7)}
    correct = len(winning & own)
    super_match = ticket["superzahl"] == d["superzahl"]
    cls = get_win_class(ticket, d)

    conn = db()
    quota = conn.execute(
        "SELECT * FROM winning_quotas WHERE draw_date=? AND class_no=?",
        (d["draw_date"], cls)).fetchone() if cls else None
    conn.close()

    if cls:
        qtext = f"Gewinnklasse {cls}\nGewinnquote: {money(quota['quota']) if quota else 'noch nicht gespeichert'}"
        play_sound()
    else:
        qtext = "Kein Gewinn"

    title = "🎉 Gewinn!" if cls else "Tipp-Ergebnis"
    messagebox.showinfo(title,
        f"Tipp: {ticket['name']}\nZiehung: {d['draw_date']} ({d['draw_day']})\n\n"
        f"Gewinnzahlen: {', '.join(str(d[f'n{i}']) for i in range(1,7))}\n"
        f"Superzahl: {d['superzahl']}\n\n"
        f"Dein Tipp: {', '.join(str(ticket[f'n{i}']) for i in range(1,7))}\n"
        f"Superzahl: {ticket['superzahl']}\n\n"
        f"Richtige Zahlen: {correct}\nSuperzahl richtig: {'Ja' if super_match else 'Nein'}\n\n{qtext}",
        parent=parent)


def check_all_saved_tips(show_message=True):
    """Check every saved tip against its exact historical draw date.

    A tip never gets compared with a newer or older drawing just because the
    weekday matches. This makes old tips (weeks/months/years back) safe to
    check as soon as their historical draw is available.
    """
    conn = db()
    tickets = conn.execute("SELECT * FROM tickets ORDER BY id").fetchall()
    draws = conn.execute("SELECT * FROM official_draws ORDER BY id").fetchall()
    wins = []

    for ticket in tickets:
        for draw in draws:
            if ticket["draw_date"]:
                if ticket["draw_date"] != draw["draw_date"]:
                    continue
            elif ticket["draw_day"] != draw["draw_day"]:
                continue
            if ticket["draw_day"] != draw["draw_day"]:
                continue

            cls = get_win_class(ticket, draw)
            if not cls:
                continue

            already = conn.execute(
                "SELECT 1 FROM notified_wins WHERE ticket_id=? AND draw_date=? AND class_no=?",
                (ticket["id"], draw["draw_date"], cls)
            ).fetchone()
            if already:
                continue

            quota = conn.execute(
                "SELECT * FROM winning_quotas WHERE draw_date=? AND class_no=?",
                (draw["draw_date"], cls)
            ).fetchone()
            conn.execute(
                "INSERT OR IGNORE INTO notified_wins(ticket_id,draw_date,class_no) VALUES(?,?,?)",
                (ticket["id"], draw["draw_date"], cls)
            )
            wins.append((ticket, draw, cls, quota))

    conn.commit()
    conn.close()

    if not wins or not show_message:
        return

    lines = ["🎉 GEWINN – ein gespeicherter Tipp hat gewonnen!\n"]
    for ticket, draw, cls, quota in wins:
        qtext = money(quota["quota"]) if quota and quota["quota"] is not None else "noch nicht gespeichert"
        lines.append(
            f"• {ticket['name']} – {draw['draw_date']} ({draw['draw_day']})\n"
            f"  Gewinnklasse {cls} – Gewinnquote: {qtext}"
        )
    play_sound()
    messagebox.showinfo("🎉 Gewinnmeldung", "\n\n".join(lines), parent=root)

def update_home_cards():
    conn = db()
    rows = conn.execute(
        "SELECT * FROM official_draws ORDER BY id DESC").fetchall()
    quotas = conn.execute(
        "SELECT * FROM winning_quotas ORDER BY class_no").fetchall()
    conn.close()
    qmap = {}
    for q in quotas:
        qmap.setdefault(q["draw_date"], {})[q["class_no"]] = q

    # Do NOT use the newest database row (id) here. The external history
    # import can insert an older drawing after a newer one, so id order is
    # not chronological. Always select the latest concrete draw date per
    # weekday. This keeps the Wednesday/Saturday cards stable and prevents
    # an older historical drawing from replacing the current one.
    latest = {}
    for r in rows:
        day = r["draw_day"]
        if day not in ("Mittwoch", "Samstag"):
            continue
        current = latest.get(day)
        if current is None or date_key(r["draw_date"]) > date_key(current["draw_date"]):
            latest[day] = r

    for day, box in (("Mittwoch", wednesday_card), ("Samstag", saturday_card)):
        for child in box.winfo_children():
            child.destroy()
        d = latest.get(day)
        if not d:
            ttk.Label(box, text="Noch keine Daten", style="CardMuted.TLabel").pack(pady=35)
            continue

        ttk.Label(box, text=f"Ziehung vom {d['draw_date']}", style="CardSmall.TLabel").pack(pady=(12, 6))
        ttk.Label(box, text="  ".join(f"{d[f'n{i}']:02d}" for i in range(1,7)),
                  style="Numbers.TLabel").pack(pady=2)
        ttk.Label(box, text=f"Superzahl: {d['superzahl']}",
                  style="Super.TLabel").pack(pady=(4, 10))

        sep = ttk.Separator(box)
        sep.pack(fill="x", padx=18, pady=5)
        ttk.Label(box, text="Gewinnquoten", style="CardHead.TLabel").pack(pady=(5, 3))

        q = qmap.get(d["draw_date"], {})
        shown = [q[i] for i in range(1, 10) if i in q]
        if not shown:
            ttk.Label(box, text="Noch keine Quoten gespeichert",
                      style="CardMuted.TLabel").pack(pady=12)
        else:
            grid = ttk.Frame(box)
            grid.pack(fill="x", padx=18, pady=(2, 12))
            for i, item in enumerate(shown):
                ttk.Label(grid, text=f"{item['class_no']}: {quota_label(item)}",
                          style="Quota.TLabel").grid(row=i//3, column=i%3, padx=5, pady=2, sticky="w")


def set_status(text):
    status_label.config(text=text)


def show_statistics():
    conn = db()
    total_sim = conn.execute("SELECT COUNT(*) FROM super_numbers").fetchone()[0]
    sim_lotto = {r["number"]: r["count"] for r in conn.execute(
        "SELECT number,COUNT(*) count FROM lotto_numbers GROUP BY number")}
    sim_supers = {r["number"]: r["count"] for r in conn.execute(
        "SELECT number,COUNT(*) count FROM super_numbers GROUP BY number")}
    draws = conn.execute("SELECT * FROM official_draws ORDER BY id").fetchall()
    conn.close()

    w = tk.Toplevel(root)
    w.title(f"Lotto-Statistik – v{VERSION}")
    w.geometry("850x680")

    ttk.Label(w, text="Lotto-Statistik", style="Title.TLabel").pack(pady=(18, 3))
    ttk.Label(w, text=f"Simulationen: {total_sim}  •  offizielle Ziehungen: {len(draws)}").pack(pady=(0, 12))

    nb = ttk.Notebook(w)
    nb.pack(fill="both", expand=True, padx=15, pady=10)

    def add_frequency_tab(title, values, denominator):
        f = ttk.Frame(nb, padding=10)
        tree = ttk.Treeview(f, columns=("n","count","pct"), show="headings")
        tree.heading("n", text=title)
        tree.heading("count", text="Anzahl")
        tree.heading("pct", text="Anteil")
        tree.column("n", width=150, anchor="center")
        tree.column("count", width=120, anchor="center")
        tree.column("pct", width=140, anchor="center")
        for n, count in values:
            pct = count / denominator * 100 if denominator else 0
            tree.insert("", "end", values=(n, count, f"{pct:.2f} %"))
        tree.pack(fill="both", expand=True)
        nb.add(f, text=title)

    add_frequency_tab("Simulation 1–49",
        [(n, sim_lotto.get(n, 0)) for n in range(1,50)], total_sim * 6)

    add_frequency_tab("Simulation Superzahl",
        [(n, sim_supers.get(n, 0)) for n in range(10)], total_sim)

    # Official statistics: real percentage of stored draws in which each number appeared.
    official_den = len(draws)
    official_counts = {n: 0 for n in range(1,50)}
    wed_counts = {n: 0 for n in range(1,50)}
    sat_counts = {n: 0 for n in range(1,50)}
    for d in draws:
        for i in range(1,7):
            official_counts[d[f"n{i}"]] += 1
            (wed_counts if d["draw_day"] == "Mittwoch" else sat_counts)[d[f"n{i}"]] += 1

    f = ttk.Frame(nb, padding=10)
    tree = ttk.Treeview(f, columns=("n","count","pct"), show="headings")
    for c,h,wid in (("n","Zahl",100),("count","Ziehungen",130),("pct","Anteil der Ziehungen",190)):
        tree.heading(c,text=h); tree.column(c,width=wid,anchor="center")
    for n in range(1,50):
        pct = official_counts[n]/official_den*100 if official_den else 0
        tree.insert("", "end", values=(n, official_counts[n], f"{pct:.2f} %"))
    tree.pack(fill="both",expand=True)
    nb.add(f,text="Offiziell 1–49")

    # Official Superzahl statistics: count only stored official draws
    # that contain a valid Superzahl (0–9).
    official_super_counts = {n: 0 for n in range(10)}
    official_super_den = 0
    for d in draws:
        try:
            sz = int(d["superzahl"])
        except (TypeError, ValueError):
            continue
        if 0 <= sz <= 9:
            official_super_counts[sz] += 1
            official_super_den += 1

    f = ttk.Frame(nb, padding=10)
    tree = ttk.Treeview(f, columns=("n","count","pct"), show="headings")
    for c,h,wid in (
        ("n","Superzahl",100),
        ("count","Ziehungen",130),
        ("pct","Anteil der Ziehungen",190),
    ):
        tree.heading(c,text=h)
        tree.column(c,width=wid,anchor="center")
    for n in range(10):
        pct = official_super_counts[n] / official_super_den * 100 if official_super_den else 0
        tree.insert("", "end", values=(n, official_super_counts[n], f"{pct:.2f} %"))
    tree.pack(fill="both",expand=True)
    nb.add(f,text="Offiziell Superzahl")

    for day, counts in (("Mittwoch", wed_counts), ("Samstag", sat_counts)):
        f = ttk.Frame(nb, padding=10)
        tree = ttk.Treeview(f, columns=("n","count","pct"), show="headings")
        for c,h,wid in (("n","Zahl",100),("count","Ziehungen",130),("pct","Anteil",160)):
            tree.heading(c,text=h); tree.column(c,width=wid,anchor="center")
        den = sum(1 for d in draws if d["draw_day"] == day)
        for n in range(1,50):
            pct = counts[n]/den*100 if den else 0
            tree.insert("", "end", values=(n, counts[n], f"{pct:.2f} %"))
        tree.pack(fill="both",expand=True)
        nb.add(f,text=day)

    ttk.Label(w, text="Offizielle Prozentwerte = Anteil der gespeicherten Ziehungen, in denen die Zahl vorkam.",
              style="CardMuted.TLabel").pack(pady=4)
    ttk.Button(w, text="Schließen", command=w.destroy).pack(pady=10)


def show_analysis():
    conn = db()
    draws = conn.execute("SELECT * FROM official_draws ORDER BY id DESC").fetchall()
    tickets = conn.execute("SELECT * FROM tickets ORDER BY id").fetchall()
    quotas = conn.execute("SELECT * FROM winning_quotas").fetchall()
    conn.close()
    qmap = {(q["draw_date"], q["class_no"]): q for q in quotas}

    w = tk.Toplevel(root)
    w.title("Lotto-Analyse")
    w.geometry("1180x700")
    ttk.Label(w, text="Lotto-Analyse", style="Title.TLabel").pack(pady=(15, 4))
    ttk.Label(w, text="Ziehungen, Gewinnquoten und eigene Tipps an einem Ort").pack(pady=(0, 8))

    nb = ttk.Notebook(w)
    nb.pack(fill="both", expand=True, padx=12, pady=8)

    f = ttk.Frame(nb, padding=8)
    nb.add(f, text="Ziehungen & Quoten")
    tr = ttk.Treeview(f, columns=("date","day","numbers","sz","quota"), show="headings")
    for c,h,wd in (("date","Datum",100),("day","Ziehung",90),("numbers","Gewinnzahlen",300),
                   ("sz","SZ",55),("quota","Gewinnquoten",420)):
        tr.heading(c,text=h); tr.column(c,width=wd,anchor="center")
    tr.pack(fill="both",expand=True)
    for d in draws:
        qs = []
        for cls in range(1,10):
            q = qmap.get((d["draw_date"],cls))
            if q:
                qs.append(f"{cls}: {quota_label(q)}")
        tr.insert("", "end", values=(d["draw_date"],d["draw_day"],
            " – ".join(str(d[f"n{i}"]) for i in range(1,7)),d["superzahl"],"; ".join(qs) or "–"))

    f = ttk.Frame(nb, padding=8)
    nb.add(f, text="Meine Tipps")
    tt = ttk.Treeview(f, columns=("name","date","day","right","class","quota"), show="headings")
    for c,h,wd in (("name","Tipp",180),("date","Datum",100),("day","Tag",85),
                   ("right","Richtige",80),("class","Gewinnklasse",110),("quota","Quote",130)):
        tt.heading(c,text=h); tt.column(c,width=wd,anchor="center")
    tt.pack(fill="both",expand=True)
    for t in tickets:
        d = next((x for x in draws if x["draw_date"] == t["draw_date"] and
                  x["draw_day"] == t["draw_day"]), None)
        if not d:
            tt.insert("", "end", values=(t["name"],t["draw_date"] or "–",t["draw_day"],"–","–","–"))
            continue
        cls = get_win_class(t,d)
        correct = len({d[f"n{i}"] for i in range(1,7)} &
                      {t[f"n{i}"] for i in range(1,7)})
        q = qmap.get((d["draw_date"],cls)) if cls else None
        tt.insert("", "end", values=(t["name"],t["draw_date"],t["draw_day"],
                    correct,cls or "Kein Gewinn",money(q["quota"]) if q else "–"))

    ttk.Label(w, text="Ein Tipp wird immer nur mit der zugehörigen Ziehung seines Datums verglichen.",
              style="CardMuted.TLabel").pack(pady=5)
    ttk.Button(w,text="Schließen",command=w.destroy).pack(pady=8)


def show_help():
    w = tk.Toplevel(root)
    w.title("Lotto – Anleitung")
    w.geometry("760x620")
    t = tk.Text(w, wrap=tk.WORD, padx=18, pady=18, font=("Arial", 11))
    t.pack(fill="both",expand=True)
    t.insert("1.0", f"""LOTTO – ANLEITUNG v{VERSION}

STARTSEITE
• Mittwoch und Samstag werden getrennt angezeigt.
• Gewinnzahlen, Superzahl und gespeicherte Gewinnquoten stehen direkt auf der Startseite.
• „Aktualisieren“ ruft die aktuellen Daten aus dem Internet ab.
• Neue Ziehungen werden nur einmal gespeichert.

DATENBANK MANAGER
• Der „Datenbank Manager“ ist direkt unter „Lottozahlen ziehen“ erreichbar.
• Ein Datum kann direkt eingegeben oder über das kleine Kalenderfenster ausgewählt werden.
• Für eine gespeicherte Mittwoch-/Samstag-Ziehung werden Lottozahlen, Superzahl und alle vorhandenen Gewinnquoten angezeigt.
• Der Manager liest die lokale Datenbank; vorhandene Daten werden nicht verändert.

MEINE TIPPS
• Du kannst beliebig viele eigene Tipps speichern.
• Für jeden Tipp wird ein konkretes Ziehungsdatum gespeichert.
• Der Ziehungstag (Mittwoch/Samstag) wird automatisch aus dem Datum erkannt.
• Auch alte Tipps können eingetragen werden.
• Beim Start und über „Aktualisieren“ werden fehlende historische Daten für deine Tipps nachgeladen.
• Unter „Datenbank“ kannst du die externe Lotto-Datenbank ein- oder ausschalten. Beim ersten Einschalten wird die vollständige verfügbare Ziehungshistorie geladen. Anschließend werden automatisch fehlende endgültige Gewinnquoten ergänzt (9 Klassen ab 01.01.2020) und die Datenbank bei jedem Start auf neue Ziehungen geprüft. Bereits lokal gespeicherte Daten bleiben beim Ausschalten erhalten.
• Bei der Prüfung wird genau die zugehörige Ziehung verwendet.

GEWINNMELDUNG
• Gespeicherte Tipps werden automatisch geprüft, wenn passende Gewinnzahlen/Quoten vorhanden sind.
• Bereits gemeldete Gewinne werden nicht erneut gemeldet.
• Die Gewinnklasse und die zur Ziehung gespeicherte Quote werden angezeigt.

STATISTIK
• Simulationen werden mit Anzahl und Prozentwert dargestellt.
• Offizielle Ziehungen werden ebenfalls statistisch ausgewertet.
• Mittwoch und Samstag können getrennt betrachtet werden.

ANALYSE
• Zeigt gespeicherte Ziehungen und Gewinnquoten.
• Zeigt die Ergebnisse deiner gespeicherten Tipps.
• Alte Ziehungen bleiben für die historische Auswertung erhalten.

SOUND
• Das eigene Menü „Sound“ enthält einen An/Aus-Schalter, Sound-Einstellungen und einen Test-Sound.
• Als Treiber stehen PulseAudio (pulse), ALSA (alsa) und PortAudio (portaudio) zur Verfügung.
• Bei einem Gewinn wird automatisch eine Glocke abgespielt.

EINSTELLUNGEN
• Unter „Einstellungen“ kannst du zwischen Hell und Dunkel wechseln.
• Dort kann auch „Externe Lotto-Datenbank verwenden“ ein- oder ausgeschaltet werden.
• Beim ersten Einschalten wird die vollständige verfügbare externe Ziehungshistorie lokal geladen. Danach prüft das Programm die externe Datenbank bei jedem Start und bei „Aktualisieren“ automatisch auf neue bzw. geänderte Ziehungen. Du musst die Einstellung nur einmal aktivieren.
• Beim Ausschalten bleiben bereits lokal gespeicherte Daten erhalten.

AKTUALISIERUNG
• „Aktualisieren“ prüft bei aktivierter externer Datenbank den aktuellen Datenfeed, ergänzt fehlende Gewinnquoten und ruft danach die aktuellen Mittwoch-/Samstag-Ziehungen samt Gewinnquoten ab. Anschließend werden alle gespeicherten Tipps geprüft.
• „Aktualisieren“ ist der zentrale Aktualisierungsbutton.

HINWEIS
Die offiziellen Daten stammen aus öffentlich verfügbaren Lotto-Archivdaten. Für die tatsächliche Teilnahme am Lotto gelten die offiziellen Angaben des Veranstalters.
""")
    t.config(state=tk.DISABLED)
    ttk.Button(w,text="Schließen",command=w.destroy).pack(pady=10)


def show_about():
    w = tk.Toplevel(root)
    w.title("Info")
    w.geometry("320x210")
    w.resizable(False,False)
    ttk.Label(w,text="Lotto",style="Title.TLabel").pack(pady=(28,8))
    ttk.Label(w,text=f"Version {VERSION}",font=("Arial",12)).pack(pady=3)
    ttk.Label(w,text="By Goldisoft 2026",font=("Arial",11)).pack(pady=(12,18))
    ttk.Button(w,text="OK",command=w.destroy).pack()


def sync_historical_ticket_data():
    """Load missing final draws/quotas for every saved tip date."""
    conn = db()
    dates = [r["draw_date"] for r in conn.execute(
        "SELECT DISTINCT draw_date FROM tickets "
        "WHERE draw_date IS NOT NULL AND draw_date<>''").fetchall()]
    conn.close()

    done = 0
    errors = []
    for date_str in dates:
        try:
            conn = db()
            draw = conn.execute(
                "SELECT * FROM official_draws WHERE draw_date=?", (date_str,)).fetchone()
            quota_count = conn.execute(
                "SELECT COUNT(*) FROM winning_quotas WHERE draw_date=?",
                (date_str,)).fetchone()[0]
            conn.close()

            # If both draw and all nine quotas already exist, do nothing.
            if draw and quota_count >= 9:
                continue

            real_date, day, nums, sz, quotas = fetch_historical_draw(date_str)
            save_official_draw(real_date, nums, sz)
            save_quotas(real_date, day, quotas)
            done += 1
        except Exception as e:
            errors.append(f"{date_str}: {e}")
    return done, errors


def _startup_after_external_refresh():
    """Continue normal startup after the optional external history refresh."""
    try:
        fetch_current_draws(False)
        hist_done, hist_errors = sync_historical_ticket_data()
        update_home_cards()
        check_all_saved_tips(show_message=True)
        if hist_errors:
            set_status(
                f"Externe Historie aktualisiert. Aktuelle Daten geprüft. "
                f"Historisch nachgeladen: {hist_done}; {len(hist_errors)} Fehler."
            )
        else:
            set_status(
                f"Externe Historie aktualisiert. Aktuelle Mittwoch-/Samstag-Daten "
                f"und Quoten geprüft. Historisch nachgeladen: {hist_done}."
            )
    except Exception as e:
        try:
            fetch_current_draws(False)
            hist_done, hist_errors = sync_historical_ticket_data()
            update_home_cards()
            check_all_saved_tips(show_message=True)
            set_status(
                "Externe Datenbank wurde aktualisiert; aktuelle Daten konnten "
                f"nicht vollständig geprüft werden: {e}"
            )
        except Exception:
            update_home_cards()
            check_all_saved_tips(show_message=True)
            set_status("Start mit vorhandenen Daten – Internetdaten konnten nicht vollständig geladen werden.")


def startup_sync():
    # If the external history is enabled, refresh it on every start. The
    # official current source is then queried separately so a stale historical
    # mirror can never prevent the current Wednesday/Saturday result from
    # being updated.
    if external_database:
        set_status("Externe Datenbank aktiviert – Datenbestand wird aktualisiert …")
        download_external_database_async(force=True, on_complete=_startup_after_external_refresh)
        return
    try:
        fetch_current_draws(False)
        hist_done, hist_errors = sync_historical_ticket_data()
        update_home_cards()
        check_all_saved_tips(show_message=True)
        if hist_errors:
            set_status(
                f"Aktuell aktualisiert. Historische Daten: {hist_done} geladen; "
                f"{len(hist_errors)} konnten nicht geladen werden.")
        else:
            set_status(
                f"Aktuelle Mittwoch-/Samstag-Daten und Quoten geprüft. "
                f"Historisch nachgeladen: {hist_done}.")
    except Exception as e:
        try:
            hist_done, hist_errors = sync_historical_ticket_data()
            update_home_cards()
            check_all_saved_tips(show_message=True)
            if hist_errors:
                set_status("Start mit gespeicherten Daten; einige historische Daten konnten nicht geladen werden.")
            else:
                set_status(f"Start mit gespeicherten Daten; historisch nachgeladen: {hist_done}.")
        except Exception:
            set_status("Start ohne Internetdaten – vorhandene gespeicherte Daten werden angezeigt.")
            check_all_saved_tips(show_message=True)


# ---------- EINSTELLUNGEN / INI ----------
SETTINGS_DIR = Path(__file__).resolve().parent / "data"
SETTINGS_FILE = SETTINGS_DIR / "settings.ini"

def load_settings():
    cfg = configparser.ConfigParser()
    try:
        if SETTINGS_FILE.exists():
            cfg.read(SETTINGS_FILE, encoding="utf-8")
        return (
            cfg.get("Appearance", "theme", fallback="light").lower(),
            cfg.getboolean("Data", "external_database", fallback=False),
            cfg.getboolean("Sound", "enabled", fallback=True),
            cfg.get("Sound", "driver", fallback="pulse").lower(),
        )
    except Exception:
        return "light", False, True, "pulse"

def save_settings():
    SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
    cfg = configparser.ConfigParser()
    cfg["Appearance"] = {"theme": current_theme}
    cfg["Data"] = {"external_database": str(external_database).lower()}
    cfg["Sound"] = {
        "enabled": str(sound_enabled).lower(),
        "driver": sound_driver,
    }
    with SETTINGS_FILE.open("w", encoding="utf-8") as f:
        cfg.write(f)

# ---------- SOUND ----------
SOUND_DRIVERS = ("pulse", "alsa", "portaudio")

def _sound_wave_path():
    """Create a tiny bell-like WAV once and return its path."""
    path = SETTINGS_DIR / "win_bell.wav"
    if path.exists():
        return path
    SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
    rate = 44100
    duration = 0.75
    samples = int(rate * duration)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(rate)
        for i in range(samples):
            t = i / rate
            env = max(0.0, 1.0 - t / duration) ** 1.6
            value = (
                math.sin(2 * math.pi * 880 * t) * 0.55
                + math.sin(2 * math.pi * 1320 * t) * 0.28
                + math.sin(2 * math.pi * 1760 * t) * 0.17
            ) * env
            wf.writeframes(int(max(-1.0, min(1.0, value)) * 32767).to_bytes(2, "little", signed=True))
    return path

def available_sound_drivers():
    found = []
    if shutil.which("paplay") or shutil.which("pactl"):
        found.append("pulse")
    if shutil.which("aplay"):
        found.append("alsa")
    try:
        import sounddevice  # noqa: F401
        found.append("portaudio")
    except Exception:
        pass
    return found

def play_sound(force=False):
    """Play the configured notification sound without blocking the GUI."""
    if not sound_enabled and not force:
        return
    def worker():
        path = _sound_wave_path()
        try:
            if sound_driver == "pulse" and shutil.which("paplay"):
                subprocess.run(["paplay", str(path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=4)
                return
            if sound_driver == "alsa" and shutil.which("aplay"):
                subprocess.run(["aplay", "-q", str(path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=4)
                return
            if sound_driver == "portaudio":
                try:
                    import sounddevice as sd
                    import numpy as np
                    with wave.open(str(path), "rb") as wf:
                        frames = wf.readframes(wf.getnframes())
                        data = np.frombuffer(frames, dtype=np.int16)
                        sd.play(data, wf.getframerate(), blocking=True)
                    return
                except Exception:
                    pass
            # Last-resort desktop bell. This keeps the notification useful
            # even if a selected backend is not installed on the system.
            root.after(0, root.bell)
        except Exception:
            try:
                root.after(0, root.bell)
            except Exception:
                pass
    import threading
    threading.Thread(target=worker, name="LottoSound", daemon=True).start()

def set_sound_enabled(enabled):
    global sound_enabled
    sound_enabled = bool(enabled)
    if "sound_var" in globals():
        sound_var.set(sound_enabled)
    save_settings()
    set_status("Gewinn-Sound: " + ("An" if sound_enabled else "Aus"))

def set_sound_driver(driver):
    global sound_driver
    sound_driver = driver if driver in SOUND_DRIVERS else "pulse"
    if "driver_var_menu" in globals():
        driver_var_menu.set(sound_driver)
    save_settings()
    set_status(f"Sound-Treiber: {sound_driver}")

def show_sound_settings():
    win = tk.Toplevel(root)
    win.title("Sound-Einstellungen")
    win.geometry("500x360")
    win.minsize(460, 320)
    ttk.Label(win, text="Sound-Einstellungen", style="Title.TLabel").pack(pady=(18, 6))
    ttk.Label(win, text="Bei einem Gewinn wird automatisch eine Glocke abgespielt.").pack(pady=(0, 14))

    enabled_var = tk.BooleanVar(value=sound_enabled)
    ttk.Checkbutton(win, text="Gewinn-Sound aktiv", variable=enabled_var).pack(pady=8)

    ttk.Label(win, text="Sound-Treiber:").pack(pady=(14, 4))
    driver_var = tk.StringVar(value=sound_driver)
    combo = ttk.Combobox(win, textvariable=driver_var, values=SOUND_DRIVERS, state="readonly", width=22)
    combo.pack()

    detected = available_sound_drivers()
    text = "Verfügbar: " + (", ".join(detected) if detected else "keiner erkannt – Desktop-Glocke als Fallback")
    ttk.Label(win, text=text, wraplength=430, justify="center", style="CardMuted.TLabel").pack(pady=14)

    def save_and_close():
        set_sound_enabled(enabled_var.get())
        set_sound_driver(driver_var.get())
        win.destroy()

    bf = ttk.Frame(win)
    bf.pack(pady=18)
    ttk.Button(bf, text="🔔 Test-Sound", command=lambda: play_sound(force=True)).pack(side="left", padx=6, ipadx=8, ipady=5)
    ttk.Button(bf, text="Speichern", command=save_and_close).pack(side="left", padx=6, ipadx=8, ipady=5)
    ttk.Button(bf, text="Schließen", command=win.destroy).pack(side="left", padx=6, ipadx=8, ipady=5)

# ---------- THEMES ----------
THEME_LIGHT = {
    "bg": "#eeeeee",
    "fg": "#111111",
    "field": "#ffffff",
    "button": "#dddddd",
    "active": "#c8c8c8",
}
THEME_DARK = {
    "bg": "#242424",
    "fg": "#f0f0f0",
    "field": "#303030",
    "button": "#404040",
    "active": "#555555",
}

current_theme, external_database, sound_enabled, sound_driver = load_settings()


def apply_theme():
    th = THEME_DARK if current_theme == "dark" else THEME_LIGHT
    root.configure(bg=th["bg"])
    style.configure("TFrame", background=th["bg"])
    style.configure("TLabel", background=th["bg"], foreground=th["fg"])
    style.configure("Title.TLabel", background=th["bg"], foreground=th["fg"], font=("Arial", 23, "bold"))
    style.configure("Hero.TLabel", background=th["bg"], foreground=th["fg"], font=("Arial", 30, "bold"))
    style.configure("Numbers.TLabel", background=th["bg"], foreground=th["fg"], font=("Arial", 22, "bold"))
    style.configure("Super.TLabel", background=th["bg"], foreground=th["fg"], font=("Arial", 12, "bold"))
    style.configure("CardHead.TLabel", background=th["bg"], foreground=th["fg"], font=("Arial", 11, "bold"))
    style.configure("CardSmall.TLabel", background=th["bg"], foreground=th["fg"], font=("Arial", 10))
    style.configure("CardMuted.TLabel", background=th["bg"], foreground=th["fg"], font=("Arial", 10))
    style.configure("Quota.TLabel", background=th["bg"], foreground=th["fg"], font=("Arial", 9))
    style.configure("TLabelframe", background=th["bg"], foreground=th["fg"])
    style.configure("TLabelframe.Label", background=th["bg"], foreground=th["fg"])
    style.configure("TButton", background=th["button"], foreground=th["fg"])
    style.map("TButton", background=[("active", th["active"])])
    style.configure("TEntry", fieldbackground=th["field"], foreground=th["fg"])
    style.configure("TCombobox", fieldbackground=th["field"], foreground=th["fg"])
    root.option_add("*Menu.background", th["bg"])
    root.option_add("*Menu.foreground", th["fg"])
    root.option_add("*Menu.activeBackground", th["active"])
    root.option_add("*Menu.activeForeground", th["fg"])


def set_external_database(enabled):
    global external_database
    external_database = bool(enabled)
    save_settings()
    if external_database:
        set_status("Externe Datenbank aktiviert – vollständiger Download wird gestartet …")
        root.after(100, lambda: download_external_database_async(force=True, on_complete=_startup_after_external_refresh))
    else:
        set_status("Externe Datenbank: Aus – lokale Daten bleiben erhalten.")

def set_theme(name):
    global current_theme
    current_theme = "dark" if name == "dark" else "light"
    apply_theme()
    save_settings()
    set_status("Darstellung: " + ("Dunkel" if current_theme == "dark" else "Hell"))


# ---------- GUI ----------
create_tables()
root = tk.Tk()
root.title(f"Lotto v{VERSION}")
root.geometry("1080x760")
root.minsize(900, 650)

style = ttk.Style(root)
try:
    style.theme_use("clam")
except tk.TclError:
    pass
style.configure("Title.TLabel", font=("Arial", 23, "bold"))
style.configure("Hero.TLabel", font=("Arial", 30, "bold"))
style.configure("Numbers.TLabel", font=("Arial", 22, "bold"))
style.configure("Super.TLabel", font=("Arial", 12, "bold"))
style.configure("CardHead.TLabel", font=("Arial", 11, "bold"))
style.configure("CardSmall.TLabel", font=("Arial", 10))
style.configure("CardMuted.TLabel", font=("Arial", 10))
style.configure("Quota.TLabel", font=("Arial", 9))

# Design Plus 2: farbige Akzente für die wichtigsten Aktionen
style.configure("Update.TButton", font=("Arial", 11, "bold"),
                foreground="#ffffff", background="#1976d2")
style.configure("Tipps.TButton", font=("Arial", 11, "bold"),
                foreground="#ffffff", background="#2e7d32")
style.configure("Draw.TButton", font=("Arial", 11, "bold"),
                foreground="#ffffff", background="#c58b00")
style.configure("Stats.TButton", font=("Arial", 11, "bold"),
                foreground="#ffffff", background="#6a1b9a")
style.configure("Db.TButton", font=("Arial", 11, "bold"),
                foreground="#ffffff", background="#00796b")

# farbige Zahlenanzeige vorbereitet, ohne die Lotto-Logik zu verändern

main = ttk.Frame(root, padding=18)
main.pack(fill="both", expand=True)

header = ttk.Frame(main)
header.pack(fill="x", pady=(0, 12))
ttk.Label(header, text="🎱 Lotto Pionier", style="Hero.TLabel").pack(side="left")
ttk.Label(header, text=f"6 aus 49  •  v{VERSION}", font=("Arial", 11)).pack(side="left", padx=18, pady=(15,0))

cards = ttk.Frame(main)
cards.pack(fill="x", pady=5)
cards.columnconfigure(0, weight=1)
cards.columnconfigure(1, weight=1)

wednesday_card = ttk.LabelFrame(cards, text="  MITTWOCH-LOTTO  ", padding=5)
wednesday_card.grid(row=0,column=0,sticky="nsew",padx=(0,7))
saturday_card = ttk.LabelFrame(cards, text="  SAMSTAG-LOTTO  ", padding=5)
saturday_card.grid(row=0,column=1,sticky="nsew",padx=(7,0))

actions = ttk.LabelFrame(main, text="  Schnellzugriff  ", padding=12)
actions.pack(fill="x", pady=14)

buttons = ttk.Frame(actions)
buttons.pack(fill="x")
for col in range(3):
    buttons.columnconfigure(col, weight=1)

quick_buttons = [
    ("🔄 Aktualisieren", lambda: refresh_all_data(True), "Update.TButton"),
    ("⭐ Meine Tipps", show_tickets, "Tipps.TButton"),
    ("🎲 Lottozahlen ziehen", draw_numbers, "Draw.TButton"),
    ("📊 Analyse", show_analysis, "Stats.TButton"),
    ("📈 Statistik", show_statistics, "Stats.TButton"),
    ("💾 Datenbank Manager", show_database_manager, "Db.TButton"),
]
for idx, (label, command, style_name) in enumerate(quick_buttons):
    ttk.Button(
        buttons, text=label, command=command, style=style_name
    ).grid(
        row=idx // 3, column=idx % 3,
        padx=5, pady=4, sticky="ew", ipady=6
    )

sim_box = ttk.LabelFrame(main,text="  Letzte Simulation  ",padding=12)
sim_box.pack(fill="x",pady=(0,12))
simulated_label = ttk.Label(sim_box,text="Noch keine Simulation",font=("Arial",12))
simulated_label.pack()

status_label = ttk.Label(main,text="Lotto-Daten werden beim Start automatisch geprüft.",
                         style="CardMuted.TLabel")
status_label.pack(pady=(3,0))

menu = tk.Menu(root)
filem = tk.Menu(menu,tearoff=0)
filem.add_command(label="Beenden",command=root.destroy)
menu.add_cascade(label="Datei",menu=filem)

statm = tk.Menu(menu,tearoff=0)
statm.add_command(label="Statistik anzeigen",command=show_statistics)
statm.add_command(label="Datenbank Manager",command=show_database_manager)
menu.add_cascade(label="Statistiken",menu=statm)

tipsm = tk.Menu(menu,tearoff=0)
tipsm.add_command(label="Tipp hinzufügen",command=add_ticket)
tipsm.add_command(label="Meine Tipps anzeigen",command=show_tickets)
menu.add_cascade(label="Meine Tipps",menu=tipsm)

analysism = tk.Menu(menu,tearoff=0)
analysism.add_command(label="Lotto-Analyse",command=show_analysis)
menu.add_cascade(label="Analyse",menu=analysism)

themem = tk.Menu(menu, tearoff=0)
themem.add_command(label="Hell", command=lambda: set_theme("light"))
themem.add_command(label="Dunkel", command=lambda: set_theme("dark"))
menu.add_cascade(label="Theme", menu=themem)

databasem = tk.Menu(menu, tearoff=0)
external_var = tk.BooleanVar(value=external_database)
databasem.add_checkbutton(
    label="Externe Lotto-Datenbank verwenden",
    variable=external_var,
    command=lambda: set_external_database(external_var.get())
)
databasem.add_command(label="Datenbank Manager", command=show_database_manager)
menu.add_cascade(label="Datenbank", menu=databasem)

soundm = tk.Menu(menu, tearoff=0)
sound_var = tk.BooleanVar(value=sound_enabled)
soundm.add_checkbutton(
    label="Gewinn-Sound an",
    variable=sound_var,
    command=lambda: set_sound_enabled(sound_var.get())
)
soundm.add_command(label="Sound-Einstellungen …", command=show_sound_settings)
soundm.add_command(label="🔔 Test-Sound", command=lambda: play_sound(force=True))
soundm.add_separator()
driver_var_menu = tk.StringVar(value=sound_driver)
for _driver in SOUND_DRIVERS:
    soundm.add_radiobutton(
        label=f"Treiber: {_driver}",
        value=_driver,
        variable=driver_var_menu,
        command=lambda: set_sound_driver(driver_var_menu.get())
    )
menu.add_cascade(label="Sound", menu=soundm)

helpm = tk.Menu(menu,tearoff=0)
helpm.add_command(label="Anleitung",command=show_help)
helpm.add_separator()
helpm.add_command(label="Info",command=show_about)
menu.add_cascade(label="Hilfe",menu=helpm)
root.config(menu=menu)
apply_theme()

update_home_cards()
root.after(300, startup_sync)
root.mainloop()
