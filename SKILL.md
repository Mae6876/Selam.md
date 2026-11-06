# /selam — Deep-Dive Trade Data Analysis + Candle Reading + Engine Tuning (v2.0)

> **"Selam" = selam scuba ke dalam data. Jangan renang di permukaan — tengok dasar laut.**
>
> Methodology lengkap untuk menganalisa enjin dagangan MQL5: baca log baris-demi-baris,
> bina daftar dagangan, faham apa candle buat, dan buat keputusan BERDASARKAN DATA —
> bukan berdasarkan perasaan atau nombor rawak.

---

## FILOSOFI ASAS (baca ini dulu)

1. **Laporan .htm ialah ringkasan. Log ialah kebenaran.** Angka agregat (PF 1.65, DD 8%)
   tidak pernah memberitahu anda *mengapa*. Log tahu.
2. **Setiap trade ada cerita.** "Kenapa untung?" "Kenapa rugi?" — jawapannya ada dalam
   log, baris demi baris. Tugas anda: baca, faham, dan ceritakan.
3. **Data mengalahkan pendapat.** Idea yang kelihatan bijak (SL mengikut volatiliti,
   filter lokasi entry) mesti diuji. Jika data menolaknya — *tolak idea itu, bukan data.*
4. **Jika perubahan menjadikannya lebih teruk — kembali ke config lama.** Sentiasa. Tiada
   pengecualian. Ego bukan sebab untuk menyimpan idea yang gagal.
5. **Kejujuran tentang 100% profit:** tiada sistem dagangan di dunia ini mempunyai 100%
   kadar menang. Yang boleh dicapai: **win rate tinggi + loss kecil + profit konsisten**.
   Sesiapa yang menjanjikan 100% sedang menipu.

---

## TIGA LAPIS LOG MT5 (peta medan — belajar ini dahulu)

Kebanyakan orang hanya tahu satu lapis. Selam tahu ketiga-tiganya, dan perangkap masing-masing:

| Lapis | Lokasi | Apa yang ada | Perangkap |
|---|---|---|---|
| **L1: Log EA (live/demo)** | `<TerminalData>\MQL5\Logs\YYYYMMDD.log` | Semua `Print()` dari EA — `[Entry]`, `[SL Hit]`, telemetri tersuai | Berputar setiap hari; campur output SEMUA EA pada terminal itu |
| **L2: Log tester terminal** | `<TerminalData>\tester\logs\YYYYMMDD.log` | Ringkasan deal setiap backtest + `final balance XXXX USD` + masa tick | **KONGSI semua ujian pada terminal** — ujian dari sesi lain boleh bercampur; `final balance` terakhir ≠ larian anda |
| **L3: Log agen tester** | `<TerminalData>\Tester\<hash>\Agent-127.0.0.1-3000\logs\YYYYMMDD.log` | Semua cetakan EA semasa backtest — sumber penuh untuk analisa backtest | Boleh reach ratusan MB; baca dengan `Seek(-N,'End')`, bukan `Get-Content` penuh |

### Perangkap medan (kebanyakan nyawa hilang di sini)

- **MT5 single-instance:** melancarkan `terminal64.exe /config:...` semasa terminal sudah
  berjalan **TIDAK MELAKUKAN APA-APA** (hanya memfokus tetingkap sedia ada). Config diabaikan
  secara senyap → anda mempercayai hasil ujian yang *tidak pernah berlari*. Sentiasa bunuh
  proses dahulu, atau sahkan baris permulaan baharu (`testing of Experts\... started`) dalam log.
- **Kongsi folder keluaran antara sesi:** dua projek/sesi menulis ke `out\tester_config.ini`
  yang sama → fail ditulis ganti secara senyap → anda melancarkan **EA yang salah**.
  Penyelesaian: ini berasingan bagi setiap projek (`tester_config_flow3d.ini`).
- **Log agent tercerolet:** membaca 150MB log penuh akan menghentikan shell. Sentiasa baca
  ekor tetap (ekor tetap 30-60KB) dan tapis dengan corak.
- **Corak `final balance` dalam L2** ialah cara paling pantas untuk mendapatkan hasil
  apabila laporan .htm tidak dijanakan: `final balance 19037.65 USD`.

### Perintah terbukti (salin-tampal ini)

```powershell
# L1: aktiviti EA live — tapis mengikut EA
$log = "$env:APPDATA\MetaQuotes\Terminal\<HASH>\MQL5\Logs\20261105.log"
Select-String -Path $log -Pattern 'Flow3D_ZoneTrend' |
  ForEach-Object { ($_.Line -replace '^\S+\s+\S+\s+','') } | Select-Object -Last 40

# L2: hasil backtest — baris keseimbangan akhir
$tlog = "$env:APPDATA\MetaQuotes\Terminal\<HASH>\tester\logs\20261105.log"
Select-String -Path $tlog -Pattern 'final balance' | Select-Object -Last 3

# L3: baca ekor log agent (jangan baca penuh!)
$fs=[IO.File]::Open($alog,'Open','Read','ReadWrite')
$fs.Seek(-300000,'End')|Out-Null; $buf=New-Object byte[] 300000
$fs.Read($buf,0,300000)|Out-Null; $fs.Close()
$txt=[Text.Encoding]::Unicode.GetString($buf)
($txt -split "`n" | Select-String '\[Entry\]|\[SL Hit\]')
```

---
## METODOLOGI SELAM (5 LANGKAH) — DENGAN DETAIL PENUH

### LANGKAH 1: BACA LOG — BUKAN SEKADAR LAPORAN

Laporan `.htm` memberi anda nombor. Log memberi anda **sebab-sebab**. Aturan kerja:

1. Kenal pasti lapis log yang betul (lihat jadual di atas): live demo → L1; backtest → L3.
2. Tapis mengikut nama EA / tag tersuai. Jika EA anda belum ada tag, **tambahkan tag**
   (`[Entry]`, `[SL Hit]`, `[Partial]`, `[ZoneDiag]`) — satu baris Print kecil yang
   menjimatkan berjam-jam analisa kemudian.
3. Baca **setiap** baris trade. Jangan langkau. Corak ini muncul di tempat yang anda
   rasa "bosan membaca".

Corak yang perlu dicari dalam log EA (daripada pengalaman sebenar):

| Corak dalam log | Apa maknanya |
|---|---|
| `[Entry] BUY 0.87 @4045.36 \| SL 4039.50 (59 p) \| TP ... \| zon [..-..]` | Entry penuh dengan geometri — SIMPAN |
| `[SL Hit] PnL -478.83 — cooldown 3 bar` | Loss + menyatakan config cooldown yang LIVE (mendedahkan perbezaan preset!) |
| `[Partial] 50% ditutup @+103 pip` | Pengurusan berjalan |
| `[ZoneDiag] ... res[99999.00-99999.00]` | Penampan penunjuk KOSONG (99999 = tiada zon) — petunjuk data |
| `[Skip] risiko 150 pip > had 250` | Penapis melindungi anda — kira berapa kerap |
| `init` berulang setiap 2-3 minit | **EA memuat semula — keadaan dalaman hilang** (lihat senarai semak bug) |
| `final market buy ... [Market closed]` | EA cuba trade di luar waktu sesuai — pengiraan waktu sesi salah |

### LANGKAH 2: BINA DAFTAR DAGANGAN (TRADE REGISTER)

Padankan deal "in" dengan deal "out" → SATU dagangan lengkap. Format yang terbukti:

```
| # | Masa    | Arah      | Entry    | SL          | TP          | Hasil                    |
|---|---------|-----------|----------|-------------|-------------|--------------------------|
| 1 | 22:41   | SELL 0.45 | 4114.81  | 4125.89(111p)| 4092.64(222p)| ✅ Partial +103p, BE+10  |
| 2 | 22:50   | SELL 0.33 | 4104.73  | 4119.76(150p)| 4074.67(301p)| ❌ SL hit −$478.83       |
| 3 | —       | tiada     | —        | —           | —           | cooldown aktif           |
```

Untuk setiap trade, kira dan tulis:
- **Jarak SL dalam pip** dan dalam **$** (untuk XAUUSD: $1.00 = 10 pip = 1 candle M15 kasar)
- **Lokasi entry dalam zon**: `posisi = (px − zLo) / (zHi − zLo)`. Bawah 25% atau atas 75%
  untuk SELL = **mengejar pecahan zon**, bukan menolaknya
- **R:R sebenar** = reward / risk. Jika 0.12:1 — trade itu cacat sebelum bermula
- **Alasan keluar** daripada log L3 (sl / tp / trailing / isyarat bertentangan)
- **Durasi pegang** — trade < 5 minit yang kena SL hampir selalu bermakna SL terlalu sempit

### LANGKAH 3: FAHAM MACAM MATA MANUSIA (baca candle & lokasi)

Nombor tanpa cerita = tiada apa-apa. Untuk setiap loss, jawab dengan LOKASI + KONTEKS:

**Kajian kes sebenar (Trade 2, EA Flow3D_ZoneTrend, live demo):**
```
Entry SELL @4104.73 — zon [4105.16-4116.76]
→ Entry 0.07 DI BAWAH tepi bawah zon supply
→ Ini bukan rejection. Ini mengejar harga yang DAH pecah bawah zon supply.
→ SL 150 pip jauhnya (tepi atas zon + 30 pip), TP 301 pip lagi
→ Harga naik semula → SL. Loss −$478.83 memadam semua profit partial.
```
**Sebab sebenar:** bukan SL "xcun" — lokasi entry paling teruk dalam zon. SL di tepi
bertentangan = risiko 5-8× reward. Satu loss memadam 5-6 win kecil.

**Kanun bacaan candle (guna bersama zon):**

| Fenomena | Tanda dalam log/candle | Tindakan |
|---|---|---|
| **REJECTION** | Harga masuk zon, candle CLOSE semula di luar zon | Entry sah — lokasi terbaik |
| **TRUE BREAKOUT** | Close melepasi paras + tidak pulang dalam 3 bar | Jangan lawan; tunggu retest |
| **FAKE BREAKOUT** | Break tapi pulang dalam 3 bar | Isyarat bertentangan (counter) — **lumpuhkan jika data kata rugi** |
| **RETEST** | Harga pulang ke zon selepas keluar | Entry kualiti kedua |
| **ZON PATAH** | Close penuh melepasi tepi jauh zon | Zon mati — jangan trade di situ lagi |

---
## LANGKAH 4: CADANGAN BERDASARKAN DATA (TERIMA / TOLAK DENGAN NOMBOR)

Setiap idea tuning mesti melalui gelung yang sama:
**ubah SATU benda → backtest config SAMA → banding → terima atau tolak.**

Contoh sebenar (satu sesi penuh, EA `Flow3D_ZoneTrend_EA`, XAUUSD M15, tick, 2023-2026, $10k):

| Eksperimen | Hasil | Keputusan | Sebab |
|---|---|---|---|
| Cooldown 3 → 20 bar | +23% → +50% | ✅ TERIMA | Churn re-entry ialah punca loss |
| Cooldown 35 | +77.7% | ✅ TERIMA | Puncak keluk |
| Cooldown 100 | +16.8% | ❌ TOLAK | Terlalu lama — ketinggalan isyarat |
| ATR floor SL (1.5×ATR14) | → +88.5% | ✅ TERIMA | SL tak boleh dalam 1 candle |
| Tiered ATR (2.0× bila ATR tinggi) | +52.5% | ❌ TOLAK | Lot kecil + R:R tak capai min → trade ditolak |
| Filter separuh zon (entry 50% betul) | +48% | ❌ TOLAK | Menunggu lokasi "sempurna" = terlepas win |
| MinScore 65 | +20.5% | ❌ TOLAK | Skor tinggi memotong winner |

**Corak kekalahan berulang yang perlu diingat:**
- **SL yang lebih lebar ≠ lebih selamat.** Dengan risiko % tetap, SL jauh → lot kecil →
  profit per win mengecil; dan TP tetap → R:R jatuh → penapis menolak trade. Lebih lebar
  hanya bagus sehingga ~1.5×ATR. Selepas itu, ia memotong edge.
- **Penapis terlalu ketat membunuh kedua-dua belah.** Menunggu entry "sempurna" buang
  winner lebih banyak daripada loser yang diselamatkan. Ukur, jangan rasa.
- **State yang hilang semasa re-init ialah bug wang sebenar.** (Lihat senarai semak.)

## LANGKAH 5: BACKTEST DAN BANDING — ATURAN KEJUJURAN

- Config ujian **SAMA** (simbol, TF, julat tarikh, deposit, model tick) — tanpa ini,
  perbandingan adalah dusta.
- **Run terdahulu ialah baseline.** Simpan `final balance` setiap larian dalam satu jadual.
- Jika lebih teruk → **revert**. Jika lebih baik → simpan sebagai baseline baharu dan
  ulang eksperimen seterusnya dari situ.
- **Jangan pernah melancarkan ujian semasa terminal sibuk** (perangkap single-instance).
- Satu-satu eksperimen. Dua perubahan serentak = anda tidak tahu yang mana satu beri kesan.

---
## SENARAI SEMAK BUG (kelas bug yang selam cari — dari luka sebenar)

| # | Kelas bug | Gejala | Perbaikan terbukti |
|---|---|---|---|
| 1 | **Hilang state semasa re-init** | Log `init` berulang; cooldown tak jalan; partial tercetus 2× | Simpan state dalam `GlobalVariableSet("EA_state_<magic>", ...)` — kembali semula dalam `OnInit` |
| 2 | **Log spam setiap tick** | Journal penuh ratusan baris sesaat | Throttle: `static datetime lastBar; if(iTime(...,0)!=lastBar)` — 1 cetakan setiap bar |
| 3 | **Repaint (baca bar forming)** | Nilai berubah dalam bar sama; backtest ≠ live | Semua bacaan indikator pada **shift 1** (bar tertutup) |
| 4 | **Bocor data masa depan (HTF)** | Skor HTF guna bar H1/H4 yang masih terbentuk | Dapatkan shift bar HTF tertutup: `iBarShift(...) + 1` |
| 5 | **Single-instance tester** | Laporan tidak dijana tetapi log menunjukkan deal lama | Bunuh `terminal64` sebelum lancar; sahkan baris `testing of ... started` |
| 6 | **Config kongsi ditulis ganti** | EA yang salah dilancarkan; laporan nama lain | Satu ini per projek; semak `Expert=` sebelum lancar |
| 7 | **Handle bocor** | "indicator is too slow", 512-handle limit | Buat dalam `OnInit`, lepaskan dalam `OnDeinit` |
| 8 | **SL terlalu sempit untuk simbol** | SL terkena dalam < 5 min; SL < 1 candle | Lantai: `SL min = 1.5 × ATR(14)` — JANGAN pergi melebihi itu (data: 2.0× = −38pt) |
| 9 | **Logik zon buatan (fallback)** | SL diletak 30 pip melepasi "zon" RN tiruan = dalam noise | Mod ketat: hanya zon penunjuk sebenar; kalau tiada zon = tiada trade |
| 10 | **Cache/sesi bercampur** | `final balance` sama to-the-cent untuk config berbeza | Ujian tidak berlari — semak log, ulang dengan bersih |

### Uraian kekal yang terbukti (GlobalVariable — salin corak ini)

```mql5
// OnInit: bina nama + pulih
g_gvLoss = "F3ZT_loss_" + _Symbol + "_" + (string)InpMagicNumber;
if(GlobalVariableCheck(g_gvLoss)) g_lastLossBarTime = (datetime)GlobalVariableGet(g_gvLoss);

// OnTradeTransaction (SL hit): simpan
GlobalVariableSet(g_gvLoss, (double)g_lastLossBarTime);

// ManagePosition (partial per tiket): simpan + pulih + bersihkan
if(ticket != g_activeTicket) { g_activeTicket = ticket;
   g_partialDone = GlobalVariableCheck(g_gvPartial + "_" + (string)ticket); }
// selepas partial berjaya: GlobalVariableSet(g_gvPartial+"_"+(string)ticket, 1.0);
// apabila kedudukan ditutup: GlobalVariableDel(...)
```

---

## JADUAL ARAHAN (apa user sebut → apa selam buat)

| User sebut | Selam buat |
|---|---|
| "selam code" | Baca log agent trade-by-trade, buat register, analisa |
| "baca candle" | Faham apa enjin nampak: rejection di zon, breakout, regime shift |
| "audit enjin" | Semak config + baca kod enjin + pastikan tiada benda rosak |
| "tune gila2" | Backtest grid kombinasi, banding dengan data sebelum ini |
| "kenapa rugi?" | Baca trade register, cari pola rugi, bagi sebab yang SPESIFIK (lokasi + konteks) |
| "faham apa candle buat" | Baca candle dalam chart: rejection / breakout / reversal |
| "semak entry live" | L1 journal → daftar dagangan → corak loss → cadangan berteraskan data |
| "kenapa xikut X?" | Baca kod laluan fallback + tambah `[XDiag]` print throttle → jawap dengan bukti |
| "gila2" | Jangan takut kaji dalam — tunjuk data mentah, buat analisa mendalam |

## KETIKA BERPADU DENGAN /SWARM

1. `/swarm` = **audit kod selari** (pecah kerja kepada pekerja, bukti fail:baris, baiki, kompil)
2. `/selam` = **analisa data mendalam** (log → daftar → corak → tuning)
3. Susunan yang terbukti: **swarm dahulu** (kod betul) → **selam** (strategi untung) → **backtest** (sahkan)
4. Hasil kacukan sebenar: swarm jumpa bug hilang-state + log spam; selam jumpa punca loss
   (lokasi entry); kedua-dua fix → backtest mengesahkan tiada regresi.

## WAWASAN KUNCI (dipelajari secara perit)

> **Counter = OFF** — turning counter-signal off doubled profit and halved drawdown.
> **TP 8.0 sweet spot** (HD engine) — semua top performers guna nilai ini.
> **Trade pegang > 3 jam = enjin profit** — 92% profit datang dari sana.
> **Cooldown churn** — re-entry pantas selepas SL ialah pembunuh senyap #1 (3→35 bar = +23%→+78%).
> **SL 1.5×ATR, jangan lebih** — 2.0× = lot kecil + R:R gagal = −38pt.
> **Config live ≠ config backtest** — log `[SL Hit] ... cooldown 3 bar` mendedahkan live
> masih guna default; SELALU sahkan preset telah dimuat.
> **100% profit tidak wujud** — sasaran sebenar: win rate tinggi, loss kecil, bulanan konsisten.

## MUAT / SAHKAN

```powershell
Get-ChildItem "$env:USERPROFILE\.cline\skills\selam" -Recurse   # pemasangan skill
```

Gunakan: taip `/selam` dalam Cline. Untuk audit kod serentak, taip `/swarm <path>`.

## Kemahiran berkaitan
- `swarm` — audit kod MQL5 selari (pecah → pekerja → diagnosa → baiki → sahkan)
- `mql5-activations-catalog` — corak pengaktifan/licens MQL5
- `rea-reverse-engineer` — ternyah jurutera binary `.ex4`/`.ex5`

---
*Selam v2.0 · dibina daripada ujian sebenar: 38+ backtest runs, bug state-loss yang
menghilangkan cooldown, SL "xcun" yang terkena dalam 30 saat, dan data yang menolak
tiga idea "bijak" yang sebenarnya memusnahkan edge.* · Lesen: MIT



