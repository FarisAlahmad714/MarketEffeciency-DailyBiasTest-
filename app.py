import matplotlib
matplotlib.use('Agg')
from flask import Flask, render_template
import requests
import pandas as pd
import mplfinance as mpf
import os

app = Flask(__name__)

os.makedirs("static/crypto", exist_ok=True)

def fetch_coingecko_data(asset_id="bitcoin", days=30):
    url = f"https://api.coingecko.com/api/v3/coins/{asset_id}/market_chart?vs_currency=usd&days={days}&interval=daily"
    print(f"Fetching data from: {url}")
    response = requests.get(url)
    if response.status_code == 200:
        prices = response.json()["prices"]
        print(f"Received {len(prices)} price points")
        if not prices:
            print("No price data returned")
            return None
        data = pd.DataFrame(prices, columns=["Date", "Close"])
        data["Date"] = pd.to_datetime(data["Date"], unit="ms")
        data.set_index("Date", inplace=True)
        data["Open"] = data["Close"].shift(1)
        data["High"] = data["Close"] * 1.02
        data["Low"] = data["Close"] * 0.98
        data = data.dropna()
        print(f"Processed data shape: {data.shape}")
        return data
    else:
        print(f"Error fetching data: {response.status_code} - {response.text}")
        return None

def generate_charts(data, date_n, asset="btc"):
    date_n_plus_1 = data.index[data.index > date_n][0]
    setup_data = data.loc[:date_n][-30:]
    outcome_data = data.loc[:date_n_plus_1][-30:]
    
    setup_path = f"static/crypto/{asset}_{date_n.strftime('%Y-%m-%d')}_setup.png"
    outcome_path = f"static/crypto/{asset}_{date_n_plus_1.strftime('%Y-%m-%d')}_outcome.png"
    
    mpf.plot(setup_data, type="candle", style="charles", figscale=1.5, savefig=setup_path)
    mpf.plot(outcome_data, type="candle", style="charles", figscale=1.5, savefig=outcome_path)
    return setup_path, outcome_path

def get_sentiment(data, date_n):
    date_n_plus_1 = data.index[data.index > date_n][0]
    if data.loc[date_n_plus_1, "Close"] > data.loc[date_n, "Close"]:
        return "Bullish"
    return "Bearish"

def prepare_test_data(asset="btc", days=30, num_tests=5):
    btc_data = fetch_coingecko_data(asset, days)
    if btc_data is None or btc_data.empty:
        print("No valid data to prepare tests")
        return []
    
    print(f"Available dates: {btc_data.index.tolist()}")
    test_dates = btc_data.index[-15::3][:num_tests]
    print(f"Selected test dates: {test_dates}")
    btc_tests = []
    
    for date_n in test_dates:
        print(f"Generating charts for {date_n}")
        setup_path, outcome_path = generate_charts(btc_data, date_n, asset)
        sentiment = get_sentiment(btc_data, date_n)
        btc_tests.append({
            "setup": setup_path,
            "outcome": outcome_path,
            "correct": sentiment
        })
    
    print(f"Prepared {len(btc_tests)} tests")
    return btc_tests

BTC_TESTS = prepare_test_data("btc", 30, 5)

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/daily_bias/btc")
def daily_bias_btc():
    if BTC_TESTS:
        test = BTC_TESTS[0]
        return f"""
        Bitcoin Bias Test (Sample):<br>
        Setup Chart: <img src='/{test['setup']}' width='800'><br>
        Outcome Chart: <img src='/{test['outcome']}' width='800'><br>
        Correct Sentiment: {test['correct']}<br>
        Total Tests Prepared: {len(BTC_TESTS)}
        """
    return "Failed to prepare Bitcoin test data."

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)