"""Collect and replay bounded, licensed observations without executing trades."""
from __future__ import annotations

import argparse
import calendar as month_calendar
import csv
import hashlib
import io
import json
import math
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path, PurePosixPath

UTC = timezone.utc
SYMBOLS = ("BTCUSDT", "ETHUSDT")
NEA_URL = "https://api-open.data.gov.sg/v2/real-time/api/pm25"
VISION_ROOT = "https://data.binance.vision/data/spot"
VISION_BASE = VISION_ROOT + "/daily/klines"
MAX_BYTES = 1_000_000
MAX_SECONDS = 600
CLAIMS = {"live_exchange_connected": False, "orders_executed": False, "forecast_performance_measured": False, "graduate_learning_demonstrated": False}
LIMITATIONS = [
    "This bounded collection run is not an always-on streaming service.",
    "Checksums establish byte consistency, not source authentication or factual correctness.",
    "Historical observations were collected after the events and cannot establish prospective performance.",
    "Environmental observations and financial prices are separate research domains; no causal relationship is asserted.",
]
SOURCE_REGISTRY = {
    "nea_pm25": {
        "enabled": True, "mode": "live_observation", "name": "NEA PM2.5 via data.gov.sg",
        "url": NEA_URL, "licence": "Singapore Open Data Licence 1.0",
        "licence_url": "https://data.gov.sg/open-data-licence",
        "reviewed_on": "2026-11-13", "attribution_required": True,
        "scope": "Environmental observation and attributed derived research; no official endorsement.",
    },
    "binance_vision": {
        "enabled": True, "mode": "historical_replay", "name": "Binance Vision historical spot klines",
        "url": "https://data.binance.vision/", "licence": "CC BY-NC-SA 4.0 and Binance Vision Dataset Terms",
        "licence_url": "https://github.com/binance/binance-public-data/blob/master/TERMS_AND_CONDITIONS.md",
        "reviewed_on": "2026-11-13", "attribution_required": True,
        "scope": "Non-commercial research and education only; attributable derivatives retain CC BY-NC-SA 4.0. No commercial signals or live execution.",
    },
    "binance_live": {"enabled": False, "mode": "live_exchange", "reason": "Intended AI and public-output rights unresolved; no connection implemented."},
    "kraken_live": {"enabled": False, "mode": "live_exchange", "reason": "Intended AI and public-output rights unresolved; no connection implemented."},
    "coinbase_live": {"enabled": False, "mode": "live_exchange", "reason": "Written consent required for proposed AI use under current market-data terms; no connection implemented."},
}


class EvidenceError(ValueError):
    """A missing or invalid observation must not become research evidence."""



def policy_check(source_id: str, use: str) -> dict:
    """Fail closed for undefined uses; permission is scoped, never inferred from access."""
    uses = {"noncommercial_research", "noncommercial_publication", "commercial_use"}
    if source_id not in SOURCE_REGISTRY or use not in uses:
        raise EvidenceError("Unknown source or intended use")
    source = SOURCE_REGISTRY[source_id]
    allowed = source["enabled"] and (source_id == "nea_pm25" or use != "commercial_use")
    return {"source_id": source_id, "use": use, "allowed": allowed,
            "conditions": source.get("scope", source.get("reason")),
            "licence_url": source.get("licence_url"), "reviewed_on": source.get("reviewed_on")}


def utc_text(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        raise EvidenceError("Timezone-aware timestamp required")
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def parse_timestamp(value: str) -> datetime:
    if not isinstance(value, str):
        raise EvidenceError("Timestamp must be text")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise EvidenceError("Invalid timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise EvidenceError("Timestamp has no timezone")
    return parsed.astimezone(UTC)


def canonical_date(value: str) -> date:
    try:
        result = date.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise EvidenceError("Date must use YYYY-MM-DD") from exc
    if result.isoformat() != value:
        raise EvidenceError("Date must use YYYY-MM-DD")
    return result


def date_range(days: int, end: date, now: datetime) -> list[date]:
    if isinstance(days, bool) or not isinstance(days, int) or not 2 <= days <= 90:
        raise EvidenceError("days must be an integer between 2 and 90")
    if end >= now.astimezone(UTC).date():
        raise EvidenceError("Historical end date must be before today UTC; incomplete candles are excluded")
    try:
        return [end - timedelta(days=offset) for offset in reversed(range(days))]
    except OverflowError as exc:
        raise EvidenceError("Historical date window is outside the supported calendar") from exc


def _number(value: object, *, positive: bool = False) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (str, int, float)):
        raise EvidenceError("Invalid numeric observation")
    try:
        number = Decimal(str(value))
    except InvalidOperation as exc:
        raise EvidenceError("Invalid numeric observation") from exc
    if not number.is_finite() or not math.isfinite(float(number)) or number < 0 or positive and number <= 0:
        raise EvidenceError("Observation must be finite and nonnegative (prices strictly positive)")
    return number


def parse_nea(payload: bytes, received_at: datetime) -> dict:
    try:
        doc = json.loads(payload)
        if not isinstance(doc, dict) or isinstance(doc.get("code"), bool) or doc.get("code") != 0:
            raise EvidenceError("NEA returned a non-success code")
        items = doc["data"]["items"]
        if not isinstance(items, list) or not 1 <= len(items) <= 48:
            raise EvidenceError("NEA returned no bounded observation set")
        observations = []
        seen = set()
        for item in items:
            event = parse_timestamp(item["timestamp"])
            updated = parse_timestamp(item["updatedTimestamp"])
            if event in seen:
                raise EvidenceError("Duplicate NEA observation timestamp")
            seen.add(event)
            if event > received_at + timedelta(minutes=5) or updated > received_at + timedelta(minutes=5):
                raise EvidenceError("NEA observation or publication time is in the future")
            if updated < event:
                raise EvidenceError("NEA publication predates observation")
            readings = item["readings"]["pm25_one_hourly"]
            if not isinstance(readings, dict) or not {"north", "south", "east", "west", "central"}.issubset(readings):
                raise EvidenceError("NEA regional observations are incomplete")
            if set(readings) - {"north", "south", "east", "west", "central", "national"}:
                raise EvidenceError("Unrecognised NEA regional schema")
            values = {key: float(_number(value)) for key, value in sorted(readings.items())}
            observations.append({"event_time_utc": utc_text(event), "published_at_utc": utc_text(updated), "values": values})
        observations.sort(key=lambda value: value["event_time_utc"])
        latest = parse_timestamp(observations[-1]["event_time_utc"])
        age = (received_at - latest).total_seconds()
        return {"status": "ok" if age <= 10800 else "stale", "mode": "live_observation", "units": "micrograms per cubic metre", "received_at_utc": utc_text(received_at), "latest_age_seconds": round(age, 3), "observations": observations}
    except (KeyError, TypeError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise EvidenceError("Invalid or missing NEA response fields") from exc


def archive_plan(days: list[date], now: datetime, *, monthly: bool = True) -> list[dict]:
    """Choose closed-month archives plus current-month daily files, never live data."""
    now = now.astimezone(UTC)
    if not days or days != sorted(set(days)) or any(day >= now.astimezone(UTC).date() for day in days):
        raise EvidenceError("Archive plan requires unique increasing completed days")
    groups = {}
    current_month = (now.year, now.month)
    for day in days:
        period = "monthly" if monthly and (day.year, day.month) < current_month else "daily"
        token = day.strftime("%Y-%m") if period == "monthly" else day.isoformat()
        groups.setdefault((period, token), []).append(day.isoformat())
    plan = []
    for (period, token), selected in groups.items():
        for symbol in SYMBOLS:
            name = f"{symbol}-1d-{token}.zip"
            plan.append({"period": period, "token": token, "symbol": symbol, "selected_dates": selected,
                         "filename": name, "url": f"{VISION_ROOT}/{period}/klines/{symbol}/1d/{name}"})
    return plan


def parse_kline_archive(payload: bytes, checksum: bytes, spec: dict, received_at: datetime) -> list[dict]:
    symbol, period, token = spec["symbol"], spec["period"], spec["token"]
    if symbol not in SYMBOLS or period not in {"daily", "monthly"}:
        raise EvidenceError("Unexpected instrument or archive frequency")
    if period == "daily":
        archive_days = [canonical_date(token)]
    else:
        if not isinstance(token, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}", token):
            raise EvidenceError("Invalid monthly archive date")
        first = canonical_date(token + "-01")
        archive_days = [first + timedelta(days=offset) for offset in range(month_calendar.monthrange(first.year, first.month)[1])]
    if archive_days[-1] >= received_at.astimezone(UTC).date():
        raise EvidenceError("Incomplete historical archive period")
    selected = spec["selected_dates"]
    if not isinstance(selected, list) or selected != sorted(set(selected)) or not selected or not set(selected).issubset(day.isoformat() for day in archive_days):
        raise EvidenceError("Requested dates do not belong to archive")
    expected_name = f"{symbol}-1d-{token}.zip"
    if spec["filename"] != expected_name or spec["url"] != f"{VISION_ROOT}/{period}/klines/{symbol}/1d/{expected_name}":
        raise EvidenceError("Archive plan metadata is inconsistent")
    try:
        fields = checksum.decode("ascii").strip().split()
    except UnicodeDecodeError as exc:
        raise EvidenceError("Checksum is not ASCII") from exc
    if len(fields) != 2 or not re.fullmatch(r"[a-fA-F0-9]{64}", fields[0]) or fields[1].lstrip("*") != expected_name:
        raise EvidenceError("Malformed checksum or wrong archive name")
    if hashlib.sha256(payload).hexdigest() != fields[0].lower():
        raise EvidenceError("Archive checksum mismatch")
    if len(payload) > MAX_BYTES:
        raise EvidenceError("Archive exceeds byte limit")
    try:
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            members = archive.infolist()
            if len(members) != 1:
                raise EvidenceError("Archive must contain exactly one CSV")
            member = members[0]
            expected_csv = expected_name[:-4] + ".csv"
            if member.filename != expected_csv or member.is_dir() or member.flag_bits & 1:
                raise EvidenceError("Unsafe or unexpected archive member")
            if member.file_size > MAX_BYTES or member.compress_size and member.file_size / member.compress_size > 200:
                raise EvidenceError("Archive expanded size or compression ratio exceeds limit")
            content = archive.read(member)
    except (zipfile.BadZipFile, RuntimeError, NotImplementedError) as exc:
        raise EvidenceError("Invalid archive") from exc
    try:
        rows = list(csv.reader(io.StringIO(content.decode("utf-8"))))
    except (UnicodeDecodeError, csv.Error) as exc:
        raise EvidenceError("Invalid candle CSV") from exc
    if len(rows) != len(archive_days) or any(len(row) != 12 for row in rows):
        raise EvidenceError("Expected exactly one candle per archive day; duplicates and gaps are rejected")
    candles = [_parse_candle(row, symbol, day, received_at) for row, day in zip(rows, archive_days)]
    return [candle for candle in candles if candle["date"] in selected]


def parse_archive(payload: bytes, checksum: bytes, symbol: str, day: date, received_at: datetime) -> dict:
    """Compatibility wrapper for one complete daily archive."""
    name = f"{symbol}-1d-{day.isoformat()}.zip"
    spec = {"symbol": symbol, "period": "daily", "token": day.isoformat(), "selected_dates": [day.isoformat()], "filename": name,
            "url": f"{VISION_BASE}/{symbol}/1d/{name}"}
    return parse_kline_archive(payload, checksum, spec, received_at)[0]


def _parse_candle(row: list[str], symbol: str, day: date, received_at: datetime) -> dict:
    try:
        opened, closed, trades = int(row[0]), int(row[6]), int(row[8])
    except ValueError as exc:
        raise EvidenceError("Non-integer candle timestamp or trade count") from exc
    scale = 1_000_000 if opened >= 100_000_000_000_000 else 1_000
    midnight = datetime.combine(day, datetime.min.time(), UTC)
    expected_open = int(midnight.timestamp()) * scale
    expected_close = int((midnight + timedelta(days=1)).timestamp()) * scale - 1
    if opened != expected_open or closed != expected_close or trades < 0:
        raise EvidenceError("Daily candle timestamps or trade count are invalid")
    prices = [_number(row[i], positive=True) for i in range(1, 5)]
    opening, high, low, closing = prices
    if low > min(opening, closing) or high < max(opening, closing) or high < low:
        raise EvidenceError("Candle OHLC relationship is inconsistent")
    for index in (5, 7, 9, 10):
        _number(row[index])
    return {"date": day.isoformat(), "symbol": symbol, "open_time_utc": utc_text(midnight), "close_time_utc": utc_text(midnight + timedelta(days=1) - timedelta(microseconds=1_000_000 // scale)), "received_at_utc": utc_text(received_at), "close": str(closing), "quote_currency": "USDT", "timestamp_unit": "microseconds" if scale == 1_000_000 else "milliseconds", "trade_count": trades}


def make_prices(candles: list[dict], days: list[date]) -> bytes:
    expected = {(day.isoformat(), symbol) for day in days for symbol in SYMBOLS}
    by_key = {}
    for candle in candles:
        key = (candle["date"], candle["symbol"])
        if key in by_key:
            raise EvidenceError("Duplicate historical candle")
        by_key[key] = str(_number(candle["close"], positive=True))
    if set(by_key) != expected:
        raise EvidenceError("Historical calendar is incomplete or contains unexpected days; no filling is permitted")
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(("date", *SYMBOLS))
    for day in days:
        writer.writerow((day.isoformat(), *(by_key[(day.isoformat(), symbol)] for symbol in SYMBOLS)))
    return buffer.getvalue().encode("utf-8")


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise EvidenceError("Unexpected HTTP redirect rejected")


def fetch(url: str, byte_limit: int = MAX_BYTES) -> bytes:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https" or parsed.netloc not in {"api-open.data.gov.sg", "data.binance.vision"} or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise EvidenceError("Only fixed public research endpoints are permitted")
    request = urllib.request.Request(url, headers={"User-Agent": "Atlas-Quant-Research/0.1 (+https://github.com/Albertito-AI/atlas-quant)", "Accept": "application/json, application/zip, text/plain"})
    with urllib.request.build_opener(_NoRedirect()).open(request, timeout=20) as response:
        if response.status != 200:
            raise EvidenceError("Public source returned a non-success response")
        payload = response.read(byte_limit + 1)
    if len(payload) > byte_limit:
        raise EvidenceError("Response exceeds byte limit")
    return payload


def _json_bytes(value: dict) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")


def attribution_bytes(source_ids: list[str], created_at: datetime) -> bytes:
    text = "# Source attribution and use conditions\n\n"
    for key in source_ids:
        source = SOURCE_REGISTRY[key]
        text += f"Contains information from {source['name']}, accessed {utc_text(created_at)}, from {source['url']}, made available under {source['licence']}: {source['licence_url']}\n\n{source['scope']}\n\n"
    return text.encode("utf-8")


def collect(output: Path, days: int = 7, end_date: str | None = None, sources: str = "all", *, downloader=fetch, clock=lambda: datetime.now(UTC)) -> dict:
    now = clock().astimezone(UTC)
    end = canonical_date(end_date) if end_date else now.date() - timedelta(days=1)
    calendar = date_range(days, end, now)
    if sources not in {"all", "nea", "binance"}:
        raise EvidenceError("Unknown source selection")
    output.mkdir(parents=True, exist_ok=False)
    (output / "raw").mkdir()
    started = time.monotonic()
    files, acquisitions, results = [], [], {}
    plan = archive_plan(calendar, now) if sources in {"all", "binance"} else []
    def save(relative: str, payload: bytes) -> None:
        with (output / relative).open("xb") as stream:
            stream.write(payload)
        files.append({"path": relative, "bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest()})
    def acquire(url: str, relative: str, limit: int = MAX_BYTES) -> tuple[bytes, datetime]:
        if time.monotonic() - started > MAX_SECONDS:
            raise EvidenceError("Bounded collection time budget exhausted")
        began = clock()
        payload = downloader(url, limit)
        received = clock()
        save(relative, payload)
        acquisitions.append({"url": url, "path": relative, "requested_at_utc": utc_text(began), "received_at_utc": utc_text(received)})
        return payload, received
    if sources in {"all", "nea"}:
        try:
            if not policy_check("nea_pm25", "noncommercial_research")["allowed"]:
                raise EvidenceError("Source policy does not permit this research")
            raw, received = acquire(NEA_URL, "raw/nea-pm25.json")
            results["nea_pm25"] = parse_nea(raw, received)
        except (EvidenceError, OSError, urllib.error.URLError) as exc:
            results["nea_pm25"] = {"status": "failed", "error": f"{type(exc).__name__}: {exc}", "mode": "live_observation"}
    if sources in {"all", "binance"}:
        candles = []
        try:
            if not policy_check("binance_vision", "noncommercial_research")["allowed"]:
                raise EvidenceError("Source policy does not permit this research")
            def get_archive(spec):
                name, url = spec["filename"], spec["url"]
                raw, received = acquire(url, "raw/" + name)
                checksum, _ = acquire(url + ".CHECKSUM", "raw/" + name + ".CHECKSUM", 2048)
                return parse_kline_archive(raw, checksum, spec, received)
            # Only two archive jobs can be active or queued; failure prevents new work.
            remaining = iter(plan)
            with ThreadPoolExecutor(max_workers=2) as executor:
                pending = {executor.submit(get_archive, item) for item in [next(remaining, None), next(remaining, None)] if item is not None}
                while pending:
                    finished, pending = wait(pending, return_when=FIRST_COMPLETED)
                    try:
                        for future in finished:
                            candles.extend(future.result())
                    except (EvidenceError, OSError, urllib.error.URLError):
                        for future in pending:
                            future.cancel()
                        raise
                    for _ in finished:
                        item = next(remaining, None)
                        if item is not None:
                            pending.add(executor.submit(get_archive, item))
            candles.sort(key=lambda candle: (candle["date"], candle["symbol"]))
            prices = make_prices(candles, calendar)
            save("prices.csv", prices)
            results["binance_vision"] = {"status": "ok", "mode": "historical_replay", "quote_currency": "USDT", "days": len(calendar), "symbols": list(SYMBOLS), "start_date": calendar[0].isoformat(), "end_date": end.isoformat(), "candles": candles, "prices_file": "prices.csv", "scope": "Selected two-asset historical close series, not a survivorship-free universe or live execution evidence."}
        except (EvidenceError, OSError, urllib.error.URLError) as exc:
            results["binance_vision"] = {"status": "failed", "error": f"{type(exc).__name__}: {exc}", "mode": "historical_replay", "verified_candles_before_failure": len(candles), "prices_file": None}
    report = {"schema": "atlas-observatory-report-v1", "created_at_utc": utc_text(now), "status": "ok" if all(item["status"] == "ok" for item in results.values()) else "incomplete", "sources": results, "claims": CLAIMS, "limitations": LIMITATIONS}
    save("report.json", _json_bytes(report))
    save("ATTRIBUTION.md", attribution_bytes(list(results), now))
    manifest = {"schema": "atlas-observatory-manifest-v2", "archive_plan": plan, "created_at_utc": utc_text(now), "completed_at_utc": utc_text(clock()), "parameters": {"days": days, "end_date": end.isoformat(), "sources": sources}, "source_registry": SOURCE_REGISTRY, "acquisitions": acquisitions, "files": files}
    (output / "manifest.json").write_bytes(_json_bytes(manifest))
    return report


def verify_run(output: Path) -> dict:
    """Check retained bytes and replay accepted observations without network access."""
    try:
        if (output / "manifest.json").stat().st_size > MAX_BYTES:
            raise EvidenceError("Manifest exceeds byte limit")
        manifest = json.loads((output / "manifest.json").read_bytes())
        if manifest["schema"] not in {"atlas-observatory-manifest-v1", "atlas-observatory-manifest-v2"} or not 1 <= len(manifest["files"]) <= 500:
            raise EvidenceError("Invalid manifest schema or file count")
        payloads = {}
        for entry in manifest["files"]:
            name = entry["path"]
            path = PurePosixPath(name)
            if not isinstance(name, str) or path.is_absolute() or any(part in {"..", "."} for part in path.parts) or "\\" in name or name in payloads:
                raise EvidenceError("Unsafe or duplicate manifest path")
            local = output / name
            if any(parent.is_symlink() for parent in [local, *local.parents] if parent != output.parent):
                raise EvidenceError("Symlink in evidence path")
            if local.stat().st_size > MAX_BYTES:
                raise EvidenceError("Evidence file exceeds byte limit")
            payload = local.read_bytes()
            if len(payload) != entry["bytes"] or hashlib.sha256(payload).hexdigest() != entry["sha256"]:
                raise EvidenceError("Evidence byte count or hash mismatch")
            payloads[name] = payload
        report = json.loads(payloads["report.json"])
        created = parse_timestamp(manifest["created_at_utc"])
        params = manifest["parameters"]
        calendar = date_range(params["days"], canonical_date(params["end_date"]), created)
        completed = parse_timestamp(manifest["completed_at_utc"])
        if completed < created or manifest["source_registry"] != SOURCE_REGISTRY:
            raise EvidenceError("Invalid completion time or unrecognised source policies")
        selected = params["sources"]
        expected_sources = {"all": {"nea_pm25", "binance_vision"}, "nea": {"nea_pm25"}, "binance": {"binance_vision"}}.get(selected)
        results = report["sources"]
        if expected_sources is None or not isinstance(results, dict) or set(results) != expected_sources:
            raise EvidenceError("Report is missing required sources or contains unexpected sources")
        expected_order = [key for key in ("nea_pm25", "binance_vision") if key in expected_sources]
        if payloads["ATTRIBUTION.md"] != attribution_bytes(expected_order, created):
            raise EvidenceError("Source attribution or licence conditions were removed or altered")
        if report["schema"] != "atlas-observatory-report-v1" or report["created_at_utc"] != manifest["created_at_utc"] or report["claims"] != CLAIMS or report["limitations"] != LIMITATIONS:
            raise EvidenceError("Report schema, timing or claims are inconsistent with this pilot")
        allowed_urls = {}
        if "nea_pm25" in expected_sources:
            allowed_urls["raw/nea-pm25.json"] = NEA_URL
        plan = archive_plan(calendar, created, monthly=manifest["schema"] == "atlas-observatory-manifest-v2") if "binance_vision" in expected_sources else []
        if manifest["schema"] == "atlas-observatory-manifest-v2" and manifest["archive_plan"] != plan:
            raise EvidenceError("Recorded archive plan differs from independently derived calendar plan")
        for spec in plan:
            for suffix in ("", ".CHECKSUM"):
                allowed_urls["raw/" + spec["filename"] + suffix] = spec["url"] + suffix
        receipts = {}
        for record in manifest["acquisitions"]:
            name = record["path"]
            requested = parse_timestamp(record["requested_at_utc"])
            received = parse_timestamp(record["received_at_utc"])
            if name in receipts or name not in payloads or allowed_urls.get(name) != record["url"] or not created <= requested <= received <= completed:
                raise EvidenceError("Invalid, duplicated or misattributed acquisition record")
            receipts[name] = received
        expected_files = {"report.json", "ATTRIBUTION.md"} | set(receipts)
        if results.get("binance_vision", {}).get("status") == "ok":
            expected_files.add("prices.csv")
        if set(payloads) != expected_files:
            raise EvidenceError("Manifest contains missing or unaccounted evidence files")
        for key, result in results.items():
            allowed_status = {"ok", "failed", "stale"} if key == "nea_pm25" else {"ok", "failed"}
            if result["status"] not in allowed_status or result["mode"] != SOURCE_REGISTRY[key]["mode"]:
                raise EvidenceError("Invalid source status or mode")
            if result["status"] == "failed":
                required = {"status", "error", "mode"}
                if key == "binance_vision":
                    required |= {"verified_candles_before_failure", "prices_file"}
                    count = result["verified_candles_before_failure"]
                    if isinstance(count, bool) or not isinstance(count, int) or not 0 <= count <= 2 * len(calendar) or result["prices_file"] is not None:
                        raise EvidenceError("Invalid failed-source accounting")
                if set(result) != required or not isinstance(result["error"], str) or not result["error"]:
                    raise EvidenceError("Failed source lacks an explicit error")
        if "nea_pm25" in results and results["nea_pm25"]["status"] in {"ok", "stale"}:
            replay = parse_nea(payloads["raw/nea-pm25.json"], receipts["raw/nea-pm25.json"])
            if replay != results["nea_pm25"]:
                raise EvidenceError("NEA replay differs from report")
        if "binance_vision" in results and results["binance_vision"]["status"] == "ok":
            candles = []
            for spec in plan:
                name = "raw/" + spec["filename"]
                candles.extend(parse_kline_archive(payloads[name], payloads[name + ".CHECKSUM"], spec, receipts[name]))
            if manifest["schema"] == "atlas-observatory-manifest-v2":
                candles.sort(key=lambda candle: (candle["date"], candle["symbol"]))
            expected_binance = {"status": "ok", "mode": "historical_replay", "quote_currency": "USDT", "days": len(calendar), "symbols": list(SYMBOLS), "start_date": calendar[0].isoformat(), "end_date": calendar[-1].isoformat(), "candles": candles, "prices_file": "prices.csv", "scope": "Selected two-asset historical close series, not a survivorship-free universe or live execution evidence."}
            if expected_binance != results["binance_vision"] or make_prices(candles, calendar) != payloads["prices.csv"]:
                raise EvidenceError("Historical replay differs from exported evidence")
        expected_status = "ok" if all(item["status"] == "ok" for item in results.values()) else "incomplete"
        if report["status"] != expected_status:
            raise EvidenceError("Overall status contradicts source status")
        return {"status": "verified", "collection_status": report["status"], "files_checked": len(payloads), "network_requests": 0}
    except (KeyError, TypeError, OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise EvidenceError("Missing or malformed evidence bundle") from exc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    collector = sub.add_parser("collect", help="Collect a bounded observation batch into a new directory")
    collector.add_argument("--output", type=Path, required=True)
    collector.add_argument("--days", type=int, default=7)
    collector.add_argument("--end-date", help="Last complete UTC historical day, YYYY-MM-DD; default yesterday")
    collector.add_argument("--sources", choices=("all", "nea", "binance"), default="all")
    verifier = sub.add_parser("verify", help="Replay and verify retained evidence without network access")
    verifier.add_argument("directory", type=Path)
    sub.add_parser("sources", help="Print enabled and explicitly gated source policies")
    args = parser.parse_args(argv)
    try:
        if args.command == "sources":
            print(json.dumps(SOURCE_REGISTRY, indent=2))
            return 0
        if args.command == "verify":
            print(json.dumps(verify_run(args.directory), sort_keys=True))
            return 0
        report = collect(args.output, args.days, args.end_date, args.sources)
        print(json.dumps({"status": report["status"], "output": str(args.output), "sources": {key: value["status"] for key, value in report["sources"].items()}}, sort_keys=True))
        return 0 if report["status"] == "ok" else 1
    except (EvidenceError, OSError) as exc:
        print(f"Observatory: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
