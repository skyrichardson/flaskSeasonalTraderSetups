from flask import Flask, render_template, request, url_for, redirect
import csv

app = Flask(__name__)

@app.route('/')
def index():
    # now = datetime.now()
    return redirect(url_for('hello_world', year=2026, month=4))
@app.route('/<int:year>/<int:month>')
def hello_world(year, month):
    period = f'{year}_{month:02d}'  # formats month as 2 digits e.g. 04
    trades = request.args.get('trades', '10')
    rr = request.args.get('rr', '0.1')
    entry_date = request.args.get('entry_date', '')
    column_header = ['Ticker', 'Win %', 'Avg Win %', 'Avg Loss %',
                     'Trades', 'Entry', 'Exit', 'Stop', 'P/L Ratio', 'ID']
    try:
        with open(f'data/{period}_long_mature_setups.csv', 'r') as f:
            reader = csv.reader(f)
            data = list(reader)
            data = [row for row in data if int(row[20]) >= int(trades)]
            data = [row for row in data if float(row[10]) >= (float(row[11]) * float(rr))]
            if entry_date:
                data = [row for row in data if row[3] == entry_date]
    except FileNotFoundError:
        data = []

    try:
        with open(f'data/{period}.csv', 'r') as f:
            reader = csv.reader(f)
            total_setups = list(reader)
    except FileNotFoundError:
        total_setups = []


    return render_template('index.html', data=data,
                           period=period, header=column_header, trades=trades,
                           rr=rr, entry_date=entry_date, total_setups=total_setups)


if __name__ == '__main__':
    app.run()
