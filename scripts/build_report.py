"""
Sbarro Mystery Shopping Report - full build pipeline.

Pulls the latest Sassie export from the live Google Sheet, computes all
per-month stats, and writes a self-contained index.html with a month
selector. Designed to be run by GitHub Actions on a schedule, but works
identically run locally: `python scripts/build_report.py`
"""
import pandas as pd
import numpy as np
import json
import os
from collections import defaultdict

# ---- CONFIG ----
SHEET_ID = "1EqW35dTmOGvWg0r71YqsexFuQKgPwzMWYn-zJz4Chk0"
GID = "0"
SHEET_CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}"

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE_PATH = os.path.join(REPO_ROOT, "template", "index.html")
OUTPUT_PATH = os.path.join(REPO_ROOT, "index.html")

MIN_ROWS_PER_MONTH = 20  # skip months with too little data to be a real "wave"

# ---- 1. Load live data ----
print(f"Fetching live sheet: {SHEET_CSV_URL}")
raw = pd.read_csv(SHEET_CSV_URL)
print(f"Loaded {len(raw)} raw rows")

raw = raw[raw['Evaluation_Status'] == 'Finalized']
raw = raw[raw['Was this location open for business?'] == 'Yes']
raw['dt'] = pd.to_datetime(raw['Evaluation_Date'], errors='coerce')
raw = raw.dropna(subset=['dt'])
raw = raw.drop_duplicates(subset='Evaluation_ID')
print(f"{len(raw)} finalized, open-store rows after filtering")


def classify_channel(name):
    n = str(name).lower()
    if any(k in n for k in ['airport', 'terminal']):
        return 'Airport'
    if any(k in n for k in ['travel plaza', 'travel center', 'travel centre', 'service plaza',
                             'oasis', ' ta ', 'petro', 'pilot', 'welcome center']) or n.startswith('ta '):
        return 'Travel Plaza'
    if any(k in n for k in ['circle k', 'kwikshop', 'loaf', 'turkey hill', 'dk ', 'dk1',
                             'eexpress', 'extra mile', 'delek', 'scotchman', 'sk express',
                             'tom thumb', 'c-store', 'fast lane']):
        return 'C-Store / Gas'
    if any(k in n for k in ['fort ', 'camp ', 'macdill', 'base', 'air force']):
        return 'Military'
    if any(k in n for k in ['casino', 'station', 'horseshoe', 'orleans hotel']):
        return 'Casino'
    if any(k in n for k in ['university', 'college', 'cal state', 'rutgers', 'penn state']):
        return 'University'
    if any(k in n for k in ['mall', 'center', 'centre', 'plaza', 'outlet', 'galleria', 'towne',
                             'square', 'fair', 'commons', 'crossing', 'mills', 'fashion',
                             'shops', 'gardens', 'park', 'place', 'trade ctr']):
        return 'Mall / Retail'
    return 'Other / Standalone'


raw['channel'] = raw['Location_Name'].apply(classify_channel)


def yn(val, reverse=False):
    if pd.isna(val):
        return None
    v = str(val).strip().lower()
    if v == 'yes':
        return 0 if reverse else 100
    if v == 'no':
        return 100 if reverse else 0
    return None


def coded_expectation(val):
    if pd.isna(val):
        return None
    v = str(val).strip().lower()
    if 'exceeded' in v or 'met' in v:
        return 100
    if "didn't meet" in v or 'did not meet' in v:
        return 0
    return None


def bubbles(val):
    if pd.isna(val):
        return None
    v = str(val).strip().lower()
    if v.startswith('no'):
        return 100
    if v.startswith('yes'):
        return 0
    return None


C = {
    'GE1': 'Guest Engagement - 1. If the employees are not already engaging with existing customers, is a warm, friendly greeting given to each potential customer who walks by?',
    'GE2': 'Guest Engagement - 2. Did the employees appearance or lack of uniform detract from your overall experience?',
    'GE3': 'Guest Engagement - 3. Were the staff members friendly, upbeat and happy you were there?',
    'GE4': 'Guest Engagement - 4. Did anyone suggest a Combo, a beverage (or larger size beverage), dipping cup, or other item?',
    'GE5': 'Guest Engagement - 5. Which option best reflects how quickly you were served?',
    'GE6': 'Guest Engagement - 6. Did the cashier thank you for coming to Sbarro and give you a warm send off?',
    'GE7': 'Guest Engagement - 7. Were you given a receipt without asking for it?',
    'M6': 'Merchandising - 6. Were professional looking labels visible in front of every product?',
    'M7': 'Merchandising - 7. Were there at least 3 pieces on each pizza and stromboli tray, and were the breadstick trays at least half full?',
    'M8': 'Merchandising - 8. Did the other food offerings displayed (pasta, potatoes, meatballs, salads, etc.) look appetizing?',
    'M9': 'Merchandising - 9. Was the restaurant clean and in good condition?',
    'M10': "Merchandising - 10. If you weren't a mystery shopper, would the restaurant appearance / design have prompted you to eat at Sbarro?",
    'M11c': 'Merchandising - 11c. If yes, were any of the displayed products in the grab-n-go expired?',
    'D1': 'Delivered Product Quality - 1. Were the portion sizes and amount of toppings acceptable?',
    'D2': 'Delivered Product Quality - 2. Did your food taste fresh?',
    'D3': 'Delivered Product Quality - 3. Did the temperature of the food meet your expectations?',
    'D5': 'Delivered Product Quality - 5. Did your pizza slice have bubbles that affected the overall food quality?',
    'O1': 'Overall Experience - 1. What is your likelihood to return? Scale 1-10',
}

QDEFS = [
    ('GE1', 'Guest Engagement', C['GE1'], 'binary', False),
    ('GE2', 'Guest Engagement', C['GE2'], 'binary', True),
    ('GE3', 'Guest Engagement', C['GE3'], 'binary', False),
    ('GE4', 'Guest Engagement', C['GE4'], 'binary', False),
    ('GE5', 'Guest Engagement', C['GE5'], 'coded', False),
    ('GE6', 'Guest Engagement', C['GE6'], 'binary', False),
    ('GE7', 'Guest Engagement', C['GE7'], 'binary', False),
    ('M6', 'Merchandising', C['M6'], 'binary', False),
    ('M7', 'Merchandising', C['M7'], 'binary', False),
    ('M8', 'Merchandising', C['M8'], 'binary', False),
    ('M9', 'Merchandising', C['M9'], 'binary', False),
    ('M10', 'Merchandising', C['M10'], 'binary', False),
    ('M11c', 'Merchandising', C['M11c'], 'binary', True),
    ('D1', 'Delivered Product Quality', C['D1'], 'binary', False),
    ('D2', 'Delivered Product Quality', C['D2'], 'binary', False),
    ('D3', 'Delivered Product Quality', C['D3'], 'binary', False),
    ('D5', 'Delivered Product Quality', C['D5'], 'binary', True),
]

SECTION_QIDS = {
    'Guest Engagement': ['GE1', 'GE2', 'GE3', 'GE4', 'GE6', 'GE7'],
    'Merchandising': ['M6', 'M7', 'M8', 'M9', 'M10', 'M11c'],
    'Delivered Product Quality': ['D1', 'D2', 'D3', 'D5'],
    'Overall Experience': ['O1'],
}

THEMES = [
    ('Wait time / speed', ['wait', 'slow', 'quick', 'fast', 'line', 'queue', 'minutes', 'took a while', 'speedy', 'prompt']),
    ('Order accuracy', ['wrong order', 'incorrect', 'mistake', 'missing item', 'forgot', 'accurate order', 'got everything']),
    ('Food temperature', ['hot', 'cold', 'warm', 'lukewarm', 'temperature', 'fresh out of the oven', 'reheated']),
    ('Cleanliness', ['clean', 'dirty', 'messy', 'tidy', 'spotless', 'trash', 'crumbs', 'sticky']),
    ('Upselling', ['upsell', 'suggest', 'combo', 'offered a', 'recommended a drink', 'asked if i wanted']),
    ('Staff friendliness', ['friendly', 'rude', 'smile', 'helpful', 'attentive', 'warm', 'courteous', 'pleasant']),
    ('Food quality/taste', ['tasty', 'fresh', 'stale', 'delicious', 'bland', 'flavorful', 'good taste', 'toppings']),
]
COMMENT_COLS = ['Guest Engagement Comments:', 'Merchandising Comments:', 'Food Quality Comments:']
POS_WORDS = ['friendly', 'great', 'excellent', 'fresh', 'hot', 'clean', 'fast', 'quick', 'delicious',
             'helpful', 'courteous', 'tasty', 'warm', 'attentive', 'good']
NEG_WORDS = ['slow', 'cold', 'rude', 'dirty', 'stale', 'wrong', 'missing', 'messy', 'unfriendly',
             'disappointing', 'bland', 'sticky', 'forgot']


def build_month(df_all, month_start, month_end, month_label):
    df = df_all[(df_all['dt'] >= month_start) & (df_all['dt'] <= month_end)].copy()
    if len(df) < MIN_ROWS_PER_MONTH:
        return None

    for qid, section, col, qtype, reverse in QDEFS:
        if qtype == 'binary':
            df[f's_{qid}'] = df[col].apply(lambda v: yn(v, reverse=reverse))
        elif qtype == 'coded':
            df[f's_{qid}'] = df[col].apply(coded_expectation)
    df['s_O1'] = pd.to_numeric(df[C['O1']], errors='coerce') * 10

    for sec, qids in SECTION_QIDS.items():
        df[f'SEC_{sec}'] = df[[f's_{q}' for q in qids]].mean(axis=1, skipna=True)
    df['overall_score'] = df[[f'SEC_{s}' for s in SECTION_QIDS]].mean(axis=1, skipna=True).round(1)
    df['band'] = df['overall_score'].apply(lambda x: 'good' if x >= 85 else ('warn' if x >= 70 else 'bad'))

    def yn_counts(col, reverse=False):
        s = df[col].dropna().astype(str).str.strip().str.lower()
        yes = (s == 'yes').sum()
        no = (s == 'no').sum()
        total = len(s)
        good = no if reverse else yes
        pct_good = round(100 * good / total, 0) if total else None
        return good, total, pct_good

    questions = {}
    priorities = []
    for qid, section, col, qtype, reverse in QDEFS:
        if qtype != 'binary':
            continue
        good, total, pct_good = yn_counts(col, reverse)
        bad = total - good
        by_channel = {}
        for ch, sub in df.groupby('channel'):
            s = sub[col].dropna().astype(str).str.strip().str.lower()
            yes = (s == 'yes').sum()
            no = (s == 'no').sum()
            tot = len(s)
            good_n = no if reverse else yes
            by_channel[ch] = {'pct_yes': round(100 * good_n / tot, 0) if tot else None, 'n': int(tot)}
        text = col.split('. ', 1)[-1] if '. ' in col else col
        questions[qid] = {
            'id': qid, 'text': text, 'type': 'binary', 'answered': int(total), 'total': int(len(df)),
            'pct_yes': int(pct_good) if pct_good is not None else None, 'yes': int(good), 'no': int(bad),
            'by_channel': by_channel, 'section': section, 'reverse': reverse,
        }
        priorities.append({'id': qid, 'text': text, 'section': section,
                            'pct_yes': questions[qid]['pct_yes'], 'fails': int(bad), 'answered': int(total)})

    s5 = df[C['GE5']].dropna()
    counts5 = s5.value_counts().to_dict()
    questions['GE5'] = {'id': 'GE5', 'text': 'Which option best reflects how quickly you were served?',
                         'type': 'coded', 'answered': int(len(s5)), 'total': int(len(df)), 'counts': counts5,
                         'order': ['Exceeded Expectations', 'Met Expectations', "Didn't Meet Expectations"],
                         'section': 'Guest Engagement'}

    o1 = pd.to_numeric(df[C['O1']], errors='coerce').dropna()
    promoters = (o1 >= 9).sum()
    passives = ((o1 >= 7) & (o1 <= 8)).sum()
    detractors = (o1 <= 6).sum()
    questions['O1'] = {
        'id': 'O1', 'text': 'Likelihood to return (0-10 scale)', 'type': 'coded',
        'answered': int(len(o1)), 'total': int(len(df)), 'avg': round(o1.mean(), 1),
        'promoters': int(promoters), 'passives': int(passives), 'detractors': int(detractors),
        'counts': {'Promoters (9-10)': int(promoters), 'Passives (7-8)': int(passives),
                   'Detractors (0-6)': int(detractors)},
        'order': ['Promoters (9-10)', 'Passives (7-8)', 'Detractors (0-6)'], 'section': 'Overall Experience',
    }

    kd = df['Overall Experience - 2. What was the key driver of your response above?'].dropna()
    driver_counts = defaultdict(int)
    for val in kd:
        for tok in str(val).split('|'):
            driver_counts[tok.strip()] += 1
    key_drivers = sorted(driver_counts.items(), key=lambda x: -x[1])

    priorities = sorted(priorities, key=lambda p: (p['pct_yes'] if p['pct_yes'] is not None else 100))

    sections_out = []
    for sec, qids in SECTION_QIDS.items():
        col = f'SEC_{sec}'
        scores = df[col].dropna().round(1).tolist()
        avg = round(df[col].mean(), 1)
        band = 'good' if avg >= 85 else ('warn' if avg >= 70 else 'bad')
        sections_out.append({'name': sec, 'avg': avg, 'n': int(df[col].notna().sum()),
                              'missing': int(df[col].isna().sum()), 'scores': scores,
                              'questions': qids, 'band': band})

    def rollup(groupcol):
        out = []
        for label, sub in df.groupby(groupcol):
            avg = round(sub['overall_score'].mean(), 1)
            band = 'good' if avg >= 85 else ('warn' if avg >= 70 else 'bad')
            out.append({'label': label, 'avg': avg, 'n': int(len(sub)), 'band': band})
        return sorted(out, key=lambda x: -x['avg'])

    by_channel = rollup('channel')

    df['_all_text'] = df[COMMENT_COLS].fillna('').agg(' '.join, axis=1).str.lower()
    theme_out = []
    for name, kws in THEMES:
        mask = df['_all_text'].apply(lambda t: any(k in t for k in kws))
        mentions = int(mask.sum())
        pct = round(100 * mentions / len(df), 0) if len(df) else 0
        avg_score = round(df.loc[mask, 'overall_score'].mean(), 1) if mentions else None
        theme_out.append({'name': name, 'keywords': kws, 'mentions': mentions, 'pct': int(pct),
                           'avg_score': avg_score, 'pos': 0, 'neg': 0, 'lean': int(pct)})
    theme_out = sorted(theme_out, key=lambda t: -t['mentions'])

    corr_speed = df[['s_GE5', 's_O1']].dropna().corr().iloc[0, 1] if df[['s_GE5', 's_O1']].dropna().shape[0] > 5 else 0
    upsell_yes = df.loc[df['s_GE4'] == 100, 'overall_score'].mean()
    upsell_no = df.loc[df['s_GE4'] == 0, 'overall_score'].mean()
    upsell_gap = round(upsell_yes - upsell_no, 1) if pd.notna(upsell_yes) and pd.notna(upsell_no) else 0

    worst_ch = min(by_channel, key=lambda c: c['avg']) if by_channel else {'label': 'n/a', 'avg': 0, 'n': 0}
    best_ch = max(by_channel, key=lambda c: c['avg']) if by_channel else {'label': 'n/a', 'avg': 0, 'n': 0}
    kd_top = key_drivers[:3] if key_drivers else [('Food', 0), ('Service', 0), ('Speed', 0)]
    kd_1 = kd_top[0] if len(kd_top) > 0 else ('n/a', 0)
    kd_2 = kd_top[1] if len(kd_top) > 1 else ('n/a', 0)

    commentary = {
        "title": "Insights - what the data is telling us",
        "lead": "Speed and cleanliness carry more weight than the survey structure suggests.",
        "body": [
            f"Speed of service correlates with return intent at r={corr_speed:.2f} across {len(df)} visits. "
            f"Speed and food together account for a large share of stated key driver mentions "
            f"({kd_1[0]}: {kd_1[1]}, {kd_2[0]}: {kd_2[1]}).",
            f"{worst_ch['label']} locations trail the network by {round(best_ch['avg']-worst_ch['avg'],1)} points "
            f"({worst_ch['avg']}% vs {best_ch['avg']}% for {best_ch['label']}, n={worst_ch['n']}).",
            f"Visits where staff suggested a combo or add-on averaged {upsell_gap} points higher overall than "
            f"visits where nothing was suggested.",
        ],
        "kicker": f"Protect the counter experience. Fix the display case at {worst_ch['label'].lower()} locations."
    }

    stores = []
    for _, row in df.iterrows():
        text = row['_all_text']
        pos = sum(text.count(w) for w in POS_WORDS)
        neg = sum(text.count(w) for w in NEG_WORDS)
        net = pos - neg
        label = 'positive' if net > 2 else ('negative' if net < -1 else 'mixed')
        narrative_parts = []
        for c in COMMENT_COLS:
            v = row.get(c)
            if pd.notna(v) and str(v).strip() and str(v).strip().lower() not in ('this is a test shop', 'test'):
                narrative_parts.append(str(v).strip())
        narrative = '  '.join(narrative_parts)
        answers = {}
        for qid, section, col, qtype, reverse in QDEFS:
            v = row.get(col)
            answers[qid] = None if pd.isna(v) else str(v)
        sec_scores = {sec: (round(row[f'SEC_{sec}'], 1) if pd.notna(row[f'SEC_{sec}']) else None) for sec in SECTION_QIDS}
        ch = row['channel']
        stores.append({
            "id": f"SB{int(row['Location_ID']):03d}", "name": row['Location_Name'], "state": row['Location_State'],
            "region": ch, "group": ch, "mgr": "", "date": str(row['Evaluation_Date']),
            "score": row['overall_score'], "band": row['band'], "link": row['Link_to_Evaluation'],
            "narrative": narrative, "sections": sec_scores, "answers": answers,
        })
    stores = sorted(stores, key=lambda s: -(s['score'] or 0))

    o1_ans = questions['O1']
    per_doc = []
    doc_counts = {"positive": 0, "mixed": 0, "negative": 0}
    for _, row in df.sort_values('overall_score', ascending=False).iterrows():
        text = row['_all_text']
        pos = sum(text.count(w) for w in POS_WORDS)
        neg = sum(text.count(w) for w in NEG_WORDS)
        net = pos - neg
        label = 'positive' if net > 2 else ('negative' if net < -1 else 'mixed')
        doc_counts[label] += 1
        per_doc.append({"store": row['Location_Name'], "state": row['channel'], "score": row['overall_score'],
                         "pos": int(pos), "neg": int(neg), "net": int(net), "label": label})

    sentiment = {
        "rating": {
            "question": "Overall Experience - 1", "text": "Likelihood to return (0-10 scale)",
            "answered": o1_ans['answered'],
            "options": [
                {"label": "Promoters (9-10)", "n": o1_ans['promoters'],
                 "pct": round(100 * o1_ans['promoters'] / max(o1_ans['answered'], 1)), "sentiment": "positive"},
                {"label": "Passives (7-8)", "n": o1_ans['passives'],
                 "pct": round(100 * o1_ans['passives'] / max(o1_ans['answered'], 1)), "sentiment": "neutral"},
                {"label": "Detractors (0-6)", "n": o1_ans['detractors'],
                 "pct": round(100 * o1_ans['detractors'] / max(o1_ans['answered'], 1)), "sentiment": "negative"},
            ],
            "counts": {"positive": o1_ans['promoters'], "neutral": o1_ans['passives'], "negative": o1_ans['detractors']}
        },
        "docs": len(df), "doc_counts": doc_counts, "per_doc": per_doc, "themes": theme_out,
        "method": "Themes are counted by keyword match across guest-engagement, merchandising and food-quality "
                  "comment fields. NPS-style promoter/detractor split uses the 0-10 likelihood-to-return question. "
                  "This is directional only, not a language model. Click a theme to read the actual comments behind it."
    }

    meta = {
        "client": "Sbarro", "title": "Mystery Shopping Report", "wave": f"{month_label} Wave",
        "generated": pd.Timestamp.now().strftime("%d %B %Y"), "n": len(df), "stores": len(df),
        "states": df['Location_State'].nunique(), "channels": df['channel'].nunique(),
        "avg": round(df['overall_score'].mean(), 1),
        "date_from": str(df['dt'].min().date()), "date_to": str(df['dt'].max().date()),
        "notes": [], "bands": {"good": 85, "warn": 70}
    }

    questions_out = {}
    for qid, q in questions.items():
        q2 = dict(q)
        q2['by_state'] = q2.pop('by_channel', {})
        questions_out[qid] = q2

    return {
        "meta": meta, "commentary": commentary, "sentiment": sentiment,
        "brand": {"primary": "#DE1D39", "primary_text": "#FFFFFF", "accent": "#5CAD46", "nav": "#B5162A",
                  "background": "#F4F4F4", "text": "#2E2A26", "good": "#2E8B57", "warn": "#E8A33D", "bad": "#C8102E",
                  "palette": ["#DE1D39", "#5CAD46", "#E8B04B", "#B5162A", "#A8A8A8", "#D4D4D4", "#2E8B57",
                              "#E8A33D", "#C8102E", "#8FA5DC", "#5576C8", "#1B2A6B"],
                  "font": "'Helvetica Neue', Helvetica, Arial, sans-serif"},
        "sections": sections_out, "stores": stores, "questions": questions_out,
        "priorities": priorities, "by_state": by_channel, "by_region": by_channel, "by_group": by_channel,
        "by_mgr": [], "verbatims": {}
    }


# ---- 2. Build every calendar month present in the data ----
months_present = sorted(raw['dt'].dt.to_period('M').unique())
ALL_MONTHS = {}
for period in months_present:
    key = str(period)  # 'YYYY-MM'
    start = period.start_time
    end = period.end_time
    label = period.strftime('%B %Y')
    result = build_month(raw, start, end, label)
    if result:
        ALL_MONTHS[key] = result
        print(f"  {key}: {result['meta']['n']} evals, avg {result['meta']['avg']}")

if not ALL_MONTHS:
    raise SystemExit("No month had enough data to build a report. Aborting.")

latest_key = sorted(ALL_MONTHS.keys())[-1]

# ---- 3. Inject into template ----
template = open(TEMPLATE_PATH, encoding='utf-8').read()
all_months_json = json.dumps(ALL_MONTHS, default=str)
html = template.replace('__ALL_MONTHS_JSON__', all_months_json)
html = html.replace('let currentMonthKey = "2026-07";', f'let currentMonthKey = "{latest_key}";')

with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
    f.write(html)

print(f"\nWrote {OUTPUT_PATH} ({len(html):,} bytes) with {len(ALL_MONTHS)} months, defaulting to {latest_key}")
