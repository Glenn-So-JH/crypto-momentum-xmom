"""
phase0_hello.py  -  Phase 0 "hello world" for the XMom project.

Goal: pull LIVE market data for a few crypto assets and print the four
numbers that decide whether a strategy makes money: bid, ask, spread,
and the maker/taker fees. No API keys needed: this uses only public data.

Run it:
    python phase0_hello.py

What to notice when it runs:
  - The spread is tiny for BTC and wider for smaller coins. That gap is a
    cost you pay every time you trade.
  - The taker fee is bigger than the maker fee. Market orders (takers)
    cost more than resting limit orders (makers).
  - These costs are exactly what we will charge the backtest in Phase 3.
"""

import ccxt  # the unified crypto exchange library


# The venue. Kraken is our candidate (US-accessible, transparent fees).
# Because we use ccxt, swapping to another exchange later is a one-line change.
EXCHANGE_ID = "kraken"

# A small starter universe of liquid USD pairs (stablecoins excluded).
SYMBOLS = ["BTC/USD", "ETH/USD", "SOL/USD", "XRP/USD", "LTC/USD"]


def main():
    # Build the exchange object. No keys = public (read-only) access only.
    exchange = getattr(ccxt, EXCHANGE_ID)()

    # load_markets() downloads the list of tradable pairs and their fee/precision
    # rules. We call it once and reuse the result.
    markets = exchange.load_markets()

    print(f"Connected to {EXCHANGE_ID}. {len(markets)} markets available.\n")
    header = f"{'PAIR':<10}{'BID':>14}{'ASK':>14}{'SPREAD %':>11}{'24H VOL (USD)':>18}"
    print(header)
    print("-" * len(header))

    for symbol in SYMBOLS:
        try:
            # Order book: the live list of buyers (bids) and sellers (asks).
            order_book = exchange.fetch_order_book(symbol, limit=5)
            best_bid = order_book["bids"][0][0]   # highest price a buyer will pay
            best_ask = order_book["asks"][0][0]   # lowest price a seller will accept
            spread_pct = (best_ask - best_bid) / best_ask * 100

            # Ticker: 24h summary stats, including volume (a liquidity proxy).
            ticker = exchange.fetch_ticker(symbol)
            # quoteVolume is volume in USD terms; fall back to base volume if missing.
            usd_vol = ticker.get("quoteVolume") or 0

            print(f"{symbol:<10}{best_bid:>14,.4f}{best_ask:>14,.4f}"
                  f"{spread_pct:>11.4f}{usd_vol:>18,.0f}")
        except Exception as e:
            print(f"{symbol:<10}  error: {str(e)[:60]}")

    # Fees: what the exchange charges to trade. Maker = you post a resting
    # limit order; taker = you cross the spread for an immediate fill.
    print("\nFee schedule (fraction of trade value):")
    sample = exchange.markets.get(SYMBOLS[0], {})
    maker = sample.get("maker")
    taker = sample.get("taker")
    print(f"  maker: {maker}  ({maker*100:.3f}% per trade)" if maker is not None
          else "  maker: not reported")
    print(f"  taker: {taker}  ({taker*100:.3f}% per trade)" if taker is not None
          else "  taker: not reported")
    print("\nReminder: a taker round-trip (buy then sell) costs roughly "
          "2x the taker fee, BEFORE spread and slippage. Keep that number "
          "in mind when a backtest looks too good.")


if __name__ == "__main__":
    main()
