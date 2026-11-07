---
name: selam
description: Deep-dive analisa trade data + baca candle macam mata trader manusia + troubleshooting enjin MQL5 (XAUUSD). Guna SETIAP KALI user sebut "selam", "baca candle", "baca chart", "faham apa candle buat", "kenapa rugi", "kenapa tak entry", "autopsi trade", "baca pasaran", "gali lagi", "trendline salah", "sepatutnya di mana", "audit enjin", "semak entry live", "tune", "stress test", atau tampal log MT5 / screenshot chart / trade register / kod EA untuk dianalisa. Guna juga bila user tanya kenapa EA entry/SL/TP di tempat tertentu, walaupun dia tak sebut "selam".
---

# /selam — Deep-Dive Trade Data + Mata Trader + Engine Tuning (v3.2)

> **"Selam" = selam scuba ke dalam data. Jangan renang di permukaan — tengok dasar laut.**
> Log ialah kebenaran. Candle ialah cerita. Nombor ialah bukti. Perasaan bukan bukti.

Skill ini ada TIGA kebolehan yang bekerja bersama:
1. **MATA** — baca candle & chart macam trader berpengalaman (Bahagian B)
2. **DOKTOR** — troubleshoot trade rugi / enjin rosak dengan bukti (Bahagian C, D)
3. **JURUUJI** — tuning berdisiplin yang tak tertipu oleh overfitting (Bahagian E)

---

## PERATURAN BESI (langgar = analisa tak sah)

1. **Fakta dulu, tafsiran kemudian.** Pisahkan "apa yang NAMPAK" (angka OHLC, jarak, masa) dari
   "apa yang AKU FIKIR" (tafsiran). Jangan campur dalam satu ayat.
2. **Jangan reka data.** Jika harga/masa/skala tak jelas dalam screenshot atau log, TANYA.
   Jangan agak paras harga dari gambar tanpa skala. Katakan "anggaran ±" bila terpaksa.
3. **Candle yang sedang terbentuk tak boleh dipercayai.** Hanya candle TERTUTUP dikira bukti.
4. **Satu trade tak membuktikan apa-apa.** Satu loss boleh jadi varians. Corak perlu sampel
   (lihat had sampel di Bahagian E).
5. **Wajib ada jawapan "TIADA SETUP / TUNGGU"** sebagai pilihan sah. Jangan paksa signal.
6. **Setiap kesimpulan wajib ada bukti**: nombor trade, masa, harga, atau fail:baris.
7. **Data mengalahkan pendapat. Lebih teruk → revert.** Tiada ego.
8. **Tiada 100% win rate.** Sasaran: expectancy positif, loss terkawal, konsisten.
9. **Sahkan sebelum percaya**: simbol, TF, julat tarikh, config, model tick, versi EA.

---

# BAHAGIAN A — PETA LOG MT5 (3 lapis)

| Lapis | Lokasi | Isi | Perangkap |
|---|---|---|---|
| **L1: Log EA live/demo** | `<TerminalData>\MQL5\Logs\YYYYMMDD.log` | `Print()` EA — `[Entry]`, `[SL Hit]`, telemetri | Berputar harian; campur SEMUA EA |
| **L2: Log tester terminal** | `<TerminalData>\tester\logs\YYYYMMDD.log` | Ringkasan deal + `final balance` | KONGSI semua ujian; `final balance` terakhir ≠ larian anda |
| **L3: Log agen tester** | `<TerminalData>\Tester\<hash>\Agent-127.0.0.1-3000\logs\YYYYMMDD.log` | Semua cetakan EA semasa backtest | Boleh ratusan MB — baca ekor sahaja |

### Perangkap medan
- **MT5 single-instance:** `terminal64.exe /config:...` semasa terminal berjalan = TIDAK BUAT APA-APA.
  Bunuh proses dahulu ATAU sahkan baris `testing of Experts\... started` dalam log.
- **Config kongsi ditulis ganti:** satu `tester_config_<projek>.ini` per projek. Semak `Expert=`.
- **Log agen besar:** baca ekor tetap 30–300KB, tapis dengan corak. Jangan `Get-Content` penuh.
- **`final balance` sama to-the-cent untuk config berbeza** = ujian tak berlari / cache. Ulang bersih.
- **Zon masa server ≠ masa tempatan.** Sahkan offset GMT broker + DST sebelum analisa sesi.

### Perintah terbukti
```powershell
# L1: aktiviti EA live — tapis mengikut EA
$log = "$env:APPDATA\MetaQuotes\Terminal\<HASH>\MQL5\Logs\20261105.log"
Select-String -Path $log -Pattern 'NamaEA' |
  ForEach-Object { ($_.Line -replace '^\S+\s+\S+\s+','') } | Select-Object -Last 40

# L2: hasil backtest
$tlog = "$env:APPDATA\MetaQuotes\Terminal\<HASH>\tester\logs\20261105.log"
Select-String -Path $tlog -Pattern 'final balance' | Select-Object -Last 3

# L3: ekor log agen (jangan baca penuh!)
$fs=[IO.File]::Open($alog,'Open','Read','ReadWrite')
$fs.Seek(-300000,'End')|Out-Null; $buf=New-Object byte[] 300000
$fs.Read($buf,0,300000)|Out-Null; $fs.Close()
$txt=[Text.Encoding]::Unicode.GetString($buf)
($txt -split "`n" | Select-String '\[Entry\]|\[SL Hit\]|\[Skip\]|\[Partial\]')
```

### Tag log yang EA WAJIB ada (kalau tiada, cadangkan tambah)
`[Entry]` `[SL Hit]` `[TP Hit]` `[Partial]` `[BE]` `[Trail]` `[Skip]` `[ZoneDiag]` dan
**`[Ctx]`** — satu baris snapshot konteks semasa entry: `trend_HTF, zon[lo-hi], posisi_dalam_zon%,
ATR14, spread, sesi, skor, trigger_candle(body%,wick%,vol_rel)`. Tanpa `[Ctx]`, autopsi hanya
separuh buta. Throttle semua cetakan: 1 per bar.

---

# BAHAGIAN B — MATA TRADER (baca candle & chart)

## B0. Protokol Screenshot / Chart (buat dulu, setiap kali)
1. **Sahkan metadata**: simbol, TF, zon masa, skala harga, indikator/legend. Tak nampak → TANYA.
2. **Cari candle terakhir TERTUTUP.** Candle paling kanan biasanya masih forming — tandakan
   "tidak dipercayai".
3. **Baca dari kiri ke kanan** (konteks → kini), bukan terus ke candle terakhir.
4. **Tulis dua blok berasingan**: `FAKTA` (apa yang nampak) dan `TAFSIRAN` (apa maknanya).
5. Beri **keyakinan 1–5** dan apa yang akan membatalkan tafsiran (invalidation).

## B1. Hierarki konteks (TOP-DOWN — susunan wajib)
Candle cantik di tempat salah = tiada nilai. Tapis dalam urutan ini; gagal satu = berhenti:

| # | Lapis | Soalan | Gagal bermakna |
|---|---|---|---|
| 1 | **Rejim** (H4/D1) | Trending, ranging, atau expansion selepas compression? | Elak strategi salah rejim |
| 2 | **Struktur** (H1/H4) | HH/HL atau LH/LL? Mana swing high/low penting? BOS/CHoCH terbaru? | Tiada bias jelas = tunggu |
| 3 | **Lokasi** | Di zon supply/demand, paras bulat (round number), swing, atau di "tengah-tengah"? | Di tengah = jangan trade |
| 4 | **Reaksi** (M30/M15) | Apa candle buat BILA sampai lokasi? Terima atau tolak? | Tiada reaksi = belum ada trade |
| 5 | **Trigger** (M5/M15) | Candle pengesahan tertutup? | Belum trigger = tunggu |
| 6 | **Risiko** | SL logik, R:R ≥ minimum, spread/berita OK? | R:R cacat = skip |

> Contoh lapis lokasi untuk XAUUSD (sesuaikan dengan definisi anda): **BRN** = paras bulat utama
> (xx00 / xx25 / xx50 / xx75, garis merah), **MRN** = paras perantara (BRN ±12.50, garis kuning).
> Zon yang sah biasanya terbentuk antara BRN dan MRN. Pastikan definisi ini sepadan dengan peraturan
> anda sebelum guna.

## B2. Anatomi satu candle (ukur, jangan agak)
Untuk setiap candle penting, hitung:

| Metrik | Formula | Makna |
|---|---|---|
| Range | `H − L` | Saiz candle |
| Range/ATR | `(H−L) / ATR14` | >1.5 = displacement/momentum; <0.5 = senyap |
| Body% | `|C−O| / (H−L)` | ≥80% = penuh (marubozu); ≤10% = doji/keraguan |
| Wick atas% | `(H − max(O,C)) / (H−L)` | Tolakan dari atas (penjual) |
| Wick bawah% | `(min(O,C) − L) / (H−L)` | Tolakan dari bawah (pembeli) |
| CLV | `(C − L) / (H−L)` | 0 = tutup di dasar, 1 = tutup di puncak |
| Vol relatif | `tickvol / SMA(tickvol,20)` | >1.5 = penyertaan kuat |

**Tafsiran asas (SENTIASA bergantung lokasi):**

| Bentuk | Ciri | Cerita |
|---|---|---|
| **Marubozu / displacement** | Body ≥80%, range >1.5×ATR, vol tinggi | Satu pihak dominan, mungkin tinggalkan imbalance (FVG) |
| **Pin bar / rejection** | Wick ≥60% range, tutup jauh dari hujung wick | Harga ditolak; kuat bila di zon + vol tinggi |
| **Doji / spinning top** | Body ≤10–20% | Keraguan; di zon = potensi pusing, di tengah = bunyi |
| **Engulfing** | Body menelan body sebelumnya, di lokasi | Kawalan bertukar tangan |
| **Inside bar** | Dalam range candle ibu | Mampatan, tunggu pecah |
| **Outside bar** | Menelan H&L sebelumnya | Sapuan dua hala; baca penutupan |
| **Climax / exhaustion** | Range besar selepas larian panjang, body mengecil, vol memuncak | Tenaga habis, bukan kekuatan baharu |
| **Absorption** | Vol tinggi, range kecil | Satu pihak menyerap; pecah lazimnya ikut arah penyerap |

## B3. Baca URUTAN candle (cerita, bukan satu-satu)
Tafsir 3–7 candle sebagai satu naratif. Corak naratif utama:

| Naratif | Urutan | Bacaan |
|---|---|---|
| **Sweep + reclaim** | Wick tembus swing/zon, candle tutup SEMULA di dalam | Likuiditi diambil, kemungkinan pusing — entry berkualiti |
| **Displacement + retest** | Candle besar meninggalkan zon, harga pulang menguji | Kemasukan kedua berkualiti; tunggu candle tolak |
| **Kemampatan → pengembangan** | Range mengecil berturut-turut, kemudian bar besar | Arah pecah = arah bias; waspada pecah palsu |
| **Tangga (staircase)** | Higher lows + body sederhana, tiada wick besar | Trend sihat; jangan lawan |
| **Klimaks + pembalikan** | Larian panjang, bar rakus, kemudian engulfing lawan | Pusingan; sahkan di lokasi |
| **Churn** | Banyak doji/inside bar bertindih di zon | Tiada pemenang — JANGAN entry, tunggu penyelesaian |

## B4. Pecah paras: SAH atau PALSU?
| Fenomena | Syarat | Tindakan |
|---|---|---|
| **Rejection** | Masuk zon, CLOSE semula di luar | Entry sah, lokasi terbaik |
| **True breakout** | Close melepasi + bertahan >3 bar + displacement | Jangan lawan; tunggu retest |
| **Fake breakout** | Wick/close tembus tapi pulang dalam 3 bar | Peluang counter — hanya jika DATA sokong |
| **Retest** | Pulang menguji paras yang dipecahkan, ditolak | Entry kualiti kedua |
| **Zon patah** | Close penuh melepasi tepi jauh zon | Zon mati |
| **Zon lemah** | Sudah disentuh 3+ kali | Menurun kekuatannya |

Peraturan emas: **close mengesahkan, wick hanya mencadangkan.**

## B5. Skor pertemuan (confluence) — telus, bukan sihir
Beri 0/1 setiap faktor, jumlah = skor. Skor mesti ditunjukkan DENGAN faktor:

`[ ] Searah bias HTF  [ ] Di zon sah (belum patah)  [ ] Posisi dalam zon baik (kedekatan tepi tolakan)
 [ ] Candle trigger tertutup  [ ] Vol relatif >1.2  [ ] Sweep/reclaim hadir
 [ ] Bersih dari berita  [ ] R:R ≥ min  [ ] Sesi sesuai`

Jangan jadikan skor tinggi satu-satunya syarat — data pernah tunjuk penapis skor terlalu tinggi
memotong winner. Gunakan skor sebagai LABEL untuk dianalisa kemudian, bukan hakim mutlak.

## B6. Mata terhadap OUTPUT ENJIN
Bila user tunjuk screenshot entri EA, jawab empat soalan:
1. **Apa yang enjin nampak?** (zon/penunjuk mana yang mencetuskan)
2. **Apa yang trader manusia nampak?** (konteks, lokasi, naratif)
3. **Adakah sama?** Jika tidak, di mana jurangnya (konteks HTF? lokasi? trigger?)
4. **Boleh dikodkan?** Terjemah jurang jadi peraturan yang boleh diukur (cth `posisi_zon ≤ 40%`,
   `close bar-1 di luar zon`, `vol_rel ≥ 1.2`) — kemudian uji di Bahagian E.

---

# BAHAGIAN C — METODOLOGI 5 LANGKAH

## Langkah 1: Baca log, bukan sekadar laporan
Laporan .htm = ringkasan. Log = sebab. Tentukan lapis log (A), tapis ikut tag, baca SETIAP baris trade.

| Corak dalam log | Makna |
|---|---|
| `[Entry] BUY 0.87 @4045.36 \| SL 4039.50 (59p) \| TP ... \| zon[..-..]` | Entry penuh geometri — simpan |
| `[SL Hit] PnL -478.83 — cooldown 3 bar` | Loss + config cooldown LIVE (bandingkan dengan preset!) |
| `[Partial] 50% @+103p` | Pengurusan berjalan |
| `[ZoneDiag] res[99999.00-99999.00]` | Buffer indikator KOSONG |
| `[Skip] risiko 150p > had 250` | Penapis bekerja — kira kekerapan |
| `init` berulang 2–3 min | EA reload, state hilang |
| `final market buy ... [Market closed]` | Pengiraan waktu sesi salah |
| `invalid stops` / `[10016]` | SL/TP melanggar stops level |
| `requote` / `off quotes` / slippage besar | Isu pelaksanaan |
| `not enough money` / `volume` invalid | Lot/margin salah |

## Langkah 2: Bina Daftar Dagangan (Trade Register)
Padankan deal in↔out. Lajur WAJIB:

```
| # | Masa | Arah/Lot | Entry | SL (p/$) | TP | Posisi zon% | R:R | MAE | MFE | Pegang | Keluar | Hasil (R & $) |
```
- **R-multiple** = hasil / risiko awal. Lapor dalam R, bukan hanya $ (bandingan adil antara lot).
- **MAE** (adverse maksimum) & **MFE** (favorable maksimum) dari log tick/bar — mendedahkan SL
  terlalu sempit (MAE hampir SL sebelum menang) atau TP terlalu jauh (MFE besar tapi pulang).
- **Posisi zon** = `(px − zLo)/(zHi − zLo)`. SELL di <25% = mengejar pecahan; BUY di >75% = sama.
- **Pegang <5 min & kena SL** = hampir pasti SL terlalu sempit/lokasi salah.
- XAUUSD: $1.00 = 10 pip = 1 candle M15 kasar (sahkan pada broker).

## Langkah 3: AUTOPSI TRADE (templat wajib untuk "kenapa rugi?")

Untuk SETIAP loss penting (atau yang user tuding), isi templat ini:

```
AUTOPSI TRADE #N
1. FAKTA        : masa, arah, entry, SL, TP, lot, spread semasa, ATR14, hasil (R,$), pegang
2. KONTEKS HTF  : rejim, bias H1/H4, struktur terakhir (BOS/CHoCH)           → betul/salah/tidak jelas
3. LOKASI       : zon/paras, posisi dalam zon %, sentuhan ke-berapa, zon masih sah? → betul/salah
4. REAKSI/TRIGGER: candle apa yang mencetuskan (body%, wick%, vol_rel); close atau wick?
5. NARATIF      : 3–7 candle sebelum entry bercerita apa? (sweep? churn? klimaks?)
6. GEOMETRI     : SL logik? (vs 1.5×ATR, vs zon), R:R sebenar, TP realistik?
7. PENGURUSAN   : partial/BE/trail bertindak betul? Ada yang memadam profit?
8. MASA/EXTERNAL: sesi, berita, gap, spread melebar?
9. KOS/PELAKSANAAN: slippage, requote, swap
10. KOD         : ada bug (rujuk Senarai Semak)? log menyokong?
VERDIK          : punca UTAMA (satu), punca sokongan, kategori (A–I di bawah)
BUKTI           : baris log / nombor candle
BETULKAN        : perubahan SPESIFIK + bagaimana mengujinya (jangan terus ubah kod)
```

**Taksonomi punca (pilih SATU utama):**
| Kod | Punca | Contoh |
|---|---|---|
| A | Konteks salah | Lawan trend HTF / rejim salah |
| B | Lokasi salah | Entry kejar, bukan di tepi tolakan |
| C | Trigger lemah | Entry atas wick, bukan close; tiada pengesahan |
| D | Geometri cacat | SL terlalu sempit/lebar; R:R 0.12:1 |
| E | Pengurusan | Partial terlalu awal; BE terlalu hampir; trail memotong |
| F | Masa/berita | Entry sebelum NFP; sesi sempit |
| G | Kos | Spread melebar, slippage |
| H | Bug kod | State hilang, repaint, handle bocor |
| I | **Varians normal** | Setup BETUL, tetap kalah — kos perniagaan |

> **Kategori I penting.** Jika semua kriteria betul dan loss tetap berlaku, JANGAN ubah peraturan.
> Mengejar setiap loss = overfitting. Katakan terus terang "ini loss normal".

**Kajian kes (EA Flow3D_ZoneTrend, live demo, Trade 2):**
```
SELL @4104.73, zon supply [4105.16-4116.76]
→ Entry 0.07 DI BAWAH tepi bawah zon = mengejar harga yang dah pecah zon (kategori B)
→ SL 150p (tepi atas zon +30p), TP 301p → risiko ≈ 5–8× ganjaran (kategori D)
→ Harga naik semula → SL −$478.83, padam semua partial.
Punca utama: B (lokasi). Sokongan: D.
```

## Langkah 4: Cadangan berdasarkan data (terima/tolak dengan nombor)
Gelung: **ubah SATU benda → backtest config SAMA → banding → terima/tolak.** Lihat Bahagian E.

| Eksperimen | Hasil | Keputusan | Sebab |
|---|---|---|---|
| Cooldown 3→20 bar | +23%→+50% | ✅ | Churn re-entry ialah punca loss |
| Cooldown 35 | +77.7% | ✅ | Puncak keluk (lihat Ujian Dataran di E) |
| Cooldown 100 | +16.8% | ❌ | Ketinggalan isyarat |
| ATR floor SL 1.5×ATR14 | +88.5% | ✅ | SL tak boleh dalam 1 candle |
| Tiered ATR 2.0× | +52.5% | ❌ | Lot kecil + R:R tak capai min |
| Filter separuh zon | +48% | ❌ | Tunggu lokasi "sempurna" = lepas win |
| MinScore 65 | +20.5% | ❌ | Skor tinggi potong winner |

## Langkah 5: Backtest & banding — aturan kejujuran
- Config SAMA (simbol, TF, tarikh, deposit, model tick). Tanpa ini = dusta.
- Run terdahulu = baseline; simpan SEMUA `final balance` dalam satu jadual.
- Lebih teruk → revert. Lebih baik → baseline baharu.
- Satu perubahan sahaja per ujian. Jangan lancar ujian bila terminal sibuk.

---

# BAHAGIAN D — KELAS ANALISA TAMBAHAN

## D1. "Kenapa EA TAK entry?" (analisa trade terlepas)
1. Kira baris `[Skip]` ikut sebab; susun mengikut kekerapan.
2. Untuk 5 candle setup yang user nampak tapi EA tak ambil: cari baris log pada masa itu.
3. Sebab biasa: penapis spread, risiko > had, cooldown aktif, zon belum sah, skor di bawah ambang,
   sesi tertutup, handle indikator `INVALID_HANDLE`, buffer kosong (99999).
4. Kontrafaktual: andai penapis X dilonggarkan, berapa trade tambahan & ia menang/kalah? (Ukur, jangan rasa.)

## D2. Analisa belah (segmentasi) — di mana edge sebenar
Pecahkan semua trade ikut: **jam / sesi (Asia, London, NY, overlap) / hari / arah (BUY vs SELL) /
posisi zon (kuartil) / tempoh pegang / ATR regim (rendah, sederhana, tinggi) / skor.**
Untuk setiap kelompok kira: N, win%, avg R, PF, jumlah R. Cari kelompok yang MEMBUNUH edge
(jumlah R negatif konsisten, N ≥ 30) dan kelompok yang MENGANGKAT edge. Cadangan = potong yang
membunuh, bukan tambah yang rumit.

## D3. Kesihatan ekuiti
`Expectancy = win% × avgWin_R − loss% × avgLoss_R` (mesti >0 selepas kos)
Lapor juga: PF, recovery factor, max DD (% & tempoh), **rentetan kalah maksimum** (untuk saiz risiko),
sebaran hasil bulanan, dan sama ada profit bergantung pada <5 trade (rapuh) — buang 5 trade terbaik &
lihat samada masih untung.

## D4. Analisa pengurusan (partial / BE / trail)
Bandingkan: (a) tiada pengurusan, (b) partial sahaja, (c) partial+BE, (d) +trail. Guna MFE: jika MFE
jauh melebihi keluar sebenar secara konsisten, trail/TP terlalu cepat; jika MAE sering menyentuh BE
lalu dihentam, BE terlalu hampir. Trade pegang >3 jam sering enjin profit — pastikan pengurusan tak
memotongnya.

## D5. Realisme pelaksanaan
Backtest mesti diuji dengan: spread +50%, slippage 1–3 pip, kelewatan, dan tick sebenar. Jika edge
hilang di bawah tekanan kos, ia bukan edge. Banding spread tester vs spread live dalam log.

---

# BAHAGIAN E — PERLINDUNGAN OVERFITTING (jangan tertipu diri sendiri)

1. **Had sampel**: jangan ubah peraturan berdasarkan <30 trade per kelompok. <100 trade total =
   kesimpulan "tentatif".
2. **In-sample / out-of-sample**: bahagi tempoh (cth 70/30). Tune di IS, sahkan di OOS. Jika OOS
   jauh lebih lemah → overfit.
3. **Walk-forward**: tune tetingkap 1 → uji 2 → gelongsor. Hasil stabil merentasi tetingkap = kukuh.
4. **Ujian dataran (plateau test)**: parameter terbaik mesti dikelilingi nilai jiran yang juga baik.
   Cooldown 35 = +78%? Semak 30 & 40. Jika jatuh mendadak = puncak rapuh (kebetulan). Pilih tengah
   dataran, bukan puncak tajam.
5. **Bilangan percubaan**: semakin banyak kombinasi dicuba ("tune gila2"), semakin besar peluang
   menjumpai hasil kebetulan. Catat berapa banyak kombinasi diuji; jadi lebih skeptikal bila banyak.
6. **Satu perubahan serentak.** Dua perubahan = tak tahu punca.
7. **Semak sensitiviti data**: ulang pada simbol/tempoh/broker lain jika boleh. Edge sebenar tak
   bergantung pada satu tempoh.
8. **Logik dulu, data kemudian**: peraturan yang ada sebab trading yang masuk akal (cth "jangan
   kejar harga yang dah pecah zon") lebih dipercayai daripada parameter rawak yang kebetulan bagus.
9. **Kos kompleksiti**: setiap penapis tambahan = satu lagi tempat overfit. Utamakan peraturan ringkas.

---

# BAHAGIAN F — SENARAI SEMAK BUG

| # | Kelas | Gejala | Pembaikan |
|---|---|---|---|
| 1 | State hilang semasa re-init | `init` berulang; cooldown tak jalan; partial 2× | `GlobalVariableSet/Get` dalam `OnInit` |
| 2 | Log spam per tick | Journal ratusan baris/saat | Throttle per bar (`iTime(...,0)!=lastBar`) |
| 3 | Repaint (baca bar forming) | Nilai berubah dalam bar; backtest ≠ live | Baca indikator pada **shift 1** |
| 4 | Bocor masa depan (HTF) | Skor HTF guna bar masih terbentuk | `iBarShift(...)+1` |
| 5 | Single-instance tester | Laporan tak dijana, log tunjuk deal lama | Bunuh `terminal64`, sahkan `started` |
| 6 | Config kongsi ditulis ganti | EA salah dilancar | Satu `.ini` per projek |
| 7 | Handle bocor | "too slow", had 512 handle | Cipta `OnInit`, lepas `OnDeinit` |
| 8 | SL terlalu sempit | Kena <5 min | Lantai `1.5×ATR14` (jangan >1.5×) |
| 9 | Zon buatan (fallback) | SL dalam noise | Mod ketat: zon penunjuk sebenar sahaja |
| 10 | Cache/sesi bercampur | `final balance` sama untuk config beza | Ulang bersih |
| 11 | Offset masa/DST salah | Entry "di luar sesi", sesi tersilap | Kira sesi dari GMT + offset broker |
| 12 | Stops/freeze level | `invalid stops` | Semak `SYMBOL_TRADE_STOPS_LEVEL`, laras SL/TP |
| 13 | Pembundaran lot | Partial gagal/lot minimum | `SYMBOL_VOLUME_STEP/MIN`, normalisasi |
| 14 | Filling mode salah | Order ditolak broker | Pilih `ORDER_FILLING_*` ikut `SYMBOL_FILLING_MODE` |
| 15 | Magic number berlanggar | Dua EA uruskan trade satu sama lain | Magic unik per EA/simbol |
| 16 | Buffer separuh / `CopyBuffer` gagal | Nilai 0 atau `EMPTY_VALUE` | Semak return value, `ArraySetAsSeries`, `BarsCalculated` |
| 17 | Logik "bar baharu" salah | Entry berganda dalam bar sama | Satu pintu `IsNewBar()` |
| 18 | Spread dinamik diabaikan | SL kena oleh spread sahaja | Masukkan spread dalam pengiraan SL/entry |

### Corak GlobalVariable (state kekal)
```mql5
g_gvLoss = "EA_loss_" + _Symbol + "_" + (string)InpMagicNumber;
if(GlobalVariableCheck(g_gvLoss)) g_lastLossBarTime = (datetime)GlobalVariableGet(g_gvLoss);
// SL hit:  GlobalVariableSet(g_gvLoss, (double)g_lastLossBarTime);
// partial per tiket: simpan "EA_partial_<ticket>", pulihkan bila tiket sama, padam bila ditutup
```

### Pengira candle (rujukan pantas, MQL5)
```mql5
double rng = high[1]-low[1];
double body = MathAbs(close[1]-open[1])/rng;
double upW  = (high[1]-MathMax(open[1],close[1]))/rng;
double loW  = (MathMin(open[1],close[1])-low[1])/rng;
double clv  = (close[1]-low[1])/rng;
double rATR = rng/atr14;          // >1.5 = displacement
double vrel = (double)tickvol[1]/avgTickVol20;
```

---

# BAHAGIAN G — FORMAT OUTPUT

## G1. "Baca candle / baca chart" → gunakan ini
```
📍 METADATA : simbol / TF / zon masa / skala (disahkan atau DITANYA)
👁 FAKTA    : (tiada tafsiran) candle X: O/H/L/C, body%, wick%, vol_rel; paras Y; jarak Z
🧠 TAFSIRAN : naratif 3–7 candle + hubungan dengan zon/struktur
🎯 BIAS     : BUY / SELL / TUNGGU  (keyakinan 1–5, kerana ...)
✅ TRIGGER  : apa yang perlu berlaku (candle apa, close di mana)
❌ INVALID  : apa yang membatalkan idea ini
⚖ RISIKO   : SL logik, TP, R:R
```

## G2. "Kenapa rugi?" → Autopsi (Langkah 3) + ringkasan 3 baris:
`Punca utama:` / `Bukti:` / `Betulkan (dan cara menguji):`

## G3. Laporan tuning → jadual: eksperimen | perubahan | hasil | vs baseline | terima/tolak | sebab.

## G4. Jurnal mingguan (bila diminta)
Trade count, win%, avg R, PF, expectancy, DD, punca loss mengikut kod A–I, satu pelajaran,
satu eksperimen seterusnya (bukan lima).

---

# BAHAGIAN H — BACA PASARAN DARI BAR MENTAH (MATA MANUSIA YANG SEBENAR)

> **Masalah yang skill ini mesti selesaikan:** AI biasanya baca LAPORAN dan LOG lalu bercerita
> tentang angka. Ia tak faham *apa candle buat*. Ia tak tahu zon mana sepatutnya, breakout mana
> sah, trendline mana betul, atau kenapa trendline asyik berubah. **Itu bukan analisa. Itu
> membaca keputusan tanpa nampak permainan.**

## H0. Prinsip (wajib)
1. **JANGAN mulakan dari laporan .htm atau ringkasan EA.** Mulakan dari BAR MENTAH (OHLC + tick volume).
   Tiada bar mentah = berhenti dan minta. Jangan teruskan dengan laporan sahaja.
2. **AI tak "nampak" chart. AI membina semula chart dari angka.** Jadi tugasnya: ubah setiap bar jadi
   fakta (anatomi), ubah rentetan bar jadi cerita (struktur, zon, breakout, trendline), kemudian
   bandingkan cerita itu dengan apa yang EA lakukan.
3. **Baca SEMUA bar, bukan sampel.** Corak penting selalu bersembunyi di bar yang "membosankan".
4. **Simpan apa yang dipelajari** (MARKET_MEMORY.json) dan **gali lagi** pada pas seterusnya.
   Satu bacaan = permukaan. Beberapa pas + hipotesis + ujian statistik = dasar laut.
5. **Tiada look-ahead.** Swing hanya wujud SELEPAS k bar pengesahan. Zon, garisan, struktur hanya
   guna maklumat yang EA boleh tahu pada masa itu. Jika tidak, "sepatutnya" itu tipu.
6. **Candle terakhir (forming) tak dikira.**

## H1. Kemahiran yang skill ini MESTI ada (dan alatannya)

| # | Kemahiran | Soalan yang dijawab | Alat / sumber |
|---|---|---|---|
| 1 | **Rekonstruksi chart** | Apa sebenarnya OHLC tiap bar? | `scripts/ExportBars.mq5` → CSV |
| 2 | **Anatomi candle** | Body/wick/CLV/range-ATR/vol tiap bar bercerita apa? | `market_story.py` (`annotate`) |
| 3 | **Swing & struktur** | Mana HH/HL/LH/LL? Bila BOS / CHoCH? | `market_story.py` (`find_swings`, tiada look-ahead) |
| 4 | **Pengesan zon** | Zon lahir bila? Disentuh berapa kali? Ditolak atau patah? | `market_story.py` (zon dari displacement) |
| 5 | **Breakout vs sweep vs palsu** | Pecah sebenar atau ambil likuiditi? Bertahan 3 bar? | `market_story.py` (breakout classifier) |
| 6 | **Trendline + kestabilan** | Garis sah? Anchor berubah? Ditembusi betul atau palsu? | `market_story.py` (trendline_log.csv) |
| 7 | **Rekonsiliasi dengan EA** | Apa EA nampak vs apa pasaran tunjuk? Sepatutnya di mana? | `--trades trades.csv` → `trade_context.md` |
| 8 | **Memori & hipotesis** | Apa yang konsisten merentasi tempoh? | `MARKET_MEMORY.json` |
| 9 | **Bacaan visual screenshot** | Apa yang user tunjuk pada chart? | Protokol B0 (sahkan skala dulu) |
| 10 | **Pembelajaran dari koreksi user** | Di mana AI tersilap baca? | `references/koreksi.md` (H5) |

Jalankan:
```bash
python scripts/market_story.py --csv XAUUSD_PERIOD_M15.csv --atr 14 --k 3 --out story_out
python scripts/market_story.py --csv XAUUSD_PERIOD_M15.csv --trades trades.csv --out story_out
```
Hasil: `market_story.md` (garis masa penuh), `bars_annotated.csv`, `trendline_log.csv`,
`trade_context.md`, dan `<out>/MARKET_MEMORY.json` (memori kekal — terkumpul antara larian pada
`--out` yang sama; ganti lokasi dengan `--memory <path>` jika perlu).

## H2. Prosedur 7 pas (apa yang MESTI dibuat, berurutan)

**Pas 0 — Data.** Eksport bar (ExportBars.mq5). Pastikan EA mencetak `[ZoneDiag]`, `[TLDiag]`, `[Ctx]`
(lihat H6). Sahkan simbol, TF, zon masa, julat tarikh. Tiada bar = berhenti.

**Pas 1 — Anotasi setiap bar.** Jalankan skrip. Baca `bars_annotated.csv`: bar `displacement_*`,
`pin_*`, `doji`, `inside_bar`, `senyap`. Tanya: di mana kluster displacement? di mana churn (banyak
doji/inside)? Itu "peta tenaga" pasaran.

**Pas 2 — Struktur.** Dari swing: tulis urutan HH/HL/LH/LL dan setiap BOS/CHoCH. Tandakan bila
rejim bertukar (trend → range → trend). Struktur ialah rangka; semua lain bergantung padanya.

**Pas 3 — Zon.** Untuk setiap zon: lahir dari bar mana, berapa ATR displacement, sentuhan ke-1/2/3
bagaimana (tolak/patah). Rumus pertama kali disentuh vs ketiga kali. Statistik: kadar tolakan
sentuhan pertama vs seterusnya. Itulah bukti peraturan "1st touch" anda (atau penafiannya).

**Pas 4 — Breakout.** Untuk setiap pecah paras: sah / palsu / sweep. Cari ciri pembeza breakout sah
(displacement? vol_rel? tutup jauh dari paras? waktu sesi?). Itulah "kenapa pecah ini berjaya".

**Pas 5 — Trendline (diagnosis tiga kemungkinan).**
Jika user kata "trendline salah / tak dikesan / asyik berubah", semak SATU-SATU:
| Kemungkinan | Cara semak | Pembaikan |
|---|---|---|
| **Tak dikesan** | Anchor tak cukup; `k` swing terlalu besar; tiada pasangan sah (garis sentiasa ditembusi) | Kurangkan `k`; cuba TF lebih tinggi; longgarkan toleransi (0.1×ATR) |
| **Salah** | Garis ditembusi close ANTARA anchor; anchor bukan swing sebenar; kecerunan terlalu curam | Wajib: tiada close menembus antara anchor; minimum 3 sentuhan; had kecerunan |
| **Sering berubah** | `trendline_changes_per_100bars` tinggi (>5 = tak stabil); anchor bertukar tiap swing baharu | **Kunci anchor** sehingga garis patah; hysteresis (garis baharu hanya ganti jika lebih sah); guna swing yang SUDAH disahkan sahaja; elak repaint |
Ukur kestabilan sebelum dan selepas pembaikan — nombor mesti bertambah baik.

**Pas 6 — Rekonsiliasi dengan EA ("sepatutnya di mana?").**
Untuk SETIAP trade EA dan setiap setup yang EA langkau: bandingkan dengan peta pasaran:
- Entry dalam zon sah? posisi %? sentuhan ke berapa? (`trade_context.md`)
- Searah struktur? Lawan trend?
- SL < 1.5×ATR? Sebelum/ selepas sweep?
- Jika EA salah: nyatakan **di mana harga sepatutnya** (zon/paras/candle) dan **kenapa** (bukti bar).
- Jika EA betul tetapi kalah: kategori I (varians). Jangan ubah.
Hasil: jadual `EA nampak | Pasaran tunjuk | Jurang | Boleh dikodkan?`

**Pas 7 — Soal pasaran, simpan, gali lagi.**
Jawab (dengan bukti bar) dan simpan dalam memori:
1. Siapa menguasai sekarang (pembeli/penjual) dan sejak bila?
2. Likuiditi mana sudah diambil? Mana belum (magnet)?
3. Zon mana dihormati, mana patah — dan apa beza keduanya?
4. Breakout mana berjaya — apa ciri sama?
5. Trendline mana dihormati? Kenapa yang lain gagal?
6. Apa yang BERUBAH berbanding tempoh sebelumnya (rejim, volatiliti, sesi aktif)?
Kemudian rumuskan **hipotesis** ("zon disentuh kali pertama menolak 70%") dan **UJI** (N≥30, OOS)
sebelum jadikan peraturan. Hipotesis tanpa ujian hanyalah pendapat.

## H3. Cara menambah baik skill ini (gelung peningkatan)

1. **Set kes emas.** User labelkan manual 10–20 chart: zon, breakout, trendline yang BETUL. Simpan
   dalam `references/golden/`. Ukur ketepatan pengesan: `precision` (berapa yang dikesan memang betul)
   dan `recall` (berapa yang betul berjaya dikesan). Sasaran jelas, bukan perasaan.
2. **Laras pengesan berasaskan kes emas**, bukan teka: `--k`, ambang displacement (1.5×ATR, body 70%),
   toleransi trendline (0.1×ATR), tetingkap breakout palsu (3 bar). Satu laras, ukur semula.
3. **Regresi.** Setiap kali ubah pengesan, jalankan semula pada SEMUA kes emas + koreksi lama. Jangan
   betulkan satu kes dengan merosakkan lima.
4. **Tambah detektor lapis paras user.** Kod BRN (xx00/25/50/75) dan MRN (±12.50) sebagai paras
   rujukan; kira tindak balas harga pada setiap paras (tolak/patah) — cantum dengan zon.
5. **Multi-TF.** Jalankan H1 (konteks) + M15/M5 (trigger); zon H1 hendaklah menapis entry M15.
6. **Kaji kegagalan pengesan.** Bila skrip dan mata user tak sama, tulis kenapa (H5) — itu bahan
   pembelajaran paling berharga.
7. **Elak overfit pengesan.** Laras pada satu tempoh, sahkan pada tempoh lain (Bahagian E).

## H4. Had yang mesti diakui (jujur)
- Skrip ialah **peraturan terkod**, bukan penglihatan sebenar. Ia mewakili cara baca yang dinyatakan
  dalam kod; ia boleh silap, terutama zon dan trendline yang subjektif.
- Pengesanan zon di sini "lahir dari displacement + candle berlawanan terakhir" sahaja. Gaya anda
  (BRN→MRN, case-by-case) mungkin berbeza — **sesuaikan, jangan percaya buta.**
- Screenshot dibaca secara visual dan hanya anggaran; jangan beri angka harga tepat tanpa skala.
- Output skrip ialah **bahan bukti**, bukan keputusan dagangan.

## H5. Pembelajaran dari koreksi user (WAJIB bila user betulkan AI)
Bila user kata "AI salah baca", rekod dalam `references/koreksi.md`:
```
## YYYY-MM-DD | simbol TF | bar/masa
- AI kata    : ...
- Sebenarnya : ... (apa yang user nampak)
- Sebab AI salah : (peraturan terlalu ketat/longgar? data kurang? konteks HTF terlepas?)
- Perubahan pengesan : (parameter / peraturan baharu)
- Disahkan pada kes emas lain: ya/tidak
```
Baca fail ini pada permulaan setiap sesi "baca pasaran" supaya kesilapan yang sama tak berulang.

## H6. Apa yang EA mesti log supaya "mata" ini boleh bekerja
```
[TLDiag] bar=<time> kind=<up|dn> A=<time,price> B=<time,price> val=<garis pada bar> status=<baru|kekal|patah>
[ZoneDiag] bar=<time> id=<n> type=<supply|demand> lo=<> hi=<> touches=<n> state=<fresh|touched|dead>
[Ctx] bar=<time> trend_htf=<> zone=<id> pos%=<> atr=<> spread=<> sesi=<> trigger=<label body% wick% vrel>
```
Throttle 1 per bar. Tanpa log ini, AI hanya boleh meneka apa yang EA "nampak".

## H7. Format laporan "Cerita Pasaran"
```
1. PETA     : rejim, struktur (HH/HL...), tempoh, TF
2. TENAGA   : kluster displacement, kawasan churn, sesi paling aktif
3. ZON      : jadual id | jenis | julat | lahir | sentuhan | tolak/patah | status
4. BREAKOUT : jadual paras | sah/palsu/sweep | ciri pembeza
5. TRENDLINE: sah? stabil? (changes/100 bar) — sebelum vs selepas pembaikan
6. EA vs PASARAN: jadual jurang + "sepatutnya di mana"
7. PASARAN BERITAHU: jawapan enam soalan (Pas 7) + hipotesis + status ujian
8. LANGKAH SETERUSNYA: SATU eksperimen
```

---

# JADUAL ARAHAN

| User sebut | Selam buat |
|---|---|
| "selam code" | Baca log agen trade-by-trade → daftar → corak |
| "baca pasaran" | Bahagian H: bar mentah → skrip → 7 pas → laporan "Cerita Pasaran" |
| "gali lagi" | Pas seterusnya: hipotesis dari MARKET_MEMORY → uji statistik |
| "trendline salah?" | Pas 5: diagnosis tak dikesan / salah / sering berubah + ukur kestabilan |
| "sepatutnya di mana?" | Pas 6: bandingkan entry EA dengan zon/paras/struktur sebenar |
| "ajar selam" / "AI salah baca" | H5: rekod koreksi, laras pengesan, uji regresi |
| "baca candle" / "baca chart" | Protokol B0 → format G1 |
| "faham apa candle buat" | Naratif B3 + anatomi B2 pada candle bernama |
| "kenapa rugi?" | Daftar → autopsi (Langkah 3) → taksonomi A–I |
| "autopsi trade #N" | Templat autopsi penuh untuk satu trade |
| "kenapa tak entry?" | D1 trade terlepas |
| "audit enjin" | Config + kod + Senarai Semak Bug + tag `[Ctx]` |
| "semak entry live" | L1 → daftar → corak loss → cadangan beracuan data |
| "di mana edge aku?" | D2 segmentasi + D3 kesihatan ekuiti |
| "tune gila2" | Grid + Bahagian E (OOS, plateau, kiraan percubaan) |
| "stress test" | D5 realisme pelaksanaan |
| "kenapa xikut X?" | Baca laluan kod + tambah `[XDiag]` throttled → jawab dengan bukti |
| "jurnal mingguan" | G4 |
| "gila2" | Data mentah + analisa mendalam |

## Bergabung dengan /swarm
1. `/swarm` = audit kod selari (fail:baris, baiki, kompil)
2. `/selam` = analisa data (log → daftar → autopsi → tuning)
3. Susunan: **swarm** (kod betul) → **selam** (strategi untung) → **backtest** (sahkan, termasuk OOS)

## Wawasan kunci (dipelajari secara perit)
> Counter = OFF menggandakan profit & separuh DD (data EA tertentu — sahkan semula pada EA lain).
> TP 8.0 sweet spot (HD engine). Trade pegang >3 jam = enjin profit (92% profit).
> Cooldown churn = pembunuh senyap #1 (3→35 bar = +23%→+78%).
> SL 1.5×ATR, jangan lebih. Config live ≠ config backtest — sahkan preset dimuat.
> Loss dengan setup betul = kos perniagaan (kategori I), bukan bug.
> 100% profit tidak wujud.

## Kemahiran berkaitan
`swarm` · `mql5-activations-catalog` · `rea-reverse-engineer`

Fail sokongan: `scripts/market_story.py` · `scripts/ExportBars.mq5` · `references/koreksi.md` · `references/golden/`

---
*Selam v3.2 · + pakej lengkap: `references/koreksi.md` & `references/golden/README.md` kini
disertakan (dahulu dirujuk tetapi tiada); memori kekal ditulis ke `--out` (dahulu ke current
directory); pembetulan kecil skrip. v3.1 = Bahagian H (baca pasaran dari bar mentah: 7 pas,
pengesan zon/breakout/trendline, memori, gelung peningkatan). v2.0 (38+ backtest, bug state-loss,
SL "xcun") + modul mata-trader (B), autopsi trade (C3), analisa belah & trade terlepas (D),
perlindungan overfitting (E), format output piawai (G). Lesen: MIT*
