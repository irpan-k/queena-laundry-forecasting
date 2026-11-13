"""
Pembersihan data transaksi Queena Laundry (hasil ekspor aplikasi 1010dry).

Cara pakai (Google Colab atau lokal):
    python pembersihan_data_laundry.py data_laundry_anonim.xlsx data_laundry_bersih.xlsx

Keluaran: satu file Excel berisi 3 sheet
    1. Data Bersih      -> satu baris per transaksi
    2. Agregat Harian   -> satu baris per hari (siap untuk forecasting)
    3. Log Pembersihan  -> catatan tiap langkah (bahan BAB III laporan)
"""
import sys
import pandas as pd
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

INPUT = sys.argv[1] if len(sys.argv) > 1 else "data_laundry_anonim.xlsx"
OUTPUT = sys.argv[2] if len(sys.argv) > 2 else "data_laundry_bersih.xlsx"

BULAN = {
    "Januari": "January", "Februari": "February", "Maret": "March",
    "April": "April", "Mei": "May", "Juni": "June", "Juli": "July",
    "Agustus": "August", "September": "September", "Oktober": "October",
    "November": "November", "Desember": "December",
}
HARI = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]


def parse_tanggal(teks):
    """'17 September 2026, 19:36' -> datetime. Teks lain ('Belum Diambil', '-') -> NaT."""
    teks = str(teks)
    for indo, inggris in BULAN.items():
        teks = teks.replace(indo, inggris)
    return pd.to_datetime(teks, format="%d %B %Y, %H:%M", errors="coerce")


log = []


def catat(langkah, tindakan, alasan, sebelum, sesudah):
    log.append([langkah, tindakan, alasan, sebelum, sesudah, sebelum - sesudah])


df = pd.read_excel(INPUT)
print("Baris awal:", len(df))

# ---------------------------------------------------------------- Langkah 1
n = len(df)
df = df[df["Tanggal Order"].notna()].copy()
catat(
    "1. Buang baris footer/ringkasan",
    "Hapus baris yang 'Tanggal Order'-nya kosong",
    "Ekspor aplikasi menambahkan baris 'Total Transaksi', 'Total Kilo', dst di bawah data. "
    "Baris ini bukan transaksi.",
    n, len(df),
)

# ---------------------------------------------------------------- Langkah 2
n = len(df)
batal = (
    df["Status Order"].astype(str).str.startswith("Batal")
    | df["Status Bayar"].astype(str).str.startswith("Batal")
)
alasan_batal = df.loc[batal, "Status Bayar"].astype(str).value_counts()
print("\nAlasan batal:\n", alasan_batal.to_string())
df = df[~batal].copy()
catat(
    "2. Buang transaksi batal",
    "Hapus transaksi dengan Status Order/Status Bayar diawali 'Batal'",
    "Transaksi dibatalkan (salah input, permintaan konsumen, data percobaan) tidak mewakili "
    "cucian yang benar-benar masuk.",
    n, len(df),
)

# ---------------------------------------------------------------- Langkah 3
n = len(df)
paket = df["Tipe Transaksi"].astype(str).str.contains(r"\d+\s*kg", case=False, regex=True)
print("\nJenis baris paket member yang dibuang:\n",
      df.loc[paket, "Tipe Transaksi"].value_counts().to_string())
df = df[~paket].copy()
catat(
    "3. Buang pembelian paket member",
    "Hapus baris dengan Tipe Transaksi berpola 'xx KG - harga' (paket 25/35/50/100 KG)",
    "Ini transaksi penjualan paket prabayar (Jumlah KG diisi 1), bukan volume cucian. "
    "Cucian member dicatat terpisah dengan harga 0.",
    n, len(df),
)

# ---------------------------------------------------------------- Langkah 4
n_kolom = df.shape[1]
konstan = [c for c in df.columns if df[c].nunique(dropna=False) <= 1]
kolom_buang = sorted(set(konstan + ["Catatan"]))
print("\nKolom dibuang:", kolom_buang)
df = df.drop(columns=kolom_buang)
catat(
    "4. Buang kolom tidak informatif",
    "Drop kolom: " + ", ".join(kolom_buang),
    "Kolom konstan (satu nilai saja) tidak punya variasi untuk dipelajari model. "
    "'Catatan' kosong ~99% dan berisi koreksi berat manual.",
    n_kolom, df.shape[1],
)
log[-1][3:6] = [f"{n_kolom} kolom", f"{df.shape[1]} kolom", f"{n_kolom - df.shape[1]} kolom"]

# ---------------------------------------------------------------- Langkah 5
for kol in ["Tanggal Order", "Tanggal Ambil", "Tanggal Lunas"]:
    df[kol] = df[kol].map(parse_tanggal)
df["Dibayar"] = pd.to_numeric(df["Dibayar"], errors="coerce")
print("\nTanggal Order gagal parse:", df["Tanggal Order"].isna().sum())
print("Dibayar tidak numerik:", df["Dibayar"].isna().sum())
log.append([
    "5. Perbaiki tipe data",
    "Ubah 'Tanggal Order/Ambil/Lunas' dari teks (nama bulan Indonesia) menjadi datetime; "
    "ubah 'Dibayar' menjadi angka",
    "Teks tanggal tidak bisa dihitung/diurutkan. 'Belum Diambil' dan 'Belum Dibayar' "
    "menjadi kosong (NaT) karena memang belum terjadi.",
    "-", "-", "-",
])

# ---------------------------------------------------------------- Langkah 6
def kelompok_tarif(t):
    t = t.upper()
    if "MEMBER" in t:
        return "Member"
    if "KARYAWAN" in t:
        return "Karyawan"
    if "EXPRESS" in t or "EXPREES" in t:
        return "Express"
    if "KILAT" in t:
        return "Kilat"
    if t.startswith("SATUAN"):
        return "Satuan"
    return "Reguler"


PETA_LAYANAN = {
    "cuci komplit": "Cuci Komplit",
    "cuci + setrika": "Cuci + Setrika",
    "setrika": "Setrika",
    "cuci lipat": "Cuci Lipat",
    "cuci kering lipat": "Cuci Kering Lipat",
    "cuci": "Cuci Satuan",
}


def layanan(t):
    bagian = t.split(" - ", 1)[1] if " - " in t else t
    return PETA_LAYANAN.get(bagian.strip().lower(), bagian.strip().title())


tipe = df["Tipe Transaksi"].astype(str)
df["Kelompok Tarif"] = tipe.map(kelompok_tarif)
df["Layanan Standar"] = tipe.map(layanan)
n_awal = tipe.nunique()
n_baru = df[["Kelompok Tarif", "Layanan Standar"]].drop_duplicates().shape[0]
print("\nKelompok Tarif:\n", df["Kelompok Tarif"].value_counts().to_string())
print("\nLayanan Standar:\n", df["Layanan Standar"].value_counts().to_string())
log.append([
    "6. Standarisasi kategori",
    "Pecah 'Tipe Transaksi' menjadi 'Kelompok Tarif' (Reguler/Member/Karyawan/Express/Kilat/Satuan) "
    "dan 'Layanan Standar'; samakan huruf besar/kecil dan typo 'EXPREES'",
    f"Nama kategori tidak konsisten ({n_awal} variasi tipe). Kolom asli dipertahankan. "
    "Asumsi: 'Cuci Komplit' dan 'Cuci + Setrika' (juga 'Cuci Lipat' dan 'Cuci Kering Lipat') "
    "sengaja TIDAK digabung karena belum dikonfirmasi owner.",
    f"{n_awal} variasi", f"{n_baru} kombinasi", "-",
])

# ---------------------------------------------------------------- Langkah 7
kiloan = df["Jenis Layanan"].eq("Kiloan")
q1, q3 = df.loc[kiloan, "Jumlah KG"].quantile([0.25, 0.75])
batas = q3 + 1.5 * (q3 - q1)
df["Flag_Outlier_KG"] = (kiloan & (df["Jumlah KG"] > batas)).astype(int)
n_out = int(df["Flag_Outlier_KG"].sum())
print(f"\nOutlier KG (> {batas:.1f} kg): {n_out} baris; maksimum {df['Jumlah KG'].max()} kg")
log.append([
    "7. Tandai outlier berat",
    f"Tambah kolom 'Flag_Outlier_KG' = 1 untuk transaksi kiloan > {batas:.1f} kg "
    f"(aturan Q3 + 1,5 x IQR); jumlah ditandai: {n_out}",
    "Cucian partai besar bisa nyata (bukan salah input), jadi TIDAK dihapus. "
    "Hanya ditandai agar bisa diputuskan nanti (pertahankan/batasi) setelah konfirmasi owner.",
    "-", "-", "-",
])

df = df.sort_values("Tanggal Order").reset_index(drop=True)

# ---------------------------------------------------------------- Agregat harian
hari_terakhir = df["Tanggal Order"].max().normalize()
data_harian = df[df["Tanggal Order"] < hari_terakhir]
tgl = data_harian["Tanggal Order"].dt.normalize()
agg = data_harian.groupby(tgl).agg(
    Jumlah_Transaksi=("No. Nota", "count"),
    Total_KG=("Jumlah KG", "sum"),
    Total_Items=("Jumlah Items", "sum"),
    Total_Harga_Tercatat=("Total Harga", "sum"),
)
semua_hari = pd.date_range(tgl.min(), tgl.max(), name="Tanggal")
agg = agg.reindex(semua_hari)
agg["Ada_Transaksi"] = agg["Jumlah_Transaksi"].notna().astype(int)
agg = agg.fillna(0).reset_index()
agg["Jumlah_Transaksi"] = agg["Jumlah_Transaksi"].astype(int)
agg["Total_KG"] = agg["Total_KG"].round(1)
agg["Total_Items"] = agg["Total_Items"].astype(int)
agg["Total_Harga_Tercatat"] = agg["Total_Harga_Tercatat"].astype(int)
agg.insert(1, "Hari", agg["Tanggal"].dt.dayofweek.map(dict(enumerate(HARI))))
agg.insert(2, "Hari_ke", agg["Tanggal"].dt.dayofweek)
agg.insert(3, "Akhir_Pekan", (agg["Hari_ke"] >= 5).astype(int))
agg.insert(4, "Bulan", agg["Tanggal"].dt.month)
hari_kosong = agg.loc[agg["Ada_Transaksi"] == 0, "Tanggal"].dt.strftime("%d-%m-%Y").tolist()
print("\nAgregat harian:", len(agg), "hari,", agg["Tanggal"].min().date(), "s/d", agg["Tanggal"].max().date())
print("Hari tanpa transaksi:", hari_kosong)
print("\nRata-rata per hari dalam seminggu:")
print(agg.groupby("Hari_ke")[["Jumlah_Transaksi", "Total_KG"]].mean().round(1)
      .rename(index=dict(enumerate(HARI))).to_string())

log.append([
    "8. Agregasi harian",
    "Kelompokkan data bersih per tanggal order: jumlah transaksi, total kg, total item, "
    "total harga tercatat. Hari terakhir (" + hari_terakhir.strftime("%d-%m-%Y") + ") dibuang.",
    "Forecasting membutuhkan satu baris per hari. Hari terakhir tidak lengkap (data ekspor berhenti "
    "di tengah hari) sehingga akan menyesatkan model.",
    f"{len(df)} transaksi", f"{len(agg)} hari", "-",
])
log.append([
    "9. Hari tanpa transaksi",
    f"{len(hari_kosong)} hari diisi 0 dengan penanda Ada_Transaksi = 0: " + ", ".join(hari_kosong),
    "Kemungkinan toko tutup (libur Lebaran dan Idul Adha), bukan data hilang. Diisi 0, tidak "
    "diimputasi rata-rata. Perlu dikonfirmasi owner.",
    "-", "-", "-",
])
log.append([
    "Catatan",
    "'Total_Harga_Tercatat' bukan omzet sebenarnya",
    "Transaksi member bernilai Rp 0 karena dibayar lewat paket prabayar. Untuk target prediksi "
    "gunakan Jumlah_Transaksi atau Total_KG.",
    "-", "-", "-",
])

# ---------------------------------------------------------------- Tulis Excel
with pd.ExcelWriter(OUTPUT, engine="openpyxl") as xl:
    df.to_excel(xl, sheet_name="Data Bersih", index=False)
    agg.to_excel(xl, sheet_name="Agregat Harian", index=False)
    log_df = pd.DataFrame(
        log,
        columns=["Langkah", "Tindakan", "Alasan", "Sebelum", "Sesudah", "Dihapus"],
    )
    log_df.to_excel(xl, sheet_name="Log Pembersihan", index=False)

    biru = PatternFill("solid", fgColor="1F4E78")
    for ws in xl.book.worksheets:
        for row in ws.iter_rows():
            for c in row:
                c.font = Font(name="Arial", size=10)
        for c in ws[1]:
            c.font = Font(name="Arial", size=10, bold=True, color="FFFFFF")
            c.fill = biru
            c.alignment = Alignment(vertical="center", wrap_text=True)
        ws.freeze_panes = "A2"
        for i, kol in enumerate(ws.columns, start=1):
            panjang = max(len(str(c.value)) if c.value is not None else 0 for c in list(kol)[:200])
            ws.column_dimensions[get_column_letter(i)].width = min(max(panjang + 2, 10), 60)

    ws = xl.book["Data Bersih"]
    for i, nama in enumerate(df.columns, start=1):
        if "Tanggal" in nama:
            for c in ws[get_column_letter(i)][1:]:
                c.number_format = "DD/MM/YYYY HH:MM"
    ws = xl.book["Agregat Harian"]
    for c in ws["A"][1:]:
        c.number_format = "DD/MM/YYYY"

    ws = xl.book["Log Pembersihan"]
    ws.column_dimensions["B"].width = 60
    ws.column_dimensions["C"].width = 70
    for row in ws.iter_rows(min_row=2):
        for c in row:
            c.alignment = Alignment(vertical="top", wrap_text=True)

print("\nTersimpan:", OUTPUT, "| Data Bersih:", df.shape, "| Agregat Harian:", agg.shape)
