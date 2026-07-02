from datetime import datetime, date

from flask import Flask, render_template, request, url_for, redirect
import csv
import yfinance as yf
import pandas as pd

from itertools import groupby
from operator import itemgetter

app = Flask(__name__)

try:
    with open(f'data/months.csv', 'r') as f:
        reader = csv.reader(f)
        period_list = list(reader)
        period_list = period_list[0]
        period_list = [datetime.strptime(p, '%Y-%m-%d') for p in period_list]
        # for p in period_list:
        #     p = datetime.strptime(p, '%Y-%m-%d')
        print(period_list[0].month)
except FileNotFoundError:
    months = []


def load_and_filter_setups(filename, trade_history_min, rr, entry_date, growth, symbol):
    """Load and filter the setups CSV, returning an empty list if not found."""
    try:
        with open(filename, 'r') as f:
            data = list(csv.reader(f))
        data = [row for row in data if int(row[20]) >= int(trade_history_min)]
        data = [row for row in data if float(row[10]) >= (3 * float(rr))]
        if entry_date:
            data = [row for row in data if row[3] == entry_date]
        if growth:
            data = [row for row in data if row[16] == growth]
        if symbol:
            data = [row for row in data if symbol in row[1]]
        return data
    except FileNotFoundError:
        return []


def load_total_setups(period):
    try:
        with open(f'data/{period}.csv', 'r') as f:
            return list(csv.reader(f))
    except FileNotFoundError:
        return []


def get_common_args():
    """Parse query args shared by both views."""
    return {
        'trade_history_min': request.args.get('trades', '10'),
        'rr':                request.args.get('rr', '0.1'),
        'entry_date':        request.args.get('entry_date', ''),
        'growth':            request.args.get('growth', ''),
        'symbol':            request.args.get('symbol', '').upper(),
        'sort':              request.args.get('sort', 0, type=int),
        'direction':         request.args.get('dir', 'asc'),
        'up':                request.args.get('up', 0, type=int),
        'down':              request.args.get('down', 0, type=int),
    }


def resolve_sort_direction(direction):
    """Return (symbol, toggled_direction) for the sort arrow."""
    if direction == 'asc':
        return '▲', 'desc'
    return '▼', 'asc'


def get_earnings_report_dates(period, data):
    try:
        with open(f'data/{period}_earnings_report_dates.csv', 'r') as f:
            reader = csv.reader(f)
            earnings_report_dates = list(reader)
    except FileNotFoundError:
        earnings_report_dates = []
    for row in data:
        row.append('')
    for row in data:
        for r in earnings_report_dates:
            if row[1] == r[0]:
                row[21] = r[1]
    return data


def get_symbol_list(data):
    symbol_list = []
    for row in data:
        symbol_list.append(row[1])
    return sorted(set(symbol_list))


def get_otm_call(symbol: str, target_date: date) -> dict:
    ticker = yf.Ticker(symbol)

    # 1. Get current price
    price = ticker.fast_info.last_price
    print(f"\n{symbol} current price: {price:.2f}")

    # 2. Find first expiry on or after target date
    expiries = ticker.options
    expiry_str = next(
        exp
        for exp in expiries
        if datetime.strptime(exp, "%Y-%m-%d").date() >= target_date
    )
    print(f"  Selected expiry : {expiry_str}")

    # 3. Fetch calls and find nearest OTM strike
    calls = ticker.option_chain(expiry_str).calls
    otm_calls = calls[calls["strike"] > price].sort_values("strike")
    if otm_calls.empty:
        raise ValueError(f"No OTM calls found for {symbol} at expiry {expiry_str}")

    otm_call = otm_calls.iloc[0]
    strike = otm_call["strike"]
    print(f"  Selected strike : {strike}")

    return {
        "symbol":           symbol,
        "current_price":    round(price, 2),
        "expiry":           expiry_str,
        "strike":           strike,
        "contract_symbol":  otm_call.get("contractSymbol", "N/A"),
        "bid":              otm_call.get("bid"),
        "ask":              otm_call.get("ask"),
        "last_price":       otm_call.get("lastPrice"),
        "volume":           otm_call.get("volume"),
        "open_interest":    otm_call.get("openInterest"),
        "implied_vol":      round(otm_call.get("impliedVolatility", float("nan")), 4),
        "in_the_money":     otm_call.get("inTheMoney"),
    }


@app.route('/')
def index():
    now = datetime.now()
    return redirect(url_for('setups_view', year=now.year, month=now.month))


@app.route('/stocks')
def stocks_index():
    now = datetime.now()
    return redirect(url_for('setups_view', year=now.year, month=now.month))


@app.route('/dev/<int:year>')
def setups_year_view(year):
    period = f'{year}_01'
    total_setups = ['foo', 999999]
    month = 4
    args = get_common_args()
    filename = f'data/{year}_long_mature_trades_80.csv'

    column_header = [['Symbol', 1], ['Win %', 7], ['Avg Win %', 10], ['Avg Loss %', 11], ['Trades', 20],
                     ['Entry', 3], ['Exit', 4], ['Stop', 5], ['P/L Ratio', 6], ['Growth', 16], ['ID', 19]]

    data = load_and_filter_setups(filename, **{k: args[k] for k in
                                             ('trade_history_min', 'rr', 'entry_date', 'growth', 'symbol')})
    # Float-cast Win % column for correct sorting
    data = [[float(v) if i == 7 else v for i, v in enumerate(row)] for row in data]

    reverse = args['direction'] == 'desc'
    sorted_data = sorted(data, key=lambda row: row[args['sort']], reverse=reverse)
    sort_direction_symbol, next_direction = resolve_sort_direction(args['direction'])
    sorted_data = get_earnings_report_dates(period, sorted_data)
    symbol_list = get_symbol_list(sorted_data)

    return render_template('setups_year.html', data=sorted_data,
                           period=period, header=column_header,
                           trades=args['trade_history_min'], rr=args['rr'],
                           entry_date=args['entry_date'], growth=args['growth'], symbol=args['symbol'],
                           total_setups=total_setups,
                           year=year, month=4,
                           period_list=period_list, month_name='Dev',
                           now=datetime.now(), sort=args['sort'],
                           dir=next_direction, sort_direction_symbol=sort_direction_symbol, symbol_list=symbol_list
                            )


@app.route('/dev/options/<int:year>/<int:month>/<int:day>')
def setups_year_month_day_view(year, month, day):
    period = f'{year}_01'
    total_setups = ['foo', 999999]
    # month = 4
    args = get_common_args()
    filename = f'data/{year}_long_mature_trades_80.csv'

    column_header = [['Win %', 7], ['Avg Win %', 10], ['Avg Loss %', 11], ['Trades', 20],
                     ['Entry', 3], ['Exit', 4], ['Stop', 5], ['P/L Ratio', 6], ['Growth', 16], ['ID', 19]]

    data = load_and_filter_setups(filename, **{k: args[k] for k in
                                               ('trade_history_min', 'rr', 'entry_date', 'growth', 'symbol')})
    # Float-cast Win % column for correct sorting
    data = [[float(v) if i == 7 else v for i, v in enumerate(row)] for row in data]

    reverse = args['direction'] == 'desc'
    sorted_data = sorted(data, key=lambda row: row[args['sort']], reverse=reverse)
    sort_direction_symbol, next_direction = resolve_sort_direction(args['direction'])
    sorted_data = get_earnings_report_dates(period, sorted_data)
    sorted_data = [row for row in sorted_data if row[3] == f'{month}/{day}']
    symbol_list = get_symbol_list(sorted_data)

    # setups_list = []
    # for row in sorted_data:
    #     exit_date = datetime.strptime(f'2026/{row[4]}', '%Y/%m/%d').date()
    #     setups_list.append([row[19], row[1], exit_date])
    # print(setups_list)

    results = []
    for row in sorted_data:
        try:
            exit_date = datetime.strptime(f'2026/{row[4]}', '%Y/%m/%d').date()
            result = get_otm_call(row[1], exit_date)
            results.append(result)
            row.append(result['contract_symbol'])
        except Exception as e:
            print(f"  ERROR for {row[1]} {row[0]}: {e}")
            results.append({"symbol": row[1], "error": str(e)})

    # Build a deduplicated dict keyed by contract_symbol
    grouped = {}
    for row in results:
        if 'error' in row:
            continue  # skip failed lookups
        cs = row['contract_symbol']
        if cs not in grouped:
            grouped[cs] = {
                'contract_symbol': cs,
                'option_data': row,
                'sorted_data_rows': []
            }
            
    # Attach the sorted_data rows that reference each contract
    for sd in sorted_data:
        cs = sd[-1]
        if cs in grouped:
            grouped[cs]['sorted_data_rows'].append(sd)

    # Convert to list if needed downstream
    results_grouped_by_option_contract = list(grouped.values())

    return render_template('setups_with_options.html', data=results_grouped_by_option_contract,
                           period=period, header=column_header,
                           trades=args['trade_history_min'], rr=args['rr'],
                           entry_date=args['entry_date'], growth=args['growth'], symbol=args['symbol'],
                           total_setups=total_setups,
                           year=year, month=4,
                           period_list=period_list, month_name='Dev',
                           now=datetime.now(), sort=args['sort'],
                           dir=next_direction, sort_direction_symbol=sort_direction_symbol, symbol_list=symbol_list
                           )


@app.route('/dev/<int:year>/<int:month>/weekly-charts')
def weekly_charts_view(year, month):
    args = get_common_args()
    filename = f'data/{year}_{month:02d}_weekly_arrows.csv'

    with open(filename, 'r') as f:
        reader = csv.reader(f)
        header = next(reader)  # skip header row: ticker, week, month, year, arrow, signal, value
        rows = list(reader)

    # columns by index: 0=ticker, 1=week, 2=month, 3=year, 4=arrow, 5=signal, 6=value
    rows.sort(key=itemgetter(0))
    print(f"before filter: {len(set(r[0] for r in rows))} tickers")
    kept_rows = []

    if not args['down'] and not args['up']:
        kept_rows = rows  # no filters requested — show everything
    else:
        for ticker, group_iter in groupby(rows, key=itemgetter(0)):
            group = list(group_iter)
            down_count = sum(1 for r in group if r[4] == 'down')
            up_count = sum(1 for r in group if r[4] == 'up')

            down_match = args['down'] and down_count >= args['down']
            up_match = args['up'] and up_count >= args['up']

            if down_match or up_match:
                kept_rows.extend(group)

    if args['symbol']:
        kept_rows = [r for r in kept_rows if r[0] == args['symbol']]

    if args['sort'] is not None:
        col = args['sort'] if 0 <= args['sort'] < 7 else 0
        kept_rows.sort(key=itemgetter(col), reverse=(args['direction'] == 'desc'))

    total_setups = [[len(set(r[0] for r in kept_rows))]]

    print(f"after filter: {len(set(r[0] for r in kept_rows))} tickers")

    return render_template('weekly_charts.html', data=kept_rows,
                            args=args,
                            year=year, month=month, now=datetime.now())

@app.route('/stocks/<int:year>/<int:month>/setups')
def setups_view(year, month):
    period = f'{year}_{month:02d}'
    month_name = datetime.strptime(str(month), '%m').strftime('%B')
    args = get_common_args()
    filename = f'data/{period}_long_mature_trades.csv'

    column_header = [['Symbol', 1], ['Win %', 7], ['Avg Win %', 10], ['Avg Loss %', 11], ['Trades', 20],
                     ['Entry', 3], ['Exit', 4], ['Stop', 5], ['P/L Ratio', 6], ['Growth', 16], ['ID', 19]]

    data = load_and_filter_setups(filename, **{k: args[k] for k in
                                             ('trade_history_min', 'rr', 'entry_date', 'growth', 'symbol')})
    # Float-cast Win % column for correct sorting
    data = [[float(v) if i == 7 else v for i, v in enumerate(row)] for row in data]

    reverse = args['direction'] == 'desc'
    sorted_data = sorted(data, key=lambda row: row[args['sort']], reverse=reverse)
    sort_direction_symbol, next_direction = resolve_sort_direction(args['direction'])
    sorted_data = get_earnings_report_dates(period, sorted_data)
    symbol_list = get_symbol_list(sorted_data)

    return render_template('setups.html', data=sorted_data,
                           period=period, header=column_header,
                           trades=args['trade_history_min'], rr=args['rr'],
                           entry_date=args['entry_date'], growth=args['growth'], symbol=args['symbol'],
                           total_setups=load_total_setups(period),
                           year=year, month=month, period_list=period_list, month_name=month_name,
                           now=datetime.now(), sort=args['sort'],
                           dir=next_direction, sort_direction_symbol=sort_direction_symbol, symbol_list=symbol_list)


@app.route('/stocks/<int:year>/<int:month>/trades')
def trades_view(year, month):
    period = f'{year}_{month:02d}'
    month_name = datetime.strptime(str(month), '%m').strftime('%B')
    args = get_common_args()
    filename = f'data/{period}_long_mature_trades.csv'

    column_header = [['Symbol', 1], ['Win %', 7], ['Avg Win %', 10], ['Avg Loss %', 11], ['Trades', 20],
                     ['Growth', 16], ['Entry', 3], ['Exit', 27], ['ID', 19]]

    setups = load_and_filter_setups(filename, **{k: args[k] for k in
                                               ('trade_history_min', 'rr', 'entry_date', 'growth', 'symbol')})
    setups = get_earnings_report_dates(period, setups)
    try:
        with open(f'data/{period}_results.csv', newline='') as f:
            trades = list(csv.reader(f))
    except FileNotFoundError:
        trades = []

    def merge_lists(list1, list2, key1, key2):
        lookup = {row[key2]: row for row in list2}
        merged = []
        for row in list1:
            match = lookup.get(row[key1])
            if match:
                extras = [v for i, v in enumerate(match) if i != key2]
                merged.append(row + extras)
        return merged

    result = merge_lists(setups, trades, key1=19, key2=0)
    reverse = args['direction'] == 'desc'
    sorted_result = sorted(result, key=lambda row: row[args['sort']], reverse=reverse)
    sort_direction_symbol, next_direction = resolve_sort_direction(args['direction'])
    symbol_list = get_symbol_list(sorted_result)

    return render_template('trades.html', data=sorted_result,
                           period=period, header=column_header,
                           trades=args['trade_history_min'], rr=args['rr'],
                           entry_date=args['entry_date'], growth=args['symbol'], symbol=args['symbol'],
                           total_setups=load_total_setups(period),
                           year=year, month=month, month_name=month_name, period_list=period_list,
                           now=datetime.now(), sort=args['sort'],
                           dir=next_direction, sort_direction_symbol=sort_direction_symbol, symbol_list=symbol_list)


@app.route('/futures/')
def futures_index():
    now = datetime.now()
    return redirect(url_for('futures_setups_view', year=now.year, month=now.month))


@app.route('/futures/<int:year>/<int:month>/setups')
def futures_setups_view(year, month):
    period = f'{year}_{month:02d}'  # formats month as 2 digits e.g. 04
    trade_history_min = request.args.get('trades', '10')
    month_name = datetime.strptime(str(month), '%m').strftime('%B')
    rr = request.args.get('rr', '0.1')
    entry_date = request.args.get('entry_date', '')
    growth = request.args.get('growth', '')
    commodity_name = request.args.get('commodity_name', '')
    print(commodity_name)
    sort = request.args.get('sort', 0, type=int)
    direction = request.args.get('dir', 'asc')
    column_header = [['Name', 0], ['Month', 1], ['Win %', 7], ['Avg Win %', 10], ['Avg Loss %', 11], ['Trades', 0],
                     ['Entry', 3], ['Exit', 4], ['Stop', 5], ['P/L Ratio', 6], ['Growth', 15], ['ID', 18]]
    try:
        with open(f'data/{period}_futures_trades.csv', 'r') as f:
            reader = csv.reader(f)
            next(reader)  # Skip header row
            data = list(reader)
            # data = [row for row in data if int(row[20]) >= int(trade_history_min)]
            data = [row for row in data if float(row[10]) >= (float(row[5]) * float(rr))]
            data = [[float(v) if i == 7 else v for i, v in enumerate(row)] for row in data]  # to sort 'Win %'
            if entry_date:
                data = [row for row in data if row[3] == entry_date]
            if growth:
                data = [row for row in data if row[15] == growth]
            if commodity_name:
                data = [row for row in data if commodity_name.lower() in row[0].lower()]
            reverse = direction == 'desc'
            sorted_data = sorted(data, key=lambda row: row[sort], reverse=reverse)
    except FileNotFoundError:
        sorted_data = []

    try:
        with open(f'data/{period}.csv', 'r') as f:
            reader = csv.reader(f)
            total_setups = list(reader)
    except FileNotFoundError:
        total_setups = []

    sort_direction_symbol = ''
    if direction == 'asc':
        sort_direction_symbol = '▲'
        direction = 'desc'
    elif direction == 'desc':  # ← elif prevents double-triggering
        sort_direction_symbol = '▼'
        direction = 'asc'

    return render_template('setups_futures.html', data=sorted_data,
                           period=period, header=column_header, trades=trade_history_min,
                           rr=rr, entry_date=entry_date, growth=growth, commodity_name=commodity_name, total_setups=total_setups,
                           year=year, month=month, period_list=period_list, month_name=month_name,
                           now=datetime.now(), sort=sort, dir=direction, sort_direction_symbol=sort_direction_symbol)


@app.route('/contact')
def contact_view():
    return render_template('contact.html', period_list=period_list, month_name='Trading Month')


if __name__ == '__main__':
    app.run()
