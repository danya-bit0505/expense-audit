import csv
import sys
import math
import urllib.request
import os
from collections import defaultdict

# Column name aliases for auto-detection
DATE_ALIASES = ['date', 'дата', 'data']
CATEGORY_ALIASES = ['category', 'категория', 'cat', 'тип', 'вид']
AMOUNT_ALIASES = ['amount', 'сумма', 'sum', 'total', 'итого', 'price', 'цена']
DESCRIPTION_ALIASES = ['description', 'описание', 'desc', 'наименование', 'название', 'name']

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
            print(f"Ошибка: не удалось определить столбцы: {', '.join(missing)}")
            print(f"Доступные столбцы: {', '.join(headers)}")
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
        print(f"Скачиваю файл: {source}")
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
    return f"  {r['date']:<12}  {r['category']:<20}  {r['description']:<40}  {r['amount']:>12.2f}"

def main():
    if len(sys.argv) < 2:
        print("Использование: python audit.py <путь_к_файлу_или_URL>")
        sys.exit(1)

    source = sys.argv[1]
    path = fetch_file(source)
    rows = load_data(path)

    lines = []

    lines.append("=" * 80)
    lines.append("ОТЧЁТ ПО АУДИТУ РАСХОДОВ")
    lines.append("=" * 80)
    lines.append(f"\nФайл: {source}")
    lines.append(f"Строк данных: {len(rows)}")

    # 1. Общая сумма
    lines.append("\n" + "─" * 80)
    lines.append("1. ОБЩАЯ СУММА РАСХОДОВ")
    lines.append("─" * 80)
    lines.append(f"  {total_sum(rows):.2f} руб.")

    # 2. По категориям
    lines.append("\n" + "─" * 80)
    lines.append("2. СУММА ПО КАТЕГОРИЯМ (по убыванию)")
    lines.append("─" * 80)
    for cat, s in by_category(rows):
        lines.append(f"  {cat:<25}  {s:>15.2f} руб.")

    # 3. Топ-5
    lines.append("\n" + "─" * 80)
    lines.append("3. ТОП-5 САМЫХ КРУПНЫХ ТРАТ")
    lines.append("─" * 80)
    lines.append(f"  {'Дата':<12}  {'Категория':<20}  {'Описание':<40}  {'Сумма':>12}")
    lines.append("  " + "-" * 74)
    for r in top5(rows):
        lines.append(fmt_row(r))

    # 4. Дубликаты
    lines.append("\n" + "─" * 80)
    lines.append("4. ДУБЛИКАТЫ (одинаковые дата + описание + сумма)")
    lines.append("─" * 80)
    dupes = duplicates(rows)
    if not dupes:
        lines.append("  Дубликаты не найдены.")
    else:
        lines.append(f"  Найдено групп дубликатов: {len(dupes)}")
        for (date, desc, amount), group in dupes.items():
            lines.append(f"\n  [{len(group)}x] {date}  |  {desc}  |  {amount:.2f} руб.")
            for r in group:
                lines.append(f"       Категория: {r['category']}")

    # 5. Аномалии
    lines.append("\n" + "─" * 80)
    lines.append("5. АНОМАЛИИ (отклонение > 3σ от среднего по категории)")
    lines.append("─" * 80)
    anom = anomalies(rows)
    if not anom:
        lines.append("  Аномалии не найдены.")
    else:
        lines.append(f"  Найдено аномалий: {len(anom)}")
        lines.append(f"\n  {'Дата':<12}  {'Категория':<20}  {'Описание':<40}  {'Сумма':>12}  {'Порог':>12}")
        lines.append("  " + "-" * 100)
        for r, mean, std, threshold in anom:
            lines.append(
                f"  {r['date']:<12}  {r['category']:<20}  {r['description']:<40}  "
                f"{r['amount']:>12.2f}  {threshold:>12.2f}"
            )

    # 6. Отрицательные суммы
    lines.append("\n" + "─" * 80)
    lines.append("6. СТРОКИ С ОТРИЦАТЕЛЬНЫМИ СУММАМИ")
    lines.append("─" * 80)
    negs = negatives(rows)
    if not negs:
        lines.append("  Отрицательных сумм не найдено.")
    else:
        lines.append(f"  Найдено: {len(negs)}")
        for r in negs:
            lines.append(fmt_row(r))

    lines.append("\n" + "=" * 80)

    report = "\n".join(lines)
    print(report)

    out_dir = os.path.dirname(os.path.abspath(__file__))
    out_path = os.path.join(out_dir, "report.txt")
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f"\nОтчёт сохранён в {out_path}")

if __name__ == "__main__":
    main()
