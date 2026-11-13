"""Adversarial evidence checks for the separate, bounded public-data collector."""
import calendar
import hashlib
import io
import json
import tempfile
import threading
import time
import unittest
import zipfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from observatory.pilot import (
    EvidenceError, SOURCE_REGISTRY, collect, date_range, fetch, make_prices,
    parse_archive, parse_kline_archive, archive_plan, parse_nea, policy_check, verify_run,
)

UTC = timezone.utc
NOW = datetime(2026, 11, 13, 8, tzinfo=UTC)


def nea_payload(event=None, updated=None, readings=None):
    event = event or NOW - timedelta(minutes=30)
    updated = updated or NOW - timedelta(minutes=10)
    readings = readings if readings is not None else dict(north=7, south=22, east=9, west=17, central=10)
    return json.dumps({"code": 0, "data": {"items": [{"timestamp": event.isoformat(), "updatedTimestamp": updated.isoformat(), "readings": {"pm25_one_hourly": readings}}]}}).encode()


def candle_archive(symbol="BTCUSDT", day=date(2026, 11, 12), *, scale=1_000_000, mutation=None, filename=None, twice=False):
    opened = int(datetime.combine(day, datetime.min.time(), UTC).timestamp()) * scale
    row = [str(opened), "100", "110", "90", "105.25", "2", str(opened + 86400 * scale - 1), "210.5", "3", "1", "105.25", "0"]
    if mutation:
        mutation(row)
    text = ",".join(row) + "\n"
    if twice:
        text += text
    name = f"{symbol}-1d-{day.isoformat()}"
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        entry = zipfile.ZipInfo(filename or name + ".csv", date_time=(2026, 1, 1, 0, 0, 0))
        entry.compress_type = zipfile.ZIP_DEFLATED
        archive.writestr(entry, text)
    raw = buffer.getvalue()
    return raw, (hashlib.sha256(raw).hexdigest() + "  " + name + ".zip\n").encode()


def monthly_archive(symbol="BTCUSDT", month="2026-10", *, change_rows=None):
    first = date.fromisoformat(month + "-01")
    rows = []
    for offset in range(calendar.monthrange(first.year, first.month)[1]):
        day = first + timedelta(days=offset)
        raw, _ = candle_archive(symbol=symbol, day=day)
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            rows.append(archive.read(archive.namelist()[0]).decode().strip())
    if change_rows:
        change_rows(rows)
    name = f"{symbol}-1d-{month}"
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        entry = zipfile.ZipInfo(name + ".csv", date_time=(2026, 1, 1, 0, 0, 0))
        entry.compress_type = zipfile.ZIP_DEFLATED
        archive.writestr(entry, "\n".join(rows) + "\n")
    raw = buffer.getvalue()
    return raw, (hashlib.sha256(raw).hexdigest() + "  " + name + ".zip\n").encode()


class ObservatoryTests(unittest.TestCase):
    def test_archive_fixtures_are_independent_of_wall_clock(self):
        for builder in (candle_archive, monthly_archive):
            with self.subTest(builder=builder.__name__):
                with patch("zipfile.time.localtime", return_value=(2026, 11, 13, 0, 0, 0, 4, 317, 0)):
                    first = builder()
                with patch("zipfile.time.localtime", return_value=(2026, 11, 13, 0, 0, 2, 4, 317, 0)):
                    second = builder()
                self.assertEqual(first, second)

    def test_current_nea_units_and_timezones(self):
        result = parse_nea(nea_payload(), NOW)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["latest_age_seconds"], 1800)
        self.assertEqual(result["observations"][0]["values"]["north"], 7)
        self.assertEqual(result["observations"][0]["event_time_utc"], "2026-11-13T07:30:00Z")
        self.assertIn("micrograms", result["units"])

    def test_stale_nea_explicitly_flagged(self):
        self.assertEqual(parse_nea(nea_payload(event=NOW - timedelta(hours=4)), NOW)["status"], "stale")

    def test_future_or_naive_nea_rejected(self):
        for field in ("timestamp", "updatedTimestamp"):
            for value in ((NOW + timedelta(hours=1)).isoformat(), "2026-11-13T07:30:00"):
                doc = json.loads(nea_payload())
                doc["data"]["items"][0][field] = value
                with self.subTest(field=field, value=value), self.assertRaises(EvidenceError):
                    parse_nea(json.dumps(doc).encode(), NOW)

    def test_nea_published_before_observation_rejected(self):
        with self.assertRaises(EvidenceError):
            parse_nea(nea_payload(updated=NOW - timedelta(hours=2)), NOW)

    def test_duplicate_nea_events_rejected(self):
        doc = json.loads(nea_payload())
        doc["data"]["items"] *= 2
        with self.assertRaises(EvidenceError):
            parse_nea(json.dumps(doc).encode(), NOW)

    def test_missing_negative_nonfinite_and_boolean_nea_rejected(self):
        for bad in (-1, float("nan"), float("inf"), True, "unknown", "1e999"):
            readings = dict(north=bad, south=22, east=9, west=17, central=10)
            with self.subTest(bad=bad), self.assertRaises(EvidenceError):
                parse_nea(nea_payload(readings=readings), NOW)
        with self.assertRaises(EvidenceError):
            parse_nea(nea_payload(readings={"north": 1}), NOW)

    def test_nea_missing_success_or_observations_rejected(self):
        for raw in (b'{}', b'{"code":1}', b'{"code":0,"data":{"items":[]}}', b'null', b'[]'):
            with self.subTest(raw=raw), self.assertRaises(EvidenceError):
                parse_nea(raw, NOW)

    def test_millisecond_and_microsecond_candles(self):
        for scale, unit in ((1_000, "milliseconds"), (1_000_000, "microseconds")):
            with self.subTest(scale=scale):
                raw, digest = candle_archive(scale=scale)
                result = parse_archive(raw, digest, "BTCUSDT", date(2026, 11, 12), NOW)
                self.assertEqual(result["close"], "105.25")
                self.assertEqual(result["timestamp_unit"], unit)
                self.assertEqual(result["date"], "2026-11-12")
                self.assertEqual(result["quote_currency"], "USDT")

    def test_checksum_mismatch_wrong_name_and_missing_digest_rejected(self):
        raw, checksum = candle_archive()
        for value in (b"bad", b"0" * 64 + b"  BTCUSDT-1d-2026-11-12.zip", checksum.replace(b"BTC", b"ETH")):
            with self.subTest(checksum=value), self.assertRaises(EvidenceError):
                parse_archive(raw, value, "BTCUSDT", date(2026, 11, 12), NOW)

    def test_zip_path_traversal_and_unexpected_member_rejected(self):
        for filename in ("../escape.csv", "/absolute.csv", "different.csv"):
            raw, checksum = candle_archive(filename=filename)
            with self.subTest(filename=filename), self.assertRaises(EvidenceError):
                parse_archive(raw, checksum, "BTCUSDT", date(2026, 11, 12), NOW)

    def test_bad_zip_rejected(self):
        raw = b"not a zip"
        checksum = (hashlib.sha256(raw).hexdigest() + "  BTCUSDT-1d-2026-11-12.zip").encode()
        with self.assertRaises(EvidenceError):
            parse_archive(raw, checksum, "BTCUSDT", date(2026, 11, 12), NOW)

    def test_duplicate_daily_candles_rejected(self):
        raw, checksum = candle_archive(twice=True)
        with self.assertRaises(EvidenceError):
            parse_archive(raw, checksum, "BTCUSDT", date(2026, 11, 12), NOW)

    def test_wrong_candle_date_future_incomplete_and_symbol_rejected(self):
        raw, checksum = candle_archive()
        for symbol, day in (("BTCUSDT", date(2026, 11, 11)), ("BTCUSDT", NOW.date()), ("UNKNOWN", date(2026, 11, 12))):
            with self.subTest(symbol=symbol, day=day), self.assertRaises(EvidenceError):
                parse_archive(raw, checksum, symbol, day, NOW)

    def test_price_volume_ohlc_and_timestamp_invariants(self):
        for index, value in ((4, "NaN"), (4, "0"), (4, "-2"), (5, "-1"), (2, "99"), (3, "106"), (0, "0"), (6, "0"), (8, "-1")):
            raw, checksum = candle_archive(mutation=lambda row: row.__setitem__(index, value))
            with self.subTest(index=index, value=value), self.assertRaises(EvidenceError):
                parse_archive(raw, checksum, "BTCUSDT", date(2026, 11, 12), NOW)

    def test_expanded_archive_size_limit(self):
        raw, checksum = candle_archive()
        with patch("observatory.pilot.MAX_BYTES", 5), self.assertRaises(EvidenceError):
            parse_archive(raw, checksum, "BTCUSDT", date(2026, 11, 12), NOW)

    def test_bounded_closed_calendar(self):
        self.assertEqual(date_range(2, date(2026, 11, 12), NOW), [date(2026, 11, 11), date(2026, 11, 12)])
        for days in (0, 1, 91, True, 3.5):
            with self.subTest(days=days), self.assertRaises(EvidenceError):
                date_range(days, date(2026, 11, 12), NOW)
        with self.assertRaises(EvidenceError):
            date_range(2, NOW.date(), NOW)

    def test_export_exact_common_calendar_no_gap_filling(self):
        days = date_range(2, date(2026, 11, 12), NOW)
        rows = [{"date": d.isoformat(), "symbol": s, "close": "105.25"} for d in days for s in ("BTCUSDT", "ETHUSDT")]
        output = make_prices(rows, days)
        self.assertEqual(output.decode(), "date,BTCUSDT,ETHUSDT\n2026-11-11,105.25,105.25\n2026-11-12,105.25,105.25\n")
        for bad in (rows[:-1], rows + rows[:1], rows + [{"date": "2026-11-10", "symbol": "BTCUSDT", "close": "1"}]):
            with self.assertRaises(EvidenceError):
                make_prices(bad, days)

    def fake_downloader(self, url, limit):
        if "api-open.data.gov.sg" in url:
            return nea_payload()
        filename = url.rsplit("/", 1)[-1].replace(".CHECKSUM", "")
        symbol = filename.split("-")[0]
        token = filename.split("-1d-")[1][:-4]
        if "/monthly/" in url:
            raw, checksum = monthly_archive(symbol=symbol, month=token)
        else:
            raw, checksum = candle_archive(symbol=symbol, day=date.fromisoformat(token))
        return checksum if url.endswith(".CHECKSUM") else raw

    def run_dir(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        return Path(temporary.name) / "run"

    def test_complete_collection_replays_without_network(self):
        target = self.run_dir()
        report = collect(target, days=2, downloader=self.fake_downloader, clock=lambda: NOW)
        self.assertEqual(report["status"], "ok")
        self.assertFalse(report["claims"]["live_exchange_connected"])
        with patch("urllib.request.build_opener", side_effect=AssertionError("network during replay")):
            verified = verify_run(target)
        self.assertEqual(verified["collection_status"], "ok")
        self.assertEqual(verified["network_requests"], 0)
        self.assertIn("CC BY-NC-SA", (target / "ATTRIBUTION.md").read_text())

    def test_existing_run_never_overwritten(self):
        target = self.run_dir()
        collect(target, days=2, sources="nea", downloader=self.fake_downloader, clock=lambda: NOW)
        before = (target / "manifest.json").read_bytes()
        with self.assertRaises(FileExistsError):
            collect(target, days=2, sources="nea", downloader=self.fake_downloader, clock=lambda: NOW)
        self.assertEqual(before, (target / "manifest.json").read_bytes())

    def test_missing_source_fails_explicitly_without_zero_or_prices(self):
        target = self.run_dir()
        def fail(url, limit):
            raise OSError("upstream unavailable")
        report = collect(target, days=2, downloader=fail, clock=lambda: NOW)
        self.assertEqual(report["status"], "incomplete")
        self.assertEqual(report["sources"]["nea_pm25"]["status"], "failed")
        self.assertIsNone(report["sources"]["binance_vision"]["prices_file"])
        self.assertFalse((target / "prices.csv").exists())
        self.assertEqual(verify_run(target)["collection_status"], "incomplete")

    def test_stale_collection_not_successful(self):
        target = self.run_dir()
        report = collect(target, sources="nea", downloader=lambda url, limit: nea_payload(event=NOW - timedelta(hours=4)), clock=lambda: NOW)
        self.assertEqual(report["status"], "incomplete")
        self.assertEqual(verify_run(target)["collection_status"], "incomplete")

    def test_retained_file_modification_detected(self):
        target = self.run_dir()
        collect(target, days=2, downloader=self.fake_downloader, clock=lambda: NOW)
        (target / "prices.csv").write_text("fabricated")
        with self.assertRaises(EvidenceError):
            verify_run(target)

    def test_report_semantic_modification_detected_even_with_updated_hash(self):
        target = self.run_dir()
        collect(target, days=2, downloader=self.fake_downloader, clock=lambda: NOW)
        report = json.loads((target / "report.json").read_bytes())
        report["sources"]["nea_pm25"]["observations"][0]["values"]["north"] = 999
        changed = json.dumps(report).encode()
        (target / "report.json").write_bytes(changed)
        manifest = json.loads((target / "manifest.json").read_bytes())
        for entry in manifest["files"]:
            if entry["path"] == "report.json":
                entry["sha256"] = hashlib.sha256(changed).hexdigest()
                entry["bytes"] = len(changed)
        (target / "manifest.json").write_text(json.dumps(manifest))
        with self.assertRaises(EvidenceError):
            verify_run(target)

    def test_untrusted_manifest_path_rejected(self):
        target = self.run_dir()
        collect(target, sources="nea", downloader=self.fake_downloader, clock=lambda: NOW)
        manifest = json.loads((target / "manifest.json").read_bytes())
        manifest["files"][0]["path"] = "../outside"
        (target / "manifest.json").write_text(json.dumps(manifest))
        with self.assertRaises(EvidenceError):
            verify_run(target)

    def test_source_policy_does_not_treat_public_access_as_permission(self):
        for source in ("binance_live", "kraken_live", "coinbase_live"):
            self.assertFalse(SOURCE_REGISTRY[source]["enabled"])
            self.assertFalse(policy_check(source, "noncommercial_research")["allowed"])
        self.assertTrue(policy_check("nea_pm25", "commercial_use")["allowed"])
        self.assertTrue(policy_check("binance_vision", "noncommercial_publication")["allowed"])
        self.assertFalse(policy_check("binance_vision", "commercial_use")["allowed"])
        for source, use in (("unknown", "noncommercial_research"), ("nea_pm25", "anything")):
            with self.assertRaises(EvidenceError):
                policy_check(source, use)

    def rewrite_report(self, target, change):
        report = json.loads((target / "report.json").read_bytes())
        change(report)
        changed = json.dumps(report).encode()
        (target / "report.json").write_bytes(changed)
        manifest = json.loads((target / "manifest.json").read_bytes())
        for entry in manifest["files"]:
            if entry["path"] == "report.json":
                entry["sha256"] = hashlib.sha256(changed).hexdigest()
                entry["bytes"] = len(changed)
        (target / "manifest.json").write_text(json.dumps(manifest))

    def test_missing_sources_cannot_pass_empty_all(self):
        for bad in ({}, {"fictional": {"status": "ok"}}):
            target = self.run_dir()
            collect(target, sources="nea", downloader=self.fake_downloader, clock=lambda: NOW)
            self.rewrite_report(target, lambda report: report.__setitem__("sources", bad))
            with self.subTest(bad=bad), self.assertRaises(EvidenceError):
                verify_run(target)

    def test_changed_claims_schema_and_market_metadata_fail_replay(self):
        mutations = [
            lambda r: r["claims"].__setitem__("live_exchange_connected", True),
            lambda r: r.__setitem__("schema", "unknown"),
            lambda r: r["sources"]["binance_vision"].__setitem__("quote_currency", "USD"),
            lambda r: r["sources"]["binance_vision"].__setitem__("mode", "live_exchange"),
            lambda r: r["sources"]["binance_vision"].__setitem__("status", "successful"),
        ]
        for mutation in mutations:
            target = self.run_dir()
            collect(target, days=2, downloader=self.fake_downloader, clock=lambda: NOW)
            self.rewrite_report(target, mutation)
            with self.assertRaises(EvidenceError):
                verify_run(target)

    def test_missing_attribution_cannot_be_hidden_by_updated_hash(self):
        target = self.run_dir()
        collect(target, sources="nea", downloader=self.fake_downloader, clock=lambda: NOW)
        (target / "ATTRIBUTION.md").write_bytes(b"")
        manifest = json.loads((target / "manifest.json").read_bytes())
        for entry in manifest["files"]:
            if entry["path"] == "ATTRIBUTION.md":
                entry["bytes"] = 0
                entry["sha256"] = hashlib.sha256(b"").hexdigest()
        (target / "manifest.json").write_text(json.dumps(manifest))
        with self.assertRaises(EvidenceError):
            verify_run(target)

    def test_tampered_registry_and_acquisition_rejected(self):
        for change in (
            lambda m: m["source_registry"]["coinbase_live"].__setitem__("enabled", True),
            lambda m: m["acquisitions"][0].__setitem__("url", "https://attacker.example/"),
            lambda m: m["acquisitions"].append(dict(m["acquisitions"][0])),
            lambda m: m["acquisitions"][0].__setitem__("received_at_utc", "2027-01-01T00:00:00Z"),
        ):
            target = self.run_dir()
            collect(target, sources="nea", downloader=self.fake_downloader, clock=lambda: NOW)
            manifest = json.loads((target / "manifest.json").read_bytes())
            change(manifest)
            (target / "manifest.json").write_text(json.dumps(manifest))
            with self.assertRaises(EvidenceError):
                verify_run(target)

    def test_malformed_response_preserves_failure_report(self):
        for body in (b"[]", b"null", b"{}"):
            target = self.run_dir()
            report = collect(target, sources="nea", downloader=lambda url, limit: body, clock=lambda: NOW)
            self.assertEqual(report["sources"]["nea_pm25"]["status"], "failed")
            self.assertTrue((target / "manifest.json").exists())
            self.assertEqual(verify_run(target)["collection_status"], "incomplete")

    def test_archive_plan_uses_utc_month_boundary(self):
        singapore = timezone(timedelta(hours=8))
        now = datetime(2026, 3, 1, 0, tzinfo=singapore)
        plan = archive_plan([date(2026, 2, 27)], now)
        self.assertTrue(all(item["period"] == "daily" for item in plan))
        with self.assertRaises(EvidenceError):
            date_range(90, date(1, 1, 1), NOW)

    def test_monthly_batch_plan_reduces_90day_requests_and_preserves_calendar(self):
        days = date_range(90, date(2026, 11, 12), NOW)
        plan = archive_plan(days, NOW)
        self.assertEqual(len(plan), 30)
        self.assertEqual(2 * len(plan), 60)  # 360 HTTP requests with daily-only planning.
        self.assertEqual(len(archive_plan(days, NOW, monthly=False)), 180)
        self.assertEqual(plan[0]["token"], "2026-08")
        self.assertEqual(plan[0]["selected_dates"][0], "2026-08-15")
        self.assertEqual(plan[-1]["period"], "daily")
        self.assertEqual(plan[-1]["token"], "2026-11-12")

    def test_monthly_parser_selects_exact_window_after_validating_whole_month(self):
        days = date_range(2, date(2026, 10, 17), NOW)
        spec = archive_plan(days, NOW)[0]
        raw, checksum = monthly_archive()
        candles = parse_kline_archive(raw, checksum, spec, NOW)
        self.assertEqual([c["date"] for c in candles], ["2026-10-16", "2026-10-17"])
        for mutation in (lambda rows: rows.pop(), lambda rows: rows.__setitem__(0, rows[1]), lambda rows: rows.reverse()):
            bad, digest = monthly_archive(change_rows=mutation)
            with self.assertRaises(EvidenceError):
                parse_kline_archive(bad, digest, spec, NOW)

    def test_monthly_leap_year_and_incomplete_month_rejected(self):
        now = datetime(2024, 3, 1, tzinfo=UTC)
        days = date_range(3, date(2024, 2, 29), now)
        spec = archive_plan(days, now)[0]
        raw, checksum = monthly_archive(month="2024-02")
        self.assertEqual(len(parse_kline_archive(raw, checksum, spec, now)), 3)
        bad, digest = monthly_archive(month="2024-02", change_rows=lambda rows: rows.pop())
        with self.assertRaises(EvidenceError):
            parse_kline_archive(bad, digest, spec, now)
        with self.assertRaises(EvidenceError):
            parse_kline_archive(raw, checksum, spec, datetime(2024, 2, 29, 23, tzinfo=UTC))

    def test_monthly_wrong_checksum_month_or_selection_rejected(self):
        spec = archive_plan(date_range(2, date(2026, 10, 17), NOW), NOW)[0]
        raw, checksum = monthly_archive()
        for mutate in (
            lambda d: d.__setitem__("token", "2026-09"),
            lambda d: d.__setitem__("selected_dates", ["2026-11-01"]),
            lambda d: d.__setitem__("selected_dates", ["2026-10-16", "2026-10-16"]),
        ):
            changed = dict(spec)
            mutate(changed)
            with self.assertRaises(EvidenceError):
                parse_kline_archive(raw, checksum, changed, NOW)
        with self.assertRaises(EvidenceError):
            parse_kline_archive(raw, b"0" * 64 + b"  BTCUSDT-1d-2026-10.zip", spec, NOW)

    def test_full_monthly_collection_replays_with_bounded_concurrency(self):
        target = self.run_dir()
        active, maximum, calls = 0, 0, 0
        lock = threading.Lock()
        def observed_download(url, limit):
            nonlocal active, maximum, calls
            with lock:
                active += 1
                calls += 1
                maximum = max(maximum, active)
            try:
                time.sleep(0.001)
                return self.fake_downloader(url, limit)
            finally:
                with lock:
                    active -= 1
        report = collect(target, days=90, sources="binance", downloader=observed_download, clock=lambda: NOW)
        self.assertEqual(report["status"], "ok")
        self.assertEqual(calls, 60)
        self.assertLessEqual(maximum, 2)
        self.assertEqual(len(report["sources"]["binance_vision"]["candles"]), 180)
        self.assertEqual(len((target / "prices.csv").read_text().splitlines()), 91)
        self.assertEqual(verify_run(target)["collection_status"], "ok")
        manifest = json.loads((target / "manifest.json").read_bytes())
        manifest["archive_plan"][0]["selected_dates"] = []
        (target / "manifest.json").write_text(json.dumps(manifest))
        with self.assertRaises(EvidenceError):
            verify_run(target)

    def test_daily_manifest_v1_still_replays(self):
        target = self.run_dir()
        collect(target, days=2, downloader=self.fake_downloader, clock=lambda: NOW)
        manifest = json.loads((target / "manifest.json").read_bytes())
        manifest["schema"] = "atlas-observatory-manifest-v1"
        del manifest["archive_plan"]
        (target / "manifest.json").write_text(json.dumps(manifest))
        self.assertEqual(verify_run(target)["collection_status"], "ok")

    def test_arbitrary_endpoint_blocked_before_network(self):
        for url in ("http://api-open.data.gov.sg/a", "https://attacker.example/", "https://data.binance.vision@attacker.example/a", "https://data.binance.vision/a?token=x"):
            with self.subTest(url=url), self.assertRaises(EvidenceError):
                fetch(url)


if __name__ == "__main__":
    unittest.main()
