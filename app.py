from datetime import datetime

from flask import Flask, render_template, request, url_for, redirect
import csv

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


@app.route('/')
def index():
    now = datetime.now()
    return redirect(url_for('setups_view', year=now.year, month=now.month))


@app.route('/stocks')
def stocks_index():
    now = datetime.now()
    return redirect(url_for('setups_view', year=now.year, month=now.month))


@app.route('/stocks/<int:year>/<int:month>/setups')
def setups_view(year, month):
    period = f'{year}_{month:02d}'  # formats month as 2 digits e.g. 04
    trade_history_min = request.args.get('trades', '10')
    month_name = datetime.strptime(str(month), '%m').strftime('%B')
    rr = request.args.get('rr', '0.1')
    entry_date = request.args.get('entry_date', '')
    growth = request.args.get('growth', '')
    symbol = request.args.get('symbol', '').upper()
    sort = request.args.get('sort', 0, type=int)
    direction = request.args.get('dir', 'asc')
    column_header = [['Symbol', 1], ['Win %', 7], ['Avg Win %', 10], ['Avg Loss %', 11], ['Trades', 20],
                     ['Entry', 3], ['Exit', 4], ['Stop', 5], ['P/L Ratio', 6], ['Growth', 16],['ID', 19]]
    try:
        with open(f'data/{period}_long_mature_setups.csv', 'r') as f:
            reader = csv.reader(f)
            data = list(reader)
            data = [row for row in data if int(row[20]) >= int(trade_history_min)]
            data = [row for row in data if float(row[10]) >= (3 * float(rr))]  # TODO switch 3 to row[5]
            data = [[float(v) if i == 7 else v for i, v in enumerate(row)] for row in data]  # to sort 'Win %'
            if entry_date:
                data = [row for row in data if row[3] == entry_date]
            if growth:
                data = [row for row in data if row[16] == growth]
            if symbol:
                data = [row for row in data if row[1] == symbol]
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

    return render_template('setups.html', data=sorted_data,
                           period=period, header=column_header, trades=trade_history_min,
                           rr=rr, entry_date=entry_date, growth=growth, symbol=symbol, total_setups=total_setups,
                           year=year, month=month, period_list=period_list, month_name=month_name,
                           now=datetime.now(), sort=sort, dir=direction, sort_direction_symbol=sort_direction_symbol)


@app.route('/stocks/<int:year>/<int:month>/trades')
def trades_view(year, month):
    period = f'{year}_{month:02d}'  # formats month as 2 digits e.g. 04
    month_name = datetime.strptime(str(month), '%m').strftime('%B')
    trade_history_min = request.args.get('trades', '10')
    rr = request.args.get('rr', '0.1')
    entry_date = request.args.get('entry_date', '')
    growth = request.args.get('growth', '')
    column_header = ['Symbol', 'Win %', 'Avg Win %', 'Avg Loss %',
                         'Trades', 'Growth', 'Entry', 'Exit', 'ID']
    try:
        with open(f'data/{period}_long_mature_setups.csv', 'r') as f:
            reader = csv.reader(f)
            setups = list(reader)
            setups = [row for row in setups if int(row[20]) >= int(trade_history_min)]
            setups = [row for row in setups if float(row[10]) >= (3 * float(rr))]
            if entry_date:
                setups = [row for row in setups if row[3] == entry_date]
            if growth:
                setups = [row for row in setups if row[16] == growth]
    except FileNotFoundError:
        setups = []

    try:
        with open(f'data/{period}.csv', 'r') as f:
            reader = csv.reader(f)
            total_setups = list(reader)
    except FileNotFoundError:
        total_setups = []

    try:
        with open(f'data/{period}_long_mature_trades.csv', newline="") as f:
            reader = csv.reader(f)
            trades = list(reader)
    except FileNotFoundError:
        trades = []

    def merge_lists(list1, list2, key1, key2):
        lookup = {row[key2]: row for row in list2}
        merged = []
        for row in list1:
            match = lookup.get(row[key1])
            if match:
                # append all list2 values except the key itself
                extras = [v for i, v in enumerate(match) if i != key2]
                merged.append(row + extras)
        return merged
    # print(setups[0])
    # print(trades[0])
    result = merge_lists(setups, trades, key1=19, key2=0)
    # print(result[0])

    return render_template('trades.html', data=result,
                           period=period, header=column_header, trades=trade_history_min,
                           rr=rr, entry_date=entry_date, growth=growth, total_setups=total_setups,
                           year=year, month=month, month_name=month_name, period_list=period_list, now=datetime.now())


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
    sort = request.args.get('sort', 0, type=int)
    direction = request.args.get('dir', 'asc')
    column_header = [['Name', 0], ['Month', 1], ['Win %', 7], ['Avg Win %', 10], ['Avg Loss %', 11],
                     ['Entry', 3], ['Exit', 4], ['Stop', 5], ['P/L Ratio', 6], ['Growth', 15], ['ID', 18]]
    try:
        with open(f'data/{period}_commodity_trades.csv', 'r') as f:
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
                           rr=rr, entry_date=entry_date, growth=growth, total_setups=total_setups,
                           year=year, month=month, period_list=period_list, month_name=month_name,
                           now=datetime.now(), sort=sort, dir=direction, sort_direction_symbol=sort_direction_symbol)


@app.route('/contact')
def contact_view():
    return render_template('contact.html', period_list=period_list, month_name='Trading Month')



if __name__ == '__main__':
    app.run()
