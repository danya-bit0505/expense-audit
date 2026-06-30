import csv
import sys
import math
import os
import urllib.request
from collections import defaultdict

DATE_COLS = ['date', 'data', 'datum', 'day']
CAT_COLS = ['category', 'cat', 'type', 'kind']
AMT_COLS = ['amount', 'sum', 'total', 'price', 'cost']
DESC_COLS = ['description', 'desc', 'name', 'title', 'note']


def detect(headers, aliases):
    for h in headers:
        if h.strip().lower() in aliases:
            return h
    return None


def load(path):
    with open(path, newline='', encoding='utf-8-sig') as f:
        r = csv.DictReader(f)
        h = r.fieldnames
        dc = detect(h, DATE_COLS)
        cc = detect(h, CAT_COLS)
        ac = detect(h, AMT_COLS)
        xc = detect(h, DESC_COLS)
        missing = [n for n, c in [('date', dc), ('category', cc), ('amount', ac)] if c is None]
        if missing:
            print('Cannot detect columns: ' + ', '.join(missing))
            print('Available: ' + ', '.join(h))
            sys.exit(1)
        rows = []
        for row in r:
            try:
                amt = float(row[ac].replace(',', '.').replace(' ', ''))
            except (ValueError, KeyError):
                continue
            rows.append({
                'date': row.get(dc, '').strip(),
                'cat': row.get(cc, '').strip(),
                'desc': row.get(xc, '').strip() if xc else '',
                'amt': amt,
            })
    return rows


def get_file(src):
    if src.startswith('http://') or src.startswith('https://'):
        dest = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_tmp.csv')
        print('Downloading ' + src)
        urllib.request.urlretrieve(src, dest)
        return dest
    return src


def calc_total(rows):
    return sum(r['amt'] for r in rows)


def calc_by_cat(rows):
    t = defaultdict(float)
    for r in rows:
        t[r['cat']] += r['amt']
    return sorted(t.items(), key=lambda x: x[1], reverse=True)


def calc_top5(rows):
    return sorted(rows, key=lambda x: x['amt'], reverse=True)[:5]


def calc_dupes(rows):
    seen = defaultdict(list)
    for r in rows:
        seen[(r['date'], r['desc'], r['amt'])].append(r)
    return {k: v for k, v in seen.items() if len(v) > 1}


def calc_anomalies(rows):
    by_cat = defaultdict(list)
    for r in rows:
        by_cat[r['cat']].append(r)
    result = []
    for cat, items in by_cat.items():
        amts = [r['amt'] for r in items]
        if len(amts) < 2:
            continue
        mean = sum(amts) / len(amts)
        std = math.sqrt(sum((a - mean) ** 2 for a in amts) / len(amts))
        if std == 0:
            continue
        limit = mean + 3 * std
        for r in items:
            if r['amt'] > limit:
                result.append((r, limit))
    return sorted(result, key=lambda x: x[0]['amt'], reverse=True)


def calc_negatives(rows):
    return [r for r in rows if r['amt'] < 0]


def row_str(r):
    return '  ' + r['date'] + '  ' + r['cat'] + '  ' + r['desc'] + '  ' + str(round(r['amt'], 2))


def make_report(src, rows):
    out = []
    out.append('=' * 60)
    out.append('EXPENSE AUDIT REPORT')
    out.append('=' * 60)
    out.append('File: ' + src)
    out.append('Rows: ' + str(len(rows)))
    out.append('')
    out.append('--- 1. TOTAL EXPENSES ---')
    out.append(str(calc_total(rows)))
    out.append('')
    out.append('--- 2. BY CATEGORY ---')
    for cat, s in calc_by_cat(rows):
        out.append(cat + ': ' + str(round(s, 2)))
    out.append('')
    out.append('--- 3. TOP 5 LARGEST ---')
    for r in calc_top5(rows):
        out.append(row_str(r))
    out.append('')
    out.append('--- 4. DUPLICATES ---')
    dupes = calc_dupes(rows)
    if not dupes:
        out.append('none')
    else:
        for (d, desc, amt), grp in dupes.items():
            out.append(str(len(grp)) + 'x: ' + d + ' | ' + desc + ' | ' + str(amt))
    out.append('')
    out.append('--- 5. ANOMALIES (mean + 3*sigma per category) ---')
    anom = calc_anomalies(rows)
    if not anom:
        out.append('none')
    else:
        for r, limit in anom:
            line = r['date'] + ' ' + r['cat'] + ' ' + r['desc']
            line = line + ' amt=' + str(round(r['amt'], 2))
            line = line + ' limit=' + str(round(limit, 2))
            out.append(line)
    out.append('')
    out.append('--- 6. NEGATIVE AMOUNTS ---')
    negs = calc_negatives(rows)
    if not negs:
        out.append('none')
    else:
        for r in negs:
            out.append(row_str(r))
    out.append('')
    out.append('=' * 60)
    return '\n'.join(out)


def main():
    if len(sys.argv) < 2:
        print('Usage: python audit.py FILE_OR_URL')
        sys.exit(1)
    src = sys.argv[1]
    path = get_file(src)
    rows = load(path)
    report = make_report(src, rows)
    print(report)
    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'report.txt')
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(report)
    print('Saved: ' + out_path)


if __name__ == '__main__':
    main()
