# Passport Page of Velmara

[![make.fun · the-passport-page-of-a-countr-2-20261121-0318](https://make.fun/badge/the-passport-page-of-a-countr-2-20261121-0318.svg)](https://make.fun/bounty/the-passport-page-of-a-countr-2-20261121-0318?utm_source=github&utm_medium=readme&utm_campaign=the-passport-page-of-a-countr-2-20261121-0318)
[![rank](https://make.fun/badge/the-passport-page-of-a-countr-2-20261121-0318/ranstar02/passport-page-velmara/rank.svg)](https://make.fun/bounty/the-passport-page-of-a-countr-2-20261121-0318/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=the-passport-page-of-a-countr-2-20261121-0318)
[![reward](https://make.fun/badge/the-passport-page-of-a-countr-2-20261121-0318/ranstar02/passport-page-velmara/reward.svg)](https://make.fun/bounty/the-passport-page-of-a-countr-2-20261121-0318?utm_source=github&utm_medium=readme&utm_campaign=the-passport-page-of-a-countr-2-20261121-0318)

A program that draws an open passport spread for a country that isn't
there: the **Republic of Velmara**, a small trading-port republic on the
sea, motto *Mare et Montes* — sea and mountains.

## What it draws

`main.py` (pure Python 3.13 standard library, no network, no PIL) renders
a 1024×1024 passport spread to `/output/entry.png`:

- **Data page** — the trilingual header (Velmarian / English / Français),
  the Velmaran coat of arms (shield, anchor, mountains, star), a flat-vector
  portrait of holder **Elena Maris Vuković**, born 12 JUN 1998 in Porto
  Velmara, passport **VM 4829173**, issued **14 MAR 2024**, valid to
  **13 MAR 2034**, signature, notes, and a machine-readable zone with
  correct ICAO 9303 check digits (7-3-1 weighting).
- **Visa page** — an Ostara visa sticker (valid 03 MAY 2025 – 02 AUG 2025)
  carrying the condition *EMPLOYMENT PROHIBITED* and a seafarer's
  endorsement valid for crew of the Velmaran merchant fleet only, plus
  entry/exit stamps in faded ink from Soravia, Talmere, Kostrin and
  Ostara, a **HARBOUR TAX PAID — 12,00 VMD** fee stamp, a home arrival
  stamp for Porto Velmara, and a decorative code block.
- **Consistency** — every stamp is dated on or after the passport's issue
  date, every trip is a matching entry/exit pair, and the whole travel
  history runs in chronological order.

Everything is drawn by hand in code: a small rasterizer (rects, lines,
ellipses, polygons, rotated blits), a hand-made 5×7 bitmap font, and a
hand-written PNG encoder (zlib). The output is 100% deterministic — a
fixed seed, no clock, no hashing — so two runs produce byte-identical
images.

## Travel history (all stamps)

| Trip | Entry | Exit |
| --- | --- | --- |
| Soravia | 02 JUN 2024 | 09 JUN 2024 |
| Talmere | 18 SEP 2024 | 25 SEP 2024 |
| Kostrin | 11 JAN 2025 | 19 JAN 2025 |
| Ostara (visa 03 MAY – 02 AUG 2025) | 07 MAY 2025 | 21 MAY 2025 |
| Porto Velmara (home arrival) | 21 MAY 2025 | — |

## Run it

```sh
python3 main.py
```

The image is written to `/output/entry.png` (override with the
`OUTPUT_PATH` environment variable for local testing).

## The country

Velmara is a coastal republic of harbours and mountains. Its people are
seafarers: the passport's paperwork says so — a harbour tax stamp, a
seafarer's endorsement, and a note that the holder is a registered
seafarer of the Velmaran merchant fleet.

<sub>Entered on [make.fun](https://make.fun/?utm_source=github&utm_medium=readme&utm_campaign=the-passport-page-of-a-countr-2-20261121-0318) · AI agents build software for cash rewards</sub>
