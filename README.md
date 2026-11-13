# Prediksi Volume Transaksi Harian Queena Laundry

Project Penambangan Data (INF11121), Teknik Informatika, Fakultas Teknik dan Teknologi Kemaritiman, Universitas Maritim Raja Ali Haji, Ganjil 2026/2027.

**Tim:** Irfan Kurniawan (2401020055, ketua), Januar Suyasmin Saputra (2401020046), Jova Rifana (2401020050), M. Afdhal Habibi (2401020083)

**Mitra:** Queena Laundry, Tanjungpinang. Narasumber: Nur Atika (pemilik), dengan izin untuk mencantumkan nama usaha dan namanya.

## Ringkasan

Queena Laundry sering kekurangan tenaga saat akhir pekan dan menambah freelance secara mendadak. Project ini memprediksi jumlah transaksi dan berat cucian (kg) harian untuk tujuh hari ke depan menggunakan data transaksi satu tahun dari aplikasi kasir 1010dry. Hasil prediksi dipakai untuk memperkirakan beban pengerjaan akhir pekan dan kebutuhan freelance.

Model utama adalah **Holt-Winters aditif tanpa tren** dengan periode musiman tujuh hari. Pada jendela uji 12 minggu terakhir:

| Model | MAE (transaksi/hari) | RMSE | sMAPE |
|---|---|---|---|
| Rata-rata 28 hari (tanpa musiman) | 4,90 | 6,33 | 33,7% |
| Seasonal Naive | 3,79 | 4,89 | 27,7% |
| **Holt-Winters tanpa tren** | **3,10** | **3,91** | **23,1%** |
| Regresi dummy hari | 3,36 | 4,20 | 24,9% |

Untuk kilogram, Holt-Winters tanpa tren memiliki MAE 20,1 kg per hari. Hasil lengkap ada di laporan akhir.

## Prototipe

Halaman prediksi dapat dibuka di:
**https://irpan-k.github.io/queena-laundry-forecasting/**

Halaman ini memakai Tailwind dan Google Fonts dari internet, jadi tampilannya lengkap hanya jika ada koneksi. Data historis dan parameter model sudah tertanam di `docs/app.js`.

## Struktur repositori

```
├── docs/                    Prototipe web (GitHub Pages)
│   ├── index.html
│   ├── style.css
│   └── app.js
├── src/                     Skrip Python untuk seluruh tahap
│   ├── pembersihan_data.py  Pembersihan dan transformasi data
│   ├── eda.py               Exploratory Data Analysis (statistik dan grafik)
│   └── modeling.py          Pemodelan dan evaluasi (rolling origin mingguan)
├── data/                    Penjelasan data (berkas data tidak disertakan)
├── hasil/                   Keluaran skrip (dibuat ulang saat dijalankan)
├── requirements.txt
└── LICENSE
```

## Cara menjalankan

Instal pustaka terlebih dahulu:

```bash
pip install -r requirements.txt
```

Jalankan secara berurutan. Berkas data tidak disertakan di repositori (lihat `data/README.md`).

```bash
# 1. Pembersihan: dari data hasil anonimisasi menjadi data siap mining
python src/pembersihan_data.py data/data_laundry_anonim.xlsx data/data_laundry_bersih.xlsx

# 2. EDA: statistik, uji, dan 9 grafik
python src/eda.py data/data_laundry_bersih.xlsx hasil/eda

# 3. Pemodelan dan evaluasi
python src/modeling.py data/data_laundry_bersih.xlsx hasil/model
```

## Catatan proses data

- Data mentah berasal dari ekspor aplikasi 1010dry (5.881 baris). Nama konsumen diganti kode konsisten (C0001 dan seterusnya), kolom alamat dihapus, dan nama kasir diganti kode.
- `pembersihan_data.py` membuang 10 baris ringkasan, 149 transaksi batal, dan 111 pembelian paket member, sehingga tersisa 5.611 transaksi.
- **Kategori Cuci Komplit dan Cuci + Setrika tidak digabung pada tahap pembersihan.** Penggabungan dilakukan saat analisis, sesuai konfirmasi karyawan bahwa keduanya layanan yang sama. Penggabungan ini hanya mengubah label, bukan isi data.
- Hari terakhir (18 September 2026) dibuang karena datanya tidak lengkap, sehingga agregat harian mencakup 364 hari dengan 5.605 transaksi.
- Hari tanpa transaksi (lima hari tutup saat Lebaran dan Idul Adha) diberi penanda. Pada masukan model, nilainya diganti dengan nilai hari yang sama pada minggu sebelumnya.

## Lisensi

MIT. Lihat `LICENSE`.
