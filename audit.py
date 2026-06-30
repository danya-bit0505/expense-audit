import csv
import sys
import math
import urllib.request
import os
from collections import defaultdict

DATE_ALIASES = ['date', 'data', 'дата']
CATEGORY_ALIASES = ['category', 'cat', 'категория', 'тип', 'вид']
AMOUNT_ALIASES = ['amount', 'sum', 'total', 'price', 'сумма', 'итого', 'цена']
DESCRIPTION_ALIASES = ['description', 'desc', 'name', 'описание', 'наименование', 'название']


def detect_column(headers, aliases):
    for h in headers:
        if h.strip().lower() in aliases:
            return h
    return None


def load_data(path):
    with open(path, newline='', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames

        date_col = detect_column(headers, DATE_ALIASES)
        cat_col = detect_column(headers, CATEGORY_ALIASES)
        amt_col = detect_column(headers, AMOUNT_ALIASES)
        desc_col = detect_column(headers, DESCRIPTION_ALIASES)

        missing = [name for name, col in [('дата', date_col), ('категория', cat_col), ('сумма', amt_col)] if col is None]
        if missing:
            print("Ошибка: не удалось определить столбцы: " + ', '.join(missing))
            print("Доступные столбцы: " + ', '.join(headers))
            sys.exit(1)

        rows = []
        for row in reader:
            try:
                amount = float(row[amt_col].replace(',', '.').replace(' ', ''))
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
        print("Скачиваю файл: " + source)
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
    sep = "-" * 80
    lines = []

    lines.append("=" * 80)
    lines.append("OTCHET PO AUDITU RASKHODOV")
    lines.append("=" * 80)
    lines.append("")
    lines.append("Fayl: " + source)
    lines.append("Strok dannykh: " + str(len(rows)))

    # 1. Общая сумма
    lines.append("")
    lines.append(sep)
    lines.append("1. OBSHCHAYA SUMMA RASKHODOV")
    lines.append(sep)
    lines.append("  {:.2f} rub.".format(total_sum(rows)))

    # 2. По категориям
    lines.append("")
    lines.append(sep)
    lines.append("2. SUMMA PO KATEGORIYAM (po ubyvaniyu)")
    lines.append(sep)
    for cat, s in by_category(rows):
        lines.append("  {:<25}  {:>15.2f} rub.".format(cat, s))

    # 3. Топ-5
    lines.append("")
    lines.append(sep)
    lines.append("3. TOP-5 SAMYKH KRUPNYKH TRAT")
    lines.append(sep)
    lines.append("  {:<12}  {:<20}  {:<40}  {:>12}".format("Data", "Kategoriya", "Opisanie", "Summa"))
    lines.append("  " + "-" * 74)
    for r in top5(rows):
        lines.append(fmt_row(r))

    # 4. Дубликаты
    lines.append("")
    lines.append(sep)
    lines.append("4. DUBLIKATY (odinakovy data + opisanie + summa)")
    lines.append(sep)
    dupes = duplicates(rows)
    if not dupes:
        lines.append("  Dublikaty ne naydeny.")
    else:
        lines.append("  Naydeno grupp dublikatov: " + str(len(dupes)))
        for (date, desc, amount), group in dupes.items():
            lines.append("")
            lines.append("  [{}x] {}  |  {}  |  {:.2f} rub.".format(len(group), date, desc, amount))
            for r in group:
                lines.append("       Kategoriya: " + r['category'])

    # 5. Аномалии
    lines.append("")
    lines.append(sep)
    lines.append("5. ANOMALII (otkloneniye > 3 sigma ot srednego po kategorii)")
    lines.append(sep)
    anom = anomalies(rows)
    if not anom:
        lines.append("  Anomalii ne naydeny.")
    else:
        lines.append("  Naydeno anomaliy: " + str(len(anom)))
        lines.append("")
        lines.append("  {:<12}  {:<20}  {:<40}  {:>12}  {:>12}".format(
            "Data", "Kategoriya", "Opisanie", "Summa", "Porog"
        ))
        lines.append("  " + "-" * 100)
        for r, mean, std, threshold in anom:
            lines.append("  {:<12}  {:<20}  {:<40}  {:>12.2f}  {:>12.2f}".format(
                r['date'], r['category'], r['description'], r['amount'], threshold
            ))

    # 6. Отрицательные суммы
    lines.append("")
    lines.append(sep)
    lines.append("6. STROKI S OTRITSATELNYMI SUMMAMI")
    lines.append(sep)
    negs = negatives(rows)
    if not negs:
        lines.append("  Otritsatelnykh summ ne naydeno.")
    else:
        lines.append("  Naydeno: " + str(len(negs)))
        for r in negs:
            lines.append(fmt_row(r))

    lines.append("")
    lines.append("=" * 80)
    return "\n".join(lines)


def main():
    if len(sys.argv) < 2:
        print("Ispolzovaniye: python audit.py <put_k_faylu_ili_URL>")
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
    print("\nOtchet sokhranen v " + out_path)


if __name__ == "__main__":
    main()
