"""
VALE search engine - SOURCE registry (the list of where to look; not the storage shelves).

The registry is a LIST OF WHERE TO LOOK. It does not store the data itself.
Each source is one small row: a name, a link (or a link pattern with {query}, {start},
{end} ...), its kind (rss, atom, api_json, csv), topic tags, and a license note.

What this file gives the other parts of VALE:
  detect_tags(text)         which topics a text is about (gold, oil, crypto, war, ...)
  pick(tags, ...)           the best sources for those topics
  plan(question)            tags + sources for a user question (the DRIVER uses this)
  rss_feeds()               the list of feeds for the collector
  render_url(source, ...)   fills a link pattern, with safe quoting

'verified' = True means we saw it work. All other rows are real places to try; the collector
skips a broken link and shows it in the log, and then we fix or disable that row.

Rules we follow: only public data, headlines + short text + link (never whole articles),
obey each site's terms, polite speed. Telegram is NOT used (its terms ban scraping and AI use).
"""
from __future__ import annotations

import os
import re
import string
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Tuple
from urllib.parse import quote


# ----------------------------------------------------------------------
# topics
# ----------------------------------------------------------------------
TOPIC_WORDS: Dict[str, List[str]] = {
    "gold": ["gold", "bullion", "xauusd"],
    "silver": ["silver"],
    "metals": ["copper", "aluminium", "aluminum", "nickel", "zinc", "lithium", "iron ore", "steel", "platinum", "palladium"],
    "oil": ["oil", "crude", "brent", "wti", "opec", "petrol", "diesel", "refinery", "refineries"],
    "gas": ["natural gas", "lng", "gas prices", "pipeline"],
    "crypto": ["bitcoin", "btc", "ethereum", "ether", "eth", "crypto", "cryptocurrency", "blockchain", "stablecoin",
               "solana", "xrp", "dogecoin", "binance", "defi", "altcoin"],
    "forex": ["dollar", "usd", "rupee", "inr", "euro", "eur", "yen", "jpy", "pound sterling", "currency", "currencies",
              "forex", "exchange rate", "yuan"],
    "stocks": ["stock", "stocks", "share price", "shares", "sensex", "nifty", "nasdaq", "dow jones", "s&p 500", "s&p",
               "equity", "equities", "ipo", "earnings", "bull market", "bear market", "rally", "sell-off", "selloff"],
    "bonds": ["bond", "bonds", "yield", "yields", "treasury", "treasuries", "gilt", "gilts"],
    "rates": ["interest rate", "interest rates", "rate cut", "rate hike", "repo rate", "central bank", "the fed",
              "federal reserve", "monetary policy", "rbi", "ecb", "bank of england", "bank of japan"],
    "economy": ["inflation", "gdp", "unemployment", "jobs report", "recession", "economy", "economic growth",
                "consumer prices", "cpi", "pmi", "deficit", "budget"],
    "trade": ["tariff", "tariffs", "export", "exports", "import", "imports", "trade deal", "trade war", "sanction", "sanctions"],
    "food": ["wheat", "rice", "sugar", "fish", "fishing", "crop", "crops", "harvest", "food price", "coffee", "cocoa",
             "cotton", "soybean", "corn", "palm oil", "fertiliser", "fertilizer"],
    "weather": ["monsoon", "drought", "flood", "floods", "hurricane", "cyclone", "heatwave", "heat wave", "el nino",
                "la nina", "rainfall", "typhoon", "storm"],
    "war": ["war", "missile", "invasion", "ceasefire", "attack", "conflict", "military", "troops", "airstrike", "terror"],
    "politics": ["election", "elections", "prime minister", "president", "parliament", "assassination", "coup", "protest", "protests"],
    "disaster": ["earthquake", "tsunami", "wildfire", "landslide", "eruption"],
    "tech": ["semiconductor", "chip", "chips", "artificial intelligence", "generative ai", "chatgpt", "openai", "nvidia", "tsmc", "software"],
    "health": ["outbreak", "pandemic", "virus", "epidemic", "bird flu", "vaccine"],
    "energy": ["electricity", "power grid", "solar", "wind power", "coal", "nuclear", "renewable"],
}

_TOPIC_RX: Dict[str, "re.Pattern[str]"] = {}
for _tag, _words in TOPIC_WORDS.items():
    _parts = [re.escape(w.strip()) for w in _words]
    # whole words only, so "rice" does not match "price" and "war" does not match "toward"
    _TOPIC_RX[_tag] = re.compile(r"(?<![a-z0-9])(?:" + "|".join(_parts) + r")(?:s|es)?(?![a-z0-9])", re.IGNORECASE)


def analyze(text: str) -> Dict[str, List[str]]:
    """Return {tag: [matched words]} for a text."""
    found: Dict[str, List[str]] = {}
    for tag, rx in _TOPIC_RX.items():
        hits = [m.group(0).lower() for m in rx.finditer(text or "")]
        if hits:
            found[tag] = sorted(set(hits))
    return found


def detect_tags(text: str) -> List[str]:
    return list(analyze(text).keys())


# ----------------------------------------------------------------------
# sources
# ----------------------------------------------------------------------
@dataclass(frozen=True)
class Source:
    id: str
    name: str
    group: str
    kind: str                      # rss | atom | api_json | csv
    url: str                       # may contain {query} {start} {end} {key} ...
    tags: Tuple[str, ...]
    note: str = "Headlines only; check terms"
    verified: bool = False         # True = we saw it work
    enabled: bool = True
    parser: str = ""               # name of the reader (implemented in live_fetch.py)
    needs_key: str = ""            # name of the secret that must be set (e.g. FRED_API_KEY)
    params: Tuple[str, ...] = field(default=(), compare=False)


def _params_of(url: str) -> Tuple[str, ...]:
    names = []
    for _, field_name, _, _ in string.Formatter().parse(url):
        if field_name and field_name not in names:
            names.append(field_name)
    return tuple(names)


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def _s(name, group, kind, url, tags, note="Headlines only; check terms", verified=False, parser="", needs_key="") -> Source:
    return Source(
        id=_slug(name), name=name, group=group, kind=kind, url=url,
        tags=tuple(tags), note=note, verified=verified, parser=parser, needs_key=needs_key,
        params=_params_of(url),
    )


NEWS = "News"
GOV = "Central banks and government"
SCI = "Weather, disasters and science"
API = "Data and search APIs"

SOURCES: List[Source] = [
    # ---- already running and seen working ----
    _s("BBC Business", NEWS, "rss", "https://feeds.bbci.co.uk/news/business/rss.xml", ["news", "business", "world"], verified=True),
    _s("BBC World", NEWS, "rss", "https://feeds.bbci.co.uk/news/world/rss.xml", ["news", "world", "war", "politics"], verified=True),
    _s("Economic Times Markets", NEWS, "rss", "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms", ["news", "india", "stocks"], verified=True),
    _s("US Federal Reserve", GOV, "rss", "https://www.federalreserve.gov/feeds/press_all.xml", ["central_bank", "rates", "economy", "us"], note="Public domain", verified=True),
    _s("Reserve Bank of India", GOV, "rss", "https://www.rbi.org.in/pressreleases_rss.xml", ["central_bank", "rates", "economy", "india"], note="Public", verified=True),

    # ---- world and business news (RSS, not yet seen working) ----
    _s("BBC Technology", NEWS, "rss", "https://feeds.bbci.co.uk/news/technology/rss.xml", ["news", "tech"]),
    _s("BBC India", NEWS, "rss", "https://feeds.bbci.co.uk/news/world/asia/india/rss.xml", ["news", "india", "world"]),
    _s("BBC Middle East", NEWS, "rss", "https://feeds.bbci.co.uk/news/world/middle_east/rss.xml", ["news", "war", "oil", "world"]),
    _s("BBC Africa", NEWS, "rss", "https://feeds.bbci.co.uk/news/world/africa/rss.xml", ["news", "world"]),
    _s("BBC Europe", NEWS, "rss", "https://feeds.bbci.co.uk/news/world/europe/rss.xml", ["news", "world", "war"]),
    _s("BBC US and Canada", NEWS, "rss", "https://feeds.bbci.co.uk/news/world/us_and_canada/rss.xml", ["news", "world", "us"]),
    _s("BBC Latin America", NEWS, "rss", "https://feeds.bbci.co.uk/news/world/latin_america/rss.xml", ["news", "world"]),
    _s("BBC Science and Environment", NEWS, "rss", "https://feeds.bbci.co.uk/news/science_and_environment/rss.xml", ["news", "weather", "disaster"]),
    _s("The Guardian World", NEWS, "rss", "https://www.theguardian.com/world/rss", ["news", "world", "politics", "war"]),
    _s("The Guardian Business", NEWS, "rss", "https://www.theguardian.com/business/rss", ["news", "business", "economy"]),
    _s("NPR Business", NEWS, "rss", "https://feeds.npr.org/1006/rss.xml", ["news", "business", "us"]),
    _s("NPR World", NEWS, "rss", "https://feeds.npr.org/1004/rss.xml", ["news", "world"]),
    _s("Al Jazeera", NEWS, "rss", "https://www.aljazeera.com/xml/rss/all.xml", ["news", "world", "war", "politics"]),
    _s("DW", NEWS, "rss", "https://rss.dw.com/rdf/rss-en-all", ["news", "world", "europe"]),
    _s("New York Times Business", NEWS, "rss", "https://rss.nytimes.com/services/xml/rss/nyt/Business.xml", ["news", "business", "us"]),
    _s("New York Times World", NEWS, "rss", "https://rss.nytimes.com/services/xml/rss/nyt/World.xml", ["news", "world"]),
    _s("CNBC Business", NEWS, "rss", "https://www.cnbc.com/id/10001147/device/rss/rss.html", ["news", "business", "stocks"]),
    _s("CNBC Top News", NEWS, "rss", "https://www.cnbc.com/id/100003114/device/rss/rss.html", ["news", "business", "stocks"]),
    _s("MarketWatch Top Stories", NEWS, "rss", "https://feeds.content.dowjones.io/public/rss/mw_topstories", ["news", "stocks", "business"]),
    _s("Yahoo Finance", NEWS, "rss", "https://finance.yahoo.com/news/rssindex", ["news", "stocks", "business"]),
    _s("Japan Times", NEWS, "rss", "https://www.japantimes.co.jp/feed/", ["news", "asia", "world"]),
    _s("The Straits Times Business", NEWS, "rss", "https://www.straitstimes.com/news/business/rss.xml", ["news", "asia", "business"]),
    _s("Dawn Pakistan", NEWS, "rss", "https://www.dawn.com/feeds/home", ["news", "asia", "world"]),
    _s("Arab News", NEWS, "rss", "https://www.arabnews.com/rss.xml", ["news", "oil", "world"]),
    _s("AllAfrica", NEWS, "rss", "https://allafrica.com/tools/headlines/rdf/latest/headlines.rdf", ["news", "africa", "world"]),

    # ---- India ----
    _s("Economic Times Economy", NEWS, "rss", "https://economictimes.indiatimes.com/news/economy/rssfeeds/1373380680.cms", ["news", "india", "economy"]),
    _s("Economic Times Top Stories", NEWS, "rss", "https://economictimes.indiatimes.com/rssfeedstopstories.cms", ["news", "india", "business"]),
    _s("Mint Markets", NEWS, "rss", "https://www.livemint.com/rss/markets", ["news", "india", "stocks"]),
    _s("Mint Economy", NEWS, "rss", "https://www.livemint.com/rss/economy", ["news", "india", "economy"]),
    _s("Business Standard Markets", NEWS, "rss", "https://www.business-standard.com/rss/markets-106.rss", ["news", "india", "stocks"]),
    _s("Moneycontrol Latest News", NEWS, "rss", "https://www.moneycontrol.com/rss/latestnews.xml", ["news", "india", "stocks"]),
    _s("Moneycontrol Market Reports", NEWS, "rss", "https://www.moneycontrol.com/rss/marketreports.xml", ["news", "india", "stocks"]),
    _s("Financial Express", NEWS, "rss", "https://www.financialexpress.com/feed/", ["news", "india", "business"]),
    _s("The Hindu BusinessLine", NEWS, "rss", "https://www.thehindubusinessline.com/feeder/default.rss", ["news", "india", "business"]),
    _s("The Hindu Business", NEWS, "rss", "https://www.thehindu.com/business/feeder/default.rss", ["news", "india", "business"]),
    _s("Hindustan Times Business", NEWS, "rss", "https://www.hindustantimes.com/feeds/rss/business/rssfeed.xml", ["news", "india", "business"]),
    _s("Times of India Business", NEWS, "rss", "https://timesofindia.indiatimes.com/rssfeeds/1898055.cms", ["news", "india", "business"]),
    _s("Indian Express Business", NEWS, "rss", "https://indianexpress.com/section/business/feed/", ["news", "india", "business"]),
    _s("PIB India", GOV, "rss", "https://pib.gov.in/RssMain.aspx?ModId=6&Lang=1&Regid=3", ["government", "india", "economy"], note="Public"),

    # ---- central banks and government ----
    _s("US Federal Reserve Monetary Policy", GOV, "rss", "https://www.federalreserve.gov/feeds/press_monetary.xml", ["central_bank", "rates", "us"], note="Public domain"),
    _s("ECB Press", GOV, "rss", "https://www.ecb.europa.eu/rss/press.xml", ["central_bank", "rates", "europe"], note="Free (credit)"),
    _s("Bank of England News", GOV, "rss", "https://www.bankofengland.co.uk/rss/news", ["central_bank", "rates", "uk"], note="Free"),
    _s("RBI Notifications", GOV, "rss", "https://www.rbi.org.in/notifications_rss.xml", ["central_bank", "rates", "india"], note="Public"),
    _s("IMF News", GOV, "rss", "https://www.imf.org/en/News/rss?language=eng", ["economy", "government", "world"], note="Check terms"),
    _s("SEC Press Releases", GOV, "rss", "https://www.sec.gov/news/pressreleases.rss", ["government", "stocks", "us"], note="Public domain"),
    _s("CFTC Press Releases", GOV, "rss", "https://www.cftc.gov/RSS/RSSGP/rssgp.xml", ["government", "us", "oil", "gold"], note="Public domain"),
    _s("EIA Today in Energy", GOV, "rss", "https://www.eia.gov/rss/todayinenergy.xml", ["oil", "gas", "energy", "us"], note="Public domain"),

    # ---- weather, disasters, health, science ----
    _s("USGS Significant Earthquakes (week)", SCI, "atom", "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/significant_week.atom", ["disaster", "weather"], note="Public domain"),
    _s("GDACS Disaster Alerts", SCI, "rss", "https://www.gdacs.org/xml/rss.xml", ["disaster", "weather", "world"], note="Check terms"),
    _s("ReliefWeb Updates", SCI, "rss", "https://reliefweb.int/updates/rss.xml", ["disaster", "war", "food", "world"], note="Check terms"),
    _s("NOAA National Hurricane Center", SCI, "rss", "https://www.nhc.noaa.gov/index-at.xml", ["weather", "disaster"], note="Public domain"),
    _s("WHO Disease Outbreak News", SCI, "rss", "https://www.who.int/feeds/entity/csr/don/en/rss.xml", ["health", "world"], note="Check terms"),
    _s("arXiv Quantitative Finance", SCI, "rss", "https://rss.arxiv.org/rss/q-fin", ["research", "stocks", "economy"], note="Free"),

    # ---- crypto, energy, metals, tech news ----
    _s("CoinDesk", NEWS, "rss", "https://www.coindesk.com/arc/outboundfeeds/rss/", ["news", "crypto"]),
    _s("Cointelegraph", NEWS, "rss", "https://cointelegraph.com/rss", ["news", "crypto"]),
    _s("OilPrice.com", NEWS, "rss", "https://oilprice.com/rss/main", ["news", "oil", "gas", "energy"]),
    _s("Mining.com", NEWS, "rss", "https://www.mining.com/feed/", ["news", "gold", "silver", "metals"]),
    _s("TechCrunch", NEWS, "rss", "https://techcrunch.com/feed/", ["news", "tech"]),

    # ---- APIs that answer a question for a topic or a date range (readers come in live_fetch.py) ----
    _s("GDELT Doc Search", API, "api_json", "https://api.gdeltproject.org/api/v2/doc/doc?query={query}&mode=artlist&maxrecords=25&format=json",
       ["news", "world", "war", "politics", "oil", "food", "economy"], note="Free", parser="gdelt_doc"),
    _s("Wikipedia Search", API, "api_json", "https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={query}&format=json&srlimit=10",
       ["history", "knowledge"], note="Free (credit)", parser="wikipedia_search"),
    _s("Wikidata Search", API, "api_json", "https://www.wikidata.org/w/api.php?action=wbsearchentities&search={query}&language=en&format=json",
       ["knowledge"], note="Public domain", parser="wikidata_search"),
    _s("arXiv Search", API, "atom", "https://export.arxiv.org/api/query?search_query=all:{query}&max_results=10",
       ["research"], note="Free", parser="atom_entries"),
    _s("OpenAlex Works", API, "api_json", "https://api.openalex.org/works?search={query}&per-page=10",
       ["research"], note="Free (credit)", parser="openalex"),
    _s("Crossref Works", API, "api_json", "https://api.crossref.org/works?query={query}&rows=10",
       ["research"], note="Free", parser="crossref"),
    _s("Open Library Search", API, "api_json", "https://openlibrary.org/search.json?q={query}&limit=10",
       ["books", "history"], note="Free (credit)", parser="openlibrary"),
    _s("Project Gutenberg (Gutendex)", API, "api_json", "https://gutendex.com/books/?search={query}",
       ["books", "history"], note="Public-domain books", parser="gutendex"),
    _s("Federal Register Search", API, "api_json", "https://www.federalregister.gov/api/v1/documents.json?conditions[term]={query}&per_page=10",
       ["government", "us", "trade"], note="Public domain", parser="federal_register"),
    _s("Hacker News Search", API, "api_json", "https://hn.algolia.com/api/v1/search?query={query}&tags=story",
       ["tech", "news"], note="Free", parser="hn_algolia"),
    _s("World Bank Indicator", API, "api_json", "https://api.worldbank.org/v2/country/{country}/indicator/{indicator}?format=json&date={start}:{end}",
       ["economy", "history"], note="Free (credit)", parser="worldbank"),
    _s("USGS Earthquakes (dates)", API, "api_json", "https://earthquake.usgs.gov/fdsnws/event/1/query?format=geojson&starttime={start}&endtime={end}&minmagnitude=5",
       ["disaster"], note="Public domain", parser="usgs_geojson"),
    _s("ECB Euro Rate vs USD", API, "csv", "https://data-api.ecb.europa.eu/service/data/EXR/D.USD.EUR.SP00.A?format=csvdata&startPeriod={start}&endPeriod={end}",
       ["forex", "history"], note="Free (credit)", parser="ecb_csv"),
    _s("Frankfurter Currency Rates", API, "api_json", "https://api.frankfurter.app/{start}..{end}?from={base}&to={symbols}",
       ["forex", "history"], note="Free", parser="frankfurter"),
    _s("Stooq Daily Prices", API, "csv", "https://stooq.com/q/d/l/?s={symbol}&i=d",
       ["stocks", "gold", "oil", "forex", "history"], note="Check terms", parser="stooq_csv"),
    _s("Cboe VIX History", API, "csv", "https://cdn.cboe.com/api/global/us_indices/daily_prices/VIX_History.csv",
       ["stocks", "history"], note="Check terms", parser="csv_rows"),
    _s("Crypto Fear and Greed", API, "api_json", "https://api.alternative.me/fng/?limit=30",
       ["crypto"], note="Free (credit)", parser="fear_greed"),
    _s("Binance 24h Ticker", API, "api_json", "https://api.binance.com/api/v3/ticker/24hr?symbol={symbol}",
       ["crypto"], note="Free", parser="binance_ticker"),
    _s("CoinGecko Simple Price", API, "api_json", "https://api.coingecko.com/api/v3/simple/price?ids={ids}&vs_currencies=usd",
       ["crypto"], note="Free tier; check commercial terms", parser="coingecko_price"),
    _s("FRED Series", API, "api_json", "https://api.stlouisfed.org/fred/series/observations?series_id={series}&observation_start={start}&observation_end={end}&api_key={key}&file_type=json",
       ["economy", "rates", "history", "oil", "gold"], note="Free key", parser="fred", needs_key="FRED_API_KEY"),
    _s("Open-Meteo Weather Archive", API, "api_json", "https://archive-api.open-meteo.com/v1/archive?latitude={lat}&longitude={lon}&start_date={start}&end_date={end}&daily=precipitation_sum,temperature_2m_max",
       ["weather", "food", "history"], note="Non-commercial only ⚠", parser="open_meteo"),
]


# ----------------------------------------------------------------------
# lookups
# ----------------------------------------------------------------------
_BY_ID: Dict[str, Source] = {s.id: s for s in SOURCES}
assert len(_BY_ID) == len(SOURCES), "two sources have the same id"


def all_sources(only_enabled: bool = True) -> List[Source]:
    return [s for s in SOURCES if s.enabled or not only_enabled]


def get(source_id: str) -> Optional[Source]:
    return _BY_ID.get(source_id)


def available(source: Source) -> bool:
    """False if the source needs a secret that is not set."""
    return not source.needs_key or bool(os.getenv(source.needs_key))


def pick(
    tags: Iterable[str],
    kinds: Optional[Iterable[str]] = None,
    limit: int = 12,
    verified_first: bool = True,
) -> List[Source]:
    """Best sources for some topic tags (more shared tags = better)."""
    wanted = {t.lower() for t in tags}
    kinds_set = {k.lower() for k in kinds} if kinds else None
    scored: List[Tuple[int, int, int, Source]] = []
    for index, source in enumerate(SOURCES):
        if not source.enabled or not available(source):
            continue
        if kinds_set and source.kind not in kinds_set:
            continue
        overlap = len(wanted.intersection(source.tags))
        if overlap == 0:
            continue
        scored.append((overlap, 1 if (verified_first and source.verified) else 0, -index, source))
    scored.sort(key=lambda row: (row[0], row[1], row[2]), reverse=True)
    return [row[3] for row in scored[:limit]]


def plan(question: str, max_sources: int = 12) -> Dict[str, object]:
    """
    A first plan for a user question: which topics it is about, and which sources to open.
    (The DRIVER brain will use this.)
    """
    found = analyze(question)
    tags = list(found.keys())
    search_tags = tags + (["news"] if tags else ["news", "world"])
    sources = pick(search_tags, limit=max_sources)
    return {"tags": tags, "terms": found, "sources": sources}


def rss_feeds(only_verified: bool = False) -> List[Tuple[str, str]]:
    """(name, link) pairs for the news collector."""
    return [
        (s.name, s.url)
        for s in SOURCES
        if s.enabled and s.kind in ("rss", "atom") and not s.params and (s.verified or not only_verified)
    ]


def render_url(source: Source, **values: str) -> str:
    """
    Fill a link pattern. Values are quoted so they are safe in a link.
    Secrets (needs_key) are read from the environment and never printed.
    """
    data: Dict[str, str] = {}
    for name in source.params:
        if name == "key" and source.needs_key:
            secret = os.getenv(source.needs_key)
            if not secret:
                raise ValueError(f"{source.needs_key} is not set")
            data[name] = quote(secret, safe="")
        elif name in values:
            data[name] = quote(str(values[name]), safe="")
        else:
            raise ValueError(f"missing value: {name}")
    return source.url.format(**data)


def summary() -> Dict[str, int]:
    return {
        "sources": len(SOURCES),
        "verified": sum(1 for s in SOURCES if s.verified),
        "feeds": sum(1 for s in SOURCES if s.kind in ("rss", "atom") and not s.params),
        "api": sum(1 for s in SOURCES if s.params or s.kind in ("api_json", "csv")),
    }
