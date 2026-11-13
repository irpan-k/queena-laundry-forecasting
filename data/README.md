# Data

Berkas data **tidak disertakan** di repositori ini, karena berisi data transaksi usaha dan privasi pelanggan.

## Sumber

- Aplikasi kasir **1010dry** milik Queena Laundry, Tanjungpinang.
- Laporan transaksi detail, diekspor pada 18 September 2026.
- Periode: 19 September 2025 sampai 18 September 2026.
- Jumlah: 5.881 baris dan 20 kolom setelah anonimisasi (21 kolom pada ekspor asli).

## Privasi

- Nama konsumen diganti kode konsisten (C0001 dan seterusnya). Nama yang sama selalu mendapat kode yang sama.
- Alamat konsumen dihapus.
- Berkas `data_laundry_anonim.xlsx` masih memuat nama kasir. Kolom ini dibuang oleh `pembersihan_data_laundry.py`, sehingga data siap mining tidak memuatnya. Berkas anonim tidak disertakan di repositori.
- Versi yang dibagikan ke publik adalah `Mentah_NIM.7z`, dengan nama kasir diganti kode K001.
- Teks bebas (Catatan dan Items Satuan) dipindai untuk nomor telepon dan email. Tidak ditemukan pada data ini.

## Berkas yang dibutuhkan

| Berkas | Keterangan |
|---|---|
| `data_laundry_anonim.xlsx` | Masukan untuk `pembersihan_data_laundry.py`. Hasil anonimisasi dari ekspor 1010dry. |
| `data_laundry_bersih.xlsx` | Keluaran `pembersihan_data_laundry.py`. Dipakai oleh `eda_laundry.py` dan `modeling_laundry.py`. |

Letakkan berkas di folder ini. Keduanya sudah dimasukkan ke `.gitignore` sehingga tidak ikut terunggah.

## Pembaruan data

Data yang tersedia berakhir 18 September 2026. Jika ada data baru, jalankan ulang ketiga skrip dengan berkas yang diperbarui.
