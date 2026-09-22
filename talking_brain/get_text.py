# =====================================================================
# GET TEXT - download free text (millions of letters) for the brain
# =====================================================================
#
# This program downloads about 140 Wikipedia articles about money,
# trading, crypto and AI. It saves them in 3 big text files in the
# "data" folder:
#
#     wiki_finance.txt    wiki_crypto.txt    wiki_ai.txt
#
# Wikipedia text is free to use for learning (license: CC BY-SA).
#
# Run it in Google Colab. It needs the internet.
# Do NOT upload these big files to GitHub. They stay in Colab.
# You do not need them in GitHub. Only the brain file (brain.npz) goes there.
#
# WIKIPEDIA CAN SAY "SLOW DOWN" (error 429).
# This program is patient. It waits, and it tries again.
# Every article it downloads is kept in the folder "wiki_cache".
# If some articles are missing at the end, wait a few minutes and run
# this program again. It only downloads the missing ones.
#
# How to run:   python get_text.py
# Then run:     python step3_big_text.py
# =====================================================================

import json
import os
import re
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request

API = "https://en.wikipedia.org/w/api.php"
HEADERS = {
    "User-Agent": "VALE-talking-brain/1.0 "
                  "(https://github.com/valeri-Tauqueer-dot/VALE-backend; personal learning project)"
}

PAUSE = 1.2            # seconds to wait between articles (be kind to Wikipedia)
MAX_TRIES = 4          # how many times to try one article
BACKOFF_START = 8      # seconds to wait after "slow down" (then 16, then 32)
GIVE_UP_AFTER = 3      # stop if this many articles in a row fail

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_FOLDER = os.path.join(HERE, "data")
CACHE_FOLDER = os.path.join(HERE, "wiki_cache")

# ---------------------------------------------------------------------
# WHAT TO DOWNLOAD - you can add or remove article names
# ---------------------------------------------------------------------

GROUPS = {
    "wiki_finance.txt": [
        "Stock market", "Stock exchange", "Financial market", "Trader (finance)",
        "Day trading", "Technical analysis", "Fundamental analysis", "Candlestick chart",
        "Moving average", "Relative strength index", "Bollinger Bands", "MACD",
        "Support and resistance", "Trend following", "Market trend", "Bull market",
        "Bear market", "Market sentiment", "Market liquidity", "Volatility (finance)",
        "Bid-ask spread", "Slippage (finance)", "Order (exchange)", "Limit order",
        "Market order", "Stop order", "Leverage (finance)", "Margin (finance)",
        "Margin call", "Short (finance)", "Risk management", "Financial risk",
        "Risk-return spectrum", "Sharpe ratio", "Drawdown (economics)",
        "Diversification (finance)", "Modern portfolio theory", "Asset allocation",
        "Value at risk", "Backtesting", "Algorithmic trading", "High-frequency trading",
        "Quantitative analysis (finance)", "Efficient-market hypothesis",
        "Random walk hypothesis", "Behavioral economics", "Behavioral finance",
        "Loss aversion", "Herd behavior", "Fear of missing out", "Gambler's fallacy",
        "Confirmation bias", "Inflation", "Interest rate", "Central bank",
        "Federal Reserve", "Monetary policy", "Recession", "Bond (finance)",
        "Foreign exchange market", "Commodity market", "Futures contract",
        "Option (finance)", "Derivative (finance)", "Broker", "Stockbroker",
        "Financial regulation", "Securities fraud", "Ponzi scheme", "Pump and dump",
        "Market maker", "Market microstructure", "Order book", "Hedge (finance)",
        "Arbitrage", "Speculation", "Investment", "Compound interest",
        "Liquidity risk", "Dot-com bubble", "Economic bubble", "Stock market crash",
    ],
    "wiki_crypto.txt": [
        "Cryptocurrency", "Bitcoin", "Ethereum", "Blockchain", "Cryptocurrency exchange",
        "Cryptocurrency wallet", "Public-key cryptography", "Cryptographic hash function",
        "Proof of work", "Proof of stake", "Smart contract", "Decentralized finance",
        "Stablecoin", "Initial coin offering", "Digital currency",
        "Central bank digital currency", "Tether (cryptocurrency)", "Satoshi Nakamoto",
        "Non-fungible token", "Cryptocurrency bubble", "Bitcoin network",
        "Bitcoin scalability problem", "Dogecoin", "Litecoin",
        "Decentralized autonomous organization", "Regulation of cryptocurrencies",
        "Double-spending", "Merkle tree", "Digital signature", "Cryptocurrency and crime",
    ],
    "wiki_ai.txt": [
        "Artificial intelligence", "Machine learning", "Neural network (machine learning)",
        "Deep learning", "Language model", "Large language model",
        "Transformer (deep learning architecture)", "Backpropagation", "Gradient descent",
        "Overfitting", "Natural language processing", "Reinforcement learning",
        "Supervised learning", "Unsupervised learning", "Data science", "Statistics",
        "Probability", "Time series", "Regression analysis", "Bayesian inference",
        "Information theory", "Entropy (information theory)", "Cross-entropy",
        "Activation function", "Word embedding", "Recurrent neural network",
        "Attention (machine learning)", "Generative artificial intelligence",
        "Turing test", "History of artificial intelligence",
        "Ethics of artificial intelligence", "Perceptron",
    ],
}


def cache_path(title):
    name = re.sub(r"[^A-Za-z0-9]+", "_", title).strip("_")
    return os.path.join(CACHE_FOLDER, name + ".txt")


def get_article(title):
    """
    Download the plain text of one Wikipedia article.
    Returns (text, problem).
    text is "" if the article does not exist. problem is "" if all is well.
    """
    params = {
        "action": "query", "format": "json", "prop": "extracts",
        "explaintext": 1, "redirects": 1, "titles": title,
    }
    url = API + "?" + urllib.parse.urlencode(params)
    problem = ""
    for attempt in range(MAX_TRIES):
        try:
            request = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(request, timeout=30) as response:
                data = json.loads(response.read().decode("utf-8"))
            for page in data.get("query", {}).get("pages", {}).values():
                return page.get("extract", ""), ""
            return "", ""
        except urllib.error.HTTPError as error:
            if error.code in (429, 503):
                # Wikipedia says: slow down. So we wait, and we try again.
                wait = BACKOFF_START * (2 ** attempt)
                try:
                    wait = int(error.headers.get("Retry-After", wait))
                except (TypeError, ValueError):
                    pass
                wait = max(1, min(wait, 60))
                problem = "Wikipedia says: slow down (error " + str(error.code) + ")"
                if attempt < MAX_TRIES - 1:
                    print("      Wikipedia says: slow down. Waiting " + str(wait)
                          + " seconds, then trying again...", flush=True)
                    time.sleep(wait)
            else:
                return "", "error " + str(error.code)
        except Exception as error:
            problem = str(error)
            time.sleep(2)
    return "", problem


def clean(text):
    """Keep plain letters and signs. Remove the == heading == marks."""
    for old, new in [("\u2013", "-"), ("\u2014", "-"), ("\u2018", "'"), ("\u2019", "'"),
                     ("\u201c", '"'), ("\u201d", '"'), ("\u00a0", " ")]:
        text = text.replace(old, new)
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"^=+\s*(.*?)\s*=+\s*$", r"\1", text, flags=re.M)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def main():
    os.makedirs(DATA_FOLDER, exist_ok=True)
    os.makedirs(CACHE_FOLDER, exist_ok=True)

    failed_in_a_row = 0
    stopped = False

    # Step 1: download every article that we do not have yet.
    for file_name, titles in GROUPS.items():
        if stopped:
            break
        print("=== " + file_name + " ===")
        for title in titles:
            path = cache_path(title)
            if os.path.exists(path) and os.path.getsize(path) > 500:
                print(f"  have  {title}")
                continue

            text, problem = get_article(title)
            text = clean(text)
            if problem:
                failed_in_a_row += 1
                print(f"  FAIL  {title}   ({problem})", flush=True)
            elif len(text) < 500:
                failed_in_a_row = 0
                print(f"  skip  {title}   (no text)", flush=True)
            else:
                failed_in_a_row = 0
                with open(path, "w", encoding="utf-8") as f:
                    f.write(text)
                print(f"  ok    {title:45s} {len(text):8,d} letters", flush=True)

            if failed_in_a_row >= GIVE_UP_AFTER:
                print()
                print("Wikipedia is too busy right now, so I stop here.")
                print("Wait about 10 minutes, then run this program again.")
                print("It keeps every article that it already downloaded.")
                stopped = True
                break
            time.sleep(PAUSE)
        print()

    # Step 2: put the articles of each group in one big file.
    total_letters = 0
    total_articles = 0
    missing = 0
    for file_name, titles in GROUPS.items():
        parts = []
        for title in titles:
            path = cache_path(title)
            if os.path.exists(path) and os.path.getsize(path) > 500:
                with open(path, "r", encoding="utf-8") as f:
                    parts.append(f.read())
            else:
                missing += 1
        if parts:
            with open(os.path.join(DATA_FOLDER, file_name), "w", encoding="utf-8") as f:
                f.write("\n\n".join(parts) + "\n")
            letters = sum(len(p) for p in parts)
            total_letters += letters
            total_articles += len(parts)
            print(f"saved {file_name}: {len(parts)} articles, {letters:,d} letters")

    print()
    print(f"DONE. {total_articles} articles, {total_letters:,d} letters in total.")
    if missing and not stopped:
        print(f"{missing} articles are missing. Some may not exist, and some may have failed.")
        print("If you saw 'slow down' messages, wait 10 minutes and run this program again.")
        print("It only downloads the missing ones.")
    if total_letters < 100000 and not stopped:
        print()
        print("Almost nothing was downloaded. Copy the FAIL lines above and send them to me.")


if __name__ == "__main__":
    main()
