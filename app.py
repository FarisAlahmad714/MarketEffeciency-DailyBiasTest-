import matplotlib
matplotlib.use('Agg')
from flask import Flask, render_template, request
import requests
import pandas as pd
import mplfinance as mpf
import os
import random

app = Flask(__name__)

os.makedirs("static/crypto", exist_ok=True)

def fetch_coingecko_data(asset_id="bitcoin", days=365):  # Changed to 365 days
    url = f"https://api.coingecko.com/api/v3/coins/{asset_id}/market_chart?vs_currency=usd&days={days}&interval=daily"
    response = requests.get(url)
    if response.status_code == 200:
        prices = response.json()["prices"]
        data = pd.DataFrame(prices, columns=["Date", "Close"])
        data["Date"] = pd.to_datetime(data["Date"], unit="ms")
        data.set_index("Date", inplace=True)
        data["Open"] = data["Close"].shift(1)
        data["High"] = data["Close"] * 1.02
        data["Low"] = data["Close"] * 0.98
        return data.dropna()
    else:
        print(f"Error fetching data: {response.status_code} - {response.text}")
        return None

def generate_charts(data, date_n, asset="btc"):
    date_n_plus_1 = data.index[data.index > date_n][0]
    setup_data = data.loc[:date_n][-30:]
    outcome_data = data.loc[:date_n_plus_1][-30:]
    
    setup_path = f"crypto/{asset}_{date_n.strftime('%Y-%m-%d')}_setup.png"
    outcome_path = f"crypto/{asset}_{date_n_plus_1.strftime('%Y-%m-%d')}_outcome.png"
    full_setup_path = f"static/{setup_path}"
    full_outcome_path = f"static/{outcome_path}"
    
    mpf.plot(setup_data, type="candle", style="charles", figscale=1.5, savefig=full_setup_path)
    mpf.plot(outcome_data, type="candle", style="charles", figscale=1.5, savefig=full_outcome_path)
    
    return setup_path, outcome_path

def get_sentiment(data, date_n):
    date_n_plus_1 = data.index[data.index > date_n][0]
    if data.loc[date_n_plus_1, "Close"] > data.loc[date_n, "Close"]:
        return "Bullish"
    return "Bearish"

def prepare_test_data(asset_id="bitcoin", days=365, num_tests=5):  # Changed to 365 days
    btc_data = fetch_coingecko_data(asset_id, days)
    if btc_data is None or btc_data.empty:
        print("No valid data to prepare tests")
        return []
    
    # Randomly sample 5 dates from the full range, excluding the last day to ensure N+1 exists
    test_dates = random.sample(list(btc_data.index[:-1]), num_tests)
    test_dates.sort()  # Sort for consistency in display
    print(f"Selected test dates: {test_dates}")
    btc_tests = []
    
    for date_n in test_dates:
        setup_path, outcome_path = generate_charts(btc_data, date_n, "btc")
        sentiment = get_sentiment(btc_data, date_n)
        ohlc = btc_data.loc[date_n]
        btc_tests.append({
            "setup": setup_path,
            "outcome": outcome_path,
            "correct": sentiment,
            "open": ohlc["Open"],
            "high": ohlc["High"],
            "low": ohlc["Low"],
            "close": ohlc["Close"]
        })
    
    print(f"Prepared {len(btc_tests)} tests")
    return btc_tests

BTC_TESTS = prepare_test_data("bitcoin", 365, 5)  # Updated to 365 days

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/daily_bias/btc", methods=["GET", "POST"])
def daily_bias_btc():
    if not BTC_TESTS:
        return "Failed to prepare Bitcoin test data."
    
    if request.method == "POST":
        score = 0
        results = []
        for i, test in enumerate(BTC_TESTS):
            user_answer = request.form.get(f"prediction_{i}")
            correct_answer = test["correct"]
            if user_answer == correct_answer:
                score += 1
            results.append({
                "setup": test["setup"],
                "outcome": test["outcome"],
                "user_answer": user_answer,
                "correct_answer": correct_answer,
                "open": test["open"],
                "high": test["high"],
                "low": test["low"],
                "close": test["close"]
            })
        return render_template("results.html", score=score, total=len(BTC_TESTS), results=results)
    
    tests = BTC_TESTS.copy()
    random.shuffle(tests)
    print(f"Serving tests with setup paths: {[test['setup'] for test in tests]}")
    return render_template("daily_bias.html", questions=tests)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)