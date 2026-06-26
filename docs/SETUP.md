# Setup (macOS)

One-time environment setup for the XMom project. Copy-paste these into Terminal.

## 1. Open Terminal in the project folder
```bash
cd "/Users/glennso/Documents/Claude/Projects/Quant Projects/crypto-momentum"
```

## 2. Check you have Python 3
```bash
python3 --version
```
If you see `Python 3.10` or higher, you are good. If `python3` is not found, install it from https://www.python.org/downloads/ or via Homebrew (`brew install python`).

## 3. Create and activate a virtual environment
A "venv" is an isolated Python sandbox for this project, so its packages do not collide with anything else on your machine.
```bash
python3 -m venv .venv
source .venv/bin/activate
```
Your prompt should now start with `(.venv)`. To leave it later, type `deactivate`.
You will run `source .venv/bin/activate` each time you start a new Terminal session for this project.

## 4. Install the libraries
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

## 5. Run the Phase 0 script
```bash
python phase0_hello.py
```
You should see a table of live bid/ask/spread for five coins, plus Kraken's maker/taker fees. No API keys are needed for this; it uses public data only.

If you get a network or geolocation error from Kraken, tell me and we will switch the `EXCHANGE_ID` in the script to another venue (the code is exchange-agnostic).

---

## API keys come later (Phase 0.4)
The script above needs no keys. You only need keys when we start pulling your account data and (much later) placing orders. When we get there, see `.env.example` and create **read-only** keys first.
