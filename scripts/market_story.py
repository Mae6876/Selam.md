#!/usr/bin/env python3
"""
market_story.py — "mata manusia" untuk selam.
Baca BAR MENTAH (bukan laporan), bina semula cerita pasaran, simpan ke memori.

Guna:
  python market_story.py --csv XAUUSD_M15.csv --atr 14 --k 3 --out story_out
  python market_story.py --csv XAUUSD_M15.csv --trades trades.csv --out story_out

CSV bar: time,open,high,low,close,tick_volume   (atau format eksport MT5 <DATE> <TIME> ...)
CSV trade (pilihan): time,dir,entry,sl           (dir = BUY/SELL)

Prinsip: TIADA look-ahead. Swing hanya "wujud" selepas k bar pengesahan.
"""
import argparse, json, os, sys
import numpy as np
import pandas as pd


# ---------------------------------------------------------------- muat data
def load_bars(path):
    df = pd.read_csv(path, sep=None, engine="python")
    df.columns = [c.strip("<>").strip().lower() for c in df.columns]
    if "date" in df.columns and "time" in df.columns:
        df["time"] = pd.to_datetime(df["date"].astype(str) + " " + df["time"].astype(str))
    else:
        df["time"] = pd.to_datetime(df["time"])
    ren = {"tickvol": "tick_volume", "vol": "tick_volume", "volume": "tick_volume"}
    df = df.rename(columns={k: v for k, v in ren.items() if k in df.columns})
    if "tick_volume" not in df.columns:
        df["tick_volume"] = 0
    df = df.sort_values("time").reset_index(drop=True)
    return df[["time", "open", "high", "low", "close", "tick_volume"]]


# ---------------------------------------------------------------- anatomi
def annotate(df, atr_n):
    d = df.copy()
    pc = d["close"].shift(1)
    tr = pd.concat([d.high - d.low, (d.high - pc).abs(), (d.low - pc).abs()], axis=1).max(axis=1)
    d["atr"] = tr.rolling(atr_n).mean()
    rng = (d.high - d.low).replace(0, np.nan)
    d["range"] = d.high - d.low
    d["body_pct"] = (d.close - d.open).abs() / rng
    d["upw_pct"] = (d.high - d[["open", "close"]].max(axis=1)) / rng
    d["low_pct"] = (d[["open", "close"]].min(axis=1) - d.low) / rng
    d["clv"] = (d.close - d.low) / rng
    d["r_atr"] = d["range"] / d["atr"]
    d["vrel"] = d.tick_volume / d.tick_volume.rolling(20).mean().replace(0, np.nan)
    d["dir"] = np.sign(d.close - d.open)

    def label(r):
        if pd.isna(r.atr) or pd.isna(r.body_pct):
            return ""
        if r.r_atr >= 1.5 and r.body_pct >= 0.7:
            return "displacement_" + ("naik" if r.dir > 0 else "turun")
        if r.low_pct >= 0.6 and r.clv >= 0.5:
            return "pin_tolakan_bawah"
        if r.upw_pct >= 0.6 and r.clv <= 0.5:
            return "pin_tolakan_atas"
        if r.body_pct <= 0.15:
            return "doji"
        if r.body_pct >= 0.8:
            return "marubozu_" + ("naik" if r.dir > 0 else "turun")
        if r.r_atr < 0.5:
            return "senyap"
        return "biasa"

    d["label"] = d.apply(label, axis=1)
    inside = (d.high < d.high.shift(1)) & (d.low > d.low.shift(1))
    d.loc[inside & (d.label == "biasa"), "label"] = "inside_bar"
    return d


# ---------------------------------------------------------------- swing (tanpa look-ahead)
def find_swings(d, k):
    sw = []  # (idx, type, price, confirm_idx)
    for i in range(k, len(d) - k):
        win_h = d.high.iloc[i - k:i + k + 1]
        win_l = d.low.iloc[i - k:i + k + 1]
        if d.high.iloc[i] == win_h.max() and (win_h == d.high.iloc[i]).sum() == 1:
            sw.append((i, "H", d.high.iloc[i], i + k))
        if d.low.iloc[i] == win_l.min() and (win_l == d.low.iloc[i]).sum() == 1:
            sw.append((i, "L", d.low.iloc[i], i + k))
    return sorted(sw, key=lambda s: s[3])


# ---------------------------------------------------------------- enjin cerita
def run(d, k):
    n = len(d)
    swings = find_swings(d, k)
    events, zones, breakouts = [], [], []
    trend = np.zeros(n, dtype=int)  # +1 naik, -1 turun, 0 belum jelas
    cur_trend = 0
    live_sh, live_sl = [], []  # paras swing belum dipecahkan: [idx, price, confirm_idx, swept_flag]
    si = 0
    tl_prev = {"up": None, "dn": None}
    tl_log, tl_changes, tl_breaks = [], {"up": 0, "dn": 0}, []
    tl_active = {"up": None, "dn": None}
    confirmed = []

    def ev(i, kind, text):
        events.append({"i": i, "time": d.time.iloc[i], "kind": kind, "text": text})

    def build_line(kind, i):
        pts = [s for s in confirmed if s[1] == ("L" if kind == "up" else "H")][-5:]
        for b in range(len(pts) - 1, 0, -1):
            for a in range(b - 1, -1, -1):
                ia, pa = pts[a][0], pts[a][2]
                ib, pb = pts[b][0], pts[b][2]
                if kind == "up" and not pb > pa:
                    continue
                if kind == "dn" and not pb < pa:
                    continue
                slope = (pb - pa) / (ib - ia)
                seg = d.close.iloc[ia:i + 1]
                line = pa + slope * (np.arange(ia, i + 1) - ia)
                tol = 0.1 * (d.atr.iloc[i] if not pd.isna(d.atr.iloc[i]) else 0)
                viol = (seg.values < line - tol) if kind == "up" else (seg.values > line + tol)
                if viol.sum() == 0:  # garis sah: tiada close menembusnya sepanjang jarak
                    return (ia, ib, pa, slope)
        return None

    for i in range(n):
        while si < len(swings) and swings[si][3] <= i:
            s = swings[si]
            confirmed.append(s)
            (live_sh if s[1] == "H" else live_sl).append([s[0], s[2], s[3], False])
            si += 1
        c, h, l = d.close.iloc[i], d.high.iloc[i], d.low.iloc[i]
        atr = d.atr.iloc[i]

        # --- breakout / sweep paras swing
        for lv in list(live_sh):
            if c > lv[1]:
                fake = any(d.close.iloc[j] < lv[1] for j in range(i + 1, min(i + 4, n)))
                kind = "CHoCH_naik" if cur_trend == -1 else "BOS_naik"
                breakouts.append({"i": i, "dir": "naik", "level": lv[1], "fake": fake})
                ev(i, "breakout", f"{kind}: close {c:.2f} lepasi swing high {lv[1]:.2f} "
                                  f"({'PALSU - pulang dalam 3 bar' if fake else 'SAH - bertahan'})")
                if not fake:
                    cur_trend = 1
                live_sh.remove(lv)
            elif h > lv[1] and not lv[3]:
                lv[3] = True
                breakouts.append({"i": i, "dir": "sweep_atas", "level": lv[1], "fake": None})
                ev(i, "sweep", f"Wick tembus swing high {lv[1]:.2f} tapi close {c:.2f} semula di bawah (ambil likuiditi)")
        for lv in list(live_sl):
            if c < lv[1]:
                fake = any(d.close.iloc[j] > lv[1] for j in range(i + 1, min(i + 4, n)))
                kind = "CHoCH_turun" if cur_trend > 0 else "BOS_turun"
                breakouts.append({"i": i, "dir": "turun", "level": lv[1], "fake": fake})
                ev(i, "breakout", f"{kind}: close {c:.2f} lepasi swing low {lv[1]:.2f} "
                                  f"({'PALSU - pulang dalam 3 bar' if fake else 'SAH - bertahan'})")
                if not fake:
                    cur_trend = -1
                live_sl.remove(lv)
            elif l < lv[1] and not lv[3]:
                lv[3] = True
                breakouts.append({"i": i, "dir": "sweep_bawah", "level": lv[1], "fake": None})
                ev(i, "sweep", f"Wick tembus swing low {lv[1]:.2f} tapi close {c:.2f} semula di atas (ambil likuiditi)")
        trend[i] = cur_trend

        # --- cipta zon dari displacement
        lab = d.label.iloc[i]
        if lab.startswith("displacement") and i >= 6:
            up = lab.endswith("naik")
            for j in range(i - 1, max(i - 7, -1), -1):
                opp = d.close.iloc[j] < d.open.iloc[j] if up else d.close.iloc[j] > d.open.iloc[j]
                if opp:
                    z = {"id": len(zones) + 1, "type": "demand" if up else "supply", "lo": d.low.iloc[j],
                         "hi": d.high.iloc[j], "born": i, "touches": 0, "rej": 0, "dead": None,
                         "_in": False}
                    zones.append(z)
                    ev(i, "zone", f"Zon {z['type'].upper()} #{z['id']} [{z['lo']:.2f}-{z['hi']:.2f}] "
                                  f"lahir dari displacement ({d.r_atr.iloc[i]:.1f}xATR)")
                    break

        # --- uji zon aktif
        for z in zones:
            if z["dead"] is not None or z["born"] >= i:
                continue
            inside = h >= z["lo"] and l <= z["hi"]
            if inside and not z["_in"]:
                z["touches"] += 1
                if z["type"] == "demand":
                    res = "TOLAK (close atas zon)" if c > z["hi"] else ("PATAH" if c < z["lo"] else "di dalam zon")
                else:
                    res = "TOLAK (close bawah zon)" if c < z["lo"] else ("PATAH" if c > z["hi"] else "di dalam zon")
                if res.startswith("TOLAK"):
                    z["rej"] += 1
                ev(i, "zone_touch", f"Zon {z['type'].upper()} #{z['id']} sentuhan ke-{z['touches']}: {res}")
            z["_in"] = inside
            if (z["type"] == "demand" and c < z["lo"]) or (z["type"] == "supply" and c > z["hi"]):
                z["dead"] = i
                ev(i, "zone_dead", f"Zon {z['type'].upper()} #{z['id']} PATAH (close {c:.2f} lepasi tepi jauh)")

        # --- garisan trend (hanya info sedia ada pada bar i)
        for kind in ("up", "dn"):
            ln = build_line(kind, i)
            key = None if ln is None else (ln[0], ln[1])
            if key != tl_prev[kind]:
                if tl_prev[kind] is not None or key is not None:
                    tl_changes[kind] += 1
                tl_prev[kind] = key
                tl_active[kind] = None if ln is None else ln
            if ln is not None:
                ia, ib, pa, slope = ln
                val = pa + slope * (i - ia)
                tl_log.append({"time": d.time.iloc[i], "kind": kind, "a": ia, "b": ib,
                               "slope": slope, "value": val})
                if not pd.isna(atr):
                    broke = (c < val - 0.1 * atr) if kind == "up" else (c > val + 0.1 * atr)
                    if broke:
                        fake = any((d.close.iloc[j] > pa + slope * (j - ia)) if kind == "up"
                                   else (d.close.iloc[j] < pa + slope * (j - ia))
                                   for j in range(i + 1, min(i + 4, n)))
                        tl_breaks.append({"i": i, "kind": kind, "fake": fake})
                        ev(i, "trendline", f"Garisan trend {'naik' if kind == 'up' else 'turun'} "
                                           f"(anchor bar {ia}->{ib}) DITEMBUS pada {c:.2f} "
                                           f"({'PALSU' if fake else 'sah'})")
                        tl_prev[kind] = None  # garisan dah patah; bina semula

    return dict(swings=swings, events=events, zones=zones, breakouts=breakouts, trend=trend,
                tl_log=tl_log, tl_changes=tl_changes, tl_breaks=tl_breaks)


# ---------------------------------------------------------------- bandingan dengan trade EA
def trade_context(d, res, trades):
    out = []
    for _, t in trades.iterrows():
        tt = pd.to_datetime(t["time"])
        idx = d.index[d.time <= tt]
        if len(idx) == 0:
            continue
        i = idx[-1]
        entry, side = float(t["entry"]), str(t["dir"]).upper()
        flags, info = [], []
        zs = [z for z in res["zones"] if z["born"] < i and (z["dead"] is None or z["dead"] > i)]
        inz = [z for z in zs if z["lo"] <= entry <= z["hi"]]
        if inz:
            z = inz[-1]
            pos = (entry - z["lo"]) / max(z["hi"] - z["lo"], 1e-9)
            info.append(f"dalam zon {z['type']} #{z['id']} posisi {pos*100:.0f}% (sentuhan ke-{z['touches']})")
            if (side == "SELL" and z["type"] == "demand") or (side == "BUY" and z["type"] == "supply"):
                flags.append("ARAH LAWAN JENIS ZON")
            if (side == "SELL" and pos < 0.25) or (side == "BUY" and pos > 0.75):
                flags.append("KEJAR (hujung jauh zon)")
        else:
            near = sorted(zs, key=lambda z: min(abs(entry - z["lo"]), abs(entry - z["hi"])))[:1]
            if near:
                z = near[0]
                dist = min(abs(entry - z["lo"]), abs(entry - z["hi"]))
                info.append(f"LUAR zon; terdekat {z['type']} #{z['id']} jarak {dist:.2f}")
            else:
                info.append("tiada zon aktif")
            flags.append("ENTRY DI LUAR ZON")
        tr = int(res["trend"][i])
        info.append("trend struktur: " + {1: "NAIK", -1: "TURUN", 0: "belum jelas"}[tr])
        if (side == "BUY" and tr < 0) or (side == "SELL" and tr > 0):
            flags.append("LAWAN TREND STRUKTUR")
        atr = d.atr.iloc[i]
        if "sl" in t and not pd.isna(t["sl"]) and not pd.isna(atr):
            risk = abs(entry - float(t["sl"]))
            info.append(f"risiko SL {risk:.2f} = {risk/atr:.2f}xATR")
            if risk < 1.5 * atr:
                flags.append("SL < 1.5xATR")
        info.append(f"candle bar-1: {d.label.iloc[i]} (vrel {d.vrel.iloc[i]:.1f})")
        out.append((tt, side, entry, info, flags))
    return out


# ---------------------------------------------------------------- memori kekal
def update_memory(path, tag, d, res):
    mem = json.load(open(path)) if os.path.exists(path) else {"runs": {}}
    z = res["zones"]
    bo = [b for b in res["breakouts"] if b["dir"] in ("naik", "turun")]
    nb = max(len(d), 1)
    mem["runs"][tag] = {
        "bars": len(d), "from": str(d.time.iloc[0]), "to": str(d.time.iloc[-1]),
        "zones": len(z), "zone_touches": sum(x["touches"] for x in z),
        "zone_rejections": sum(x["rej"] for x in z), "zones_dead": sum(1 for x in z if x["dead"] is not None),
        "breakouts_true": sum(1 for b in bo if not b["fake"]), "breakouts_fake": sum(1 for b in bo if b["fake"]),
        "sweeps": sum(1 for b in res["breakouts"] if b["dir"].startswith("sweep")),
        "trendline_changes_per_100bars": {k: round(v * 100 / nb, 1) for k, v in res["tl_changes"].items()},
        "trendline_breaks_true": sum(1 for x in res["tl_breaks"] if not x["fake"]),
        "trendline_breaks_fake": sum(1 for x in res["tl_breaks"] if x["fake"]),
    }
    R = mem["runs"].values()
    t = sum(r["zone_touches"] for r in R)
    mem["totals"] = {
        "zone_touch_to_rejection_rate": round(sum(r["zone_rejections"] for r in R) / t, 3) if t else None,
        "fake_breakout_rate": round(sum(r["breakouts_fake"] for r in R) /
                                    max(sum(r["breakouts_fake"] + r["breakouts_true"] for r in R), 1), 3),
        "trendline_fake_break_rate": round(sum(r["trendline_breaks_fake"] for r in R) /
                                           max(sum(r["trendline_breaks_fake"] + r["trendline_breaks_true"] for r in R), 1), 3),
    }
    json.dump(mem, open(path, "w"), indent=2, default=str)
    return mem


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True)
    ap.add_argument("--trades")
    ap.add_argument("--atr", type=int, default=14)
    ap.add_argument("--k", type=int, default=3, help="bar pengesahan swing (fraktal)")
    ap.add_argument("--out", default="story_out")
    ap.add_argument("--memory", default=None,
                    help="fail memori kekal (lalai: <out>/MARKET_MEMORY.json)")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    mem_path = a.memory or os.path.join(a.out, "MARKET_MEMORY.json")

    d = annotate(load_bars(a.csv), a.atr)
    res = run(d, a.k)

    d.to_csv(os.path.join(a.out, "bars_annotated.csv"), index=False)
    pd.DataFrame(res["tl_log"]).to_csv(os.path.join(a.out, "trendline_log.csv"), index=False)

    z = res["zones"]
    lines = [f"# Cerita Pasaran — {os.path.basename(a.csv)}",
             f"Bar: {len(d)} | {d.time.iloc[0]} -> {d.time.iloc[-1]} | ATR{a.atr}, swing k={a.k}", "",
             "## Ringkasan", f"- Zon: {len(z)} lahir; {sum(x['touches'] for x in z)} sentuhan; "
             f"{sum(x['rej'] for x in z)} tolakan; {sum(1 for x in z if x['dead'] is not None)} patah",
             f"- Breakout: {sum(1 for b in res['breakouts'] if b['fake'] is False)} sah, "
             f"{sum(1 for b in res['breakouts'] if b['fake'])} palsu, "
             f"{sum(1 for b in res['breakouts'] if b['dir'].startswith('sweep'))} sweep",
             f"- Garisan trend berubah anchor per 100 bar: naik={res['tl_changes']['up']*100/len(d):.1f}, "
             f"turun={res['tl_changes']['dn']*100/len(d):.1f} (tinggi = garisan tak stabil)",
             f"- Tembusan garisan trend: {sum(1 for x in res['tl_breaks'] if not x['fake'])} sah, "
             f"{sum(1 for x in res['tl_breaks'] if x['fake'])} palsu", "", "## Garis masa"]
    for e in res["events"]:
        lines.append(f"- `{e['time']}` (bar {e['i']}) [{e['kind']}] {e['text']}")
    open(os.path.join(a.out, "market_story.md"), "w", encoding="utf-8").write("\n".join(lines))

    if a.trades:
        tr = pd.read_csv(a.trades)
        ctx = trade_context(d, res, tr)
        L = ["# Konteks setiap trade EA vs apa yang pasaran tunjuk", ""]
        for tt, side, entry, info, flags in ctx:
            L.append(f"## {tt} {side} @ {entry}")
            L += [f"- {x}" for x in info]
            L.append(f"- **AMARAN:** {', '.join(flags)}" if flags else "- tiada amaran konteks")
            L.append("")
        open(os.path.join(a.out, "trade_context.md"), "w", encoding="utf-8").write("\n".join(L))

    tag = f"{os.path.basename(a.csv)}|{d.time.iloc[0]}|{d.time.iloc[-1]}"
    mem = update_memory(mem_path, tag, d, res)
    print(f"Siap -> {a.out}/market_story.md | memori: {mem_path}")
    print(json.dumps(mem["totals"], indent=2))


if __name__ == "__main__":
    sys.exit(main())
