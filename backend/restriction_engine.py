from datetime import datetime, timedelta

DAY_MAP = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}
STATUS_RANK = {"ok": 0, "warning": 1, "blocked": 2}
SEVERITY_STATUS = {"red": "blocked", "orange": "warning", "yellow": "warning"}


def _parse_mmdd(mmdd):
    """'07-01' → (7, 1)"""
    if not mmdd:
        return None
    m, d = mmdd.split("-")
    return (int(m), int(d))


def _in_season(dt, date_from, date_to):
    """True jos dt:n kk-pv osuu date_from…date_to välille (vuosi ei merkitse)."""
    if not date_from or not date_to:
        return True
    start = _parse_mmdd(date_from)
    end = _parse_mmdd(date_to)
    cur = (dt.month, dt.day)
    if start <= end:
        return start <= cur <= end
    # vuodenvaihteen yli (esim. 11-01 … 03-31)
    return cur >= start or cur <= end


def _time_to_minutes(t):
    """'22:30' → 1350"""
    if not t:
        return None
    h, m = t.split(":")
    return int(h) * 60 + int(m)


def _times_overlap(day_start_min, day_end_min, rule_from, rule_to):
    """
    Tarkistaa, osuuko [day_start_min, day_end_min] johonkin kohtaan [rule_from, rule_to].
    Kaikki minuutteina. rule_to voi ylittää 24*60 (yön yli).
    """
    rf = _time_to_minutes(rule_from)
    rt = _time_to_minutes(rule_to)
    if rf is None or rt is None:
        return True

    if rule_to == "24:00":
        rt = 24 * 60

    # Yörajaukset (rf > rt = kaari yli puolenyön, esim. 22:00-05:00 → 1320-300)
    if rf > rt:
        # [0, rt] tai [rf, 1440]
        overlap1 = day_start_min < rt and day_end_min > 0
        overlap2 = day_start_min < 1440 and day_end_min > rf
        return overlap1 or overlap2

    return day_start_min < rt and day_end_min > rf


def check_restrictions(db, country_codes, departure_dt, arrival_dt, weight_t=24.0):
    """
    Tarkistaa ajokiellot ja painorajoitukset.

    Args:
        db: sqlite3-yhteys (row_factory=sqlite3.Row)
        country_codes: lista, esim. ['DE', 'CH']
        departure_dt: datetime
        arrival_dt: datetime
        weight_t: ajoneuvon kokonaispaino tonneissa

    Returns:
        {
          'overall': 'ok'|'warning'|'blocked',
          'by_country': { 'DE': {'status': ..., 'violations': [...]}, ... }
        }
    """
    by_country = {}
    overall_rank = 0

    for cc in country_codes:
        rules = db.execute(
            "SELECT * FROM country_restrictions WHERE country_code=? AND active=1",
            (cc,)
        ).fetchall()

        violations = []
        country_rank = 0

        for rule in rules:
            rtype = rule["restriction_type"]
            severity = rule["severity"]
            vstatus = SEVERITY_STATUS.get(severity, "warning")

            if rtype == "WEIGHT_LIMIT":
                if weight_t >= rule["min_weight_t"]:
                    violations.append({
                        "rule_id": rule["id"],
                        "type": rtype,
                        "description": rule["description"],
                        "severity": severity,
                        "status": vstatus,
                        "detail": f"Ajoneuvopaino {weight_t}t ≥ raja {rule['min_weight_t']}t"
                    })
                    country_rank = max(country_rank, STATUS_RANK[vstatus])
                continue

            # Aikarajoitukset — iteroi päivä kerrallaan
            current = departure_dt.replace(hour=0, minute=0, second=0, microsecond=0)
            end_day = arrival_dt.replace(hour=0, minute=0, second=0, microsecond=0)
            hit_days = []

            while current <= end_day:
                # Paino-ehto
                if weight_t < rule["min_weight_t"]:
                    current += timedelta(days=1)
                    continue

                # Kausi-ehto
                if not _in_season(current, rule["date_from"], rule["date_to"]):
                    current += timedelta(days=1)
                    continue

                # Viikonpäiväehto
                dow = rule["day_of_week"]
                if dow and dow != "all":
                    if DAY_MAP.get(dow) != current.weekday():
                        current += timedelta(days=1)
                        continue

                # Aikaikkuna: mikä osa tästä päivästä matka kattaa?
                day_start = current
                day_end = current + timedelta(days=1)

                trip_start_min = 0
                trip_end_min = 24 * 60

                if current.date() == departure_dt.date():
                    trip_start_min = departure_dt.hour * 60 + departure_dt.minute
                if current.date() == arrival_dt.date():
                    trip_end_min = arrival_dt.hour * 60 + arrival_dt.minute

                if _times_overlap(trip_start_min, trip_end_min, rule["time_from"], rule["time_to"]):
                    hit_days.append(current.strftime("%a %d.%m."))

                current += timedelta(days=1)

            if hit_days:
                violations.append({
                    "rule_id": rule["id"],
                    "type": rtype,
                    "description": rule["description"],
                    "severity": severity,
                    "status": vstatus,
                    "detail": f"Osuu päiville: {', '.join(hit_days)}",
                    "exemptions": rule["exemptions"]
                })
                country_rank = max(country_rank, STATUS_RANK[vstatus])

        rank_to_status = {0: "ok", 1: "warning", 2: "blocked"}
        by_country[cc] = {
            "status": rank_to_status[country_rank],
            "violations": violations
        }
        overall_rank = max(overall_rank, country_rank)

    return {
        "overall": rank_to_status[overall_rank],
        "by_country": by_country
    }
