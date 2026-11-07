# Selam.md — Skill `/selam` untuk Cline

> **"Selam" = selam scuba ke dalam data. Jangan renang di permukaan — tengok dasar laut.**
> Log ialah kebenaran. Candle ialah cerita. Nombor ialah bukti. Perasaan bukan bukti.

Skill analisa dagangan MQL5 (fokus XAUUSD) untuk Cline — **v3.2**. Tiga kebolehan yang bekerja
bersama:

| Kebolehan | Apa ia buat |
|---|---|
| 👁 **MATA** | Baca candle & chart macam trader berpengalaman (anatomi bar, struktur, zon, breakout vs sweep, trendline) |
| 🩺 **DOKTOR** | Autopsi trade rugi / trade terlepas dengan bukti log baris-demi-baris + taksonomi punca A–I |
| 🎛 **JURUUJI** | Tuning berdisiplin: perlindungan overfitting (OOS, plateau test, kiraan percubaan), revert bila lebih teruk |

## Kandungan

```
SKILL.md                        ← intipati skill (MUAT INI)
scripts/market_story.py         ← "mata manusia": bar mentah → cerita pasaran + memori kekal
scripts/ExportBars.mq5          ← skrip MT5: eksport bar TERTUTUP ke CSV untuk market_story.py
references/koreksi.md           ← jurnal koreksi bacaan AI (gelung pembelajaran)
references/golden/README.md     ← format kes emas + cara ukur precision/recall pengesan
LICENSE                         ← MIT
```

## Pasang (Cline)

Salin keseluruhan repo ini (atau kandungannya) ke folder skill:

```powershell
git clone https://github.com/Mae6876/Selam.md.git "$env:USERPROFILE\.cline\skills\selam"
```

Kemudian taip `/selam` dalam Cline. Perkataan pencetus lain: "baca candle", "baca pasaran",
"kenapa rugi", "autopsi trade", "audit enjin", "tune gila2", "stress test", "sepatutnya di mana".

## Guna cepat

```bash
# 1. Dalam MT5: jalankan ExportBars.mq5 → <TerminalData>\MQL5\Files\XAUUSD_PERIOD_M15.csv
# 2. Bina cerita pasaran dari bar mentah:
python scripts/market_story.py --csv XAUUSD_PERIOD_M15.csv --atr 14 --k 3 --out story_out
# 3. Bandingkan dengan trade EA:
python scripts/market_story.py --csv XAUUSD_PERIOD_M15.csv --trades trades.csv --out story_out
```

Output: `market_story.md` (garis masa), `bars_annotated.csv`, `trendline_log.csv`,
`trade_context.md` (amaran konteks setiap trade EA), `MARKET_MEMORY.json` (memori kekal).

## Perubahan

| Versi | Apa baharu |
|---|---|
| **v3.2** | Pakej lengkap (`references/` kini wujud, dahulu dirujuk tetapi tiada); memori kekal ke `--out`; pembetulan kecil skrip |
| v3.1 | Bahagian H: baca pasaran dari bar mentah (7 pas), pengesan zon/breakout/trendline, memori, gelung peningkatan; modul mata-trader (B), autopsi (C3), analisa belah & trade terlepas (D), anti-overfitting (E), format output (G) |
| v2.0 | 38+ backtest runs, bug state-loss cooldown, SL "xcun", data menolak tiga idea "bijak" |

## Peraturan besi (ringkas)

Fakta dulu, tafsiran kemudian · jangan reka data · hanya candle tertutup dikira · satu trade tak
membuktikan apa-apa · "TIADA SETUP / TUNGGU" ialah jawapan sah · setiap kesimpulan ada bukti ·
lebih teruk → revert · tiada 100% win rate · sahkan simbol/TF/config sebelum percaya.

## Lesen

MIT — lihat [LICENSE](LICENSE).
