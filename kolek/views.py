
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Q
from django.core.paginator import Paginator
from django.http import HttpResponse
from datetime import datetime
from .models import (
    PergerakanKolekKonvensional,
    PergerakanKolekSyariah,
    KantorCabang,
    KantorCabangPembantu,
)
import pandas as pd
import json
import io
import re


# ─────────────────────────────────────────────────────────────
# KOLOM MAP
# ─────────────────────────────────────────────────────────────
KOLOM_MAP_KONVENSIONAL = {
    'RATING_KOLEK'      : 'kelompok_sandi',
    'KELOMPOK_SANDI'    : 'kelompok_sandi',
    'REK_KREDIT'        : 'accnbr',
    'ACCNBR'            : 'accnbr',
    'CIFID'             : 'cifid',
    'NAMA'              : 'cifnm',
    'CIFNM'             : 'cifnm',
    'CABANG'            : 'branchid',
    'BRANCHID'          : 'branchid',
    'PLAFOND'           : 'plafond',
    'SALDO_AKHIR'       : 'saldo_akhir',
    'NILAI_WAJAR'       : 'nilai_wajar',
    'HR_TUNGG_POKOK'    : 'hr_tungg_pokok',
    'HR_TUNGG_BUNGA'    : 'hr_tungg_margin',
    'HR_TUNGG_MARGIN'   : 'hr_tungg_margin',
    'KOLEK'             : 'kolek',
}

KOLOM_MAP_SYARIAH = {
    'KELOMPOK_SANDI'    : 'kelompok_sandi',
    'RATING_KOLEK'      : 'kelompok_sandi',
    'ACCNBR'            : 'accnbr',
    'REK_KREDIT'        : 'accnbr',
    'CIFID'             : 'cifid',
    'CIFNM'             : 'cifnm',
    'NAMA'              : 'cifnm',
    'BRANCHID'          : 'branchid',
    'CABANG'            : 'branchid',
    'PLAFOND'           : 'plafond',
    'SALDO_AKHIR'       : 'saldo_akhir',
    'NILAI_WAJAR'       : 'nilai_wajar',
    'HR_TUNGG_POKOK'    : 'hr_tungg_pokok',
    'HR_TUNGG_MARGIN'   : 'hr_tungg_margin',
    'HR_TUNGG_BUNGA'    : 'hr_tungg_margin',
    'KOLEK'             : 'kolek',
}

KOLOM_WAJIB = ['accnbr']


# ─────────────────────────────────────────────────────────────
# HELPER: data KC & KCP untuk cascading dropdown
# ─────────────────────────────────────────────────────────────
def _get_cabang_context(show_syariah=False):
    """Kembalikan list KC (induk) dan JSON mapping KC→KCP untuk template (filter Konven/Syariah)."""
    # Filter KC
    if show_syariah:
        kc_query = KantorCabang.objects.filter(is_aktif=True, jenis__icontains='SYARIAH')
    else:
        kc_query = KantorCabang.objects.filter(is_aktif=True).exclude(jenis__icontains='SYARIAH')
    
    kc_list = kc_query.prefetch_related('cabang_pembantu').all()
    cabang_mapping = {}
    for kc in kc_list:
        # Filter KCP sesuai jenis induknya
        cabang_mapping[kc.kode] = [
            {'kode': kcp.kode, 'nama': kcp.nama}
            for kcp in kc.cabang_pembantu.filter(is_aktif=True)
        ]
    return {
        'kc_list': kc_list,
        'cabang_mapping': cabang_mapping,
    }


# ─────────────────────────────────────────────────────────────
# HELPER: parse angka dari string / float
# ─────────────────────────────────────────────────────────────
def _parse_angka(v):
    if pd.isna(v):
        return 0
    if isinstance(v, (int, float)):
        return v
    s = str(v).strip().replace(' ', '')
    s = re.sub(r'[^\d.,()\\+-]', '', s)
    if not s:
        return 0
    if ',' in s and '.' in s:
        if s.rfind(',') > s.rfind('.'):
            s = s.replace('.', '').replace(',', '.')
        else:
            s = s.replace(',', '')
    elif ',' in s:
        parts = s.split(',')
        if all(len(p) == 3 and p.isdigit() for p in parts[1:]):
            s = s.replace(',', '')
        else:
            s = s.replace(',', '.')
    try:
        return float(s)
    except ValueError:
        return 0


def _clamp_int(val, min_val=-2147483648, max_val=2147483647):
    return max(min_val, min(max_val, int(val)))


# Batas wajar hari tunggakan: 0 s/d 36.500 hari (≈100 tahun).
# Nilai di atas ini PASTI bukan hari tunggakan — kemungkinan data finansial yang salah kolom.
MAX_HARI_TUNGGAKAN = 36_500

def _clamp_hari(val) -> int:
    """Kembalikan hari tunggakan yang wajar. Jika di luar [0, MAX_HARI_TUNGGAKAN] → 0."""
    try:
        v = int(val)
        if 0 <= v <= MAX_HARI_TUNGGAKAN:
            return v
        return 0
    except (ValueError, TypeError, OverflowError):
        return 0


# ─────────────────────────────────────────────────────────────
# HELPER: bersihkan dataframe (rename + tipe data)
# ─────────────────────────────────────────────────────────────
def _bersihkan_df(df: pd.DataFrame, kolom_map: dict) -> pd.DataFrame:
    df.columns = [re.sub(r'\s+', '_', str(c).strip().upper()) for c in df.columns]

    # Hapus kolom duplikat (ambil yang pertama)
    df = df.loc[:, ~df.columns.duplicated()]

    # FUZZY MAPPING: Catch column name variations (e.g., "HARI_TUNGGAKAN_POKOK", "TUNG_POKOK", "TUNGG_MRGN")
    for c in list(df.columns):
        if 'TUNG' in c and 'POKOK' in c:
            df.rename(columns={c: 'HR_TUNGG_POKOK'}, inplace=True)
        elif 'TUNG' in c and ('MARGIN' in c or 'BUNGA' in c):
            df.rename(columns={c: 'HR_TUNGG_MARGIN'}, inplace=True)

    rename_dict = {k: v for k, v in kolom_map.items() if k in df.columns}
    df = df.rename(columns=rename_dict)
    df = df.dropna(how='all')

    # kelompok_sandi: float 1.0 → '1', 2A → '2A'
    if 'kelompok_sandi' in df.columns:
        def _sandi(v):
            if pd.isna(v) or v == '':
                return ''
            if isinstance(v, float) and v == int(v):
                return str(int(v))
            return str(v).strip().upper()
        df['kelompok_sandi'] = df['kelompok_sandi'].apply(_sandi)

    # cifid: simpan sebagai string
    if 'cifid' in df.columns:
        df['cifid'] = df['cifid'].fillna('').astype(str).str.strip()

    # cifnm: string
    if 'cifnm' in df.columns:
        df['cifnm'] = df['cifnm'].fillna('').astype(str)

    # branchid: integer
    if 'branchid' in df.columns:
        df['branchid'] = pd.to_numeric(df['branchid'], errors='coerce').fillna(0).astype(int)

    # plafond, saldo_akhir, nilai_wajar: desimal
    for col in ['plafond', 'saldo_akhir', 'nilai_wajar']:
        if col in df.columns:
            df[col] = df[col].apply(_parse_angka)

    # hr_tungg_pokok, hr_tungg_margin: integer wajar (0 – 36.500 hari)
    # Jika nilainya > MAX_HARI_TUNGGAKAN (misalnya data finansial yang nyasar kolom), set ke 0.
    for col in ['hr_tungg_pokok', 'hr_tungg_margin']:
        if col in df.columns:
            df[col] = (
                df[col]
                .apply(_parse_angka)
                .fillna(0)
                .apply(_clamp_hari)
            )

    # kolek: integer
    if 'kolek' in df.columns:
        df['kolek'] = pd.to_numeric(df['kolek'], errors='coerce').fillna(0).astype(int)

    return df


# ─────────────────────────────────────────────────────────────
# HELPER: upload generik (dipakai konvensional & syariah)
# ─────────────────────────────────────────────────────────────
def _proses_upload(request, ModelKelas, kolom_map, redirect_name, template_name, extra_ctx=None):
    hasil = {'berhasil': 0, 'gagal': 0, 'errors': [], 'selesai': False}

    if request.method == 'POST':
        file           = request.FILES.get('file_excel')
        tanggal_upload = request.POST.get('tanggal_upload')

        if not file:
            messages.error(request, 'Pilih file Excel terlebih dahulu.')
            return redirect(redirect_name)
        if not tanggal_upload:
            messages.error(request, 'Pilih tanggal upload terlebih dahulu.')
            return redirect(redirect_name)
        if not (file.name.endswith('.xlsx') or file.name.endswith('.xls')):
            messages.error(request, 'Format file harus .xlsx atau .xls')
            return redirect(redirect_name)

        try:
            file_bytes = io.BytesIO(file.read())
            
            # ── Baca Excel dengan pandas menggunakan engine tercepat ──
            try:
                import python_calamine
                engine = 'calamine'
            except ImportError:
                engine = 'openpyxl' if file.name.endswith('.xlsx') else 'xlrd'
                
            df = pd.read_excel(file_bytes, engine=engine, header=0, dtype={2: str})
            df = _bersihkan_df(df, kolom_map)

            for col in KOLOM_WAJIB:
                if col not in df.columns:
                    messages.error(request, f'Kolom wajib tidak ditemukan: {col}. Kolom terbaca: {list(df.columns)}')
                    return redirect(redirect_name)

            # Ambil REK_KREDIT yang sudah ada untuk memisahkan insert dan update
            existing_pks = set(
                ModelKelas.objects.filter(tanggal_upload=tanggal_upload).values_list('accnbr', flat=True)
            )

            FIELD_DB = ['kelompok_sandi', 'cifid', 'cifnm', 'branchid',
                        'plafond', 'saldo_akhir', 'nilai_wajar',
                        'hr_tungg_pokok', 'hr_tungg_margin', 'kolek']

            mask_existing = df['accnbr'].isin(existing_pks)
            df_insert = df[~mask_existing].copy()
            df_update = df[mask_existing].copy()
            
            # 1. PROSES INSERT CEPAT MENGGUNAKAN POSTGRESQL COPY
            if not df_insert.empty:
                # Pastikan SEMUA kolom FIELD_DB ada di DataFrame, karena Django tidak menyetel 
                # default=0 di skema tabel database (ia mengaturnya dari level Python).
                # Jika kita tidak mengirim kolom tersebut, PostgreSQL akan mencoba memasukkan NULL.
                for col in FIELD_DB:
                    if col not in df_insert.columns:
                        if col in ['hr_tungg_pokok', 'hr_tungg_margin', 'kolek', 'branchid']:
                            df_insert[col] = 0
                        elif col in ['plafond', 'saldo_akhir', 'nilai_wajar']:
                            df_insert[col] = 0.0
                        elif col in ['kelompok_sandi', 'cifid', 'cifnm']:
                            df_insert[col] = ''

                # Sekarang ambil semua field secara eksplisit
                insert_cols = ['tanggal_upload', 'accnbr'] + FIELD_DB
                df_insert['tanggal_upload'] = tanggal_upload
                df_final_insert = df_insert[insert_cols].copy()
                
                # Isi nilai kosong (NaN) dengan 0 untuk numeric, dan string kosong untuk text
                for f in insert_cols:
                    if f in ['hr_tungg_pokok', 'hr_tungg_margin', 'kolek', 'branchid']:
                        df_final_insert[f] = df_final_insert[f].fillna(0).astype(int)
                    elif f in ['plafond', 'saldo_akhir', 'nilai_wajar']:
                        df_final_insert[f] = df_final_insert[f].fillna(0)
                    elif f in ['kelompok_sandi', 'cifid', 'cifnm']:
                        df_final_insert[f] = df_final_insert[f].fillna('')

                csv_buffer = io.StringIO()
                df_final_insert.to_csv(csv_buffer, index=False, header=False, sep='\t')
                csv_buffer.seek(0)
                
                from django.db import connection
                with connection.cursor() as cursor:
                    table_name = ModelKelas._meta.db_table
                    # KUNCI UTAMA: Sebutkan semua kolomnya secara ketat.
                    columns_sql = ', '.join([f'"{col}"' for col in insert_cols])
                    sql = f"COPY {table_name} ({columns_sql}) FROM STDIN WITH CSV DELIMITER '\t' NULL ''"
                    cursor.copy_expert(sql, csv_buffer)
                
                hasil['berhasil'] += len(df_final_insert)

            # 2. PROSES UPDATE EFEKTIF
            if not df_update.empty:
                # Muat batch record yang ingin diupdate ke memory
                existing_objs = {
                    obj.accnbr: obj for obj in ModelKelas.objects.filter(
                        tanggal_upload=tanggal_upload,
                        accnbr__in=existing_pks
                    )
                }

                to_update_objs = []
                update_fields_available = [f for f in FIELD_DB if f in df_update.columns]
                
                recordsToUpdate = df_update.to_dict('records')
                for row in recordsToUpdate:
                    rek = row['accnbr']
                    if rek in existing_objs:
                        obj = existing_objs[rek]
                        for f in update_fields_available:
                            setattr(obj, f, row[f])
                        to_update_objs.append(obj)
                
                if to_update_objs:
                    ModelKelas.objects.bulk_update(to_update_objs, update_fields_available, batch_size=1000)
                    hasil['berhasil'] += len(to_update_objs)

            hasil['selesai'] = True

        except Exception as e:
            messages.error(request, f'Gagal membaca/memproses file: {e}')
            import traceback
            traceback.print_exc()

    ctx = {'hasil': hasil}
    if extra_ctx:
        ctx.update(extra_ctx)
    return render(request, template_name, ctx)


# ─────────────────────────────────────────────────────────────
# HELPER: bandingkan generik
# ─────────────────────────────────────────────────────────────
def _bandingkan(request, ModelKelas, template_name, extra_ctx=None):
    tanggal1      = request.GET.get('tanggal1')
    tanggal2      = request.GET.get('tanggal2')
    filter_kat    = request.GET.get('kategori', '')
    filter_rating = request.GET.get('filter_rating', '')
    hasil_banding = None
    ringkasan     = {}
    page_obj      = None
    perubahan_list = []

    tanggal_list = (
        ModelKelas.objects
        .values_list('tanggal_upload', flat=True)
        .distinct()
        .order_by('tanggal_upload')
    )

    if tanggal1 and tanggal2:
        try:
            d1 = datetime.strptime(tanggal1, "%Y-%m-%d").date()
            d2 = datetime.strptime(tanggal2, "%Y-%m-%d").date()
            redirect_url = extra_ctx.get('redirect_url') if extra_ctx else 'kolek:bandingkan'
            if d2 <= d1:
                messages.error(request, "Tanggal 2 harus lebih baru dari Tanggal 1.")
                return redirect(redirect_url)
            if (d2 - d1).days > 31:
                messages.error(request, "Jarak perbandingan maksimal adalah 1 bulan (31 hari).")
                return redirect(redirect_url)
        except ValueError:
            pass

        COLS = ['accnbr', 'cifnm', 'kelompok_sandi', 'kolek', 'saldo_akhir', 'nilai_wajar']
        qs1 = ModelKelas.objects.filter(tanggal_upload=tanggal1).values(*COLS)
        qs2 = ModelKelas.objects.filter(tanggal_upload=tanggal2).values(*COLS)

        df1 = pd.DataFrame(list(qs1))
        df2 = pd.DataFrame(list(qs2))

        EMPTY = pd.DataFrame(columns=COLS)
        if df1.empty: df1 = EMPTY.copy()
        if df2.empty: df2 = EMPTY.copy()

        if df1.empty and df2.empty:
            hasil_banding = []
        else:
            df1['sumber'] = 'T1'
            df2['sumber'] = 'T2'
            df_all = pd.concat([df1, df2], ignore_index=True)
            df_pivot = df_all.pivot_table(
                index='accnbr',
                columns='sumber',
                values=['cifnm', 'kolek', 'kelompok_sandi', 'saldo_akhir', 'nilai_wajar'],
                aggfunc='first'
            )
            df_pivot.columns = [f"{col[0]}_{col[1].lower()}" for col in df_pivot.columns]
            df = df_pivot.reset_index()

            cols_needed = ['cifnm_t1', 'cifnm_t2', 'kolek_t1', 'kolek_t2',
                           'kelompok_sandi_t1', 'kelompok_sandi_t2',
                           'saldo_akhir_t1', 'saldo_akhir_t2',
                           'nilai_wajar_t1', 'nilai_wajar_t2']
            for c in cols_needed:
                if c not in df.columns:
                    df[c] = None

            df['cifnm'] = df['cifnm_t1'].combine_first(df['cifnm_t2']).fillna('-')

            has_t1 = df['kolek_t1'].notna()
            has_t2 = df['kolek_t2'].notna()
            rating_t1_str = df['kelompok_sandi_t1'].fillna('').astype(str).str.strip().str.upper()
            rating_t2_str = df['kelompok_sandi_t2'].fillna('').astype(str).str.strip().str.upper()

            def _get_status(r1, r2):
                if not r1 and not r2: return 'tetap'
                
                # Hierarki kolektibilitas (semakin besar angkanya, semakin memburuk)
                hierarki = {'1': 1, '2A': 2, '2B': 3, '2C': 4, '3': 5, '4': 6, '5': 7}
                val1 = hierarki.get(r1)
                val2 = hierarki.get(r2)
                
                if val1 is None or val2 is None:
                    return 'tetap' if r1 == r2 else 'berbeda'
                    
                if val1 == val2:
                    return 'tetap'
                elif val1 > val2:
                    return 'membaik'
                else:
                    return 'memburuk'

            df['kategori'] = 'baru'
            df.loc[has_t1 & ~has_t2, 'kategori'] = 'lunas'
            
            mask_has_both = has_t1 & has_t2
            if mask_has_both.any():
                df.loc[mask_has_both, 'kategori'] = df[mask_has_both].apply(
                    lambda row: _get_status(row['kelompok_sandi_t1'].strip().upper() if pd.notna(row['kelompok_sandi_t1']) else '', 
                                            row['kelompok_sandi_t2'].strip().upper() if pd.notna(row['kelompok_sandi_t2']) else ''), 
                    axis=1
                )

            r1 = df['kelompok_sandi_t1'].fillna('-').astype(str)
            r2 = df['kelompok_sandi_t2'].fillna('-').astype(str)
            df['perubahan_label'] = r1 + ' -> ' + r2
            df.loc[df['kategori'] == 'lunas', 'perubahan_label'] = 'Lunas / Tutup'
            df.loc[df['kategori'] == 'baru',  'perubahan_label'] = 'Fasilitas Baru'

            ringkasan = {
                'tetap'   : int((df['kategori'] == 'tetap').sum()),
                'membaik' : int((df['kategori'] == 'membaik').sum()),
                'memburuk': int((df['kategori'] == 'memburuk').sum()),
                'berbeda' : int((df['kategori'] == 'berbeda').sum()),
                'lunas'   : int((df['kategori'] == 'lunas').sum()),
                'baru'    : int((df['kategori'] == 'baru').sum()),
                'total'   : len(df),
            }
            perubahan_list = sorted(
                df.loc[df['kategori'].isin(['membaik', 'memburuk', 'berbeda']), 'perubahan_label'].unique().tolist()
            )

            if filter_kat:
                df = df[df['kategori'] == filter_kat]
            if filter_rating:
                df = df[df['perubahan_label'] == filter_rating]

            df['kolek_t1_disp']   = df.apply(lambda r: int(r['kolek_t1']) if pd.notna(r['kolek_t1']) else '-', axis=1)
            df['kolek_t2_disp']   = df.apply(lambda r: int(r['kolek_t2']) if pd.notna(r['kolek_t2']) else '-', axis=1)
            df['rating_t1_disp']  = df['kelompok_sandi_t1'].fillna('-').astype(str)
            df['rating_t2_disp']  = df['kelompok_sandi_t2'].fillna('-').astype(str)
            df['saldo_t1_disp']   = df['saldo_akhir_t1'].fillna('-')
            df['saldo_t2_disp']   = df['saldo_akhir_t2'].fillna('-')
            df['nilai_wajar_t2_disp'] = df['nilai_wajar_t2'].fillna('-')

            # --- ECHARTS DATA PREPARATION ---
            import json
            import math

            def safe_float(v):
                if pd.isna(v) or math.isinf(v) or math.isnan(v):
                    return 0.0
                return float(v)

            # 1. Pie Chart / Donut Chart (Jumlah per kategori)
            pie_data = [
                {'name': 'Tetap', 'value': ringkasan['tetap'], 'itemStyle': {'color': '#94a3b8'}},
                {'name': 'Membaik', 'value': ringkasan['membaik'], 'itemStyle': {'color': '#10b981'}},
                {'name': 'Memburuk', 'value': ringkasan['memburuk'], 'itemStyle': {'color': '#ef4444'}},
                {'name': 'Lunas / Tutup', 'value': ringkasan['lunas'], 'itemStyle': {'color': '#3b82f6'}},
                {'name': 'Fasilitas Baru', 'value': ringkasan['baru'], 'itemStyle': {'color': '#8b5cf6'}},
            ]
            
            # 2. Sankey Diagram (Removed per user request)
            
            # 3. Bar Chart (Exposure Finansial per Kategori: Saldo T2 vs Nilai T2)
            # Filter bar group by kategori
            bar_categories = ['tetap', 'membaik', 'memburuk', 'baru']
            bar_saldo = []
            bar_nilai = []
            for cat in bar_categories:
                df_cat = df[df['kategori'] == cat]
                # Sum floats safely
                sum_saldo = safe_float(df_cat['saldo_akhir_t2'].sum()) if 'saldo_akhir_t2' in df_cat.columns else 0.0
                sum_nilai = safe_float(df_cat['nilai_wajar_t2'].sum()) if 'nilai_wajar_t2' in df_cat.columns else 0.0
                bar_saldo.append(sum_saldo)
                bar_nilai.append(sum_nilai)
                
            echarts_data = {
                'pie_data': json.dumps(pie_data),
                'bar_categories': json.dumps(['Tetap', 'Membaik', 'Memburuk', 'Baru']),
                'bar_saldo': json.dumps(bar_saldo),
                'bar_nilai': json.dumps(bar_nilai),
            }
            # --- END ECHARTS DATA ---

            if request.GET.get('export') == 'excel':
                export_cols = {
                    'accnbr': 'No. Rekening',
                    'cifnm': 'Nama Debitur',
                    'rating_t1_disp': 'Kelompok Sandi T1',
                    'rating_t2_disp': 'Kelompok Sandi T2',
                    'kolek_t1_disp': 'Kolek T1',
                    'kolek_t2_disp': 'Kolek T2',
                    'nilai_wajar_t2_disp': 'Nilai Wajar T2',
                    'saldo_t2_disp': 'Saldo Akhir T2',
                    'perubahan_label': 'Perubahan Rating',
                    'kategori': 'Status',
                }
                df_export = df[list(export_cols.keys())].copy()
                status_map = {
                    'tetap': 'Tetap', 
                    'membaik': 'Membaik', 
                    'memburuk': 'Memburuk', 
                    'berbeda': 'Berubah', 
                    'lunas': 'Lunas/Tutup', 
                    'baru': 'Baru'
                }
                df_export['kategori'] = df_export['kategori'].map(status_map).fillna(df_export['kategori'])
                df_export['cifnm'] = df_export['cifnm'].astype(str).str.replace(',', ' ', regex=False)
                df_export['accnbr'] = '="' + df_export['accnbr'].astype(str) + '"'
                df_export = df_export.rename(columns=export_cols)

                response = HttpResponse(content_type='text/csv')
                bank_label = extra_ctx.get('bank_label', 'Bank') if extra_ctx else 'Bank'
                response['Content-Disposition'] = (
                    f'attachment; filename="Perbandingan_{bank_label}_{tanggal1}_vs_{tanggal2}.csv"'
                )
                export_token = request.GET.get('export_token')
                if export_token:
                    response.set_cookie(f'export_done_{export_token}', 'true', max_age=60)
                df_export.to_csv(response, sep=';', index=False, encoding='utf-8-sig')
                return response

            hasil_banding = df[[
                'accnbr', 'cifnm',
                'rating_t1_disp', 'rating_t2_disp',
                'kolek_t1_disp', 'kolek_t2_disp',
                'saldo_t1_disp', 'saldo_t2_disp',
                'nilai_wajar_t2_disp',
                'perubahan_label', 'kategori',
            ]].to_dict('records')

            paginator = Paginator(hasil_banding, 100)
            page_num  = request.GET.get('page', 1)
            page_obj  = paginator.get_page(page_num)

    ctx = {
        'tanggal1'      : tanggal1,
        'tanggal2'      : tanggal2,
        'tanggal_list'  : tanggal_list,
        'hasil_banding' : hasil_banding,
        'page_obj'      : page_obj,
        'ringkasan'     : ringkasan,
        'filter_kat'    : filter_kat,
        'filter_rating' : filter_rating,
        'perubahan_list': perubahan_list,
    }
    
    if hasil_banding is not None and 'echarts_data' in locals():
        ctx.update(echarts_data)
        
    if extra_ctx:
        ctx.update(extra_ctx)
    return render(request, template_name, ctx)


# ══════════════════════════════════════════════════════════════
# VIEWS — BANK KONVENSIONAL
# ══════════════════════════════════════════════════════════════

@login_required
def kolek_konvensional_view(request):
    data        = PergerakanKolekKonvensional.objects.all()
    rating_list = (
        PergerakanKolekKonvensional.objects
        .values_list('kelompok_sandi', flat=True)
        .distinct().order_by('kelompok_sandi')
    )
    tanggal_list = (
        PergerakanKolekKonvensional.objects
        .values_list('tanggal_upload', flat=True)
        .distinct().order_by('-tanggal_upload')
    )

    rating  = request.GET.get('rating')
    search  = request.GET.get('search')
    tanggal = request.GET.get('tanggal')
    cabang  = request.GET.get('cabang')   # kode KC yang dipilih
    kcp     = request.GET.get('kcp')      # kode KCP yang dipilih

    if 'tanggal' not in request.GET and tanggal_list.exists():
        tgl = tanggal_list.first()
        tanggal = tgl.strftime('%Y-%m-%d') if hasattr(tgl, 'strftime') else str(tgl)

    if rating:
        data = data.filter(kelompok_sandi=rating)
    if search:
        try:
            data = data.filter(Q(cifnm__icontains=search) | Q(accnbr=int(search)))
        except ValueError:
            data = data.filter(cifnm__icontains=search)
    if tanggal:
        data = data.filter(tanggal_upload=tanggal)

    # Filter bertingkat: KCP lebih spesifik dari KC
    if kcp:
        data = data.filter(branchid=kcp)
    elif cabang:
        # Ambil semua kode KCP di bawah KC ini, lalu sertakan kode KC sendiri
        kcp_kodes = list(
            KantorCabangPembantu.objects
            .filter(cabang_induk__kode=cabang)
            .values_list('kode', flat=True)
        )
        kcp_kodes.append(cabang)
        data = data.filter(branchid__in=kcp_kodes)

    summary   = data.aggregate(total_saldo=Sum('saldo_akhir'))
    paginator = Paginator(data, 100)
    page_obj  = paginator.get_page(request.GET.get('page', 1))

    ctx = {
        'page_obj'     : page_obj,
        'summary'      : summary,
        'total'        : data.count(),
        'rating_list'  : rating_list,
        'tanggal_list' : tanggal_list,
        'tanggal_aktif': tanggal,
        'bank'         : 'konvensional',
    }
    ctx.update(_get_cabang_context(show_syariah=False))
    return render(request, 'kolek/konvensional/pergerakan.html', ctx)


@login_required
def upload_konvensional_view(request):
    return _proses_upload(
        request,
        ModelKelas   = PergerakanKolekKonvensional,
        kolom_map    = KOLOM_MAP_KONVENSIONAL,
        redirect_name= 'kolek:konvensional_upload',
        template_name= 'kolek/konvensional/upload.html',
        extra_ctx    = {'bank': 'konvensional', 'kolom_map': KOLOM_MAP_KONVENSIONAL},
    )


@login_required
def bandingkan_konvensional_view(request):
    return _bandingkan(
        request,
        ModelKelas  = PergerakanKolekKonvensional,
        template_name = 'kolek/konvensional/bandingkan.html',
        extra_ctx   = {
            'bank': 'konvensional',
            'bank_label': 'Konvensional',
            'redirect_url': 'kolek:konvensional_bandingkan',
        },
    )


# ══════════════════════════════════════════════════════════════
# VIEWS — BANK SYARIAH
# ══════════════════════════════════════════════════════════════

@login_required
def kolek_syariah_view(request):
    data        = PergerakanKolekSyariah.objects.all()
    rating_list = (
        PergerakanKolekSyariah.objects
        .values_list('kelompok_sandi', flat=True)
        .distinct().order_by('kelompok_sandi')
    )
    tanggal_list = (
        PergerakanKolekSyariah.objects
        .values_list('tanggal_upload', flat=True)
        .distinct().order_by('-tanggal_upload')
    )

    rating  = request.GET.get('rating')
    search  = request.GET.get('search')
    tanggal = request.GET.get('tanggal')
    cabang  = request.GET.get('cabang')   # kode KC yang dipilih
    kcp     = request.GET.get('kcp')      # kode KCP yang dipilih

    if 'tanggal' not in request.GET and tanggal_list.exists():
        tgl = tanggal_list.first()
        tanggal = tgl.strftime('%Y-%m-%d') if hasattr(tgl, 'strftime') else str(tgl)

    if rating:
        data = data.filter(kelompok_sandi=rating)
    if search:
        try:
            data = data.filter(Q(cifnm__icontains=search) | Q(accnbr=int(search)))
        except ValueError:
            data = data.filter(cifnm__icontains=search)
    if tanggal:
        data = data.filter(tanggal_upload=tanggal)

    # Filter bertingkat: KCP lebih spesifik dari KC
    if kcp:
        data = data.filter(branchid=kcp)
    elif cabang:
        kcp_kodes = list(
            KantorCabangPembantu.objects
            .filter(cabang_induk__kode=cabang)
            .values_list('kode', flat=True)
        )
        kcp_kodes.append(cabang)
        data = data.filter(branchid__in=kcp_kodes)

    summary   = data.aggregate(total_saldo=Sum('saldo_akhir'))
    paginator = Paginator(data, 100)
    page_obj  = paginator.get_page(request.GET.get('page', 1))

    ctx = {
        'page_obj'     : page_obj,
        'summary'      : summary,
        'total'        : data.count(),
        'rating_list'  : rating_list,
        'tanggal_list' : tanggal_list,
        'tanggal_aktif': tanggal,
        'bank'         : 'syariah',
    }
    ctx.update(_get_cabang_context(show_syariah=True))
    return render(request, 'kolek/syariah/pergerakan.html', ctx)


@login_required
def upload_syariah_view(request):
    return _proses_upload(
        request,
        ModelKelas   = PergerakanKolekSyariah,
        kolom_map    = KOLOM_MAP_SYARIAH,
        redirect_name= 'kolek:syariah_upload',
        template_name= 'kolek/syariah/upload.html',
        extra_ctx    = {'bank': 'syariah', 'kolom_map': KOLOM_MAP_SYARIAH},
    )


@login_required
def bandingkan_syariah_view(request):
    return _bandingkan(
        request,
        ModelKelas  = PergerakanKolekSyariah,
        template_name = 'kolek/syariah/bandingkan.html',
        extra_ctx   = {
            'bank': 'syariah',
            'bank_label': 'Syariah',
            'redirect_url': 'kolek:syariah_bandingkan',
        },
    )
