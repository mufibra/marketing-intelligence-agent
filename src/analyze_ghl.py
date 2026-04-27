"""
Quick GHL Data Analysis — explore patterns before pipeline integration.
Run this to see what insights are possible with current data.
"""
import json
import pandas as pd
from ghl_fetcher import fetch_all_ghl_data, create_ghl_summary

print("Loading GHL data (from cache)...\n")
data = fetch_all_ghl_data()

contacts = data.get("contacts", pd.DataFrame())
opps = data.get("opportunities", pd.DataFrame())
tags_df = data.get("tags", pd.DataFrame())

print("\n" + "=" * 70)
print("GHL DATA ANALYSIS — What patterns can we find?")
print("=" * 70)

# ---- 1. Contact Sources ----
print("\n📊 1. WHERE DO CONTACTS COME FROM? (Top 15 sources)")
if not contacts.empty:
    sources = contacts["source"].value_counts().head(15)
    for src, count in sources.items():
        pct = count / len(contacts) * 100
        bar = "█" * int(pct / 2)
        print(f"  {src or '(no source)':50s} {count:>6,} ({pct:.1f}%) {bar}")
    no_source = contacts["source"].isna().sum()
    print(f"\n  Contacts with NO source: {no_source:,} ({no_source/len(contacts)*100:.1f}%)")

# ---- 2. Tag Analysis ----
print("\n\n🏷️  2. TOP TAGS (what segments/campaigns exist?)")
if not contacts.empty:
    all_tags = []
    for t in contacts["tags"].dropna():
        all_tags.extend([tag.strip() for tag in t.split(",") if tag.strip()])
    if all_tags:
        tag_counts = pd.Series(all_tags).value_counts()
        for tag, count in tag_counts.head(20).items():
            pct = count / len(contacts) * 100
            print(f"  {tag[:55]:55s} {count:>6,} ({pct:.1f}%)")
        print(f"\n  Total unique tags: {len(tag_counts)}")
        print(f"  Avg tags per contact: {contacts['tag_count'].mean():.1f}")

# ---- 3. Geography ----
print("\n\n🌍 3. GEOGRAPHIC DISTRIBUTION")
if not contacts.empty:
    countries = contacts["country"].value_counts().head(10)
    if not countries.empty:
        print("  Top countries:")
        for c, count in countries.items():
            print(f"    {c or '(blank)':30s} {count:>6,}")
    else:
        print("  No country data available")

    cities = contacts["city"].value_counts().head(10)
    if not cities.empty:
        print("\n  Top cities:")
        for c, count in cities.items():
            print(f"    {c or '(blank)':30s} {count:>6,}")

# ---- 4. Company Analysis ----
print("\n\n🏢 4. COMPANY DATA")
if not contacts.empty:
    has_company = contacts["company"].notna().sum()
    print(f"  Contacts with company name: {has_company:,} ({has_company/len(contacts)*100:.1f}%)")
    if has_company > 0:
        companies = contacts["company"].value_counts().head(15)
        print("  Top companies:")
        for c, count in companies.items():
            print(f"    {str(c)[:40]:40s} {count:>4,}")

# ---- 5. Email Domain Analysis (proxy for industry) ----
print("\n\n📧 5. EMAIL DOMAIN ANALYSIS (proxy for company/industry)")
if not contacts.empty and "email" in contacts.columns:
    domains = contacts["email"].dropna().apply(
        lambda x: x.split("@")[1].lower() if "@" in str(x) else None
    ).dropna()
    domain_counts = domains.value_counts()

    # Separate personal vs business
    personal_domains = {"gmail.com", "yahoo.com", "hotmail.com", "outlook.com",
                        "icloud.com", "live.com", "yahoo.co.id", "ymail.com",
                        "googlemail.com", "protonmail.com", "mail.com"}
    personal = domains[domains.isin(personal_domains)].count()
    business = domains[~domains.isin(personal_domains)].count()

    print(f"  Personal email (gmail, yahoo, etc): {personal:,} ({personal/len(domains)*100:.1f}%)")
    print(f"  Business email (company domain):    {business:,} ({business/len(domains)*100:.1f}%)")
    print(f"\n  Top business domains:")
    biz_domains = domain_counts[~domain_counts.index.isin(personal_domains)]
    for d, count in biz_domains.head(15).items():
        print(f"    {d:40s} {count:>4,}")

# ---- 6. Pipeline Analysis ----
print("\n\n💰 6. PIPELINE / OPPORTUNITY ANALYSIS")
if not opps.empty:
    print(f"  Total opportunities: {len(opps):,}")
    print(f"  Total pipeline value: ${opps['monetary_value'].sum():,.2f}")
    print(f"  Avg deal size: ${opps['monetary_value'].mean():,.2f}")
    print(f"\n  By status:")
    for status, count in opps["status"].value_counts().items():
        val = opps[opps["status"] == status]["monetary_value"].sum()
        print(f"    {status:15s} {count:>5,} deals  ${val:>12,.2f}")

    print(f"\n  By pipeline (top 10):")
    for pipe, group in opps.groupby("pipeline"):
        count = len(group)
        val = group["monetary_value"].sum()
        won = len(group[group["status"] == "won"])
        print(f"    {str(pipe)[:40]:40s} {count:>4,} deals  ${val:>10,.0f}  ({won} won)")

    print(f"\n  By stage (top 10):")
    stage_data = opps.groupby("stage_name").agg(
        count=("id", "count"),
        value=("monetary_value", "sum")
    ).sort_values("count", ascending=False).head(10)
    for stage, row in stage_data.iterrows():
        print(f"    {str(stage)[:40]:40s} {row['count']:>4,} deals  ${row['value']:>10,.0f}")

# ---- 7. Contact-to-Opportunity Conversion ----
print("\n\n🔄 7. SOURCE → OPPORTUNITY CONVERSION")
if not contacts.empty and not opps.empty:
    # Match contacts to opportunities via contact_id
    opp_contact_ids = set(opps["contact_id"].dropna())
    contacts_with_opp = contacts[contacts["id"].isin(opp_contact_ids)]

    print(f"  Contacts with at least 1 opportunity: {len(contacts_with_opp):,} / {len(contacts):,} ({len(contacts_with_opp)/len(contacts)*100:.2f}%)")

    if not contacts_with_opp.empty:
        print(f"\n  Top sources for contacts WHO BECAME opportunities:")
        conv_sources = contacts_with_opp["source"].value_counts().head(10)
        for src, count in conv_sources.items():
            total_from_src = len(contacts[contacts["source"] == src])
            rate = count / total_from_src * 100 if total_from_src > 0 else 0
            print(f"    {src or '(no source)':40s} {count:>4,} opps / {total_from_src:>5,} contacts ({rate:.1f}% conversion)")

# ---- 8. Time Patterns ----
print("\n\n📅 8. WHEN DO CONTACTS COME IN?")
if not contacts.empty and "date_added" in contacts.columns:
    contacts["month"] = contacts["date_added"].dt.to_period("M")
    monthly = contacts.groupby("month").size()
    print("  Monthly new contacts (last 12 months):")
    for month, count in monthly.tail(12).items():
        bar = "█" * min(int(count / 200), 50)
        print(f"    {month}  {count:>6,}  {bar}")

# ---- 9. Data Quality / Enrichment Needs ----
print("\n\n⚠️  9. DATA QUALITY & ENRICHMENT OPPORTUNITIES")
if not contacts.empty:
    total = len(contacts)
    checks = {
        "Has email": contacts["email"].notna().sum(),
        "Has phone": contacts["phone"].notna().sum(),
        "Has source": contacts["source"].notna().sum(),
        "Has company": contacts["company"].notna().sum(),
        "Has country": contacts["country"].notna().sum(),
        "Has city": contacts["city"].notna().sum(),
        "Has tags": (contacts["tag_count"] > 0).sum(),
    }
    print(f"  {'Field':25s} {'Has data':>10s} {'Missing':>10s} {'% filled':>10s}")
    print(f"  {'-'*55}")
    for field, has in checks.items():
        missing = total - has
        pct = has / total * 100
        flag = " ← needs enrichment" if pct < 30 else ""
        print(f"  {field:25s} {has:>10,} {missing:>10,} {pct:>9.1f}%{flag}")

print("\n\n" + "=" * 70)
print("ANALYSIS COMPLETE")
print("=" * 70)
