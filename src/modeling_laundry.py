"""
Pemodelan dan evaluasi forecasting transaksi harian Queena Laundry  ->  BAB IV dan BAB V

Cara pakai (Google Colab atau lokal):
    python modeling_laundry.py data_laundry_bersih.xlsx hasil_model

Masukan : workbook hasil pembersihan (sheet 'Agregat Harian')
Keluaran: folder berisi grafik (.png) dan 'hasil_model.xlsx'

Skema pengujian (rolling origin mingguan):
  Pada setiap awal minggu T, model dilatih memakai data sebelum T, lalu memperkirakan 7 hari
  ke depan. Diulang untuk 12 minggu terakhir (84 hari) sebagai data uji. Data tidak diacak.
"""
import os
import sys

import matplotlib
import numpy as np
import pandas as pd
from scipy import optimize, stats

matplotlib.use("Agg")
import matplotlib.pyplot as plt

INPUT = sys.argv[1] if len(sys.argv) > 1 else "data_laundry_bersih.xlsx"
OUT = sys.argv[2] if len(sys.argv) > 2 else "hasil_model"
os.makedirs(OUT, exist_ok=True)

M = 7          # periode musiman (mingguan)
H = 7          # horizon prediksi (hari)
N_UJI = 84     # panjang data uji (12 minggu)
HARI = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
BIRU, ORANYE, ABU, MERAH, HIJAU = "#1F4E78", "#E07B39", "#9AA5B1", "#C0392B", "#2E8B57"
plt.rcParams.update({"savefig.dpi": 150, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.grid": True, "grid.alpha": 0.25, "font.size": 10})

a = pd.read_excel(INPUT, sheet_name="Agregat Harian")
a["Tanggal"] = pd.to_datetime(a["Tanggal"])
tutup = (a["Ada_Transaksi"] == 0).values
hari_ke = a["Hari_ke"].values
n = len(a)

MODEL = [
    "Rata-rata 28 hari (tanpa musiman)",
    "Seasonal Naive",
    "Rata-rata 4 minggu (hari sama)",
    "Holt-Winters tanpa tren",
    "Holt-Winters dengan tren",
    "Regresi dummy hari",
    "Regresi dummy hari + lag",
]


# ------------------------------------------------------------------ utilitas data
def imputasi_tutup(y):
    """Hari tutup (nilai 0 struktural) diganti nilai hari yang sama minggu sebelumnya.
    Hanya untuk masukan model deret waktu; data aslinya tidak diubah."""
    y = y.astype(float).copy()
    for i in np.where(tutup)[0]:
        j = i - M
        while j >= 0 and tutup[j]:
            j -= M
        y[i] = y[j] if j >= 0 else np.nan
    return y


# ------------------------------------------------------------------ Holt-Winters aditif
def hw_run(y, alpha, beta, gamma, trend, catat=0):
    """Rekursi Holt-Winters aditif.
    Prediksi 1 langkah : yhat_t = l_(t-1) + b_(t-1) + s_(t-m)
    Level   : l_t = alpha (y_t - s_(t-m)) + (1-alpha)(l_(t-1) + b_(t-1))
    Tren    : b_t = beta (l_t - l_(t-1)) + (1-beta) b_(t-1)
    Musiman : s_t = gamma (y_t - l_(t-1) - b_(t-1)) + (1-gamma) s_(t-m)
    """
    nn = len(y)
    l = y[:M].mean()
    b = (y[M:2 * M].mean() - y[:M].mean()) / M if trend else 0.0
    s = np.empty(nn)
    s[:M] = y[:M] - l
    sse, jejak = 0.0, []
    for t in range(M, nn):
        yhat = l + b + s[t - M]
        e = y[t] - yhat
        sse += e * e
        l_baru = alpha * (y[t] - s[t - M]) + (1 - alpha) * (l + b)
        b_baru = beta * (l_baru - l) + (1 - beta) * b if trend else 0.0
        s[t] = gamma * (y[t] - l - b) + (1 - gamma) * s[t - M]
        if t - M < catat:
            jejak.append([t, y[t], yhat, e, l_baru, b_baru, s[t]])
        l, b = l_baru, b_baru
    return sse, l, b, s, jejak


def hw_fit(y, trend):
    """Cari alpha, beta, gamma yang meminimalkan jumlah kuadrat galat 1 langkah pada data latih."""
    if trend:
        fun = lambda p: hw_run(y, p[0], p[1], p[2], True)[0]
        awal = [[.1, .01, .1], [.3, .05, .3], [.05, .01, .05]]
    else:
        fun = lambda p: hw_run(y, p[0], 0.0, p[1], False)[0]
        awal = [[.1, .1], [.3, .3], [.05, .05]]
    batas = [(0.001, 0.999)] * len(awal[0])
    terbaik = min((optimize.minimize(fun, x0, bounds=batas, method="L-BFGS-B") for x0 in awal),
                  key=lambda r: r.fun)
    p = terbaik.x
    return (p[0], p[1], p[2]) if trend else (p[0], 0.0, p[1])


def hw_forecast(y, par, trend):
    sse, l, b, s, _ = hw_run(y, par[0], par[1], par[2], trend)
    nn = len(y)
    return np.array([l + h * b + s[nn + h - 1 - M * int(np.ceil(h / M))] for h in range(1, H + 1)])


# ------------------------------------------------------------------ Regresi linear berganda (OLS)
def desain(y, idx, lag):
    kolom = [np.ones(len(idx))]
    nama = ["Konstanta (hari Senin)"]
    for k in range(1, 7):
        kolom.append((hari_ke[idx] == k).astype(float))
        nama.append(f"Dummy {HARI[k]}")
    if lag:
        kolom += [y[idx - 7], y[idx - 14]]
        nama += ["Lag 7 hari", "Lag 14 hari"]
    return np.column_stack(kolom), nama


def ols_fit(y, T, lag):
    idx = np.array([t for t in range(14, T) if not tutup[t]])
    X, nama = desain(y, idx, lag)
    beta = np.linalg.lstsq(X, y[idx], rcond=None)[0]
    return beta, nama, X, y[idx]


def ols_predict(y, beta, T, lag):
    idx = np.arange(T, T + H)
    X, _ = desain(y, idx, lag)
    return X @ beta


# ------------------------------------------------------------------ metrik
def metrik(y, p):
    e = y - p
    return {
        "MAE": np.mean(np.abs(e)),
        "RMSE": np.sqrt(np.mean(e ** 2)),
        "MAPE (%)": np.mean(np.abs(e / y)) * 100,
        "sMAPE (%)": np.mean(2 * np.abs(e) / (np.abs(y) + np.abs(p))) * 100,
        "Bias (prediksi - aktual)": np.mean(p - y),
    }


def jalankan(target):
    y_asli = a[target].values.astype(float)
    y = imputasi_tutup(y_asli)
    asal = np.arange(n - N_UJI, n, H)
    pred = {m: [] for m in MODEL}
    par_log = []
    for T in asal:
        yt = y[:T]
        pred[MODEL[0]] += [yt[-28:].mean()] * H
        pred[MODEL[1]] += [y[T - M + h] for h in range(H)]
        pred[MODEL[2]] += [np.mean([y[T + h - M * k] for k in range(1, 5)]) for h in range(H)]
        for nama, tren in ((MODEL[3], False), (MODEL[4], True)):
            par = hw_fit(yt, tren)
            pred[nama] += list(hw_forecast(yt, par, tren))
            par_log.append([nama, T, *par])
        for nama, lag in ((MODEL[5], False), (MODEL[6], True)):
            beta, _, _, _ = ols_fit(y, T, lag)
            pred[nama] += list(ols_predict(y, beta, T, lag))
    pred = {m: np.clip(np.array(v), 0, None) for m, v in pred.items()}
    aktual = y_asli[n - N_UJI:]
    ok = ~tutup[n - N_UJI:]
    tgl_uji = a["Tanggal"].values[n - N_UJI:]
    hasil = pd.DataFrame({m: metrik(aktual[ok], pred[m][ok]) for m in MODEL}).T
    mae_sn = hasil.loc[MODEL[1], "MAE"]
    hasil["MAE relatif thd Seasonal Naive"] = hasil["MAE"] / mae_sn
    hasil = hasil.round(3)
    return y_asli, y, pred, aktual, ok, tgl_uji, hasil, par_log


# =================================================================== Jalankan
hasil_semua = {}
for target, label in (("Jumlah_Transaksi", "transaksi"), ("Total_KG", "kg")):
    hasil_semua[label] = jalankan(target)

y_asli, y_imp, pred, aktual, ok, tgl_uji, hasil, par_log = hasil_semua["transaksi"]
terbaik = hasil["MAE"].idxmin()
print("Data uji:", pd.Timestamp(tgl_uji[0]).date(), "s/d", pd.Timestamp(tgl_uji[-1]).date(), "| hari uji valid:", ok.sum())
print("\n== Metrik (target: jumlah transaksi) ==\n", hasil.to_string())
print("\nModel terbaik menurut MAE:", terbaik)

# uji Wilcoxon: galat absolut model terbaik vs Seasonal Naive
e_sn = np.abs(aktual[ok] - pred[MODEL[1]][ok])
e_best = np.abs(aktual[ok] - pred[terbaik][ok])
if terbaik != MODEL[1]:
    wil = stats.wilcoxon(e_sn, e_best, alternative="greater")
    print(f"Wilcoxon (galat Seasonal Naive > galat {terbaik}): p = {wil.pvalue:.4f}")
else:
    wil = None

print("\n== Metrik (target: total kg) ==\n", hasil_semua["kg"][6].to_string())

# MAE per hari dalam seminggu
hari_uji = pd.DatetimeIndex(tgl_uji).dayofweek
per_hari = pd.DataFrame({
    m: pd.Series(np.abs(aktual - pred[m])[ok]).groupby(hari_uji[ok]).mean() for m in
    [MODEL[0], MODEL[1], MODEL[3], MODEL[5], MODEL[6]]
}).round(2)
per_hari.index = HARI
print("\n== MAE per hari (transaksi) ==\n", per_hari.to_string())

# ------------------------------------------------------------------ Parameter akhir (data penuh)
par_hw = {}
tabel_par = []
for nama, tren in ((MODEL[3], False), (MODEL[4], True)):
    par = hw_fit(y_imp, tren)
    par_hw[nama] = par
    sse, l, b, s, _ = hw_run(y_imp, par[0], par[1], par[2], tren)
    tabel_par.append([nama, par[0], par[1], par[2], l, b])
    if not tren:
        indeks_musiman = pd.Series(
            [s[n - M + k] for k in range(M)],
            index=[HARI[int(hari_ke[n - M + k])] for k in range(M)],
        ).reindex(HARI).round(2)
        level_akhir = l
tabel_par = pd.DataFrame(tabel_par, columns=["Model", "alpha", "beta", "gamma", "Level akhir", "Tren akhir"]).round(4)
print("\n== Parameter Holt-Winters (data penuh) ==\n", tabel_par.to_string(index=False))
print("\nKomponen musiman akhir (HW tanpa tren):\n", indeks_musiman.to_string())

# Koefisien regresi (data penuh) + uji signifikansi
koef_tabel = {}
for nama, lag in ((MODEL[5], False), (MODEL[6], True)):
    beta, nm, X, yy = ols_fit(y_imp, n, lag)
    resid = yy - X @ beta
    dof = len(yy) - X.shape[1]
    s2 = resid @ resid / dof
    se = np.sqrt(np.diag(s2 * np.linalg.inv(X.T @ X)))
    tt = beta / se
    pv = 2 * (1 - stats.t.cdf(np.abs(tt), dof))
    r2 = 1 - (resid @ resid) / ((yy - yy.mean()) @ (yy - yy.mean()))
    koef_tabel[nama] = (pd.DataFrame({"Koefisien": beta, "Galat baku": se, "t": tt, "p-value": pv}, index=nm).round(4), r2, len(yy))
    print(f"\n== Koefisien {nama} (n={len(yy)}, R2={r2:.3f}) ==\n", koef_tabel[nama][0].to_string())

# ------------------------------------------------------------------ Contoh perhitungan
# (a) Holt-Winters tanpa tren: 8 langkah rekursi pertama pada data penuh
par = par_hw[MODEL[3]]
_, _, _, _, jejak = hw_run(y_imp, par[0], par[1], par[2], False, catat=8)
contoh_hw = pd.DataFrame(jejak, columns=["t", "y aktual", "y prediksi (l+b+s)", "galat", "level baru", "tren baru", "musiman baru"])
contoh_hw.insert(1, "Tanggal", [a["Tanggal"].iloc[int(t)].strftime("%d-%m-%Y") for t in contoh_hw["t"]])
contoh_hw.insert(2, "Hari", [HARI[int(hari_ke[int(t)])] for t in contoh_hw["t"]])
contoh_hw = contoh_hw.round(3)
awal_info = pd.DataFrame({
    "Inisialisasi": ["Level awal l = rata-rata 7 hari pertama", "Musiman awal s_i = y_i - l (i = 1..7)"],
    "Nilai": [round(y_imp[:M].mean(), 3), ", ".join(f"{v:.2f}" for v in (y_imp[:M] - y_imp[:M].mean()))],
})

# (b) Regresi dummy hari + lag: satu contoh prediksi untuk hari Jumat pertama data uji
beta_l, nm_l, _, _ = ols_fit(y_imp, n - N_UJI, True)
j = next(i for i in range(n - N_UJI, n) if hari_ke[i] == 4)
Xj, _ = desain(y_imp, np.array([j]), True)
komp = Xj[0] * beta_l
contoh_reg = pd.DataFrame({"Fitur": nm_l, "Nilai fitur": Xj[0].round(2), "Koefisien": beta_l.round(4), "Kontribusi": komp.round(3)})
contoh_reg.loc[len(contoh_reg)] = [f"PREDIKSI {a['Tanggal'].iloc[j]:%d-%m-%Y} (Jumat)", "", "", round(komp.sum(), 3)]
contoh_reg.loc[len(contoh_reg)] = ["Nilai aktual", "", "", float(y_asli[j])]

# ------------------------------------------------------------------ Grafik
tgl = pd.to_datetime(tgl_uji)

fig, ax = plt.subplots(figsize=(11, 4.3))
ax.plot(tgl, aktual, color="black", lw=1.6, marker="o", ms=3, label="Aktual")
ax.plot(tgl, pred[MODEL[1]], color=ABU, lw=1.2, label="Seasonal Naive")
ax.plot(tgl, pred[MODEL[0]], color=MERAH, lw=1.2, ls="--", label="Rata-rata 28 hari (tanpa musiman)")
ax.plot(tgl, pred[terbaik], color=ORANYE, lw=2, label=terbaik)
ax.set(title="Prediksi vs aktual pada data uji (12 minggu terakhir)", ylabel="Transaksi per hari")
ax.legend(fontsize=8, ncol=2)
fig.tight_layout(); fig.savefig(os.path.join(OUT, "10_prediksi_vs_aktual.png")); plt.close(fig)

fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
urut = hasil.sort_values("MAE")
for ax, kol in zip(axes, ["MAE", "RMSE"]):
    ax.barh(urut.index, urut[kol], color=[ORANYE if m == terbaik else BIRU for m in urut.index], alpha=0.9)
    for i, v in enumerate(urut[kol]):
        ax.text(v + 0.05, i, f"{v:.2f}", va="center", fontsize=8)
    ax.set(title=f"{kol} (makin kecil makin baik)")
    ax.set_xlim(0, urut[kol].max() * 1.15)
    ax.invert_yaxis()
fig.tight_layout(); fig.savefig(os.path.join(OUT, "11_perbandingan_metrik.png")); plt.close(fig)

fig, ax = plt.subplots(figsize=(9, 4))
lebar = 0.16
for k, m in enumerate(per_hari.columns):
    ax.bar(np.arange(7) + (k - 2) * lebar, per_hari[m], lebar, label=m,
           color=[MERAH, ABU, BIRU, HIJAU, ORANYE][k])
ax.set_xticks(range(7)); ax.set_xticklabels([h[:3] for h in HARI])
ax.set(title="Galat rata-rata (MAE) per hari pada data uji", ylabel="MAE (transaksi)")
ax.legend(fontsize=7)
fig.tight_layout(); fig.savefig(os.path.join(OUT, "12_galat_per_hari.png")); plt.close(fig)

fig, ax = plt.subplots(figsize=(5.5, 5.2))
ax.scatter(aktual[ok], pred[terbaik][ok], color=ORANYE, alpha=0.8)
lim = [0, max(aktual.max(), pred[terbaik].max()) + 2]
ax.plot(lim, lim, color="black", lw=1, ls="--")
ax.set(title=f"Aktual vs prediksi ({terbaik})", xlabel="Aktual", ylabel="Prediksi", xlim=lim, ylim=lim)
fig.tight_layout(); fig.savefig(os.path.join(OUT, "13_scatter_aktual_prediksi.png")); plt.close(fig)

# ------------------------------------------------------------------ Excel
from openpyxl.styles import Font, PatternFill

prediksi_df = pd.DataFrame({"Tanggal": tgl.strftime("%d-%m-%Y"), "Hari": [HARI[d] for d in hari_uji],
                            "Aktual": aktual})
for m in MODEL:
    prediksi_df[m] = pred[m].round(2)

with pd.ExcelWriter(os.path.join(OUT, "hasil_model.xlsx"), engine="openpyxl") as w:
    hasil.to_excel(w, sheet_name="Metrik Transaksi")
    hasil_semua["kg"][6].to_excel(w, sheet_name="Metrik KG")
    per_hari.to_excel(w, sheet_name="MAE per Hari")
    prediksi_df.to_excel(w, sheet_name="Prediksi Data Uji", index=False)
    tabel_par.to_excel(w, sheet_name="Parameter HW", index=False)
    indeks_musiman.rename("Komponen musiman").to_frame().to_excel(w, sheet_name="Parameter HW", startrow=len(tabel_par) + 3)
    r = 0
    for nama, (kt, r2, nobs) in koef_tabel.items():
        pd.DataFrame({nama: [f"n = {nobs}, R2 = {r2:.3f}"]}).to_excel(w, sheet_name="Koefisien Regresi", startrow=r, index=False)
        kt.to_excel(w, sheet_name="Koefisien Regresi", startrow=r + 2)
        r += len(kt) + 5
    awal_info.to_excel(w, sheet_name="Contoh Hitung HW", index=False)
    contoh_hw.to_excel(w, sheet_name="Contoh Hitung HW", index=False, startrow=len(awal_info) + 3)
    contoh_reg.to_excel(w, sheet_name="Contoh Hitung Regresi", index=False)
    for ws in w.book.worksheets:
        for baris in ws.iter_rows():
            for sel in baris:
                sel.font = Font(name="Arial", size=10)
        for sel in ws[1]:
            sel.font = Font(name="Arial", size=10, bold=True, color="FFFFFF")
            sel.fill = PatternFill("solid", fgColor="1F4E78")
        for kolom in ws.columns:
            lk = max(len(str(c.value)) if c.value is not None else 0 for c in kolom)
            ws.column_dimensions[kolom[0].column_letter].width = min(max(lk + 2, 10), 48)

print("\n== Contoh hitung HW ==\n", awal_info.to_string(index=False), "\n", contoh_hw.to_string(index=False))
print("\n== Contoh hitung regresi ==\n", contoh_reg.to_string(index=False))
print("\nSelesai. Hasil di folder:", OUT)
