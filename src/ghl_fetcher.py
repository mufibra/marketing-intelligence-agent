"""
GHL Fetcher v5.1 — Complete GoHighLevel data extraction.
Uses GET /contacts/ with cursor pagination (no 10K limit).
Uses epoch milliseconds for calendar events (not ISO dates).
Resumable: saves progress, picks up where it left off.

Usage:
    python src/ghl_fetcher.py              # resumes from cache
    python src/ghl_fetcher.py --refresh    # full fresh fetch
"""

import os
import sys
import json
import time
import requests
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

GHL_API_TOKEN = os.getenv("GHL_API_TOKEN")
GHL_LOCATION_ID = os.getenv("GHL_LOCATION_ID")
GHL_BASE_URL = "https://services.leadconnectorhq.com"
GHL_API_VERSION = "2021-07-28"

CACHE_DIR = Path(__file__).parent.parent / ".cache" / "ghl"
CACHE_MAX_AGE_HOURS = 12

# ============================================================
# Cache
# ============================================================

def _cache_path(name):
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR / f"{name}.json"

def _cache_fresh(name):
    p = _cache_path(name)
    if not p.exists():
        return False
    return (datetime.now() - datetime.fromtimestamp(p.stat().st_mtime)) < timedelta(hours=CACHE_MAX_AGE_HOURS)

def _cache_age(name):
    p = _cache_path(name)
    if not p.exists():
        return "no cache"
    mins = (datetime.now() - datetime.fromtimestamp(p.stat().st_mtime)).total_seconds() / 60
    return f"{int(mins)}m ago" if mins < 60 else f"{mins/60:.1f}h ago"

def _save(name, data):
    with open(_cache_path(name), "w") as f:
        json.dump(data, f, default=str)

def _load(name):
    p = _cache_path(name)
    if not p.exists():
        return []
    with open(p, "r") as f:
        return json.load(f)

# ============================================================
# API
# ============================================================

def _headers():
    return {
        "Authorization": f"Bearer {GHL_API_TOKEN}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Version": GHL_API_VERSION,
    }

def _get(endpoint, params=None):
    url = f"{GHL_BASE_URL}{endpoint}"
    for attempt in range(3):
        try:
            r = requests.get(url, headers=_headers(), params=params or {}, timeout=30)
            if r.status_code in (502, 503):
                time.sleep(5)
                continue
            if r.status_code != 200:
                print(f"    API {r.status_code} on {endpoint}: {r.text[:150]}")
                return None
            return r.json()
        except Exception as e:
            if attempt < 2:
                time.sleep(3)
            else:
                print(f"    Request error: {str(e)[:100]}")
                return None
    return None

def _post(endpoint, body=None, params=None):
    url = f"{GHL_BASE_URL}{endpoint}"
    for attempt in range(3):
        try:
            r = requests.post(url, headers=_headers(), json=body or {}, params=params or {}, timeout=30)
            if r.status_code in (502, 503):
                time.sleep(5)
                continue
            if r.status_code not in (200, 201):
                print(f"    API {r.status_code} on POST {endpoint}: {r.text[:150]}")
                return None
            return r.json()
        except Exception as e:
            if attempt < 2:
                time.sleep(3)
            else:
                print(f"    Request error: {str(e)[:100]}")
                return None
    return None

# ============================================================
# Contacts — GET /contacts/ with cursor pagination
# ============================================================

def _process_contact(c):
    return {
        "id": c.get("id"),
        "name": f"{c.get('firstName', '')} {c.get('lastName', '')}".strip(),
        "email": c.get("email"),
        "phone": c.get("phone"),
        "source": c.get("source"),
        "tags": ", ".join(c.get("tags", [])),
        "tag_count": len(c.get("tags", [])),
        "country": c.get("country"),
        "city": c.get("city"),
        "company": c.get("companyName"),
        "date_added": c.get("dateAdded"),
        "date_updated": c.get("dateUpdated"),
        "dnd": c.get("dnd", False),
    }

def fetch_contacts(force=False):
    name = "contacts"
    meta_path = _cache_path("contacts_meta")

    existing = _load(name) if _cache_path(name).exists() else []
    existing_ids = {c["id"] for c in existing if "id" in c}

    if not force and _cache_fresh(name):
        meta = {}
        if meta_path.exists():
            with open(meta_path) as f:
                meta = json.load(f)
        if meta.get("complete", False):
            print(f"  📇 Contacts: cached & complete ({_cache_age(name)}, {len(existing):,})")
            df = pd.DataFrame(existing)
            if not df.empty:
                df["date_added"] = pd.to_datetime(df["date_added"], errors="coerce")
                df["date_updated"] = pd.to_datetime(df["date_updated"], errors="coerce")
            return df

    if force:
        existing = []
        existing_ids = set()

    params = {"locationId": GHL_LOCATION_ID, "limit": 100}
    if not force and meta_path.exists():
        with open(meta_path) as f:
            m = json.load(f)
        sa = m.get("next_startAfter")
        said = m.get("next_startAfterId")
        if sa is not None and said is not None and not m.get("complete", False):
            params["startAfter"] = sa
            params["startAfterId"] = said
            print(f"  📇 Resuming contacts from page ~{len(existing)//100 + 1} ({len(existing):,} cached)...")
        else:
            print(f"  📇 Fetching contacts from API...")
    else:
        print(f"  📇 Fetching contacts from API...")

    page = 0
    errors = 0

    while True:
        page += 1
        data = _get("/contacts/", params)

        if not data:
            errors += 1
            if errors >= 3:
                print(f"    3 consecutive errors, saving progress.")
                break
            time.sleep(5)
            continue

        errors = 0
        contacts = data.get("contacts", [])
        if not contacts:
            break

        new_count = 0
        for c in contacts:
            cid = c.get("id")
            if cid and cid not in existing_ids:
                existing_ids.add(cid)
                existing.append(_process_contact(c))
                new_count += 1

        if new_count == 0:
            print(f"    Pagination loop detected at page {page}, stopping.")
            break

        if page % 10 == 0:
            print(f"    ... page {page}, {len(existing):,} unique contacts")

        if page % 50 == 0:
            _save(name, existing)
            print(f"    💾 Progress saved ({len(existing):,})")

        meta = data.get("meta", {})
        next_after = meta.get("startAfter")
        next_after_id = meta.get("startAfterId")

        if next_after is not None and next_after_id is not None:
            params["startAfter"] = next_after
            params["startAfterId"] = next_after_id
            with open(meta_path, "w") as f:
                json.dump({"complete": False, "total_fetched": len(existing),
                           "next_startAfter": next_after, "next_startAfterId": next_after_id,
                           "last_page": page, "last_updated": datetime.now().isoformat()}, f)
        else:
            break

        if len(contacts) < 100:
            break

        time.sleep(0.15)

    _save(name, existing)
    with open(meta_path, "w") as f:
        json.dump({"complete": True, "total_fetched": len(existing),
                    "last_updated": datetime.now().isoformat()}, f)

    print(f"    ✅ {len(existing):,} total contacts")
    df = pd.DataFrame(existing)
    if not df.empty:
        df["date_added"] = pd.to_datetime(df["date_added"], errors="coerce")
        df["date_updated"] = pd.to_datetime(df["date_updated"], errors="coerce")
    return df

# ============================================================
# Generic paginated GET
# ============================================================

def _get_all(endpoint, results_key, params=None):
    if params is None:
        params = {}
    params["limit"] = 100
    all_results = []
    seen_ids = set()

    while True:
        data = _get(endpoint, params)
        if not data:
            break
        results = data.get(results_key, [])
        if not results:
            break

        new = 0
        for r in results:
            rid = r.get("id") or r.get("_id")
            if rid and rid not in seen_ids:
                seen_ids.add(rid)
                all_results.append(r)
                new += 1
            elif not rid:
                all_results.append(r)
                new += 1

        if new == 0:
            break

        meta = data.get("meta", {})
        if isinstance(meta, dict):
            cursor = meta.get("startAfterId") or meta.get("startAfter")
            if cursor:
                params["startAfterId"] = cursor
                params["startAfter"] = cursor
            else:
                break
        else:
            break

        if len(results) < 100:
            break
        time.sleep(0.15)

    return all_results

# ============================================================
# Opportunities
# ============================================================

def fetch_opportunities(force=False):
    name = "opportunities"
    if not force and _cache_fresh(name):
        print(f"  💰 Opportunities: cached ({_cache_age(name)})")
        raw = _load(name)
        df = pd.DataFrame(raw) if raw else pd.DataFrame()
        if not df.empty:
            df["date_added"] = pd.to_datetime(df["date_added"], errors="coerce")
            df["monetary_value"] = pd.to_numeric(df["monetary_value"], errors="coerce").fillna(0)
        print(f"    → {len(df):,} opportunities")
        return df

    print(f"  💰 Fetching opportunities...")
    pipelines_data = _get("/opportunities/pipelines", {"locationId": GHL_LOCATION_ID})
    if not pipelines_data:
        return pd.DataFrame()

    pipelines = pipelines_data.get("pipelines", [])
    stage_lookup = {}
    for p in pipelines:
        for s in p.get("stages", []):
            stage_lookup[s.get("id")] = s.get("name")

    all_opps = []
    for pipeline in pipelines:
        opps = _get_all("/opportunities/search", "opportunities",
                        {"location_id": GHL_LOCATION_ID, "pipeline_id": pipeline.get("id")})
        for o in opps:
            all_opps.append({
                "id": o.get("id"), "name": o.get("name"),
                "pipeline": pipeline.get("name"),
                "stage_name": stage_lookup.get(o.get("pipelineStageId"), "Unknown"),
                "status": o.get("status"), "monetary_value": o.get("monetaryValue", 0),
                "source": o.get("source"), "contact_id": o.get("contactId"),
                "date_added": o.get("createdAt"), "date_updated": o.get("updatedAt"),
            })

    _save(name, all_opps)
    df = pd.DataFrame(all_opps)
    if not df.empty:
        df["date_added"] = pd.to_datetime(df["date_added"], errors="coerce")
        df["monetary_value"] = pd.to_numeric(df["monetary_value"], errors="coerce").fillna(0)
    print(f"    → {len(df):,} opportunities across {len(pipelines)} pipelines")
    return df

# ============================================================
# Appointments — uses EPOCH MILLISECONDS (not ISO dates)
# ============================================================

def fetch_appointments(force=False):
    name = "appointments"
    if not force and _cache_fresh(name):
        print(f"  📅 Appointments: cached ({_cache_age(name)})")
        raw = _load(name)
        df = pd.DataFrame(raw) if raw else pd.DataFrame()
        if not df.empty and "start_time" in df.columns:
            df["start_time"] = pd.to_datetime(df["start_time"], errors="coerce")
            df["date"] = df["start_time"].dt.date
        print(f"    → {len(df):,} appointments")
        return df

    print(f"  📅 Fetching appointments...")
    cals = _get("/calendars/", {"locationId": GHL_LOCATION_ID})
    if not cals:
        return pd.DataFrame()
    calendars = cals.get("calendars", [])

    # GHL requires epoch milliseconds, NOT ISO date strings
    start = int((datetime.now() - timedelta(days=365)).timestamp() * 1000)
    end = int(datetime.now().timestamp() * 1000)

    all_events = []
    for cal in calendars:
        cal_id = cal.get("id")
        cal_name = cal.get("name")

        events_data = _get("/calendars/events", {
            "locationId": GHL_LOCATION_ID,
            "calendarId": cal_id,
            "startTime": start,
            "endTime": end,
        })
        if not events_data:
            continue

        events = events_data.get("events", [])
        for e in events:
            all_events.append({
                "id": e.get("id"),
                "calendar": cal_name,
                "title": e.get("title"),
                "status": e.get("appointmentStatus", "unknown"),
                "start_time": e.get("startTime"),
                "end_time": e.get("endTime"),
                "contact_id": e.get("contactId"),
            })

        if events:
            print(f"    {cal_name}: {len(events)} events")

    _save(name, all_events)
    df = pd.DataFrame(all_events)
    if not df.empty:
        df["start_time"] = pd.to_datetime(df["start_time"], errors="coerce")
        df["date"] = df["start_time"].dt.date
    print(f"    → {len(df):,} total appointments across {len(calendars)} calendars")
    return df

# ============================================================
# Conversations
# ============================================================

def fetch_conversations(force=False):
    name = "conversations"
    if not force and _cache_fresh(name):
        print(f"  💬 Conversations: cached ({_cache_age(name)})")
        raw = _load(name)
    else:
        print(f"  💬 Fetching conversations...")
        raw_list = _get_all("/conversations/search", "conversations", {"locationId": GHL_LOCATION_ID})
        raw = [{"id": c.get("id"), "type": c.get("type"), "contact_id": c.get("contactId"),
                "last_message_type": c.get("lastMessageType"),
                "unread_count": c.get("unreadCount", 0), "date_added": c.get("dateAdded")} for c in raw_list]
        _save(name, raw)

    df = pd.DataFrame(raw) if raw else pd.DataFrame()
    if not df.empty and "date_added" in df.columns:
        df["date_added"] = pd.to_datetime(df["date_added"], errors="coerce")
    print(f"    → {len(df):,} conversations")
    return df

# ============================================================
# Simple fetchers
# ============================================================

def _fetch_simple(name, endpoint, results_key, force=False):
    icons = {"campaigns": "📧", "tags": "🏷️", "users": "👥", "forms": "📝", "funnels": "🔗"}
    icon = icons.get(name, "📦")
    if not force and _cache_fresh(name):
        print(f"  {icon} {name.title()}: cached ({_cache_age(name)})")
        raw = _load(name)
        print(f"    → {len(raw):,} {name}")
        return pd.DataFrame(raw) if raw else pd.DataFrame()
    print(f"  {icon} Fetching {name}...")
    data = _get(endpoint, {"locationId": GHL_LOCATION_ID})
    raw = data.get(results_key, []) if data else []
    _save(name, raw)
    print(f"    → {len(raw):,} {name}")
    return pd.DataFrame(raw) if raw else pd.DataFrame()

def fetch_campaigns(force=False):
    return _fetch_simple("campaigns", "/campaigns/", "campaigns", force)

def fetch_tags(force=False):
    name = "tags"
    if not force and _cache_fresh(name):
        print(f"  🏷️  Tags: cached ({_cache_age(name)})")
        raw = _load(name)
        print(f"    → {len(raw):,} tags")
        return pd.DataFrame(raw) if raw else pd.DataFrame()
    print(f"  🏷️  Fetching tags...")
    data = _get(f"/locations/{GHL_LOCATION_ID}/tags", {})
    raw = data.get("tags", []) if data else []
    _save(name, raw)
    print(f"    → {len(raw):,} tags")
    return pd.DataFrame(raw) if raw else pd.DataFrame()

def fetch_users(force=False):
    return _fetch_simple("users", "/users/", "users", force)
def fetch_forms(force=False):
    return _fetch_simple("forms", "/forms/", "forms", force)
def fetch_funnels(force=False):
    return _fetch_simple("funnels", "/funnels/funnel/list", "funnels", force)

def fetch_invoices(force=False):
    name = "invoices"
    if not force and _cache_fresh(name):
        print(f"  🧾 Invoices: cached ({_cache_age(name)})")
        raw = _load(name)
    else:
        print(f"  🧾 Fetching invoices...")
        data = _get("/payments/transactions", {"locationId": GHL_LOCATION_ID})
        if not data:
            data = _get("/invoices/", {"locationId": GHL_LOCATION_ID, "altType": "location"})
        raw = data.get("data", data.get("invoices", data.get("transactions", []))) if data else []
        _save(name, raw)
    if not raw:
        print(f"    → 0 invoices"); return pd.DataFrame()
    rows = [{"id": t.get("_id", t.get("id")), "amount": t.get("amount", t.get("total", 0)),
             "status": t.get("status"), "contact_id": t.get("contactId"),
             "date_created": t.get("createdAt")} for t in raw]
    df = pd.DataFrame(rows)
    if not df.empty:
        df["date_created"] = pd.to_datetime(df["date_created"], errors="coerce")
        df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0)
    print(f"    → {len(df):,} invoices"); return df

# ============================================================
# Master Fetch
# ============================================================

def fetch_all_ghl_data(force_refresh=False):
    if not GHL_API_TOKEN or not GHL_LOCATION_ID:
        return {"_error": "GHL_API_TOKEN or GHL_LOCATION_ID not found in .env"}

    print("=" * 60)
    print("GoHighLevel Data Fetcher v5.1")
    print(f"Location: {GHL_LOCATION_ID[:8]}...")
    print(f"Cache: {'FORCE REFRESH' if force_refresh else f'max age {CACHE_MAX_AGE_HOURS}h'}")
    print("=" * 60)

    data = {}
    for key, func in {
        "contacts": fetch_contacts, "opportunities": fetch_opportunities,
        "appointments": fetch_appointments, "conversations": fetch_conversations,
        "campaigns": fetch_campaigns, "invoices": fetch_invoices,
        "forms": fetch_forms, "funnels": fetch_funnels,
        "tags": fetch_tags, "users": fetch_users,
    }.items():
        try:
            data[key] = func(force=force_refresh)
        except Exception as e:
            print(f"    ❌ Error: {e}")
            data[key] = pd.DataFrame()

    print()
    print("=" * 60)
    total = 0
    for k, df in data.items():
        if isinstance(df, pd.DataFrame):
            n = len(df)
            total += n
            print(f"  {k:20s} → {n:>8,} records")
    print(f"  {'TOTAL':20s} → {total:>8,} records")
    print("=" * 60)
    return data

# ============================================================
# Daily Aggregation + Summary
# ============================================================

def aggregate_ghl_daily(data):
    daily = {}
    contacts = data.get("contacts", pd.DataFrame())
    if not contacts.empty and "date_added" in contacts.columns:
        for d, n in contacts.groupby(contacts["date_added"].dt.date).size().items():
            daily.setdefault(d, {})["new_contacts"] = n
    opps = data.get("opportunities", pd.DataFrame())
    if not opps.empty and "date_added" in opps.columns:
        for d, n in opps.groupby(opps["date_added"].dt.date).size().items():
            daily.setdefault(d, {})["new_opportunities"] = n
        for d, v in opps.groupby(opps["date_added"].dt.date)["monetary_value"].sum().items():
            daily.setdefault(d, {})["opportunity_value"] = v
        won = opps[opps["status"] == "won"]
        if not won.empty:
            for d, n in won.groupby(won["date_added"].dt.date).size().items():
                daily.setdefault(d, {})["deals_won"] = n
    appts = data.get("appointments", pd.DataFrame())
    if not appts.empty and "date" in appts.columns:
        for d, n in appts.groupby("date").size().items():
            daily.setdefault(d, {})["appointments"] = n
    convos = data.get("conversations", pd.DataFrame())
    if not convos.empty and "date_added" in convos.columns:
        for d, n in convos.groupby(convos["date_added"].dt.date).size().items():
            daily.setdefault(d, {})["new_conversations"] = n
    if not daily:
        return pd.DataFrame()
    rows = [{"date": pd.Timestamp(d), **m} for d, m in sorted(daily.items())]
    return pd.DataFrame(rows).fillna(0)

def create_ghl_summary(data):
    s = {"source": "GoHighLevel CRM"}
    contacts = data.get("contacts", pd.DataFrame())
    if not contacts.empty:
        s["total_contacts"] = len(contacts)
        s["contacts_with_email"] = int(contacts["email"].notna().sum())
        s["contacts_with_phone"] = int(contacts["phone"].notna().sum())
        s["top_sources"] = contacts["source"].value_counts().head(5).to_dict()
        all_tags = []
        for t in contacts["tags"].dropna():
            all_tags.extend([tag.strip() for tag in t.split(",") if tag.strip()])
        if all_tags:
            s["top_tags"] = pd.Series(all_tags).value_counts().head(10).to_dict()
    opps = data.get("opportunities", pd.DataFrame())
    if not opps.empty:
        s["total_opportunities"] = len(opps)
        s["total_pipeline_value"] = float(opps["monetary_value"].sum())
        s["opps_by_status"] = opps["status"].value_counts().to_dict()
    appts = data.get("appointments", pd.DataFrame())
    if not appts.empty:
        s["total_appointments"] = len(appts)
        if "status" in appts.columns:
            s["appts_by_status"] = appts["status"].value_counts().to_dict()
    return s

# ============================================================
# Main
# ============================================================

if __name__ == "__main__":
    force = "--refresh" in sys.argv
    print()
    if not GHL_API_TOKEN:
        print("ERROR: GHL_API_TOKEN not found in .env"); exit(1)
    if not GHL_LOCATION_ID:
        print("ERROR: GHL_LOCATION_ID not found in .env"); exit(1)

    data = fetch_all_ghl_data(force_refresh=force)
    if "_error" in data:
        print(f"\nERROR: {data['_error']}")
    else:
        print("\n✅ Done!")
        summary = create_ghl_summary(data)
        print("\nGHL Summary:")
        print(json.dumps(summary, indent=2, default=str))
        daily = aggregate_ghl_daily(data)
        if not daily.empty:
            print(f"\nDaily Metrics ({len(daily)} days):")
            print(daily.tail(10).to_string(index=False))
