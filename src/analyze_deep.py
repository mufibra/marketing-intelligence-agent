"""
Deep GHL Analysis — the 3 high-value analyses.
1. Industry → Revenue mapping (via email domains)
2. Campaign → Pipeline attribution (via tags on opportunity contacts)
3. Pipeline velocity & stage leakage
"""
import json
import pandas as pd
from ghl_fetcher import fetch_all_ghl_data

print("Loading GHL data (from cache)...\n")
data = fetch_all_ghl_data()

contacts = data.get("contacts", pd.DataFrame())
opps = data.get("opportunities", pd.DataFrame())

# Build email domain → industry mapping
INDUSTRY_MAP = {
    # Financial Services / Insurance
    "aia.com.sg": "Insurance", "prudential.com.sg": "Insurance",
    "dbs.com": "Banking", "uobgroup.com": "Banking", "ocbc.com": "Banking",
    "sc.com": "Banking", "hsbc.com": "Banking", "citi.com": "Banking",
    "manulife.com": "Insurance", "greateasternlife.com": "Insurance",
    # Tech
    "google.com": "Tech", "tiktok.com": "Tech", "meta.com": "Tech",
    "quickdesk.io": "Tech (QD)", "engages.ai": "Tech (QD)",
    # Pharma / Healthcare
    "its.jnj.com": "Pharma", "jnj.com": "Pharma", "abbott.com": "Pharma",
    "roche.com": "Pharma", "pfizer.com": "Pharma",
    # Education
    "smu.edu.sg": "Education", "nus.edu.sg": "Education",
    "ntu.edu.sg": "Education", "moe.edu.sg": "Education (Gov)",
    "sp.edu.sg": "Education", "np.edu.sg": "Education",
    "tp.edu.sg": "Education", "rp.edu.sg": "Education",
    "nyp.edu.sg": "Education", "sutd.edu.sg": "Education",
    # Telco
    "singtel.com": "Telco", "starhub.com": "Telco", "m1.com.sg": "Telco",
    # Hospitality / Retail
    "marriott.com": "Hospitality", "hilton.com": "Hospitality",
    "fairprice.com.sg": "Retail", "ntuc.org.sg": "Retail",
    # Government
    "gov.sg": "Government",
    # Logistics
    "dhl.com": "Logistics", "fedex.com": "Logistics",
}

PERSONAL_DOMAINS = {"gmail.com", "yahoo.com", "hotmail.com", "outlook.com",
                    "icloud.com", "live.com", "yahoo.co.id", "ymail.com",
                    "googlemail.com", "protonmail.com", "mail.com",
                    "yahoo.com.sg", "live.com.sg", "singnet.com.sg"}


def get_industry(email):
    if not email or "@" not in str(email):
        return "Unknown"
    domain = str(email).split("@")[1].lower()
    if domain in PERSONAL_DOMAINS:
        return "Personal Email"
    if domain in INDUSTRY_MAP:
        return INDUSTRY_MAP[domain]
    # Try partial matches
    for key, industry in INDUSTRY_MAP.items():
        if key in domain:
            return industry
    # Check TLD patterns
    if ".edu." in domain:
        return "Education"
    if ".gov." in domain:
        return "Government"
    return "Other Business"


# ============================================================
print("=" * 70)
print("ANALYSIS 1: INDUSTRY → REVENUE MAPPING")
print("=" * 70)

if not contacts.empty and not opps.empty:
    # Add industry to contacts
    contacts["industry"] = contacts["email"].apply(get_industry)

    # Match contacts to opportunities
    opp_contacts = opps.merge(
        contacts[["id", "email", "industry"]],
        left_on="contact_id", right_on="id", how="left", suffixes=("", "_contact")
    )

    # Industry breakdown for ALL contacts
    print("\n📊 All contacts by industry:")
    ind_all = contacts["industry"].value_counts()
    for ind, count in ind_all.head(15).items():
        pct = count / len(contacts) * 100
        print(f"  {ind:25s} {count:>6,} ({pct:.1f}%)")

    # Industry breakdown for contacts WITH opportunities
    print("\n💰 Opportunities by contact industry:")
    ind_opps = opp_contacts.groupby("industry").agg(
        deals=("id", "count"),
        value=("monetary_value", "sum"),
        won=("status", lambda x: (x == "won").sum()),
        won_value=("monetary_value", lambda x: x[opp_contacts.loc[x.index, "status"] == "won"].sum()),
    ).sort_values("value", ascending=False)

    print(f"\n  {'Industry':25s} {'Deals':>6s} {'Pipeline $':>12s} {'Won':>5s} {'Won $':>12s} {'Win Rate':>10s}")
    print(f"  {'-'*72}")
    for ind, row in ind_opps.head(15).iterrows():
        win_rate = row["won"] / row["deals"] * 100 if row["deals"] > 0 else 0
        print(f"  {str(ind):25s} {int(row['deals']):>6,} ${row['value']:>11,.0f} {int(row['won']):>5,} ${row['won_value']:>11,.0f} {win_rate:>9.1f}%")

    # Conversion rate by industry
    print("\n🔄 Conversion rate by industry (contact → opportunity):")
    for ind in ind_all.head(10).index:
        total = len(contacts[contacts["industry"] == ind])
        with_opp = len(opp_contacts[opp_contacts["industry"] == ind])
        rate = with_opp / total * 100 if total > 0 else 0
        if total >= 50:  # only show industries with enough data
            print(f"  {ind:25s} {with_opp:>5,} / {total:>6,} contacts → {rate:.2f}% conversion")


# ============================================================
print("\n\n" + "=" * 70)
print("ANALYSIS 2: CAMPAIGN TAG → PIPELINE ATTRIBUTION")
print("=" * 70)

if not contacts.empty and not opps.empty:
    # Get contacts who have opportunities
    opp_contact_ids = set(opps["contact_id"].dropna())
    contacts_with_opps = contacts[contacts["id"].isin(opp_contact_ids)]
    contacts_without_opps = contacts[~contacts["id"].isin(opp_contact_ids)]

    # Get contacts who have WON opportunities
    won_contact_ids = set(opps[opps["status"] == "won"]["contact_id"].dropna())
    contacts_with_wins = contacts[contacts["id"].isin(won_contact_ids)]

    # Analyze tags
    def get_tag_counts(df):
        all_tags = []
        for t in df["tags"].dropna():
            all_tags.extend([tag.strip() for tag in t.split(",") if tag.strip()])
        return pd.Series(all_tags).value_counts()

    all_tags = get_tag_counts(contacts)
    opp_tags = get_tag_counts(contacts_with_opps)
    won_tags = get_tag_counts(contacts_with_wins)

    print(f"\n📊 Tags that appear DISPROPORTIONATELY on opportunity contacts:")
    print(f"   (tags where opportunity contacts have a higher % than the general population)\n")
    print(f"  {'Tag':55s} {'All %':>7s} {'Opp %':>7s} {'Lift':>7s} {'Won':>5s}")
    print(f"  {'-'*83}")

    lifts = []
    for tag in opp_tags.head(50).index:
        all_pct = all_tags.get(tag, 0) / len(contacts) * 100
        opp_pct = opp_tags.get(tag, 0) / len(contacts_with_opps) * 100
        won_count = won_tags.get(tag, 0)
        if all_pct > 1:  # only meaningful tags
            lift = opp_pct / all_pct if all_pct > 0 else 0
            lifts.append((tag, all_pct, opp_pct, lift, won_count))

    lifts.sort(key=lambda x: x[3], reverse=True)
    for tag, all_pct, opp_pct, lift, won_count in lifts[:20]:
        marker = " ⭐" if lift > 1.5 else ""
        print(f"  {tag[:55]:55s} {all_pct:>6.1f}% {opp_pct:>6.1f}% {lift:>6.2f}x {won_count:>5,}{marker}")

    print("\n  ⭐ = tag is 1.5x+ more common on opportunity contacts (high-value campaign)")

    # Tags unique to won deals
    print(f"\n🏆 Tags on WON deal contacts (top 15):")
    for tag, count in won_tags.head(15).items():
        pct_of_wins = count / len(contacts_with_wins) * 100
        print(f"  {tag[:55]:55s} {count:>4,} ({pct_of_wins:.0f}% of won contacts)")


# ============================================================
print("\n\n" + "=" * 70)
print("ANALYSIS 3: PIPELINE VELOCITY & STAGE LEAKAGE")
print("=" * 70)

if not opps.empty:
    print(f"\n📊 Overall Pipeline Health:")
    total_opps = len(opps)
    total_value = opps["monetary_value"].sum()
    open_opps = opps[opps["status"] == "open"]
    won_opps = opps[opps["status"] == "won"]
    lost_opps = opps[opps["status"] == "lost"]

    print(f"  Total deals: {total_opps:,}")
    print(f"  Total value: ${total_value:,.0f}")
    print(f"  Open:  {len(open_opps):>5,} ({len(open_opps)/total_opps*100:.1f}%) — ${open_opps['monetary_value'].sum():>12,.0f}")
    print(f"  Won:   {len(won_opps):>5,} ({len(won_opps)/total_opps*100:.1f}%) — ${won_opps['monetary_value'].sum():>12,.0f}")
    print(f"  Lost:  {len(lost_opps):>5,} ({len(lost_opps)/total_opps*100:.1f}%) — ${lost_opps['monetary_value'].sum():>12,.0f}")
    print(f"  Win rate: {len(won_opps)/(len(won_opps)+len(lost_opps))*100:.1f}% (won / won+lost)")

    # Stage analysis — where are deals stuck?
    print(f"\n🔍 Where are deals STUCK? (Open deals by stage)")
    open_by_stage = open_opps.groupby("stage_name").agg(
        count=("id", "count"),
        value=("monetary_value", "sum"),
    ).sort_values("count", ascending=False)

    print(f"\n  {'Stage':45s} {'Deals':>6s} {'Value':>12s} {'% of open':>10s}")
    print(f"  {'-'*75}")
    for stage, row in open_by_stage.head(15).iterrows():
        pct = row["count"] / len(open_opps) * 100
        bar = "█" * int(pct / 2)
        print(f"  {str(stage)[:45]:45s} {int(row['count']):>6,} ${row['value']:>11,.0f} {pct:>8.1f}%  {bar}")

    # Pipeline-level analysis
    print(f"\n💰 Pipeline Performance:")
    print(f"\n  {'Pipeline':40s} {'Total':>5s} {'Won':>4s} {'Lost':>5s} {'Win%':>6s} {'Pipeline $':>12s}")
    print(f"  {'-'*75}")
    for pipe, group in opps.groupby("pipeline"):
        t = len(group)
        w = len(group[group["status"] == "won"])
        l = len(group[group["status"] == "lost"])
        v = group["monetary_value"].sum()
        wr = w / (w + l) * 100 if (w + l) > 0 else 0
        print(f"  {str(pipe)[:40]:40s} {t:>5,} {w:>4,} {l:>5,} {wr:>5.0f}% ${v:>11,.0f}")

    # Money sitting in pipeline
    print(f"\n💸 Top stages with VALUE sitting idle:")
    value_by_stage = open_opps.groupby("stage_name")["monetary_value"].sum().sort_values(ascending=False)
    for stage, val in value_by_stage.head(10).items():
        if val > 0:
            count = len(open_opps[open_opps["stage_name"] == stage])
            avg = val / count if count > 0 else 0
            print(f"  {str(stage)[:45]:45s} ${val:>12,.0f}  ({count} deals, avg ${avg:,.0f})")


print("\n\n" + "=" * 70)
print("ANALYSIS COMPLETE")
print("=" * 70)
