# XMom LinkedIn Content Kit

A complete content package for the crypto momentum build-in-public series. Posts are paste-ready. Strategy, calendar, and credibility rules included.

Style rule inherited from the project owner: **no em dashes, ever.** Also no en dashes for ranges (write "20 to 40", not "20-40" where a dash could read as a range dash). This is both a personal style rule and a deliberate anti-AI-slop tell.

---

## 1. Content Strategy

### Positioning: The Honest Quant

The angle is not "I built a bot that prints money." The angle is the opposite, and that is precisely why it works:

> **A finance-literate professional is testing, in public and with real rigor, whether one of the most famous edges in the academic literature survives contact with fees, thin liquidity, and reality. The data is allowed to say no. If it does, that is a successful outcome and it gets posted too.**

This positioning does three things:

1. **It is falsifiable.** Every post makes claims that can be checked against a public GitHub repo. That is the single biggest credibility differentiator on a platform full of unverifiable trading claims.
2. **It pre-commits to honesty.** By announcing up front that "the strategy might not survive costs," every subsequent post inherits credibility. Readers know you are not selling anything.
3. **It reframes failure as content.** A dead edge is a publishable finding, exactly as it is in academia. This removes the incentive to fudge, and readers can feel that.

Secondary positioning threads to weave in over time, never as the headline:

- **Learning professional technique to high fidelity.** You are not inventing methods, you are implementing the standard playbook (point-in-time universes, cost modeling, walk-forward validation) and showing your work.
- **AI as teacher and pair programmer.** You are finance-literate and a light coder using AI to close the gap. Handled honestly, this is a differentiator, not a confession. Handled dishonestly (pretending you hand-wrote everything), it is a time bomb. Own it early.

### Audience

In priority order:

1. **Working quants and systematic traders.** The hardest audience and the most valuable. They have seen a thousand fake track records. They will engage only with real numbers, correct terminology, and admitted mistakes. Every post should survive their scrutiny. If a post would make a professional quant wince, cut the offending line.
2. **Serious retail/aspiring quants and finance students.** The largest engaged segment. They want the teaching payload: what is survivorship bias, why do fees kill strategies, how do you validate a backtester. Write the explanations for them.
3. **Recruiters and hiring managers in finance/fintech.** They will not comment. They will read three posts, click the GitHub link, and form a judgment about rigor, communication, and follow-through. The series is a living work sample.
4. **General professional network.** They provide the baseline engagement that gets posts distributed. The hooks and plain-language framing are for them.

### Cadence

- **One post per week** during active build phases. This matches the actual pace of real findings. Do not post filler to hit a schedule; a skipped week is better than a padded post.
- **One post per phase gate** as the anchor (the big finding or milestone), with optional smaller "lab note" posts in between when something genuinely surprising happens.
- **Monthly reviews** once the system is running (paper or live), on a fixed date, with the same metrics table every time. Consistency of format is itself a credibility signal.
- Best posting windows for a finance audience: Tuesday to Thursday, morning in your audience's core timezone. Do not obsess over this; content quality dominates timing.

### What makes build-in-public credible vs cringe

**Credible:**
- Specific numbers with units and context (0.40% taker fee, 13 coins, 30-day dollar volume screen).
- Showing the mistake before the fix, in that order.
- Citing sources by author and year, including the ones that argue against your strategy.
- Code and data that anyone can check (link the repo, but not in the post body; LinkedIn suppresses posts with external links, so put the link in the first comment).
- Verbs in the past tense about things you actually did, not the future tense about things you intend.
- Admitting what you do not know yet, precisely.
- Restraint. One idea per post, fully developed.

**Cringe:**
- Screenshots of green PnL with no methodology.
- "I cracked the code" energy. Any implication of secret knowledge.
- Engagement-bait formatting: one-word lines, endless line breaks, "Agree?", fake vulnerability ("I cried when my backtest finished").
- Emoji walls, rocket ships, fire.
- Lessons stretched far past what the evidence supports ("this taught me everything about leadership").
- Announcing a journey repeatedly instead of shipping findings.
- Hiding the AI assistance, then getting asked a question you cannot answer.

**Voice checklist for every draft:** first person, past tense for work done, at least one real number, at least one thing that went wrong or remains uncertain, one citation where a claim leans on literature, zero promises of returns, and it must read aloud like a person talking to a colleague.

---

## 2. Drafted Posts (paste-ready)

Posting order matches the journey. Put the GitHub link in the first comment of each post, not the body. Suggested first-comment line: "Repo with all code and the progress log: [link]. Everything in this post is reproducible from there."

---

### Post 1: Kickoff. Why I am building a crypto momentum system in public

I am going to spend the next several months trying to prove myself wrong, in public.

The project: build a fully automated, long-only crypto momentum strategy from scratch. Rank the most liquid coins by trailing return, hold the strongest, rebalance weekly. If, and only if, it survives honest testing, run it live with $10,000 of my own money on Kraken.

Why momentum? Because it is one of the most documented effects in finance, and in crypto specifically the evidence is genuinely contested. Time-series momentum (is the asset itself trending?) holds up reasonably well in the literature. Cross-sectional momentum (is it trending more than its peers?) looks great in papers until realistic transaction costs are applied, at which point recent work suggests much of the profit disappears. Han, Kang and Ryu (2024) is the sharpest version of that argument.

That tension is the whole point. I am not assuming the edge exists. I am measuring whether it survives fees, slippage, and out-of-sample testing. Professional quants spend most of their time trying to kill their own ideas. I want to learn that discipline for real, not from a textbook.

Some honest context. I come from the finance side, not the engineering side. I can read a factor paper comfortably; I cannot yet write production Python comfortably. I am using AI heavily as a teacher and pair programmer, and I will be transparent about that throughout. The judgment calls, the methodology, and the mistakes will be mine.

Ground rules I am committing to now, before any results exist:

1. Every backtest models real fees and slippage from day one.
2. No look-ahead, no survivorship bias, validated out-of-sample.
3. "The data says no, so I did not trade it" counts as success.
4. Everything is version-controlled and public. If I claim a number, you can reproduce it.

If the edge is dead, you will read about it here in exactly the same tone as if it works.

What would you test first if you were trying to kill this strategy? Genuinely collecting a list.

---

### Post 2: The fee wall. My strategy's first enemy is not the market

Before writing a single line of strategy code, I did some arithmetic that reshaped the whole project.

Kraken's taker fee at my volume tier is 0.40%. A rebalance means selling one coin and buying another, so a full position swap costs roughly 0.80% round trip. For comparison, the bid-ask spread on the liquid majors is often just a few basis points. I had assumed spread and slippage would be the main cost story. Wrong. At retail size, the fee schedule dwarfs everything else. Fees are the wall.

Now compound that with turnover. A weekly rebalanced momentum portfolio that swaps even a quarter of its positions each week pays roughly 0.20% weekly, which is over 10% a year in fees alone. Swap half the book weekly and you need the strategy to clear a hurdle north of 20% annually before it earns a cent. Buy-and-hold Bitcoin pays approximately zero.

This single calculation now drives multiple design decisions:

- Weekly rebalancing, not daily. Turnover is the multiplier on the fee, so I control what I can.
- The benchmark is buy-and-hold BTC. The strategy must justify its costs against doing almost nothing.
- Maker orders instead of taker orders are worth investigating later, but I will backtest with taker fees because that is the conservative, honest assumption.
- Every backtest result I ever post will be net of costs, with the cost assumptions stated.

The academic version of this lesson: the papers that report beautiful crypto cross-sectional momentum returns mostly report them gross. The papers that apply realistic costs report something much less beautiful. I now understand viscerally why.

If you run systematic strategies: what is the highest all-in cost hurdle you have seen a live strategy consistently clear? I would love a reality check on what is achievable.

---

### Post 3: The bias that makes dead coins invisible

My backtest was about to lie to me, and the lie is worth explaining because it fools a lot of people.

Suppose I test my momentum strategy on "the top coins on Kraken today," using their full price history. Sounds reasonable. It is actually a rigged experiment. Every coin in that list is, by definition, a survivor. The coins that got delisted, went to zero, or faded into illiquidity are excluded before the test even starts. My strategy would get graded only on assets that we already know made it.

This is survivorship bias, and in crypto it is brutal, because the failure rate of coins is far higher than the failure rate of, say, S&P 500 constituents. A momentum strategy backtested on survivors looks systematically better than anything you could have actually traded.

The fix is a point-in-time universe. For every date in the backtest, the eligible list contains only the coins that were actually listed and actually liquid on that date, measured by trailing 30-day dollar volume, stablecoins excluded. The strategy is only allowed to pick from what it could genuinely have seen and traded at the time.

So that is what I spent the past stretch building. Not signals. Not strategy. A data pipeline: multi-year daily OHLCV for every candidate pair, stored locally, plus a script that reconstructs the tradable universe for any historical date. Kraken's REST API only returns about 720 recent candles per request, so deep history had to come from their downloadable archives, which was its own small adventure.

Unglamorous week. Probably the highest-value one so far, because every result downstream inherits the honesty of this layer.

For those who backtest anything: what is the data bias that has burned you the worst? Survivorship is the famous one, but I suspect the embarrassing stories involve subtler ones.

---

### Post 4: I built a backtester. Step one was proving it can do nothing correctly

The most useful test I ran this week was deliberately boring: I made my backtest engine buy Bitcoin and do nothing for several years.

Why? Because a backtester is a measurement instrument, and you do not trust an instrument until you calibrate it against known answers. If my engine simulates "buy and hold BTC" and the resulting equity curve does not match BTC's actual return over the same window, the engine is broken, and every exciting result it will ever produce is noise.

So before testing any actual strategy, the engine had to pass a validation suite:

1. Buy-and-hold BTC must equal BTC's return, to within rounding.
2. An equal-weight portfolio of the universe must match the hand-computed average of returns.
3. Zero-cost and with-cost runs must differ by exactly the fee model, nothing more.
4. A look-ahead test: shift all signals forward one day and confirm performance degrades. If using tomorrow's information does not help, the engine is somehow leaking the future already.

That last one matters most. Look-ahead bias is the quiet killer in vectorized backtests, because pandas makes it trivially easy to rank on a return that includes the very day you trade. The discipline is simple to state and easy to botch: signals computed on data through day T can only inform positions held from day T+1.

Confession: the first version failed test 1. Off by a small but real margin. The bug was in how I aligned rebalance timestamps with candle closes. It took an evening to find, and it was a useful humiliation, because that same bug inside a "real" strategy result would have been invisible and flattering.

Nothing in this post makes money. That is the point. Next post has actual strategy results, and now I have earned the right to believe them.

Curious what validation tests others require before trusting a new backtest engine. My list has four; I doubt it is complete.

---

### Post 5: I planned to trade 20 to 40 coins. Reality gave me 13

Small finding, big consequences.

My project charter targeted a universe of 20 to 40 liquid coins. When I ran the actual screen on Kraken USD spot pairs (trailing 30-day dollar volume above a sane threshold, stablecoins removed), the point-in-time universe came out at roughly 13 names. Not 40. Thirteen.

Crypto looks enormous from the outside. Thousands of tokens, headlines about a multi-trillion dollar asset class. But "exists" and "tradable at retail size on a US-accessible exchange without eating the order book" are very different filters. Once you demand real, sustained dollar volume in USD pairs, the investable universe collapses to a short list, and it gets shorter the further back in history you go.

Why this matters for a cross-sectional strategy specifically:

- Cross-sectional momentum ranks assets against peers and holds the top slice. With 13 names, the "top quartile" is three coins. Concentration risk stops being a footnote and becomes the portfolio.
- Small universes are noisy universes. The difference between rank 3 and rank 4 can be a coin flip, and a strategy that churns on coin flips pays real fees for random trades (see my earlier post on the fee wall).
- The academic papers reporting strong cross-sectional crypto momentum typically use universes of 50 to several hundred coins from aggregated data sources. My tradable reality is an order of magnitude thinner. Their result is not automatically my result.

I could inflate the universe by lowering the liquidity bar. I will not. A backtest full of coins I could not actually trade at size is just a more elaborate way of lying to myself, and untradable breadth is fake breadth.

Instead, this finding raises the prior on the alternative: time-series momentum, which asks "is this asset trending?" rather than "is it trending more than 12 others?", and which degrades far more gracefully in a thin universe.

The meta-lesson: constraints discovered early are cheap; the same constraint discovered after deployment is expensive. I will happily keep collecting these.

Has anyone here run cross-sectional strategies on genuinely small universes? Where does ranking stop making sense for you, 10 names, 20, 30?

---

### Post 6: My working thesis: this strategy probably does not survive costs. Testing it anyway

Time to pre-register a prediction, so you can hold me to it.

Everything I have built so far (the point-in-time data pipeline, the validated backtest engine, the cost model) exists to answer one question: does long-only cross-sectional crypto momentum, traded weekly on Kraken's liquid USD universe, beat buy-and-hold Bitcoin after realistic costs?

Here is what the evidence I have gathered says before I run the test:

- The academic literature is reasonably kind to time-series momentum in crypto: trend-following on individual assets has held up across multiple studies and periods.
- It is much harsher on cross-sectional momentum once costs enter. Han, Kang and Ryu (2024) find that most of the cross-sectional profit evaporates under realistic transaction cost and price-move assumptions.
- My own preliminary work adds two local aggravating factors: a fee wall of roughly 0.80% per round trip at my tier, and a tradable universe of about 13 coins, far thinner than the papers assume.

So my honest, written-down-in-advance expectation: gross performance will look attractive, and net-of-cost performance will struggle to beat holding BTC. I would estimate I am more likely to end up trading a time-series variant, or a hybrid with a trend filter, than the pure cross-sectional strategy I named the project after.

Why run the test at all if I expect a no?

Because "I read a paper" and "I reproduced the finding on my own exchange, my own universe, my own costs" are different levels of knowledge, and only one of them is mine. Because the papers might not transfer to a 13-coin universe in either direction. And because pre-registering the hypothesis before seeing results is the single cheapest defense against fooling myself. If I peek first and predict after, my prediction is worthless.

The backtest runs next. Whatever it says gets posted: the equity curves, the metrics table, gross versus net, and the verdict. If I was wrong in the optimistic direction, you will see that. If I was wrong in the pessimistic direction, you will see that too, followed by an extended period of me trying to find the bug, because a result that good is more likely a mistake than a miracle.

Before I run it: what is your prediction? Survives costs, dies to costs, or dies to something I have not thought of yet?

---

### Post 7 (optional, flexible timing): The uncomfortable post about AI writing my code

Some of the code in my quant project was written by AI. Here is exactly how that works and where I draw the lines, because I would rather say it plainly than have it discovered awkwardly.

My background is finance, not software engineering. I can read a momentum paper and argue about methodology; six months ago I could not have built a data pipeline. For this project I use AI the way you would use a very fast, very patient senior developer who happens to sit next to you: I describe what I need and why, it drafts, I interrogate, we iterate.

What that looks like in practice:

- I set the methodology. The decision to build a point-in-time universe, to benchmark against buy-and-hold BTC, to model taker fees rather than maker: those calls come from reading the literature and thinking about my constraints, and I own them.
- AI writes most first drafts of code, and it teaches as it goes. I do not accept code I cannot explain line by line. That rule is slow and non-negotiable, because the failure mode is obvious: an unexamined backtest bug flattering me into losing real money.
- Verification is mine. The validation suite from my earlier post (buy-and-hold must equal BTC, look-ahead tests, cost reconciliation) exists precisely because I do not extend blind trust to my tools, AI included. Trust the output because it passed tests, not because it sounded confident.

The honest accounting: this project would be impossible for me at this quality bar without AI, and it would be worthless without the parts AI cannot do, which are judgment, skepticism, and the willingness to accept an unprofitable answer.

I think this is simply what learning technical fields looks like now, and pretending otherwise is its own small dishonesty. But I hold my view loosely.

If you are technical: where do you draw the trust line with AI-written code in anything that touches money?

---

## 3. Content Calendar: Mapping Posts to the Remaining Roadmap

Posts 1 to 7 above cover Phases 0 to 1 and the setup of the Phase 2/3 question. The calendar below covers what comes next. Dates are placeholders keyed to phase completion; publish on gate completion, not on the calendar, and let the schedule slip rather than the quality.

| # | Timing (approx) | Roadmap phase | Working title / angle | Payload |
|---|---|---|---|---|
| 8 | Phase 2 gate | Phase 2: First backtest | "My first backtest results, and the three reasons I do not believe them yet" | Gross equity curve, metrics table (CAGR, Sharpe, max DD, turnover), benchmarked vs BTC. Explicitly labeled pre-costs and pre-validation. |
| 9 | Phase 3 gate | Phase 3: Costs and slippage | "I added real costs and watched the edge shrink by X%" | The centerpiece post. Gross vs net side by side, sensitivity to rebalance frequency and lookback. The verdict on the pre-registered thesis from Post 6. |
| 10 | Phase 4 midpoint | Phase 4: Robustness | "How I tried to fool myself: walk-forward testing" | Explain in-sample vs out-of-sample and the multiple-testing problem. Parameter heatmaps. Admit any parameters that only worked in-sample. |
| 11 | Phase 4 gate | Phase 4: Robustness | "The strategy that survived was not the one I started with" | Cross-sectional vs time-series vs hybrid comparison. The evidence-based pick, and what got killed. |
| 12 | Phase 5 gate | Phase 5: Portfolio and risk | "A signal is not a strategy: the risk layer that decides how much" | Volatility targeting, per-asset caps, drawdown circuit breaker, with before/after worst-case drawdown numbers. |
| 13 | Phase 6 start | Phase 6: Paper trading | "It trades itself now (with fake money). The architecture" | Event-driven vs vectorized, scheduling, idempotency, logging, the kill switch. Include the first bug that nearly broke it. |
| 14 | Phase 6, week 3 to 4 | Phase 6: Paper trading | "Two weeks of paper trading: backtest expectations vs reality" | Reconciliation table: expected trades vs actual, paper fills vs modeled costs. Any drift gets named and investigated. |
| 15 | Phase 6 gate | Phase 6 wrap | "Go / no-go: the evidence for putting real money behind this" | The decision memo, published. If it is no-go, this becomes the capstone honesty post and the series pivots to iteration. |
| 16 | Phase 7 start | Phase 7: Live deployment | "I wired real money to my code. First tranche, $1,000 to $2,000" | Operational security (trade-only keys, no withdrawal scope), first live fills vs paper, what live slippage actually was. |
| 17+ | Monthly, fixed date | Phase 8: Operate | "Month N review: what the system did and what I learned" | Same metrics table every month: return vs BTC, turnover, fees paid, deviations from backtest, incidents, one lesson. Boring on purpose. Consistency is the content. |
| Capstone | After 3+ live months | Phase 8 | "One year of building a quant system in public: the full honest accounting" | Long-form retrospective. Total costs (fees, time, tools), total P&L, what the literature got right, what I would tell someone starting. Strong recruiter artifact. |

**Flexible slots (use when they actually happen, they are the best posts):**
- Any bug postmortem that changed a result you had already posted. Correct the record loudly; nothing builds trust faster.
- Any dead end: a variant tested and killed, with the numbers.
- Answering the best skeptical comment you receive as a full follow-up post.

---

## 4. Rules of Credibility

Pin these. Reread before every post.

1. **Show real numbers with units and context.** "Fees hurt" is content. "0.80% round trip against a few basis points of spread, times 52 weekly rebalances" is credibility.
2. **Report net of costs, always, and state the cost assumptions.** Any gross number must be explicitly labeled gross and paired with net.
3. **Admit dead ends and mistakes, with specifics, before anyone finds them.** The buy-and-hold bug, the parameter that only worked in-sample, the assumption that broke. Errors admitted early are assets; errors discovered by readers are liabilities.
4. **Cite sources by author and year, especially the ones that argue against you.** Han, Kang and Ryu (2024) is more useful to this series as an adversary than a hundred supportive blog posts.
5. **Never imply guaranteed or expected returns. Ever.** No projections, no "if this continues," no annualizing three good weeks. Include a plain one-line disclaimer on any post with performance figures: this is a personal research project, not investment advice, and the capital at risk is money I can afford to lose.
6. **Pre-register predictions before running tests, then grade yourself in public.** A prediction made after seeing the result is marketing, not research.
7. **Everything reproducible or clearly flagged as not.** If a number cannot be regenerated from the public repo, either fix that or say so in the post.
8. **Be transparent about AI assistance and its limits.** Never present understanding you do not have; never post code you cannot explain.
9. **One idea per post, fully earned.** Do not stretch a small finding into a life lesson. The evidence sets the ceiling on the conclusion.
10. **When in doubt, write for the skeptical professional quant in the audience.** If the post would make them wince, cut the line. If it would make them nod, ship it.
