"""
Management command: import_cabang
Membaca 'Kode Kantor dan anaknya.xlsx' dari root project dan mengisi
tabel KantorCabang + KantorCabangPembantu.

Jalankan dengan:
    python manage.py import_cabang
"""

import os
import pandas as pd
from django.core.management.base import BaseCommand
from kolek.models import KantorCabang, KantorCabangPembantu


# Jenis kantor yang berfungsi sebagai INDUK (Kantor Cabang)
KC_TYPES = {'CABANG', 'CABANG KOORDINATOR MEDAN', 'CABANG SYARIAH'}


class Command(BaseCommand):
    help = 'Import data Kantor Cabang & KCP dari file Excel ke database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            default='Kode Kantor dan anaknya.xlsx',
            help='Path ke file Excel (relatif dari root project atau absolut)',
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Hapus semua data KC & KCP yang ada sebelum import ulang',
        )

    def handle(self, *args, **options):
        file_path = options['file']
        if not os.path.isabs(file_path):
            # Cari relatif ke BASE_DIR (root project, 2 level di atas file ini)
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
                os.path.abspath(__file__)
            ))))
            file_path = os.path.join(base_dir, file_path)

        if not os.path.exists(file_path):
            self.stderr.write(self.style.ERROR(f'File tidak ditemukan: {file_path}'))
            return

        self.stdout.write(f'Membaca: {file_path}')

        try:
            if file_path.lower().endswith('.csv'):
                # Coba baca CSV
                df = pd.read_csv(file_path, sep=None, engine='python')
            else:
                # Default Excel
                df = pd.read_excel(file_path, sheet_name=0, header=0)
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'Gagal baca file: {e}'))
            return


        
        # Cari kolom yang mirip
        col_map = {}
        for c in df.columns:
            c_upper = str(c).upper().strip()
            if c_upper == 'NO': col_map['no'] = c
            elif 'KD_CAB' in c_upper or 'KODE' in c_upper: col_map['kode'] = c
            elif 'JENIS' in c_upper: col_map['jenis'] = c
            elif 'NAMA' in c_upper: col_map['nama'] = c
            elif 'STATUS' in c_upper: col_map['status'] = c

        # Validasi kolom minimal
        if not all(k in col_map for k in ['no', 'kode', 'jenis', 'nama']):
            self.stderr.write(self.style.ERROR(f'Kolom wajib (NO, KODE/KD_CAB, JENIS, NAMA) tidak ditemukan. Ada: {list(df.columns)}'))
            return

        # Hapus data lama jika diminta
        if options['clear']:
            KantorCabangPembantu.objects.all().delete()
            KantorCabang.objects.all().delete()
            self.stdout.write(self.style.WARNING('Data lama dihapus.'))

        # Bangun hierarki KC → KCP dari urutan baris menggunakan KC_INDICES
        current_kc = None
        kc_count   = 0
        kcp_count  = 0
        skip_count = 0

        for _, row in df.iterrows():
            # Ambil nilai baris (NO)
            try:
                row_no = int(float(row[col_map['no']]))
            except:
                skip_count += 1
                continue

            kode  = str(row[col_map['kode']]).strip()
            jenis = str(row[col_map['jenis']]).upper().strip()
            nama  = str(row[col_map['nama']]).strip()
            
            # Status: AKTIF/TUTUP
            aktif = True
            if 'status' in col_map:
                st = str(row[col_map['status']]).upper().strip()
                aktif = ('AKTIF' in st)

            # Cek apakah baris ini adalah Kantor Pusat (Reset Hierarki)
            if 'KANTOR PUSAT' in jenis or 'UNIT USAHA SYARIAH' in nama.upper():
                current_kc = None
                skip_count += 1
                continue

            # Cek apakah baris ini adalah Kantor Cabang (KC)
            if jenis in KC_TYPES:
                kc_obj, created = KantorCabang.objects.update_or_create(
                    kode=kode,
                    defaults={
                        'nama': nama, 
                        'jenis': jenis,
                        'is_aktif': aktif
                    },
                )
                current_kc = kc_obj
                if created:
                    kc_count += 1
                else:
                    kc_obj.is_aktif = aktif
                    kc_obj.save()
            elif current_kc is not None:
                # Ini adalah KCP (Unit di bawah KC terakhir)
                _, created = KantorCabangPembantu.objects.update_or_create(
                    kode=kode,
                    defaults={
                        'cabang_induk': current_kc,
                        'nama': nama,
                        'jenis': jenis,
                        'is_aktif': aktif
                    },
                )
                if created:
                    kcp_count += 1
            else:
                # Lewati Baris 1 (Pusat) atau baris sebelum KC pertama
                skip_count += 1

        self.stdout.write(self.style.SUCCESS(
            f'Import Hierarki Selesai: {kc_count} KC, {kcp_count} KCP, {skip_count} baris dilewati.'
        ))
