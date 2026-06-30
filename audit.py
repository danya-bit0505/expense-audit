import csv, sys, math, os, urllib.request
from collections import defaultdict

DATE_COLS = ['date', 'data', 'datum']
CAT_COLS  = ['category', 'cat', 'type']
AMT_COLS  = ['amount', 'sum', 'total', 'price']
DESC_COLS = ['description', 'desc', 'name']

def detect(hdrs, al):
    return next((h for h in hdrs if h.strip().lower() in al), None)

def load(path):
    with open(path, newline='', encoding='utf-8-sig') as f:
        rd = csv.DictReader(f); h = rd.fieldnames
        dc = detect(h, DATE_COLS); cc = detect(h, CAT_COLS)
        ac = detect(h, AMT_COLS);  xc = detect(h, DESC_COLS)
        if not (dc and cc and ac):
            print('Error: missing required columns'); sys.exit(1)
        rows = []
        for row in rd:
            try:
                amt = float(row[ac].replace(',', '.').replace(' ', ''))
                rows.append({'date': row.get(dc,'').strip(), 'cat': row.get(cc,'').strip(),
                             'desc': row.get(xc,'').strip() if xc else '', 'amt': amt})
            except (ValueError, KeyError): pass
    return rows

def get_file(src):
    if src.startswith('http'):
        urllib.request.urlretrieve(src, '_tmp.csv'); return '_tmp.csv'
    return src

def total_sum(rows): return sum(r['amt'] for r in rows)

def by_category(rows):
    t = defaultdict(float)
    for r in rows: t[r['cat']] += r['amt']
    return sorted(t.items(), key=lambda x: x[1], reverse=True)

def top5(rows): return sorted(rows, key=lambda x: x['amt'], reverse=True)[:5]

def find_duplicates(rows):
    s = defaultdict(list)
    for r in rows: s[(r['date'], r['desc'], r['amt'])].append(r)
    return {k: v for k, v in s.items() if len(v) > 1}

def find_anomalies(rows):
    bc = defaultdict(list)
    for r in rows: bc[r['cat']].append(r)
    res = []
    for items in bc.values():
        a = [r['amt'] for r in items]
        if len(a) < 2: continue
        m = sum(a) / len(a)
        std = math.sqrt(sum((x-m)**2 for x in a) / len(a))
        if std > 0: res += [(r, m+3*std) for r in items if r['amt'] > m+3*std]
    return sorted(res, key=lambda x: x[0]['amt'], reverse=True)

def find_negatives(rows): return [r for r in rows if r['amt'] < 0]

def build_report(src, rows):
    L = ['EXPENSE AUDIT REPORT', 'File: '+src, 'Rows: '+str(len(rows))]
    L += ['', '1. TOTAL: '+str(total_sum(rows))]
    L += ['', '2. BY CATEGORY:'] + [c+': '+str(round(s,2)) for c,s in by_category(rows)]
    L += ['', '3. TOP 5:'] + [r['date']+' '+r['cat']+' '+r['desc']+' '+str(r['amt']) for r in top5(rows)]
    d = find_duplicates(rows)
    L += ['', '4. DUPLICATES:'] + ([str(len(g))+'x '+dt+' | '+de+' | '+str(a) for (dt,de,a),g in d.items()] or ['none'])
    an = find_anomalies(rows)
    L += ['', '5. ANOMALIES:'] + ([r['date']+' '+r['cat']+' amt='+str(round(r['amt'],2))+' limit='+str(round(l,2)) for r,l in an] or ['none'])
    ng = find_negatives(rows)
    L += ['', '6. NEGATIVES:'] + ([r['date']+' '+r['cat']+' '+str(r['amt']) for r in ng] or ['none'])
    return chr(10).join(L)

def main():
    if len(sys.argv) < 2: print('Usage: python audit.py FILE_OR_URL'); sys.exit(1)
    src = sys.argv[1]; rows = load(get_file(src))
    rpt = build_report(src, rows); print(rpt)
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'report.txt')
    open(p, 'w', encoding='utf-8').write(rpt); print('Saved: '+p)

if __name__ == '__main__': main()
