# Kes Emas (Golden Set) — alat ukur pengesan selam

Set kes emas = **label manual dari mata user** yang dipakai untuk mengukur ketepatan pengesan
`market_story.py` dengan nombor, bukan perasaan. Rujuk SKILL.md §H3 (gelung peningkatan).

## Cara bina
1. Pilih 10–20 tempoh chart yang anda **TAHU jawapannya** (zon, breakout, trendline yang betul).
2. Untuk setiap tempoh: eksport bar CSV (`scripts/ExportBars.mq5`) + tulis label manual di bawah.
3. Namakan berpasangan: `case_<n>_<SIMBOL>_<TF>_<tarikh>.csv` (bar) dan
   `case_<n>_<SIMBOL>_<TF>_<tarikh>.labels.csv` (label).

## Format `.labels.csv` (koordinat = bar index dalam CSV bar)
```
kind,start_idx,end_idx,lo,hi,note
zone,120,126,4189.10,4196.40,demand - sentuhan pertama ditolak
breakout,142,142,4198.50,,true breakout - bertahan 3 bar
trendline,80,150,,,garis naik anchor bar 80->150
```
`kind` = `zone` | `breakout` | `trendline`. Untuk `breakout`, `note` nyatakan sah/palsu/sweep.

## Ukur precision / recall (jalankan skrip pada kes yang sama)
- **Precision (zon)** = zon skrip yang PADAN dengan label / jumlah zon skrip
- **Recall (zon)** = zon skrip yang padan / jumlah zon label
- **Padan** = jenis sama + pertindihan julat harga ≥50% + lahir dalam ±10 bar
- Ulang untuk breakout (sah/palsu/sweep) dan trendline (sah/patah).
- Catat nombor setiap gelung. Laras **SATU** parameter (`--k`, ambang displacement, toleransi TL,
  tetingkap breakout palsu), ukur semula — itu gelung H3.

## Peraturan anti-overfit pengesan
- Laras parameter pada SEBAHAGIAN kes, sahkan pada yang lain (out-of-sample).
- Setiap kali pengesan diubah: jalankan semula **SEMUA** kes (uji regresi). Jangan baiki satu
  kes dengan merosakkan lima.
- Simpan skor semasa dalam jadual di bawah setiap kali ukur.

## Log pengukuran
| Tarikh | Kes | Parameter | Precision | Recall | Nota |
|---|---|---|---|---|---|
| | | | | | |
