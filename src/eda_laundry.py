"""
Exploratory Data Analysis (EDA) data transaksi Queena Laundry  ->  bahan BAB II.3

Cara pakai (Google Colab atau lokal):
    python eda_laundry.py data_laundry_bersih.xlsx hasil_eda

Masukan : workbook hasil pembersihan (sheet 'Data Bersih' dan 'Agregat Harian')
Keluaran: folder berisi 9 grafik (.png) dan 'statistik_eda.xlsx'
"""
import os
import sys

import matplotlib
import numpy as np
import pandas as pd
from scipy import stats

matplotlib.use("Agg")
import matplotlib.pyplot as plt

INPUT = sys.argv[1] if len(sys.argv) > 1 else "data_laundry_bersih.xlsx"
OUT = sys.argv[2] if len(sys.argv) > 2 else "hasil_eda"
os.makedirs(OUT, exist_ok=True)

HARI = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
BIRU, ORANYE, ABU, MERAH = "#1F4E78", "#E07B39", "#9AA5B1", "#C0392B"
plt.rcParams.update({
    "figure.dpi": 100, "savefig.dpi": 150, "axes.spines.top": False,
    "axes.spines.right": False, "axes.grid": True, "grid.alpha": 0.25, "font.size": 10,
})

xl = pd.ExcelFile(INPUT)
d = xl.parse("Data Bersih")
a = xl.parse("Agregat Harian")
for kol in ["Tanggal Order", "Tanggal Ambil", "Tanggal Lunas"]:
    d[kol] = pd.to_datetime(d[kol])
a["Tanggal"] = pd.to_datetime(a["Tanggal"])

tutup = a["Ada_Transaksi"] == 0          # hari tanpa transaksi (toko tutup)
buka = a[~tutup].copy()                   # hanya hari beroperasi
seri = a["Jumlah_Transaksi"].astype(float).where(~tutup)  # hari tutup -> NaN


def simpan(fig, nama):
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, nama))
    plt.close(fig)


# ============================================================ 1. Deret waktu
fig, ax = plt.subplots(figsize=(11, 4.2))
ax.plot(a["Tanggal"], a["Jumlah_Transaksi"], color=ABU, lw=0.8, label="Harian")
ma7 = seri.rolling(7, center=True, min_periods=4).mean()
ax.plot(a["Tanggal"], ma7, color=BIRU, lw=2, label="Rata-rata bergerak 7 hari")
ax.scatter(a.loc[tutup, "Tanggal"], a.loc[tutup, "Jumlah_Transaksi"], color=MERAH,
           s=22, zorder=3, label="Hari tanpa transaksi")
i = a["Jumlah_Transaksi"].idxmax()
ax.annotate(f"Puncak: {a.loc[i, 'Tanggal']:%d %b %Y}\n({a.loc[i, 'Jumlah_Transaksi']} transaksi)",
            (a.loc[i, "Tanggal"], a.loc[i, "Jumlah_Transaksi"]),
            xytext=(15, -5), textcoords="offset points", fontsize=8,
            arrowprops=dict(arrowstyle="-", color="gray"))
ax.set(title="Jumlah transaksi harian Queena Laundry", ylabel="Transaksi per hari")
ax.legend(loc="upper right", fontsize=8)
simpan(fig, "01_deret_waktu_harian.png")

# ============================================================ 2. Pola per hari
fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
for ax, kol, judul in zip(axes, ["Jumlah_Transaksi", "Total_KG"],
                          ["Jumlah transaksi per hari", "Total kilogram per hari"]):
    data = [buka.loc[buka["Hari_ke"] == k, kol].values for k in range(7)]
    bp = ax.boxplot(data, patch_artist=True, showmeans=True, widths=0.6,
                    meanprops=dict(marker="D", markerfacecolor="white", markeredgecolor="black", markersize=5),
                    medianprops=dict(color="black"))
    for k, kotak in enumerate(bp["boxes"]):
        kotak.set(facecolor=ORANYE if k == 4 else BIRU, alpha=0.75)
    ax.set_xticks(range(1, 8))
    ax.set_xticklabels([h[:3] for h in HARI])
    ax.set(title=judul)
fig.suptitle("Sebaran per hari dalam seminggu (belah ketupat putih = rata-rata)", fontsize=11)
simpan(fig, "02_pola_hari_dalam_seminggu.png")

# ============================================================ 3. Tren bulanan
buka["bulan"] = buka["Tanggal"].dt.to_period("M")
bln = buka.groupby("bulan")["Jumlah_Transaksi"].mean()
fig, ax = plt.subplots(figsize=(10, 4))
batang = ax.bar(range(len(bln)), bln.values, color=BIRU, alpha=0.85)
for j in (0, len(bln) - 1):     # bulan pertama & terakhir tidak penuh
    batang[j].set(hatch="//", alpha=0.5)
ax.set_xticks(range(len(bln)))
ax.set_xticklabels([p.strftime("%b %y") for p in bln.index], rotation=45)
for j, v in enumerate(bln.values):
    ax.text(j, v + 0.2, f"{v:.1f}", ha="center", fontsize=8)
ax.set(title="Rata-rata transaksi per hari menurut bulan (garis miring = bulan tidak penuh)",
       ylabel="Rata-rata transaksi/hari")
simpan(fig, "03_tren_bulanan.png")

# ============================================================ 4. Dekomposisi klasik aditif (periode 7)
tren = seri.rolling(7, center=True, min_periods=5).mean()
detren = seri - tren
indeks = detren.groupby(a["Hari_ke"]).mean()
indeks = indeks - indeks.mean()
musiman = a["Hari_ke"].map(indeks)
sisa = seri - tren - musiman
valid = detren.notna() & sisa.notna()
kekuatan = max(0.0, 1 - sisa[valid].var() / detren[valid].var())

fig, axes = plt.subplots(4, 1, figsize=(11, 8), sharex=True)
for ax, ser, nama, warna in zip(
    axes, [seri, tren, musiman, sisa],
    ["Data asli", "Tren (rata-rata bergerak 7 hari)", "Komponen musiman mingguan", "Sisa (residual)"],
    [ABU, BIRU, ORANYE, MERAH],
):
    ax.plot(a["Tanggal"], ser, color=warna, lw=1.1)
    ax.set_ylabel(nama, fontsize=8)
axes[0].set_title(f"Dekomposisi deret waktu (aditif, periode 7 hari) - kekuatan musiman = {kekuatan:.2f}")
simpan(fig, "04_dekomposisi_musiman.png")

# ============================================================ 5. Distribusi
kiloan = d[(d["Jenis Layanan"] == "Kiloan") & (d["Jumlah KG"] > 0)]
q1, q3 = kiloan["Jumlah KG"].quantile([0.25, 0.75])
batas = q3 + 1.5 * (q3 - q1)
fig, axes = plt.subplots(1, 2, figsize=(11, 4))
axes[0].hist(buka["Jumlah_Transaksi"], bins=range(0, 42, 2), color=BIRU, alpha=0.85, edgecolor="white")
axes[0].axvline(buka["Jumlah_Transaksi"].mean(), color=ORANYE, lw=2,
                label=f"Rata-rata {buka['Jumlah_Transaksi'].mean():.1f}")
axes[0].axvline(buka["Jumlah_Transaksi"].median(), color="black", ls="--", label=f"Median {buka['Jumlah_Transaksi'].median():.0f}")
axes[0].set(title="Distribusi transaksi per hari", xlabel="Transaksi per hari", ylabel="Jumlah hari")
axes[0].legend(fontsize=8)
axes[1].hist(kiloan["Jumlah KG"], bins=np.arange(0, 60, 1.5), color=BIRU, alpha=0.85, edgecolor="white")
axes[1].axvline(batas, color=MERAH, ls="--", label=f"Batas outlier {batas:.1f} kg")
axes[1].set(title="Distribusi berat per transaksi (kiloan)", xlabel="Kilogram", ylabel="Jumlah transaksi")
axes[1].legend(fontsize=8)
simpan(fig, "05_distribusi.png")

# ============================================================ 6. Komposisi
fig, axes = plt.subplots(1, 2, figsize=(11, 3.8))
for ax, kol, judul in zip(axes, ["Kelompok Tarif", "Layanan Standar"],
                          ["Komposisi kelompok tarif", "Komposisi jenis layanan"]):
    pct = d[kol].value_counts(normalize=True).sort_values() * 100
    ax.barh(pct.index, pct.values, color=BIRU, alpha=0.85)
    for j, v in enumerate(pct.values):
        ax.text(v + 0.5, j, f"{v:.1f}%", va="center", fontsize=8)
    ax.set(title=judul, xlabel="% dari transaksi")
    ax.set_xlim(0, pct.max() * 1.18)
simpan(fig, "06_komposisi.png")

# ============================================================ 7. Jam order
d["jam"] = d["Tanggal Order"].dt.hour
d["jumat"] = d["Tanggal Order"].dt.dayofweek == 4
jam = pd.crosstab(d["jam"], d["jumat"], normalize="columns") * 100
fig, ax = plt.subplots(figsize=(10, 4))
lebar = 0.4
ax.bar(jam.index - lebar / 2, jam[False], lebar, color=BIRU, label="Hari lain")
ax.bar(jam.index + lebar / 2, jam[True], lebar, color=ORANYE, label="Jumat")
ax.set_xticks(jam.index)
ax.set(title="Jam masuk order (persen dari transaksi pada kelompok harinya)",
       xlabel="Jam", ylabel="% transaksi")
ax.legend()
simpan(fig, "07_jam_order.png")

# ============================================================ 8. Autokorelasi
maks_lag = 28
acf = np.array([seri.autocorr(k) for k in range(1, maks_lag + 1)])
ci = 1.96 / np.sqrt(seri.notna().sum())
fig, ax = plt.subplots(figsize=(10, 4))
warna = [ORANYE if k % 7 == 0 else BIRU for k in range(1, maks_lag + 1)]
ax.bar(range(1, maks_lag + 1), acf, color=warna, width=0.6)
ax.axhline(ci, color="gray", ls="--", lw=0.8)
ax.axhline(-ci, color="gray", ls="--", lw=0.8)
ax.axhline(0, color="black", lw=0.8)
ax.set(title="Autokorelasi jumlah transaksi harian (oranye = kelipatan 7 hari)",
       xlabel="Lag (hari)", ylabel="Autokorelasi")
simpan(fig, "08_autokorelasi.png")

# ============================================================ 9. Order vs pengambilan
amb = d.dropna(subset=["Tanggal Ambil"]).copy()
lag_ambil = (amb["Tanggal Ambil"].dt.normalize() - amb["Tanggal Order"].dt.normalize()).dt.days
share_order = d["Tanggal Order"].dt.dayofweek.value_counts(normalize=True).sort_index() * 100
share_ambil = amb["Tanggal Ambil"].dt.dayofweek.value_counts(normalize=True).sort_index() * 100
fig, ax = plt.subplots(figsize=(9, 4))
ax.bar(np.arange(7) - 0.2, share_order.values, 0.4, color=BIRU, label="Order masuk")
ax.bar(np.arange(7) + 0.2, share_ambil.values, 0.4, color=ORANYE, label="Cucian diambil")
ax.set_xticks(range(7))
ax.set_xticklabels([h[:3] for h in HARI])
ax.set(title="Hari order masuk vs hari cucian diambil", ylabel="% dari total")
ax.legend()
simpan(fig, "09_order_vs_pengambilan.png")

# ============================================================ Statistik
def ringkas(s):
    return pd.Series({
        "Jumlah hari": s.count(), "Rata-rata": s.mean(), "Simpangan baku": s.std(),
        "Minimum": s.min(), "Q1": s.quantile(.25), "Median": s.median(),
        "Q3": s.quantile(.75), "Maksimum": s.max(), "Skewness": s.skew(),
        "Koef. variasi": s.std() / s.mean(),
    })


desk = pd.concat({
    "Transaksi/hari (semua hari)": ringkas(a["Jumlah_Transaksi"]),
    "Transaksi/hari (tanpa hari tutup)": ringkas(buka["Jumlah_Transaksi"]),
    "Kg/hari (semua hari)": ringkas(a["Total_KG"]),
    "Kg/hari (tanpa hari tutup)": ringkas(buka["Total_KG"]),
}, axis=1).round(2)

per_hari = buka.groupby("Hari_ke").agg(
    Rata_transaksi=("Jumlah_Transaksi", "mean"), SD_transaksi=("Jumlah_Transaksi", "std"),
    Median_transaksi=("Jumlah_Transaksi", "median"), Maks_transaksi=("Jumlah_Transaksi", "max"),
    Rata_KG=("Total_KG", "mean"), SD_KG=("Total_KG", "std"), Jumlah_hari=("Tanggal", "count"),
).round(1)
per_hari.index = HARI

per_bulan = buka.groupby("bulan").agg(
    Rata_transaksi=("Jumlah_Transaksi", "mean"), Rata_KG=("Total_KG", "mean"),
    Jumlah_hari_buka=("Tanggal", "count"),
).round(1)
per_bulan.index = per_bulan.index.astype(str)

kelompok_hari = [g["Jumlah_Transaksi"].values for _, g in buka.groupby("Hari_ke")]
kw = stats.kruskal(*kelompok_hari)
jumat = buka.loc[buka["Hari_ke"] == 4, "Jumlah_Transaksi"]
lain = buka.loc[buka["Hari_ke"] != 4, "Jumlah_Transaksi"]
mw = stats.mannwhitneyu(jumat, lain, alternative="greater")
reg = stats.linregress(np.arange(len(buka)), buka["Jumlah_Transaksi"])

buka["rasio"] = buka["Jumlah_Transaksi"] / buka.groupby("Hari_ke")["Jumlah_Transaksi"].transform("mean")
hr = buka["Tanggal"].dt.day
buka["kelompok_tgl"] = np.where((hr <= 3) | (hr >= 29), "awal/akhir bulan (29-3)",
                                np.where((hr >= 13) & (hr <= 16), "tengah bulan (13-16)", "lainnya"))
kw_tgl = stats.kruskal(*[g["rasio"].values for _, g in buka.groupby("kelompok_tgl")])
rasio_tgl = buka.groupby("kelompok_tgl")["rasio"].mean().round(3)

uji = pd.DataFrame([
    ["Kruskal-Wallis: transaksi berbeda antar hari?", f"H = {kw.statistic:.1f}", f"{kw.pvalue:.2e}",
     "Ada perbedaan nyata antar hari dalam seminggu" if kw.pvalue < .05 else "Tidak ada perbedaan nyata"],
    ["Mann-Whitney: Jumat > hari lain?", f"U = {mw.statistic:.0f}", f"{mw.pvalue:.2e}",
     "Jumat nyata lebih ramai" if mw.pvalue < .05 else "Tidak nyata"],
    ["Regresi linear tren harian", f"kemiringan = {reg.slope:.4f} transaksi/hari; R2 = {reg.rvalue**2:.3f}",
     f"{reg.pvalue:.3f}", "Tren naik/turun nyata" if reg.pvalue < .05 else "Tidak ada tren linear yang nyata"],
    ["Kekuatan musiman mingguan (dekomposisi)", f"{kekuatan:.2f} (skala 0-1)", "-",
     "Musiman kuat" if kekuatan > .6 else "Musiman sedang/lemah"],
    ["Kruskal-Wallis: rasio transaksi vs kelompok tanggal", f"H = {kw_tgl.statistic:.1f}", f"{kw_tgl.pvalue:.3f}",
     "Indikasi efek tanggal (lemah, hati-hati)" if kw_tgl.pvalue < .05 else "Tidak nyata"],
    ["Korelasi transaksi vs total kg harian", f"r = {a['Jumlah_Transaksi'].corr(a['Total_KG']):.3f}", "-",
     "Hampir sejajar, jadi bisa dipakai bergantian sebagai target"],
], columns=["Uji / ukuran", "Nilai", "p-value", "Kesimpulan"])

acf_tab = pd.DataFrame({"Lag (hari)": range(1, maks_lag + 1), "Autokorelasi": acf.round(3)})
komposisi = pd.concat([
    d["Kelompok Tarif"].value_counts().rename("Jumlah").to_frame().assign(
        Persen=lambda x: (x["Jumlah"] / x["Jumlah"].sum() * 100).round(1)).rename_axis("Kelompok Tarif").reset_index(),
    d["Layanan Standar"].value_counts().rename("Jumlah").to_frame().assign(
        Persen=lambda x: (x["Jumlah"] / x["Jumlah"].sum() * 100).round(1)).rename_axis("Layanan Standar").reset_index(),
], axis=1)
pengambilan = pd.DataFrame({
    "Ukuran": ["Median selisih order ke ambil (hari)", "Rata-rata (hari)", "Maksimum (hari)",
               "Pengambilan terbanyak pada hari", "Order terbanyak pada hari"],
    "Nilai": [lag_ambil.median(), round(lag_ambil.mean(), 1), lag_ambil.max(),
              HARI[int(share_ambil.idxmax())], HARI[int(share_order.idxmax())]],
})

with pd.ExcelWriter(os.path.join(OUT, "statistik_eda.xlsx"), engine="openpyxl") as w:
    desk.to_excel(w, sheet_name="Deskriptif Harian")
    per_hari.to_excel(w, sheet_name="Per Hari")
    per_bulan.to_excel(w, sheet_name="Per Bulan")
    uji.to_excel(w, sheet_name="Uji Statistik", index=False)
    acf_tab.to_excel(w, sheet_name="Autokorelasi", index=False)
    komposisi.to_excel(w, sheet_name="Komposisi", index=False)
    pengambilan.to_excel(w, sheet_name="Order vs Pengambilan", index=False)
    from openpyxl.styles import Font, PatternFill
    for ws in w.book.worksheets:
        for baris in ws.iter_rows():
            for sel in baris:
                sel.font = Font(name="Arial", size=10)
        for sel in ws[1]:
            sel.font = Font(name="Arial", size=10, bold=True, color="FFFFFF")
            sel.fill = PatternFill("solid", fgColor="1F4E78")
        for kolom in ws.columns:
            lebar_kol = max(len(str(c.value)) if c.value is not None else 0 for c in kolom)
            ws.column_dimensions[kolom[0].column_letter].width = min(max(lebar_kol + 2, 10), 55)

print("== Deskriptif harian ==\n", desk.to_string())
print("\n== Per hari ==\n", per_hari.to_string())
print("\n== Uji ==\n", uji.to_string(index=False))
print("\nRasio per kelompok tanggal:\n", rasio_tgl.to_string())
print("\nACF lag 1,7,14,21,28:", {k: round(float(acf[k - 1]), 2) for k in (1, 7, 14, 21, 28)})
print("\nKekuatan musiman:", round(kekuatan, 3))
print("\nIndeks musiman (selisih dari rata-rata, transaksi):")
print(indeks.round(1).rename(dict(enumerate(HARI))).to_string())
print("\n", pengambilan.to_string(index=False))
print("\nSelesai. Hasil di folder:", OUT)
