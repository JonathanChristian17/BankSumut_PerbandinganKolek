"""
Management command: import_cabang
Membaca 'tmp_analysis/kode_kantor_all.csv' dari root project dan mengisi
tabel KantorCabang + KantorCabangPembantu.

Jalankan dengan:
    python manage.py import_cabang
    python manage.py import_cabang --clear   (hapus semua dulu)
    python manage.py import_cabang --file path/lain.xlsx
"""

import os
import pandas as pd
from django.core.management.base import BaseCommand
from kolek.models import KantorCabang, KantorCabangPembantu


# Jenis kantor yang berfungsi sebagai INDUK (Kantor Cabang)
KC_TYPES = {'CABANG', 'CABANG KOORDINATOR MEDAN', 'CABANG SYARIAH'}

# ── Safety Patch ──────────────────────────────────────────────────────────────
# Daftar KCP yang wajib ada tapi mungkin tidak ada di file Excel/CSV sumber.
# Format: {kode_kcp: (kode_kc_induk, nama_kcp, jenis)}
# Tambahkan entri baru di sini jika ada cabang serupa di masa depan.
MANUAL_PATCHES = {
    '286': ('210', 'CAPEM SEI BEROMBANG', 'CABANG PEMBANTU KONVENSIONAL'),
}
# ─────────────────────────────────────────────────────────────────────────────


class Command(BaseCommand):
    help = 'Import data Kantor Cabang & KCP dari file CSV/Excel ke database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            default='',
            help='Path ke file CSV/Excel (default: tmp_analysis/kode_kantor_all.csv)',
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Hapus semua data KC & KCP yang ada sebelum import ulang',
        )

    def handle(self, *args, **options):
        # ── Tentukan path file ────────────────────────────────────────────────
        file_path = options['file']
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__)
        ))))

        if not file_path:
            # Default: gunakan CSV di tmp_analysis
            file_path = os.path.join(base_dir, 'tmp_analysis', 'kode_kantor_all.csv')
        elif not os.path.isabs(file_path):
            file_path = os.path.join(base_dir, file_path)

        if not os.path.exists(file_path):
            self.stderr.write(self.style.ERROR(f'File tidak ditemukan: {file_path}'))
            return

        self.stdout.write(f'Membaca: {file_path}')

        # ── Baca file ─────────────────────────────────────────────────────────
        try:
            if file_path.lower().endswith('.csv'):
                df = pd.read_csv(file_path, sep=None, engine='python')
            else:
                df = pd.read_excel(file_path, sheet_name=0, header=0)
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'Gagal baca file: {e}'))
            return

        # ── Mapping kolom ─────────────────────────────────────────────────────
        col_map = {}
        for c in df.columns:
            cu = str(c).upper().strip()
            if cu == 'NO':                          col_map['no']     = c
            elif 'KD_CAB' in cu or 'KODE' in cu:   col_map['kode']   = c
            elif 'JENIS' in cu:                     col_map['jenis']  = c
            elif 'NAMA' in cu:                      col_map['nama']   = c
            elif 'STATUS' in cu:                    col_map['status'] = c

        if not all(k in col_map for k in ['no', 'kode', 'jenis', 'nama']):
            self.stderr.write(self.style.ERROR(
                f'Kolom wajib (NO, KODE/KD_CAB, JENIS, NAMA) tidak ditemukan. '
                f'Kolom tersedia: {list(df.columns)}'
            ))
            return

        # ── Hapus data lama jika --clear ──────────────────────────────────────
        if options['clear']:
            KantorCabangPembantu.objects.all().delete()
            KantorCabang.objects.all().delete()
            self.stdout.write(self.style.WARNING('Data lama dihapus.'))

        # ── Import baris per baris ─────────────────────────────────────────────
        current_kc = None
        kc_count = kcp_count = skip_count = 0

        for _, row in df.iterrows():
            try:
                int(float(row[col_map['no']]))
            except Exception:
                skip_count += 1
                continue

            kode  = str(row[col_map['kode']]).strip()
            jenis = str(row[col_map['jenis']]).upper().strip()
            nama  = str(row[col_map['nama']]).strip()

            aktif = True
            if 'status' in col_map:
                st = str(row[col_map['status']]).upper().strip()
                aktif = ('AKTIF' in st)

            if 'KANTOR PUSAT' in jenis or 'UNIT USAHA SYARIAH' in nama.upper():
                current_kc = None
                skip_count += 1
                continue

            if jenis in KC_TYPES:
                kc_obj, created = KantorCabang.objects.update_or_create(
                    kode=kode,
                    defaults={'nama': nama, 'jenis': jenis, 'is_aktif': aktif},
                )
                current_kc = kc_obj
                if created:
                    kc_count += 1
                else:
                    kc_obj.is_aktif = aktif
                    kc_obj.save()
            elif current_kc is not None:
                _, created = KantorCabangPembantu.objects.update_or_create(
                    kode=kode,
                    defaults={
                        'cabang_induk': current_kc,
                        'nama': nama,
                        'jenis': jenis,
                        'is_aktif': aktif,
                    },
                )
                if created:
                    kcp_count += 1
            else:
                skip_count += 1

        self.stdout.write(self.style.SUCCESS(
            f'Import CSV Selesai: {kc_count} KC baru, {kcp_count} KCP baru, {skip_count} baris dilewati.'
        ))

        # ── Terapkan Safety Patch (entri manual yang wajib ada) ───────────────
        patch_count = 0
        for kcp_kode, (kc_kode, kcp_nama, kcp_jenis) in MANUAL_PATCHES.items():
            try:
                kc_induk = KantorCabang.objects.get(kode=kc_kode)
            except KantorCabang.DoesNotExist:
                self.stderr.write(self.style.WARNING(
                    f'[PATCH] KC induk kode={kc_kode} tidak ditemukan, '
                    f'lewati patch untuk KCP {kcp_kode}.'
                ))
                continue

            _, created = KantorCabangPembantu.objects.update_or_create(
                kode=kcp_kode,
                defaults={
                    'cabang_induk': kc_induk,
                    'nama': kcp_nama,
                    'jenis': kcp_jenis,
                    'is_aktif': True,
                },
            )
            if created:
                patch_count += 1
                self.stdout.write(self.style.SUCCESS(
                    f'[PATCH] Ditambahkan: [{kcp_kode}] {kcp_nama} -> KC [{kc_kode}] {kc_induk.nama}'
                ))
            else:
                self.stdout.write(
                    f'[PATCH] Sudah ada & diperbarui: [{kcp_kode}] {kcp_nama} -> KC [{kc_kode}] {kc_induk.nama}'
                )

        # ── Verifikasi akhir ──────────────────────────────────────────────────
        total_kc  = KantorCabang.objects.count()
        total_kcp = KantorCabangPembantu.objects.count()
        self.stdout.write(self.style.SUCCESS(
            f'\nVerifikasi Database: {total_kc} KC, {total_kcp} KCP tersimpan.'
        ))

        # Tampilkan KCP yang masuk MANUAL_PATCHES sebagai bukti
        self.stdout.write('\n=== BUKTI KONSOLIDASI CABANG SEI BEROMBANG ===')
        for kcp_kode in MANUAL_PATCHES:
            try:
                kcp = KantorCabangPembantu.objects.select_related('cabang_induk').get(kode=kcp_kode)
                self.stdout.write(self.style.SUCCESS(
                    f'  [{kcp.kode}] {kcp.nama} -> Induk: [{kcp.cabang_induk.kode}] {kcp.cabang_induk.nama} OK'
                ))
            except KantorCabangPembantu.DoesNotExist:
                self.stderr.write(self.style.ERROR(f'  [{kcp_kode}] TIDAK DITEMUKAN!'))
