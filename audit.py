import csv
import sys
import math
import os
import urllib.request
from collections import defaultdict

DATE_COLS = ['date', 'data', 'datum', 'дата']
CAT_COLS  = ['category', 'cat', 'type', 'категория', 'тип']
AMT_COLS  = ['amount', 'sum', 'total', 'price', 'сумма', 'итого']
DESC_COLS = ['description', 'desc', 'name', 'описание', 'название']


def detect_col(headers, aliases):
    for h in headers:
        if h.strip().lower() in aliases:
            return h
    return None


def load(path):
    with open(path, newline='', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames
        dc = detect_col(headers, DATE_COLS)
        cc = detect_col(headers, CAT_COLS)
        ac = detect_col(headers, AMT_COLS)
        xc = detect_col(headers, DESC_COLS)
        if not (dc and cc and ac):
            print('Error: required columns not found (date, category, amount)')
            sys.exit(1)
        rows = []
        for row in reader:
            try:
                amt = float(row[ac].replace(',', '.').replace(' ', ''))
                rows.append({
                    'date': row.get(dc, '').strip(),
                    'cat':  row.get(cc, '').strip(),
                    'desc': row.get(xc, '').strip() if xc else '',
                    'amt':  amt,
                })
            except (ValueError, KeyError):
                pass
    return rows


def get_file(src):
    if src.startswith('http'):
        urllib.request.urlretrieve(src, '_tmp.csv')
        return '_tmp.csv'
    return src


def total_sum(rows):
    return sum(r['amt'] for r in rows)


def by_category(rows):
    totals = defaultdict(float)
    for r in rows:
        totals[r['cat']] += r['amt']
    return sorted(totals.items(), key=lambda x: x[1], reverse=True)


def top5(rows):
    return sorted(rows, key=lambda x: x['amt'], reverse=True)[:5]


def find_duplicates(rows):
    seen = defaultdict(list)
    for r in rows:
        seen[(r['date'], r['desc'], r['amt'])].append(r)
    return {k: v for k, v in seen.items() if len(v) > 1}


def find_anomalies(rows):
    by_cat = defaultdict(list)
    for r in rows:
        by_cat[r['cat']].append(r)
    result = []
    for items in by_cat.values():
        amounts = [r['amt'] for r in items]
        if len(amounts) < 2:
            continue
        mean = sum(amounts) / len(amounts)
        std = math.sqrt(sum((x - mean) ** 2 for x in amounts) / len(amounts))
        if std > 0:
            limit = mean + 3 * std
            result += [(r, limit) for r in items if r['amt'] > limit]
    return sorted(result, key=lambda x: x[0]['amt'], reverse=True)


def find_negatives(rows):
    return [r for r in rows if r['amt'] < 0]


def build_report(src, rows):
    lines = [
        '=' * 60,
        'EXPENSE AUDIT REPORT',
        '=' * 60,
        'File: ' + src,
        'Rows: ' + str(len(rows)),
    ]

    lines += ['', '1. TOTAL', '-' * 40]
    lines.append('  ' + str(round(total_sum(rows), 2)))

    lines += ['', '2. BY CATEGORY', '-' * 40]
    for cat, s in by_category(rows):
        lines.append(f'  {cat}: {round(s, 2)}')

    lines += ['', '3. TOP 5', '-' * 40]
    for r in top5(rows):
        lines.append(f"  {r['date']}  {r['cat']}  {r['desc']}  {r['amt']}")

    lines += ['', '4. DUPLICATES', '-' * 40]
    dupes = find_duplicates(rows)
    if dupes:
        for (dt, de, a), g in dupes.items():
            lines.append(f'  {len(g)}x  {dt} | {de} | {a}')
    else:
        lines.append('  none')

    lines += ['', '5. ANOMALIES (> 3 std from category mean)', '-' * 40]
    anomalies = find_anomalies(rows)
    if anomalies:
        for r, limit in anomalies:
            lines.append(
                f"  {r['date']}  {r['cat']}  amt={round(r['amt'], 2)}  limit={round(limit, 2)}"
            )
    else:
        lines.append('  none')

    lines += ['', '6. NEGATIVES', '-' * 40]
    negatives = find_negatives(rows)
    if negatives:
        for r in negatives:
            lines.append(f"  {r['date']}  {r['cat']}  {r['amt']}")
    else:
        lines.append('  none')

    lines.append('=' * 60)
    return '\n'.join(lines)


def main():
    if len(sys.argv) < 2:
        print('Usage: python audit.py FILE_OR_URL')
        sys.exit(1)

    src = sys.argv[1]
    rows = load(get_file(src))
    report = build_report(src, rows)
    print(report)

    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'report.txt')
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(report)
    print('Saved: ' + out_path)


if __name__ == '__main__':
    main()
