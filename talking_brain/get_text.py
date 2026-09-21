# =====================================================================
# GET TEXT - download free text (millions of letters) for the brain
# =====================================================================
#
# This program downloads about 150 Wikipedia articles about money,
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
# If an article cannot be downloaded, the program skips it and goes on.
#
# How to run:   python get_text.py
# Then run:     python step3_big_text.py
# =====================================================================

import json
import os
import re
import time
import unicodedata
import urllib.parse
import urllib.request

API = "https://en.wikipedia.org/w/api.php"
HEADERS = {"User-Agent": "VALE-talking-brain/1.0 (personal learning project)"}
PAUSE = 0.3          # seconds to wait between downloads (be kind to Wikipedia)

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_FOLDER = os.path.join(HERE, "data")

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


def get_article(title):
    """Download the plain text of one Wikipedia article. Returns '' if it fails."""
    params = {
        "action": "query", "format": "json", "prop": "extracts",
        "explaintext": 1, "redirects": 1, "titles": title,
    }
    url = API + "?" + urllib.parse.urlencode(params)
    last_error = ""
    for attempt in range(2):
        try:
            request = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(request, timeout=30) as response:
                data = json.loads(response.read().decode("utf-8"))
            for page in data.get("query", {}).get("pages", {}).values():
                return page.get("extract", "")
            return ""
        except Exception as error:
            last_error = str(error)
            time.sleep(1)
    print("      problem: " + last_error)
    return ""


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
    total_letters = 0
    total_articles = 0

    for file_name, titles in GROUPS.items():
        print("=== " + file_name + " ===")
        parts = []
        for title in titles:
            text = clean(get_article(title))
            if len(text) < 500:
                print(f"  skip  {title}")
            else:
                parts.append(text)
                print(f"  ok    {title:45s} {len(text):8,d} letters", flush=True)
            time.sleep(PAUSE)

        if parts:
            path = os.path.join(DATA_FOLDER, file_name)
            with open(path, "w", encoding="utf-8") as f:
                f.write("\n\n".join(parts) + "\n")
            letters = sum(len(p) for p in parts)
            total_letters += letters
            total_articles += len(parts)
            print(f"  saved {file_name}: {len(parts)} articles, {letters:,d} letters")
        print()

    print(f"DONE. {total_articles} articles, {total_letters:,d} letters in total.")
    if total_letters < 100000:
        print()
        print("Almost nothing was downloaded. Is Colab connected to the internet?")
        print("Copy the 'problem:' lines above and send them to me.")


if __name__ == "__main__":
    main()
