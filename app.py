import matplotlib
matplotlib.use('Agg')
from flask import Flask, render_template, request
import requests
import pandas as pd
import mplfinance as mpf
import os
import random
import time
import pickle

app = Flask(__name__)

os.makedirs("static/crypto", exist_ok=True)
os.makedirs("static/equities", exist_ok=True)

# Fetch data for cryptocurrencies using CoinGecko
def fetch_coingecko_data(asset_id="bitcoin", days=365):
    cache_file = f"cache/crypto_{asset_id}_data.pkl"
    os.makedirs("cache", exist_ok=True)
    
    if os.path.exists(cache_file):
        with open(cache_file, 'rb') as f:
            data = pickle.load(f)
        print(f"Loaded {asset_id} data from cache (CoinGecko)")
        return data
    
    url = f"https://api.coingecko.com/api/v3/coins/{asset_id}/market_chart?vs_currency=usd&days={days}&interval=daily"
    response = requests.get(url)
    if response.status_code == 200:
        prices = response.json()["prices"]
        data = pd.DataFrame(prices, columns=["Date", "Close"])
        data["Date"] = pd.to_datetime(data["Date"], unit="ms")
        data.set_index("Date", inplace=True)
        data["Open"] = data["Close"].shift(1)
        data["High"] = data["Close"] * 1.02  # Simulate High
        data["Low"] = data["Close"] * 0.98   # Simulate Low
        data = data.dropna()
        with open(cache_file, 'wb') as f:
            pickle.dump(data, f)
        print(f"Saved {asset_id} data to cache (CoinGecko)")
        return data
    else:
        print(f"Error fetching {asset_id} data (CoinGecko): {response.status_code} - {response.text}")
        return None

# Fetch data for equities using Alpha Vantage
def fetch_alpha_vantage_data(symbol="NVDA", days=365):
    cache_file = f"cache/equity_{symbol}_data.pkl"
    os.makedirs("cache", exist_ok=True)
    
    if os.path.exists(cache_file):
        with open(cache_file, 'rb') as f:
            data = pickle.load(f)
        print(f"Loaded {symbol} data from cache (Alpha Vantage)")
        return data
    
    api_key = "QRL7874F7OJAGJHY"
    url = f"https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={symbol}&outputsize=full&apikey={api_key}"
    response = requests.get(url)
    if response.status_code == 200:
        json_data = response.json()
        if "Time Series (Daily)" not in json_data:
            print(f"Error fetching {symbol} data (Alpha Vantage): {json_data.get('Error Message', 'Unknown error')}")
            return None
        
        time_series = json_data["Time Series (Daily)"]
        data = pd.DataFrame.from_dict(time_series, orient="index")
        data = data.rename(columns={
            "1. open": "Open",
            "2. high": "High",
            "3. low": "Low",
            "4. close": "Close",
            "5. volume": "Volume"
        })
        data.index = pd.to_datetime(data.index)
        data = data.astype(float)
        data = data.sort_index()
        data = data.tail(days)
        with open(cache_file, 'wb') as f:
            pickle.dump(data, f)
        print(f"Saved {symbol} data to cache (Alpha Vantage)")
        return data
    else:
        print(f"Error fetching {symbol} data (Alpha Vantage): {response.status_code} - {response.text}")
        return None

def generate_charts(data, date_n, asset, asset_type="crypto"):
    date_n_plus_1 = data.index[data.index > date_n][0]
    setup_data = data.loc[:date_n][-30:]
    outcome_data = data.loc[:date_n_plus_1][-30:]
    
    setup_path = f"{asset_type}/{asset}_{date_n.strftime('%Y-%m-%d')}_setup.png"
    outcome_path = f"{asset_type}/{asset}_{date_n_plus_1.strftime('%Y-%m-%d')}_outcome.png"
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

def prepare_test_data(fetch_func, asset_id, asset_symbol, asset_type="crypto", days=365, num_tests=5):
    data = fetch_func(asset_id, days)
    if data is None or data.empty:
        print(f"No valid data to prepare tests for {asset_symbol}")
        return []
    
    test_dates = random.sample(list(data.index[:-1]), num_tests)
    test_dates.sort()
    print(f"{asset_symbol} selected test dates: {test_dates}")
    tests = []
    
    for date_n in test_dates:
        setup_path, outcome_path = generate_charts(data, date_n, asset_symbol.lower(), asset_type)
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

# Prepare tests for cryptocurrencies (CoinGecko)
BTC_TESTS = prepare_test_data(fetch_coingecko_data, "bitcoin", "btc", "crypto")
time.sleep(3)
ETH_TESTS = prepare_test_data(fetch_coingecko_data, "ethereum", "eth", "crypto")
time.sleep(3)
SOL_TESTS = prepare_test_data(fetch_coingecko_data, "solana", "sol", "crypto")
time.sleep(3)
BNB_TESTS = prepare_test_data(fetch_coingecko_data, "binancecoin", "bnb", "crypto")
time.sleep(3)

# Prepare tests for equities (Alpha Vantage)
NVDA_TESTS = prepare_test_data(fetch_alpha_vantage_data, "NVDA", "nvda", "equities")
time.sleep(3)
AAPL_TESTS = prepare_test_data(fetch_alpha_vantage_data, "AAPL", "aapl", "equities")
time.sleep(3)
TSLA_TESTS = prepare_test_data(fetch_alpha_vantage_data, "TSLA", "tsla", "equities")
time.sleep(3)
GLD_TESTS = prepare_test_data(fetch_alpha_vantage_data, "GLD", "gld", "equities")

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

# Crypto routes (CoinGecko)
create_bias_route("btc", BTC_TESTS, "Bitcoin")
create_bias_route("eth", ETH_TESTS, "Ethereum")
create_bias_route("sol", SOL_TESTS, "Solana")
create_bias_route("bnb", BNB_TESTS, "Binance Coin")

# Equity routes (Alpha Vantage)
create_bias_route("nvda", NVDA_TESTS, "Nvidia")
create_bias_route("aapl", AAPL_TESTS, "Apple")
create_bias_route("tsla", TSLA_TESTS, "Tesla")
create_bias_route("gld", GLD_TESTS, "Gold")

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)