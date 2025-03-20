import matplotlib
matplotlib.use('Agg')
from flask import Flask, render_template, request
import requests
import pandas as pd
import mplfinance as mpf
import os
import random
import time
import pickle  # Added for caching

app = Flask(__name__)

os.makedirs("static/crypto", exist_ok=True)

def fetch_coingecko_data(asset_id="bitcoin", days=365):
    cache_file = f"cache/{asset_id}_data.pkl"
    os.makedirs("cache", exist_ok=True)
    
    # Check if cached data exists
    if os.path.exists(cache_file):
        with open(cache_file, 'rb') as f:
            data = pickle.load(f)
        print(f"Loaded {asset_id} data from cache")
        return data
    
    # Fetch from API if no cache
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
        data = data.dropna()
        # Save to cache
        with open(cache_file, 'wb') as f:
            pickle.dump(data, f)
        print(f"Saved {asset_id} data to cache")
        return data
    else:
        print(f"Error fetching {asset_id} data: {response.status_code} - {response.text}")
        return None

def generate_charts(data, date_n, asset):
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

def prepare_test_data(asset_id, asset_symbol, days=365, num_tests=5):
    data = fetch_coingecko_data(asset_id, days)
    if data is None or data.empty:
        print(f"No valid data to prepare tests for {asset_symbol}")
        return []
    
    test_dates = random.sample(list(data.index[:-1]), num_tests)
    test_dates.sort()
    print(f"{asset_symbol} selected test dates: {test_dates}")
    tests = []
    
    for date_n in test_dates:
        setup_path, outcome_path = generate_charts(data, date_n, asset_symbol.lower())
        sentiment = get_sentiment(data, date_n)
        ohlc = data.loc[date_n]
        tests.append({
            "setup": setup_path,
            "outcome": outcome_path,
            "correct": sentiment,
            "open": ohlc["Open"],
            "high": ohlc["High"],
            "low": ohlc["Low"],
            "close": ohlc["Close"]
        })
    
    print(f"Prepared {len(tests)} tests for {asset_symbol}")
    return tests

# Prepare tests with delays to avoid rate limits
BTC_TESTS = prepare_test_data("bitcoin", "btc")
time.sleep(3)  # Increased to 3 seconds
ETH_TESTS = prepare_test_data("ethereum", "eth")
time.sleep(3)
SOL_TESTS = prepare_test_data("solana", "sol")
time.sleep(3)
BNB_TESTS = prepare_test_data("binancecoin", "bnb")

@app.route("/")
def home():
    return render_template("index.html")

def create_bias_route(asset_symbol, asset_tests, asset_name):
    endpoint_name = f"bias_test_{asset_symbol}"
    @app.route(f"/daily_bias/{asset_symbol}", methods=["GET", "POST"], endpoint=endpoint_name)
    def bias_test():
        if not asset_tests:
            return f"Failed to prepare {asset_name} test data."
        
        if request.method == "POST":
            score = 0
            results = []
            for i, test in enumerate(asset_tests):
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
            return render_template("results.html", score=score, total=len(asset_tests), results=results, 
                                 asset=asset_name, asset_symbol=asset_symbol)
        
        tests = asset_tests.copy()
        random.shuffle(tests)
        print(f"Serving {asset_name} tests with setup paths: {[test['setup'] for test in tests]}")
        return render_template("daily_bias.html", questions=tests, asset=asset_name, asset_symbol=asset_symbol)
    return bias_test

create_bias_route("btc", BTC_TESTS, "Bitcoin")
create_bias_route("eth", ETH_TESTS, "Ethereum")
create_bias_route("sol", SOL_TESTS, "Solana")
create_bias_route("bnb", BNB_TESTS, "Binance Coin")

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)