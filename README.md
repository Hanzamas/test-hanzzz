# TPN Locations API (Full Feature)

Ini adalah sebuah API RESTful lengkap yang dibuat menggunakan FastAPI untuk mengelola data lokasi dari dunia The Promised Neverland. API ini menyediakan fungsionalitas CRUD (Create, Read, Update, Delete) penuh, dilengkapi dengan fitur filter, pencarian, dan sorting yang canggih.

Proyek ini di-deploy di **Vercel** dan menggunakan database **PostgreSQL** gratis yang di-hosting di **Neon**.



---

## ✨ Fitur Utama

- **CRUD Penuh**: Fungsi `Create`, `Read`, `Update`, dan `Delete` untuk data lokasi.
- **Filter Canggih**: Saring data lokasi berdasarkan dunianya (`loca`).
- **Pencarian Teks**: Lakukan pencarian *case-insensitive* di nama dan deskripsi lokasi.
- **Pengurutan (Sorting)**: Urutkan hasil berdasarkan `id` atau `name`.
- **Dokumentasi Otomatis**: Dokumentasi API interaktif yang dibuat otomatis oleh FastAPI dan dapat diakses di endpoint `/docs`.
- **Seeding Jarak Jauh**: Endpoint khusus (`/api/seed`) untuk mengisi data awal ke database langsung dari Vercel tanpa memerlukan instalasi Python lokal.
- **Serverless**: Di-deploy di platform Vercel yang skalabel dan efisien.

---

## 🛠️ Teknologi yang Digunakan

- **Backend**: Python 3.11+
- **Framework API**: FastAPI
- **Database**: PostgreSQL (di-hosting di [Neon](https://neon.tech))
- **Platform Deploy**: [Vercel](https://vercel.com)
- **Interaksi DB**: SQLAlchemy (sebagai ORM)
- **Validasi Data**: Pydantic

---

## 🚀 Endpoint API

Berikut adalah ringkasan endpoint yang tersedia:

| Metode | Endpoint                     | Deskripsi                                                   |
| :------ | :--------------------------- | :---------------------------------------------------------- |
| `GET`   | `/locations`                 | Mengambil semua lokasi dengan filter, sort, dan search.     |
| `POST`  | `/locations`                 | Menambahkan lokasi baru.                                    |
| `GET`   | `/locations/{location_id}`   | Mengambil satu lokasi berdasarkan ID-nya.                   |
| `PATCH` | `/locations/{location_id}`   | Memperbarui sebagian data lokasi yang sudah ada.            |
| `DELETE`| `/locations/{location_id}`   | Menghapus lokasi berdasarkan ID-nya.                        |
| `POST`  | `/api/seed`                  | **[Admin]** Mengisi database dengan data awal. Membutuhkan kunci rahasia. |

Untuk detail lengkap mengenai parameter dan model data, silakan akses dokumentasi interaktif di `/docs`.

---

## ⚙️ Setup dan Deployment

Berikut cara men-deploy proyek ini dari awal:

### 1. Siapkan Database
- Buat akun gratis di [Neon](https://neon.tech).
- Buat proyek baru untuk mendapatkan database PostgreSQL.
- Salin **URL Koneksi** database Anda.

### 2. Fork dan Clone Repositori
- Fork repositori ini ke akun GitHub Anda.
- Clone repositori yang sudah Anda fork ke komputer Anda.

### 3. Deploy ke Vercel
- Masuk ke [Vercel](https://vercel.com) dengan akun GitHub Anda.
- Klik **Add New... > Project**.
- Pilih repositori yang baru saja Anda clone.
- Buka bagian **Environment Variables** dan tambahkan:
    - `DATABASE_URL`: Isi dengan URL koneksi dari Neon.
    - `SEED_SECRET`: Isi dengan kata sandi rahasia yang kuat (buat sendiri).
- Klik **Deploy**.

### 4. Isi Data Awal (Seeding)
- Setelah deployment berhasil, buka URL API Anda dan tambahkan `/docs` di belakangnya (misal: `https://proyek-anda.vercel.app/docs`).
- Cari endpoint `POST /api/seed`.
- Klik "Try it out", masukkan `SEED_SECRET` yang Anda buat, lalu klik "Execute".
- Database Anda kini sudah terisi dengan data dari `db.json`.

### 5. (Opsional) Hapus Endpoint Seeding
- Untuk keamanan maksimal, hapus endpoint `/api/seed` dari file `api/index.py`, lalu commit dan push perubahan tersebut ke GitHub. Vercel akan otomatis men-deploy ulang versi yang lebih aman.

---

Aplikasi API Anda kini sudah siap digunakan!