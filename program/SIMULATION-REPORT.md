# OSFT 1.3.0-beta — Week simulation report

Run on 2026-10-24 by `tests/sim_week.py` against the **real Flask server**. Each run used a fresh throwaway copy of the program on its own port (`/tmp/osft-sim-*`), with logins: Owner (admin) and Crew Ana (crew, limited to **daily** counts). Every call went through the HTTP API. Screenshots of the resulting screens are in `screenshots/sim/`, desktop 1440 and phone 390.

## Scenario

| Step | Date (business) | Who | What |
|---|---|---|---|
| Opening count | Mon 2026-10-05, before service | Owner | Weekly full count, 10 of every product |
| POS imports | Mon–Sat 2026-10-05…10 | Owner | One generic CSV per day; menu recipes use exactly **5** of every product over the week (split 10/20/20/20/15/15 %) |
| Daily partial | Tue 2026-10-06, end of shift | Crew Ana | Daily count of the protein watch list only, true quantities (crew was also refused a weekly: 403) |
| Daily partial | Thu 2026-10-08, end of shift | Crew Ana | Same |
| Weekly count | Mon 2026-10-12, before service | Owner | Full count, 5 of each. In the **short** variant, 2 products are counted at 3 (2 short) |

Expected results: on-hand 5 (or 3 for the short products), theoretical usage 5 and counted usage 5 → variance 0 (or +2 for the short products). The order list should be par 8 minus on-hand. The daily partials must not zero anything, flag anything missing, or change the weekly math.

## Test 1 — 10 products — exact  (28/28 checks passed)

| Check | Expected | Actual | OK |
|---|---|---|---|
| rows with wrong on-hand/theoretical/variance | 0 | 0 | ✅ |
| variance rows reported | 10 | 10 | ✅ |
| items flagged by variance report | [] | [] | ✅ |
| report start = opening weekly 2026-10-05 | 2026-10-05 | 2026-10-05 | ✅ |
| report end = weekly 2026-10-12 | 2026-10-12 | 2026-10-12 | ✅ |
| daily partials skipped by weekly report | 2 | 2 | ✅ |
| total variance $ | 0 | 0 | ✅ |
| inventory value $ | 185.5 | 185.5 | ✅ |
| sales $ in window | 660.0 | 660.0 | ✅ |
| ideal COGS $ (theoretical × cost) | 185.5 | 185.5 | ✅ |
| actual COGS $ (counted × cost) | 185.5 | 185.5 | ✅ |
| food cost % | 28.1 | 28.1 | ✅ |
| ideal food cost % | 28.1 | 28.1 | ✅ |
| order list lines (all below par 8) | 10 | 10 | ✅ |
| order qty = par − on-hand | 0 | 0 | ✅ |
| order list $ | 111.3 | 111.3 | ✅ |
| dashboard low-par count | 10 | 10 | ✅ |
| daily 2026-10-06: no out-of-scope item zeroed | 0 | 0 | ✅ |
| daily 2026-10-06: nothing flagged missing | 0 | 0 | ✅ |
| daily 2026-10-06: counted by crew login | Crew Ana | Crew Ana | ✅ |
| daily 2026-10-08: no out-of-scope item zeroed | 0 | 0 | ✅ |
| daily 2026-10-08: nothing flagged missing | 0 | 0 | ✅ |
| daily 2026-10-08: counted by crew login | Crew Ana | Crew Ana | ✅ |
| plate cost Al pastor taco | 0.6079 | 0.6079 | ✅ |
| plate cost Beef taco | 1.5492 | 1.5492 | ✅ |
| plate cost Carnitas taco | 1.0954 | 1.0954 | ✅ |
| plate cost Chicken burrito | 2.77 | 2.77 | ✅ |
| count history types (newest first) | ['weekly', 'daily', 'daily', 'weekly'] | ['weekly', 'daily', 'daily', 'weekly'] | ✅ |

Per product (expected → actual):

| Product | Unit | Cost | On-hand | Theoretical | Counted usage | Variance | Variance $ |
|---|---|---|---|---|---|---|---|
| Ground beef | lb | 4.89 | 5 → 5.0 | 5 → 5.0 | 5 → 5.0 | 0 → 0.0 | 0.0 → 0.0 |
| Chicken thigh | lb | 2.79 | 5 → 5.0 | 5 → 5.0 | 5 → 5.0 | 0 → 0.0 | 0.0 → 0.0 |
| Carnitas | lb | 5.25 | 5 → 5.0 | 5 → 5.0 | 5 → 5.0 | 0 → 0.0 | 0.0 → 0.0 |
| Al pastor pork | lb | 4.10 | 5 → 5.0 | 5 → 5.0 | 5 → 5.0 | 0 → 0.0 | 0.0 → 0.0 |
| Flour tortillas 12in | pack | 3.49 | 5 → 5.0 | 5 → 5.0 | 5 → 5.0 | 0 → 0.0 | 0.0 → 0.0 |
| Corn tortillas | pack | 2.29 | 5 → 5.0 | 5 → 5.0 | 5 → 5.0 | 0 → -0.0 | 0.0 → -0.0 |
| Shredded cheese | lb | 3.99 | 5 → 5.0 | 5 → 5.0 | 5 → 5.0 | 0 → 0.0 | 0.0 → 0.0 |
| Sour cream | qt | 3.20 | 5 → 5.0 | 5 → 5.0 | 5 → 5.0 | 0 → 0.0 | 0.0 → 0.0 |
| Pico de gallo | qt | 5.50 | 5 → 5.0 | 5 → 5.0 | 5 → 5.0 | 0 → 0.0 | 0.0 → 0.0 |
| Limes | lb | 1.60 | 5 → 5.0 | 5 → 5.0 | 5 → 5.0 | 0 → 0.0 | 0.0 → 0.0 |

Menu plate costs:

| Menu item | Price | Sold | Plate cost exp → act | Food cost % |
|---|---|---|---|---|
| Al pastor taco | 3.75 | 40 | 0.6079 → 0.6079 | 16.2 |
| Beef taco | 3.5 | 40 | 1.5492 → 1.5492 | 44.3 |
| Carnitas taco | 3.75 | 40 | 1.0954 → 1.0954 | 29.2 |
| Chicken burrito | 11.0 | 20 | 2.77 → 2.77 | 25.2 |

Count history (newest first): 2026-10-12 Weekly full count — Full truck — Owner — 10 counted; 2026-10-08 Daily end-of-shift — Protein, Proteins, Meat — Crew Ana — 4 counted; 2026-10-06 Daily end-of-shift — Protein, Proteins, Meat — Crew Ana — 4 counted; 2026-10-05 Weekly full count — Full truck — Owner — 10 counted

## Test 1 — 10 products — short  (28/28 checks passed)

| Check | Expected | Actual | OK |
|---|---|---|---|
| rows with wrong on-hand/theoretical/variance | 0 | 0 | ✅ |
| variance rows reported | 10 | 10 | ✅ |
| items flagged by variance report | ['Chicken thigh', 'Sour cream'] | ['Chicken thigh', 'Sour cream'] | ✅ |
| report start = opening weekly 2026-10-05 | 2026-10-05 | 2026-10-05 | ✅ |
| report end = weekly 2026-10-12 | 2026-10-12 | 2026-10-12 | ✅ |
| daily partials skipped by weekly report | 2 | 2 | ✅ |
| total variance $ | 11.98 | 11.98 | ✅ |
| inventory value $ | 173.52 | 173.52 | ✅ |
| sales $ in window | 660.0 | 660.0 | ✅ |
| ideal COGS $ (theoretical × cost) | 185.5 | 185.5 | ✅ |
| actual COGS $ (counted × cost) | 197.48 | 197.48 | ✅ |
| food cost % | 29.9 | 29.9 | ✅ |
| ideal food cost % | 28.1 | 28.1 | ✅ |
| order list lines (all below par 8) | 10 | 10 | ✅ |
| order qty = par − on-hand | 0 | 0 | ✅ |
| order list $ | 123.28 | 123.28 | ✅ |
| dashboard low-par count | 10 | 10 | ✅ |
| daily 2026-10-06: no out-of-scope item zeroed | 0 | 0 | ✅ |
| daily 2026-10-06: nothing flagged missing | 0 | 0 | ✅ |
| daily 2026-10-06: counted by crew login | Crew Ana | Crew Ana | ✅ |
| daily 2026-10-08: no out-of-scope item zeroed | 0 | 0 | ✅ |
| daily 2026-10-08: nothing flagged missing | 0 | 0 | ✅ |
| daily 2026-10-08: counted by crew login | Crew Ana | Crew Ana | ✅ |
| plate cost Al pastor taco | 0.6079 | 0.6079 | ✅ |
| plate cost Beef taco | 1.5492 | 1.5492 | ✅ |
| plate cost Carnitas taco | 1.0954 | 1.0954 | ✅ |
| plate cost Chicken burrito | 2.77 | 2.77 | ✅ |
| count history types (newest first) | ['weekly', 'daily', 'daily', 'weekly'] | ['weekly', 'daily', 'daily', 'weekly'] | ✅ |

Per product (expected → actual):

| Product | Unit | Cost | On-hand | Theoretical | Counted usage | Variance | Variance $ |
|---|---|---|---|---|---|---|---|
| Ground beef | lb | 4.89 | 5 → 5.0 | 5 → 5.0 | 5 → 5.0 | 0 → 0.0 | 0.0 → 0.0 |
| Chicken thigh | lb | 2.79 | 3 → 3.0 | 5 → 5.0 | 7 → 7.0 | 2 → 2.0 | 5.58 → 5.58 |
| Carnitas | lb | 5.25 | 5 → 5.0 | 5 → 5.0 | 5 → 5.0 | 0 → 0.0 | 0.0 → 0.0 |
| Al pastor pork | lb | 4.10 | 5 → 5.0 | 5 → 5.0 | 5 → 5.0 | 0 → 0.0 | 0.0 → 0.0 |
| Flour tortillas 12in | pack | 3.49 | 5 → 5.0 | 5 → 5.0 | 5 → 5.0 | 0 → 0.0 | 0.0 → 0.0 |
| Corn tortillas | pack | 2.29 | 5 → 5.0 | 5 → 5.0 | 5 → 5.0 | 0 → -0.0 | 0.0 → -0.0 |
| Shredded cheese | lb | 3.99 | 5 → 5.0 | 5 → 5.0 | 5 → 5.0 | 0 → 0.0 | 0.0 → 0.0 |
| Sour cream | qt | 3.20 | 3 → 3.0 | 5 → 5.0 | 7 → 7.0 | 2 → 2.0 | 6.4 → 6.4 |
| Pico de gallo | qt | 5.50 | 5 → 5.0 | 5 → 5.0 | 5 → 5.0 | 0 → 0.0 | 0.0 → 0.0 |
| Limes | lb | 1.60 | 5 → 5.0 | 5 → 5.0 | 5 → 5.0 | 0 → 0.0 | 0.0 → 0.0 |

Menu plate costs:

| Menu item | Price | Sold | Plate cost exp → act | Food cost % |
|---|---|---|---|---|
| Al pastor taco | 3.75 | 40 | 0.6079 → 0.6079 | 16.2 |
| Beef taco | 3.5 | 40 | 1.5492 → 1.5492 | 44.3 |
| Carnitas taco | 3.75 | 40 | 1.0954 → 1.0954 | 29.2 |
| Chicken burrito | 11.0 | 20 | 2.77 → 2.77 | 25.2 |

Count history (newest first): 2026-10-12 Weekly full count — Full truck — Owner — 10 counted; 2026-10-08 Daily end-of-shift — Protein, Proteins, Meat — Crew Ana — 4 counted; 2026-10-06 Daily end-of-shift — Protein, Proteins, Meat — Crew Ana — 4 counted; 2026-10-05 Weekly full count — Full truck — Owner — 10 counted

## Test 2 — 40 products — exact  (37/37 checks passed)

| Check | Expected | Actual | OK |
|---|---|---|---|
| rows with wrong on-hand/theoretical/variance | 0 | 0 | ✅ |
| variance rows reported | 40 | 40 | ✅ |
| items flagged by variance report | [] | [] | ✅ |
| report start = opening weekly 2026-10-05 | 2026-10-05 | 2026-10-05 | ✅ |
| report end = weekly 2026-10-12 | 2026-10-12 | 2026-10-12 | ✅ |
| daily partials skipped by weekly report | 2 | 2 | ✅ |
| total variance $ | 0 | 0 | ✅ |
| inventory value $ | 1385.5 | 1385.5 | ✅ |
| sales $ in window | 1605.0 | 1605.0 | ✅ |
| ideal COGS $ (theoretical × cost) | 1385.5 | 1385.5 | ✅ |
| actual COGS $ (counted × cost) | 1385.5 | 1385.5 | ✅ |
| food cost % | 86.3 | 86.3 | ✅ |
| ideal food cost % | 86.3 | 86.3 | ✅ |
| order list lines (all below par 8) | 40 | 40 | ✅ |
| order qty = par − on-hand | 0 | 0 | ✅ |
| order list $ | 831.3 | 831.3 | ✅ |
| dashboard low-par count | 40 | 40 | ✅ |
| daily 2026-10-06: no out-of-scope item zeroed | 0 | 0 | ✅ |
| daily 2026-10-06: nothing flagged missing | 0 | 0 | ✅ |
| daily 2026-10-06: counted by crew login | Crew Ana | Crew Ana | ✅ |
| daily 2026-10-08: no out-of-scope item zeroed | 0 | 0 | ✅ |
| daily 2026-10-08: nothing flagged missing | 0 | 0 | ✅ |
| daily 2026-10-08: counted by crew login | Crew Ana | Crew Ana | ✅ |
| plate cost Al pastor taco | 1.2725 | 1.2725 | ✅ |
| plate cost Beef taco | 1.8379 | 1.8379 | ✅ |
| plate cost Carnitas taco | 1.3754 | 1.3754 | ✅ |
| plate cost Chicken burrito | 4.5883 | 4.5883 | ✅ |
| plate cost Chorizo & egg burrito | 11.6408 | 11.6408 | ✅ |
| plate cost Fish taco | 6.0725 | 6.0725 | ✅ |
| plate cost Guac & chips | 6.2825 | 6.2825 | ✅ |
| plate cost Horchata | 3.5625 | 3.5625 | ✅ |
| plate cost Jarritos | 6.0 | 6.0 | ✅ |
| plate cost Mexican Coke | 8.0 | 8.0 | ✅ |
| plate cost Quesadilla | 3.0483 | 3.0483 | ✅ |
| plate cost Shrimp taco | 4.1083 | 4.1083 | ✅ |
| plate cost Water | 7.0 | 7.0 | ✅ |
| count history types (newest first) | ['weekly', 'daily', 'daily', 'weekly'] | ['weekly', 'daily', 'daily', 'weekly'] | ✅ |

Per product (expected → actual):

| Product | Unit | Cost | On-hand | Theoretical | Counted usage | Variance | Variance $ |
|---|---|---|---|---|---|---|---|
| Ground beef | lb | 4.89 | 5 → 5.0 | 5 → 5.0 | 5 → 5.0 | 0 → 0.0 | 0.0 → 0.0 |
| Chicken thigh | lb | 2.79 | 5 → 5.0 | 5 → 5.0 | 5 → 5.0 | 0 → 0.0 | 0.0 → 0.0 |
| Carnitas | lb | 5.25 | 5 → 5.0 | 5 → 5.0 | 5 → 5.0 | 0 → 0.0 | 0.0 → 0.0 |
| Al pastor pork | lb | 4.10 | 5 → 5.0 | 5 → 5.0 | 5 → 5.0 | 0 → 0.0 | 0.0 → 0.0 |
| Flour tortillas 12in | pack | 3.49 | 5 → 5.0 | 5 → 5.0 | 5 → 5.0 | 0 → 0.0 | 0.0 → 0.0 |
| Corn tortillas | pack | 2.29 | 5 → 5.0 | 5 → 5.0 | 5 → 5.0 | 0 → -0.0 | 0.0 → -0.0 |
| Shredded cheese | lb | 3.99 | 5 → 5.0 | 5 → 5.0 | 5 → 5.0 | 0 → 0.0 | 0.0 → 0.0 |
| Sour cream | qt | 3.20 | 5 → 5.0 | 5 → 5.0 | 5 → 5.0 | 0 → 0.0 | 0.0 → 0.0 |
| Pico de gallo | qt | 5.50 | 5 → 5.0 | 5 → 5.0 | 5 → 5.0 | 0 → 0.0 | 0.0 → 0.0 |
| Limes | lb | 1.60 | 5 → 5.0 | 5 → 5.0 | 5 → 5.0 | 0 → 0.0 | 0.0 → 0.0 |
| Cilantro | bunch | 0.89 | 5 → 5.0 | 5 → 5.0 | 5 → 5.0 | 0 → 0.0 | 0.0 → 0.0 |
| White onion | lb | 0.99 | 5 → 5.0 | 5 → 5.0 | 5 → 5.0 | 0 → 0.0 | 0.0 → 0.0 |
| Avocados | ea | 1.25 | 5 → 5.0 | 5 → 5.0 | 5 → 5.0 | 0 → 0.0 | 0.0 → 0.0 |
| Jalapeños | lb | 1.49 | 5 → 5.0 | 5 → 5.0 | 5 → 5.0 | 0 → 0.0 | 0.0 → 0.0 |
| Romaine | head | 1.79 | 5 → 5.0 | 5 → 5.0 | 5 → 5.0 | 0 → 0.0 | 0.0 → 0.0 |
| Tomatoes | lb | 1.89 | 5 → 5.0 | 5 → 5.0 | 5 → 5.0 | 0 → 0.0 | 0.0 → 0.0 |
| Salsa roja | qt | 4.25 | 5 → 5.0 | 5 → 5.0 | 5 → 5.0 | 0 → 0.0 | 0.0 → 0.0 |
| Salsa verde | qt | 4.00 | 5 → 5.0 | 5 → 5.0 | 5 → 5.0 | 0 → 0.0 | 0.0 → 0.0 |
| Crema | qt | 4.60 | 5 → 5.0 | 5 → 5.0 | 5 → 5.0 | 0 → 0.0 | 0.0 → 0.0 |
| Queso fresco | lb | 5.10 | 5 → 5.0 | 5 → 5.0 | 5 → 5.0 | 0 → 0.0 | 0.0 → 0.0 |
| Black beans | can | 1.35 | 5 → 5.0 | 5 → 5.0 | 5 → 5.0 | 0 → 0.0 | 0.0 → 0.0 |
| Rice | lb | 0.85 | 5 → 5.0 | 5 → 5.0 | 5 → 5.0 | 0 → 0.0 | 0.0 → 0.0 |
| Fryer oil | jug | 28.00 | 5 → 5.0 | 5 → 5.0 | 5 → 5.0 | 0 → 0.0 | 0.0 → 0.0 |
| Tortilla chips | bag | 6.50 | 5 → 5.0 | 5 → 5.0 | 5 → 5.0 | 0 → 0.0 | 0.0 → 0.0 |
| Shrimp | lb | 8.90 | 5 → 5.0 | 5 → 5.0 | 5 → 5.0 | 0 → 0.0 | 0.0 → 0.0 |
| Fish fillet | lb | 7.40 | 5 → 5.0 | 5 → 5.0 | 5 → 5.0 | 0 → 0.0 | 0.0 → 0.0 |
| Chorizo | lb | 4.30 | 5 → 5.0 | 5 → 5.0 | 5 → 5.0 | 0 → 0.0 | 0.0 → 0.0 |
| Eggs | dozen | 3.10 | 5 → 5.0 | 5 → 5.0 | 5 → 5.0 | 0 → 0.0 | 0.0 → 0.0 |
| Cabbage | head | 1.20 | 5 → 5.0 | 5 → 5.0 | 5 → 5.0 | 0 → 0.0 | 0.0 → 0.0 |
| Radishes | bunch | 1.10 | 5 → 5.0 | 5 → 5.0 | 5 → 5.0 | 0 → 0.0 | 0.0 → 0.0 |
| Chipotle mayo | qt | 5.80 | 5 → 5.0 | 5 → 5.0 | 5 → 5.0 | 0 → 0.0 | 0.0 → 0.0 |
| Horchata mix | bag | 7.25 | 5 → 5.0 | 5 → 5.0 | 5 → 5.0 | 0 → 0.0 | 0.0 → 0.0 |
| Mexican Coke | case | 32.00 | 5 → 5.0 | 5 → 5.0 | 5 → 5.0 | 0 → 0.0 | 0.0 → 0.0 |
| Jarritos | case | 24.00 | 5 → 5.0 | 5 → 5.0 | 5 → 5.0 | 0 → 0.0 | 0.0 → 0.0 |
| Bottled water | case | 6.00 | 5 → 5.0 | 5 → 5.0 | 5 → 5.0 | 0 → 0.0 | 0.0 → 0.0 |
| Ice | bag | 2.50 | 5 → 5.0 | 5 → 5.0 | 5 → 5.0 | 0 → 0.0 | 0.0 → 0.0 |
| Foil wraps | pack | 9.00 | 5 → 5.0 | 5 → 5.0 | 5 → 5.0 | 0 → 0.0 | 0.0 → 0.0 |
| Clamshells | case | 38.00 | 5 → 5.0 | 5 → 5.0 | 5 → 5.0 | 0 → 0.0 | 0.0 → 0.0 |
| Napkins | case | 22.00 | 5 → 5.0 | 5 → 5.0 | 5 → 5.0 | 0 → 0.0 | 0.0 → 0.0 |
| Cups 16oz | sleeve | 4.50 | 5 → 5.0 | 5 → 5.0 | 5 → 5.0 | 0 → 0.0 | 0.0 → 0.0 |

Menu plate costs:

| Menu item | Price | Sold | Plate cost exp → act | Food cost % |
|---|---|---|---|---|
| Al pastor taco | 3.75 | 40 | 1.2725 → 1.2725 | 33.9 |
| Beef taco | 3.5 | 40 | 1.8379 → 1.8379 | 52.5 |
| Carnitas taco | 3.75 | 40 | 1.3754 → 1.3754 | 36.7 |
| Chicken burrito | 11.0 | 20 | 4.5883 → 4.5883 | 41.7 |
| Chorizo & egg burrito | 10.0 | 20 | 11.6408 → 11.6408 | 116.4 |
| Fish taco | 4.25 | 20 | 6.0725 → 6.0725 | 142.9 |
| Guac & chips | 7.0 | 20 | 6.2825 → 6.2825 | 89.8 |
| Horchata | 4.0 | 20 | 3.5625 → 3.5625 | 89.1 |
| Jarritos | 3.0 | 20 | 6.0 → 6.0 | 200.0 |
| Mexican Coke | 3.5 | 20 | 8.0 → 8.0 | 228.6 |
| Quesadilla | 9.0 | 20 | 3.0483 → 3.0483 | 33.9 |
| Shrimp taco | 4.5 | 20 | 4.1083 → 4.1083 | 91.3 |
| Water | 2.0 | 20 | 7.0 → 7.0 | 350.0 |

Count history (newest first): 2026-10-12 Weekly full count — Full truck — Owner — 40 counted; 2026-10-08 Daily end-of-shift — Protein, Proteins, Meat — Crew Ana — 7 counted; 2026-10-06 Daily end-of-shift — Protein, Proteins, Meat — Crew Ana — 7 counted; 2026-10-05 Weekly full count — Full truck — Owner — 40 counted

## Test 2 — 40 products — short  (37/37 checks passed)

| Check | Expected | Actual | OK |
|---|---|---|---|
| rows with wrong on-hand/theoretical/variance | 0 | 0 | ✅ |
| variance rows reported | 40 | 40 | ✅ |
| items flagged by variance report | ['Chicken thigh', 'Clamshells'] | ['Chicken thigh', 'Clamshells'] | ✅ |
| report start = opening weekly 2026-10-05 | 2026-10-05 | 2026-10-05 | ✅ |
| report end = weekly 2026-10-12 | 2026-10-12 | 2026-10-12 | ✅ |
| daily partials skipped by weekly report | 2 | 2 | ✅ |
| total variance $ | 81.58 | 81.58 | ✅ |
| inventory value $ | 1303.92 | 1303.92 | ✅ |
| sales $ in window | 1605.0 | 1605.0 | ✅ |
| ideal COGS $ (theoretical × cost) | 1385.5 | 1385.5 | ✅ |
| actual COGS $ (counted × cost) | 1467.08 | 1467.08 | ✅ |
| food cost % | 91.4 | 91.4 | ✅ |
| ideal food cost % | 86.3 | 86.3 | ✅ |
| order list lines (all below par 8) | 40 | 40 | ✅ |
| order qty = par − on-hand | 0 | 0 | ✅ |
| order list $ | 912.88 | 912.88 | ✅ |
| dashboard low-par count | 40 | 40 | ✅ |
| daily 2026-10-06: no out-of-scope item zeroed | 0 | 0 | ✅ |
| daily 2026-10-06: nothing flagged missing | 0 | 0 | ✅ |
| daily 2026-10-06: counted by crew login | Crew Ana | Crew Ana | ✅ |
| daily 2026-10-08: no out-of-scope item zeroed | 0 | 0 | ✅ |
| daily 2026-10-08: nothing flagged missing | 0 | 0 | ✅ |
| daily 2026-10-08: counted by crew login | Crew Ana | Crew Ana | ✅ |
| plate cost Al pastor taco | 1.2725 | 1.2725 | ✅ |
| plate cost Beef taco | 1.8379 | 1.8379 | ✅ |
| plate cost Carnitas taco | 1.3754 | 1.3754 | ✅ |
| plate cost Chicken burrito | 4.5883 | 4.5883 | ✅ |
| plate cost Chorizo & egg burrito | 11.6408 | 11.6408 | ✅ |
| plate cost Fish taco | 6.0725 | 6.0725 | ✅ |
| plate cost Guac & chips | 6.2825 | 6.2825 | ✅ |
| plate cost Horchata | 3.5625 | 3.5625 | ✅ |
| plate cost Jarritos | 6.0 | 6.0 | ✅ |
| plate cost Mexican Coke | 8.0 | 8.0 | ✅ |
| plate cost Quesadilla | 3.0483 | 3.0483 | ✅ |
| plate cost Shrimp taco | 4.1083 | 4.1083 | ✅ |
| plate cost Water | 7.0 | 7.0 | ✅ |
| count history types (newest first) | ['weekly', 'daily', 'daily', 'weekly'] | ['weekly', 'daily', 'daily', 'weekly'] | ✅ |

Per product (expected → actual):

| Product | Unit | Cost | On-hand | Theoretical | Counted usage | Variance | Variance $ |
|---|---|---|---|---|---|---|---|
| Ground beef | lb | 4.89 | 5 → 5.0 | 5 → 5.0 | 5 → 5.0 | 0 → 0.0 | 0.0 → 0.0 |
| Chicken thigh | lb | 2.79 | 3 → 3.0 | 5 → 5.0 | 7 → 7.0 | 2 → 2.0 | 5.58 → 5.58 |
| Carnitas | lb | 5.25 | 5 → 5.0 | 5 → 5.0 | 5 → 5.0 | 0 → 0.0 | 0.0 → 0.0 |
| Al pastor pork | lb | 4.10 | 5 → 5.0 | 5 → 5.0 | 5 → 5.0 | 0 → 0.0 | 0.0 → 0.0 |
| Flour tortillas 12in | pack | 3.49 | 5 → 5.0 | 5 → 5.0 | 5 → 5.0 | 0 → 0.0 | 0.0 → 0.0 |
| Corn tortillas | pack | 2.29 | 5 → 5.0 | 5 → 5.0 | 5 → 5.0 | 0 → -0.0 | 0.0 → -0.0 |
| Shredded cheese | lb | 3.99 | 5 → 5.0 | 5 → 5.0 | 5 → 5.0 | 0 → 0.0 | 0.0 → 0.0 |
| Sour cream | qt | 3.20 | 5 → 5.0 | 5 → 5.0 | 5 → 5.0 | 0 → 0.0 | 0.0 → 0.0 |
| Pico de gallo | qt | 5.50 | 5 → 5.0 | 5 → 5.0 | 5 → 5.0 | 0 → 0.0 | 0.0 → 0.0 |
| Limes | lb | 1.60 | 5 → 5.0 | 5 → 5.0 | 5 → 5.0 | 0 → 0.0 | 0.0 → 0.0 |
| Cilantro | bunch | 0.89 | 5 → 5.0 | 5 → 5.0 | 5 → 5.0 | 0 → 0.0 | 0.0 → 0.0 |
| White onion | lb | 0.99 | 5 → 5.0 | 5 → 5.0 | 5 → 5.0 | 0 → 0.0 | 0.0 → 0.0 |
| Avocados | ea | 1.25 | 5 → 5.0 | 5 → 5.0 | 5 → 5.0 | 0 → 0.0 | 0.0 → 0.0 |
| Jalapeños | lb | 1.49 | 5 → 5.0 | 5 → 5.0 | 5 → 5.0 | 0 → 0.0 | 0.0 → 0.0 |
| Romaine | head | 1.79 | 5 → 5.0 | 5 → 5.0 | 5 → 5.0 | 0 → 0.0 | 0.0 → 0.0 |
| Tomatoes | lb | 1.89 | 5 → 5.0 | 5 → 5.0 | 5 → 5.0 | 0 → 0.0 | 0.0 → 0.0 |
| Salsa roja | qt | 4.25 | 5 → 5.0 | 5 → 5.0 | 5 → 5.0 | 0 → 0.0 | 0.0 → 0.0 |
| Salsa verde | qt | 4.00 | 5 → 5.0 | 5 → 5.0 | 5 → 5.0 | 0 → 0.0 | 0.0 → 0.0 |
| Crema | qt | 4.60 | 5 → 5.0 | 5 → 5.0 | 5 → 5.0 | 0 → 0.0 | 0.0 → 0.0 |
| Queso fresco | lb | 5.10 | 5 → 5.0 | 5 → 5.0 | 5 → 5.0 | 0 → 0.0 | 0.0 → 0.0 |
| Black beans | can | 1.35 | 5 → 5.0 | 5 → 5.0 | 5 → 5.0 | 0 → 0.0 | 0.0 → 0.0 |
| Rice | lb | 0.85 | 5 → 5.0 | 5 → 5.0 | 5 → 5.0 | 0 → 0.0 | 0.0 → 0.0 |
| Fryer oil | jug | 28.00 | 5 → 5.0 | 5 → 5.0 | 5 → 5.0 | 0 → 0.0 | 0.0 → 0.0 |
| Tortilla chips | bag | 6.50 | 5 → 5.0 | 5 → 5.0 | 5 → 5.0 | 0 → 0.0 | 0.0 → 0.0 |
| Shrimp | lb | 8.90 | 5 → 5.0 | 5 → 5.0 | 5 → 5.0 | 0 → 0.0 | 0.0 → 0.0 |
| Fish fillet | lb | 7.40 | 5 → 5.0 | 5 → 5.0 | 5 → 5.0 | 0 → 0.0 | 0.0 → 0.0 |
| Chorizo | lb | 4.30 | 5 → 5.0 | 5 → 5.0 | 5 → 5.0 | 0 → 0.0 | 0.0 → 0.0 |
| Eggs | dozen | 3.10 | 5 → 5.0 | 5 → 5.0 | 5 → 5.0 | 0 → 0.0 | 0.0 → 0.0 |
| Cabbage | head | 1.20 | 5 → 5.0 | 5 → 5.0 | 5 → 5.0 | 0 → 0.0 | 0.0 → 0.0 |
| Radishes | bunch | 1.10 | 5 → 5.0 | 5 → 5.0 | 5 → 5.0 | 0 → 0.0 | 0.0 → 0.0 |
| Chipotle mayo | qt | 5.80 | 5 → 5.0 | 5 → 5.0 | 5 → 5.0 | 0 → 0.0 | 0.0 → 0.0 |
| Horchata mix | bag | 7.25 | 5 → 5.0 | 5 → 5.0 | 5 → 5.0 | 0 → 0.0 | 0.0 → 0.0 |
| Mexican Coke | case | 32.00 | 5 → 5.0 | 5 → 5.0 | 5 → 5.0 | 0 → 0.0 | 0.0 → 0.0 |
| Jarritos | case | 24.00 | 5 → 5.0 | 5 → 5.0 | 5 → 5.0 | 0 → 0.0 | 0.0 → 0.0 |
| Bottled water | case | 6.00 | 5 → 5.0 | 5 → 5.0 | 5 → 5.0 | 0 → 0.0 | 0.0 → 0.0 |
| Ice | bag | 2.50 | 5 → 5.0 | 5 → 5.0 | 5 → 5.0 | 0 → 0.0 | 0.0 → 0.0 |
| Foil wraps | pack | 9.00 | 5 → 5.0 | 5 → 5.0 | 5 → 5.0 | 0 → 0.0 | 0.0 → 0.0 |
| Clamshells | case | 38.00 | 3 → 3.0 | 5 → 5.0 | 7 → 7.0 | 2 → 2.0 | 76.0 → 76.0 |
| Napkins | case | 22.00 | 5 → 5.0 | 5 → 5.0 | 5 → 5.0 | 0 → 0.0 | 0.0 → 0.0 |
| Cups 16oz | sleeve | 4.50 | 5 → 5.0 | 5 → 5.0 | 5 → 5.0 | 0 → 0.0 | 0.0 → 0.0 |

Menu plate costs:

| Menu item | Price | Sold | Plate cost exp → act | Food cost % |
|---|---|---|---|---|
| Al pastor taco | 3.75 | 40 | 1.2725 → 1.2725 | 33.9 |
| Beef taco | 3.5 | 40 | 1.8379 → 1.8379 | 52.5 |
| Carnitas taco | 3.75 | 40 | 1.3754 → 1.3754 | 36.7 |
| Chicken burrito | 11.0 | 20 | 4.5883 → 4.5883 | 41.7 |
| Chorizo & egg burrito | 10.0 | 20 | 11.6408 → 11.6408 | 116.4 |
| Fish taco | 4.25 | 20 | 6.0725 → 6.0725 | 142.9 |
| Guac & chips | 7.0 | 20 | 6.2825 → 6.2825 | 89.8 |
| Horchata | 4.0 | 20 | 3.5625 → 3.5625 | 89.1 |
| Jarritos | 3.0 | 20 | 6.0 → 6.0 | 200.0 |
| Mexican Coke | 3.5 | 20 | 8.0 → 8.0 | 228.6 |
| Quesadilla | 9.0 | 20 | 3.0483 → 3.0483 | 33.9 |
| Shrimp taco | 4.5 | 20 | 4.1083 → 4.1083 | 91.3 |
| Water | 2.0 | 20 | 7.0 → 7.0 | 350.0 |

Count history (newest first): 2026-10-12 Weekly full count — Full truck — Owner — 40 counted; 2026-10-08 Daily end-of-shift — Protein, Proteins, Meat — Crew Ana — 7 counted; 2026-10-06 Daily end-of-shift — Protein, Proteins, Meat — Crew Ana — 7 counted; 2026-10-05 Weekly full count — Full truck — Owner — 40 counted

## Bugs found and fixed

1. **The weekly sales variance was hijacked by daily partials.** The old code used "the last two completed counts". With Thursday's daily count as the start, only the 4 to 6 protein products were reported, using a 4-day window, and everything else was "not counted in both". Now the report defaults to previous full count → latest full count, skips the partials in between and lists them (`skipped_partials` = 2 above). Products only on a daily list use their own last count.
2. **Variance vs prior used the last session, not the last count of that product.** After a daily count, the next weekly compared non-protein products against nothing. Now the prior is set per product.
3. **The food-cost % sales window used a different date rule than the usage math.** It is now one shared, timing-aware window: end-of-shift counts include that day's sales.
4. **Generic POS CSV didn't recognize a `Sold` column** (the bundled sample uses it). `sold` and `units` were added as quantity aliases.
5. **Crew logins hit a 403** after finishing a count (sent to Variance) and when switching language. Both are fixed.

Bugs 1 and 2 were found while designing the partial counts and are pinned by `tests/test_v13_counts.py`. The simulations then passed on the first run with the fixes in place. The pre-fix code was not re-run through the simulation.

## Not verified
- Real POS exports from Square, Toast or Clover. The simulation used the generic CSV adapter.
- Recipe unit conversion (none exists; recipes are in each product's own unit).
- Clicking through the whole week in a browser. The UI flow for count types is clicked through separately in `tests/e2e_counts.py`.
