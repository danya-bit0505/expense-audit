import csv
import sys
import math
import urllib.request
import os
from collections import defaultdict

DATE_ALIASES = ['date', 'data', 'data', 'datum']
CATEGORY_ALIASES = ['category', 'cat', 'type', 'kind']
AMOUNT_ALIASES = ['amount', 'sum', 'total', 'price', 'cost', 'value']
DESCRIPTION_ALIASES = ['description', 'desc', 'name', 'title', 'note']

RU_DATE_ALIASES = ['data', 'date']
RU_CATEGORY_ALIASES = ['kategoriya', 'tip', 'vid']
RU_AMOUNT_ALIASES = ['summa', 'itogo', 'tsena']
RU_DESCRIPTION_ALIASES = ['opisanie', 'naimenovanie', 'nazvanie']

ALL_DATE = ['date', 'data', 'datum', 'дата']
ALL_CATEGORY = ['category', 'cat', 'type', 'kind', 'категория', 'тип', 'вид']
ALL_AMOUNT = ['amount', 'sum', 'total', 'price', 'cost', 'value', 'сумма', 'итого', 'цена']
ALL_DESC = ['description', 'desc', 'name', 'title', 'note', 'описание', 'наименование', 'название']


def detect_column(headers, aliases):
    for h in headers:
        if h.strip().lower() in aliases:
            return h
    return None


def load_data(path):
    with open(path, newline='', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames

        date_col = detect_column(headers, ALL_DATE)
        cat_col = detect_column(headers, ALL_CATEGORY)
        amt_col = detect_column(headers, ALL_AMOUNT)
        desc_col = detect_column(headers, ALL_DESC)

        missing = []
        if date_col is None:
            missing.append('date/data')
        if cat_col is None:
            missing.append('category/kategoriya')
        if amt_col is None:
            missing.append('amount/summa')

        if missing:
            print("Error: could not detect columns: " + ', '.join(missing))
            print("Available columns: " + ', '.join(headers))
            sys.exit(1)

        rows = []
        for row in reader:
            try:
                raw = row[amt_col].replace(',', '.').replace(' ', '')
                amount = float(raw)
            except (ValueError, KeyError):
                continue
            rows.append({
                'date': row.get(date_col, '').strip(),
                'category': row.get(cat_col, '').strip(),
                'description': row.get(desc_col, '').strip() if desc_col else '',
                'amount': amount,
            })
    return rows


def fetch_file(source):
    if source.startswith('http://') or source.startswith('https://'):
        local_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_downloaded.csv')
        print("Downloading: " + source)
        urllib.request.urlretrieve(source, local_path)
        return local_path
    return source


def total_sum(rows):
    return sum(r['amount'] for r in rows)


def by_category(rows):
    totals = defaultdict(float)
    for r in rows:
        totals[r['category']] += r['amount']
    return sorted(totals.items(), key=lambda x: x[1], reverse=True)


def top5(rows):
    return sorted(rows, key=lambda x: x['amount'], reverse=True)[:5]


def duplicates(rows):
    seen = defaultdict(list)
    for r in rows:
        key = (r['date'], r['description'], r['amount'])
        seen[key].append(r)
    return {k: v for k, v in seen.items() if len(v) > 1}


def anomalies(rows):
    by_cat = defaultdict(list)
    for r in rows:
        by_cat[r['category']].append(r)

    result = []
    for cat, items in by_cat.items():
        amounts = [r['amount'] for r in items]
        if len(amounts) < 2:
            continue
        mean = sum(amounts) / len(amounts)
        variance = sum((a - mean) ** 2 for a in amounts) / len(amounts)
        std = math.sqrt(variance)
        if std == 0:
            continue
        threshold = mean + 3 * std
        for r in items:
            if r['amount'] > threshold:
                result.append((r, mean, std, threshold))

    return sorted(result, key=lambda x: x[0]['amount'], reverse=True)


def negatives(rows):
    return [r for r in rows if r['amount'] < 0]


def fmt_row(r):
    return "  {:<12}  {:<20}  {:<40}  {:>12.2f}".format(
        r['date'], r['category'], r['description'], r['amount']
    )


def build_report(source, rows):
    SEP = "-" * 80
    lines = []

    lines.append("=" * 80)
    lines.append("EXPENSE AUDIT REPORT")
    lines.append("=" * 80)
    lines.append("")
    lines.append("File: " + source)
    lines.append("Rows: " + str(len(rows)))

    lines.append("")
    lines.append(SEP)
    lines.append("1. TOTAL EXPENSES")
    lines.append(SEP)
    lines.append("  {:.2f}".format(total_sum(rows)))

    lines.append("")
    lines.append(SEP)
    lines.append("2. BY CATEGORY (descending)")
    lines.append(SEP)
    for cat, s in by_category(rows):
        lines.append("  {:<30}  {:>15.2f}".format(cat, s))

    lines.append("")
    lines.append(SEP)
    lines.append("3. TOP 5 LARGEST EXPENSES")
    lines.append(SEP)
    lines.append("  {:<12}  {:<20}  {:<40}  {:>12}".format("Date", "Category", "Description", "Amount"))
    lines.append("  " + "-" * 74)
    for r in top5(rows):
        lines.append(fmt_row(r))

    lines.append("")
    lines.append(SEP)
    lines.append("4. DUPLICATES (same date + description + amount)")
    lines.append(SEP)
    dupes = duplicates(rows)
    if not dupes:
        lines.append("  No duplicates found.")
    else:
        lines.append("  Duplicate groups found: " + str(len(dupes)))
        for (date, desc, amount), group in dupes.items():
            lines.append("")
            lines.append("  [{}x] {}  |  {}  |  {:.2f}".format(len(group), date, desc, amount))
            for r in group:
                lines.append("       Category: " + r['category'])

    lines.append("")
    lines.append(SEP)
    lines.append("5. ANOMALIES (amount > mean + 3*sigma per category)")
    lines.append(SEP)
    anom = anomalies(rows)
    if not anom:
        lines.append("  No anomalies found.")
    else:
        lines.append("  Anomalies found: " + str(len(anom)))
        lines.append("")
        lines.append("  {:<12}  {:<20}  {:<40}  {:>12}  {:>12}".format(
            "Date", "Category", "Description", "Amount", "Threshold"
        ))
        lines.append("  " + "-" * 100)
        for r, mean, std, threshold in anom:
            lines.append("  {:<12}  {:<20}  {:<40}  {:>12.2f}  {:>12.2f}".format(
                r['date'], r['category'], r['description'], r['amount'], threshold
            ))

    lines.append("")
    lines.append(SEP)
    lines.append("6. NEGATIVE AMOUNTS")
    lines.append(SEP)
    negs = negatives(rows)
    if not negs:
        lines.append("  No negative amounts found.")
    else:
        lines.append("  Found: " + str(len(negs)))
        for r in negs:
            lines.append(fmt_row(r))

    lines.append("")
    lines.append("=" * 80)
    return "\n".join(lines)


def main():
    if len(sys.argv) < 2:
        print("Usage: python audit.py <file_path_or_URL>")
        sys.exit(1)

    source = sys.argv[1]
    path = fetch_file(source)
    rows = load_data(path)
    report = build_report(source, rows)

    print(report)

    out_dir = os.path.dirname(os.path.abspath(__file__))
    out_path = os.path.join(out_dir, "report.txt")
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(report)
    print("\nReport saved to " + out_path)


if __name__ == "__main__":
    main()
