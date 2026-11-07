# Koreksi Bacaan AI (jurnal pembelajaran selam)

> Diisi SETIAP kali user betulkan bacaan AI ("AI salah baca"). **Baca fail ini pada permulaan
> setiap sesi "baca pasaran"** supaya kesilapan yang sama tidak berulang. Format penuh: SKILL.md §H5.

## Format entri (salin templat ini untuk setiap koreksi)

```
## YYYY-MM-DD | SIMBOL TF | bar/masa
- AI kata    : ...
- Sebenarnya : ... (apa yang user nampak)
- Sebab AI salah : (peraturan terlalu ketat/longgar? data kurang? konteks HTF terlepas?)
- Perubahan pengesan : (parameter / peraturan baharu — cth --k, ambang displacement, toleransi TL)
- Disahkan pada kes emas lain: ya/tidak
```

## Peraturan
1. **Terbaru di atas.** Entri baharu masuk selepas garis di bawah.
2. Satu koreksi = satu entri. Jangan gabung beberapa kesilapan dalam satu entri.
3. Jika koreksi menukar parameter pengesan, catat nilai LAMA dan BAHARU.
4. Sebelum tutup entri: jalankan semula kes emas yang berkaitan (regresi — lihat `golden/README.md`).

---

<!-- ===== ENTRI SEBENAR DI BAWAH GARIS INI (terbaru di atas) ===== -->
