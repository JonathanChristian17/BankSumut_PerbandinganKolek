
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
# ═══════════════════════════════════════════════════════════════
# ██ ZONA HIBERNASI OTP — JANGAN HAPUS BLOK INI ██
# ═══════════════════════════════════════════════════════════════
# Blok di bawah ini adalah KODE OTP LENGKAP yang sudah berfungsi.
# Dibekukan sementara karena sistem masih berjalan dengan 1 user.
# CARA MENGAKTIFKAN KEMBALI: hilangkan tanda '#' pada semua baris
# di bawah ini, dan buka kembali path 'verifikasi/' di kolek/urls.py.
# ─────────────────────────────────────────────────────────────
# from functools import wraps
# from django_otp.plugins.otp_totp.models import TOTPDevice
# from django_otp import login as otp_login
# import qrcode
# import base64
#
# # DECORATOR CUSTOM UNTUK OTP
# def require_otp(view_func):
#     """
#     Decorator tambahan setelah @login_required.
#     Jika user sudah login tapi belum lewati verifikasi OTP, lempar ke halaman OTP.
#     """
#     @wraps(view_func)
#     def _wrapped_view(request, *args, **kwargs):
#         user = request.user
#         if hasattr(user, 'is_authenticated') and user.is_authenticated:
#             if hasattr(user, 'is_verified') and not user.is_verified():
#                 return redirect('kolek:otp_verifikasi')
#         return view_func(request, *args, **kwargs)
#     return _wrapped_view
#
# # VIEW SETUP / VALIDASI OTP
# @login_required
# def otp_verifikasi_view(request):
#     user = request.user
#     if user.is_verified():
#         return redirect('kolek:konvensional_pergerakan')
#     device = TOTPDevice.objects.filter(user=user, confirmed=True).first()
#     msg_error = ""
#     if not device:
#         unconfirmed_device = TOTPDevice.objects.filter(user=user, confirmed=False).first()
#         if not unconfirmed_device:
#             unconfirmed_device = TOTPDevice.objects.create(user=user, confirmed=False)
#         url = unconfirmed_device.config_url
#         img = qrcode.make(url)
#         buf = io.BytesIO()
#         img.save(buf)
#         qr_b64 = base64.b64encode(buf.getvalue()).decode('utf-8')
#         if request.method == "POST":
#             token = request.POST.get('token')
#             if unconfirmed_device.verify_token(token):
#                 unconfirmed_device.confirmed = True
#                 unconfirmed_device.save()
#                 otp_login(request, unconfirmed_device)
#                 return redirect('kolek:konvensional_pergerakan')
#             else:
#                 msg_error = "Kode tidak sesuai. Coba lagi."
#         return render(request, 'kolek/otp_validation.html', {'qr_b64': qr_b64, 'msg_error': msg_error})
#     else:
#         if request.method == "POST":
#             token = request.POST.get('token')
#             if device.verify_token(token):
#                 otp_login(request, device)
#                 return redirect('kolek:konvensional_pergerakan')
#             else:
#                 msg_error = "Kode tidak sesuai atau sudah kadaluarsa. Coba lagi."
#         return render(request, 'kolek/otp_validation.html', {'msg_error': msg_error})
# ═══════════════════════════════════════════════════════════════
# ██ ZONA AKTIF: Dekorator passthrough pengganti sementara ██
# Saat OTP dibekukan, @require_otp langsung meloloskan user.
# ═══════════════════════════════════════════════════════════════
from functools import wraps

def require_otp(view_func):
    """Passthrough sementara — OTP sedang dihibernasi. Aktifkan kembali blok di atas untuk produksi multi-user."""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        return view_func(request, *args, **kwargs)
    return _wrapped_view

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
    'CKPN'              : 'ckpn',
    'STRTDT'            : 'strtdt',
    'DUEDT'             : 'duedt',
    'PRODID'            : 'prodid',
    'PRODNM'            : 'prodnm',
    'TUNGGAKAN_POKOK'   : 'tunggakan_pokok',
    'TUNGGAKAN_BUNGA'   : 'tunggakan_bunga',
    'HR_TUNGG_POKOK'    : 'hr_tungg_pokok',
    'HR_TUNGG_BUNGA'    : 'hr_tungg_margin',
    'HR_TUNGG_MARGIN'   : 'hr_tungg_margin',
    'KOLEK'             : 'kolek',
}

KOLOM_MAP_SYARIAH = {
    'KELOMPOK_SANDI'    : 'kelompok_sandi',
    'ACCNBR'            : 'accnbr',
    'CIFID'             : 'cifid',
    'CIFNM'             : 'cifnm',
    'BRANCHID'          : 'branchid',
    'PLAFOND'           : 'plafond',
    'SALDO_AKHIR'       : 'saldo_akhir',
    'NILAI_WAJAR'       : 'nilai_wajar',
    'AMTCKPNPSAK'       : 'ckpn',
    'OPENDT'            : 'strtdt',
    'DUEDT'             : 'duedt',
    'PRODNM'            : 'prodnm',
    'PRODID'            : 'prodid',
    'TUNGGAKAN_POKOK'   : 'tunggakan_pokok',
    'TUNGGAKAN_MARGIN'  : 'tunggakan_bunga',
    'HARI_TUNGGAKAN_POKOK': 'hr_tungg_pokok',
    'HARI_TUNGGAKAN_MARGIN': 'hr_tungg_margin',
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


# Batas wajar hari tunggakan: 0 s/d 3.650 hari (≈10 tahun).
# Nilai di atas ini kemungkinan besar data finansial (Saldo) yang salah kolom.
MAX_HARI_TUNGGAKAN = 3650

def _clamp_hari(val) -> int:
    """Kembalikan hari tunggakan yang wajar. Jika di luar [0, MAX_HARI_TUNGGAKAN] → 0."""
    try:
        v = int(float(val)) # bypass float strings
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

    # FUZZY MAPPING: Catch variations, but EXCLUDE money/balance columns
    for c in list(df.columns):
        # Jika kolom mengandung kata 'SALDO', 'PLAFOND', atau 'WAJAR', jangan jadikan HR_TUNGG
        if any(x in c for x in ['SALDO', 'PLAFOND', 'WAJAR', 'OS_']):
            continue
            
        # Pengecualian mutlak untuk nominal tunggakan uang, agar tidak dicaplok oleh fuzzy hari tunggakan
        if c in ['TUNGGAKAN_POKOK', 'TUNGGAKAN_BUNGA', 'TUNGGAKAN_MARGIN']:
            continue

        if 'TUNG' in c and 'POKOK' in c and 'HR_TUNGG_POKOK' not in df.columns:
            df.rename(columns={c: 'HR_TUNGG_POKOK'}, inplace=True)
        elif 'TUNG' in c and ('MARGIN' in c or 'BUNGA' in c) and 'HR_TUNGG_MARGIN' not in df.columns:
            df.rename(columns={c: 'HR_TUNGG_MARGIN'}, inplace=True)

    rename_dict = {k: v for k, v in kolom_map.items() if k in df.columns}
    df = df.rename(columns=rename_dict)
    
    # Hapus duplikat pasca rename untuk menghindari exception Pandas `Series is ambiguous`
    df = df.loc[:, ~df.columns.duplicated()]
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

    # cifid, cifnm, strtdt, duedt, prodid, prodnm: simpan sebagai string
    for f in ['cifid', 'cifnm', 'strtdt', 'duedt', 'prodid', 'prodnm']:
        if f in df.columns:
            df[f] = df[f].fillna('').astype(str).str.strip()

    # branchid: integer
    if 'branchid' in df.columns:
        df['branchid'] = pd.to_numeric(df['branchid'], errors='coerce').fillna(0).astype(int)

    # plafond, saldo_akhir, nilai_wajar, ckpn, tunggakan_pokok, tunggakan_bunga: desimal
    for col in ['plafond', 'saldo_akhir', 'nilai_wajar', 'ckpn', 'tunggakan_pokok', 'tunggakan_bunga']:
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
            
            # --- Pembacaan Excel dengan engine performa tinggi ---
            try:
                import python_calamine
                engine = 'calamine'
            except ImportError:
                engine = 'openpyxl' if file.name.endswith('.xlsx') else 'xlrd'
                
            df = pd.read_excel(file_bytes, engine=engine, header=0, dtype={2: str})
            df = _bersihkan_df(df, kolom_map)

            for col in KOLOM_WAJIB:
                if col not in df.columns:
                    messages.error(request, f'Kolom wajib tidak ditemukan: {col}')
                    return redirect(redirect_name)

            # ── Validasi Kode Cabang ─────────────────────────────────────
            if 'branchid' in df.columns:
                valid_kc  = set(str(int(float(k))) for k in KantorCabang.objects.values_list('kode', flat=True)
                                if k is not None)
                valid_kcp = set(str(int(float(k))) for k in KantorCabangPembantu.objects.values_list('kode', flat=True)
                                if k is not None)
                all_valid_codes = valid_kc | valid_kcp

                def _norm_code(v):
                    try:
                        return str(int(float(v)))
                    except Exception:
                        return str(v)

                df['_kode_norm'] = df['branchid'].apply(_norm_code)
                df_invalid = df[~df['_kode_norm'].isin(all_valid_codes)]

                if not df_invalid.empty:
                    invalid_summary = df_invalid.groupby('_kode_norm').apply(
                        lambda g: {
                            'kode': g['_kode_norm'].iloc[0],
                            'jumlah': len(g),
                            'contoh': g['cifnm'].iloc[0] if 'cifnm' in g.columns else '-',
                        }
                    ).tolist()

                    ctx = {
                        'hasil': {'berhasil': 0, 'gagal': len(df_invalid), 'errors': [], 'selesai': False},
                        'invalid_branches': invalid_summary,
                        'total_invalid': len(df_invalid),
                        'total_data': len(df),
                    }
                    if extra_ctx:
                        ctx.update(extra_ctx)
                    return render(request, template_name, ctx)

                df.drop(columns=['_kode_norm'], inplace=True)
            # ── Selesai Validasi Kode Cabang ─────────────────────────────

            # --- OPTIMISASI: DELETE-THEN-INSERT (PostgreSQL) ---
            from django.db import connection, transaction
            
            FIELD_DB = ['kelompok_sandi', 'cifid', 'cifnm', 'branchid',
                        'plafond', 'saldo_akhir', 'nilai_wajar',
                        'ckpn', 'strtdt', 'duedt', 'prodid', 'prodnm',
                        'tunggakan_pokok', 'tunggakan_bunga',
                        'hr_tungg_pokok', 'hr_tungg_margin', 'kolek']
            
            # Memastikan semua kolom database ada di DataFrame
            for col in FIELD_DB:
                if col not in df.columns:
                    if col in ['hr_tungg_pokok', 'hr_tungg_margin', 'kolek', 'branchid']:
                        df[col] = 0
                    elif col in ['plafond', 'saldo_akhir', 'nilai_wajar', 'ckpn', 'tunggakan_pokok', 'tunggakan_bunga']:
                        df[col] = 0.0
                    else:
                        df[col] = ''

            insert_cols = ['tanggal_upload', 'accnbr'] + FIELD_DB
            df['tanggal_upload'] = tanggal_upload
            
            # Normalisasi tipe data untuk performa maksimal COPY command
            for f in insert_cols:
                if f in ['hr_tungg_pokok', 'hr_tungg_margin', 'kolek', 'branchid']:
                    df[f] = df[f].fillna(0).astype(int)
                elif f in ['plafond', 'saldo_akhir', 'nilai_wajar', 'ckpn', 'tunggakan_pokok', 'tunggakan_bunga']:
                    df[f] = df[f].fillna(0)
                else:
                    df[f] = df[f].fillna('')

            # Buffer in-memory untuk transfer data cepat
            csv_buffer = io.StringIO()
            df[insert_cols].to_csv(csv_buffer, index=False, header=False, sep='\t')
            csv_buffer.seek(0)

            with transaction.atomic():
                # 1. Hapus data lama pada tanggal tersebut (Atomik & Sangat Cepat)
                ModelKelas.objects.filter(tanggal_upload=tanggal_upload).delete()
                
                # 2. Masukkan data baru menggunakan PostgreSQL COPY (Sangat Cepat)
                with connection.cursor() as cursor:
                    table_name = ModelKelas._meta.db_table
                    columns_sql = ', '.join([f'"{col}"' for col in insert_cols])
                    sql = f"COPY {table_name} ({columns_sql}) FROM STDIN WITH CSV DELIMITER '\t' NULL ''"
                    cursor.copy_expert(sql, csv_buffer)
                
                hasil['berhasil'] = len(df)
            
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
    cabang        = request.GET.get('cabang')
    kcp           = request.GET.get('kcp')
    per_page_raw  = request.GET.get('per_page_hidden') or request.GET.get('per_page', '20')
    per_page      = int(per_page_raw) if per_page_raw in ('20', '50', '100', 20, 50, 100) else 20
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

    # Format tanggal display (Indonesian locale)
    tanggal1_display = ''
    tanggal2_display = ''
    BULAN_ID = {1:'Januari',2:'Februari',3:'Maret',4:'April',5:'Mei',6:'Juni',
                7:'Juli',8:'Agustus',9:'September',10:'Oktober',11:'November',12:'Desember'}

    if tanggal1 and tanggal2:
        try:
            d1 = datetime.strptime(tanggal1, "%Y-%m-%d").date()
            d2 = datetime.strptime(tanggal2, "%Y-%m-%d").date()
            tanggal1_display = f"{d1.day} {BULAN_ID[d1.month]} {d1.year}"
            tanggal2_display = f"{d2.day} {BULAN_ID[d2.month]} {d2.year}"
            redirect_url = extra_ctx.get('redirect_url') if extra_ctx else 'kolek:bandingkan'
            if d2 <= d1:
                messages.error(request, "Tanggal 2 harus lebih baru dari Tanggal 1.")
                return redirect(redirect_url)
            if (d2 - d1).days > 366:
                messages.error(request, "Jarak perbandingan maksimal adalah 1 tahun (366 hari).")
                return redirect(redirect_url)
        except ValueError:
            pass

        COLS = ['accnbr', 'cifid', 'cifnm', 'kelompok_sandi', 'kolek', 'saldo_akhir', 'nilai_wajar', 'branchid', 'hr_tungg_pokok', 'hr_tungg_margin',
                'ckpn', 'strtdt', 'duedt', 'prodid', 'prodnm', 'plafond', 'tunggakan_pokok', 'tunggakan_bunga']
        qs1 = ModelKelas.objects.filter(tanggal_upload=tanggal1).values(*COLS)
        qs2 = ModelKelas.objects.filter(tanggal_upload=tanggal2).values(*COLS)

        if kcp:
            qs1 = qs1.filter(branchid=kcp)
            qs2 = qs2.filter(branchid=kcp)
        elif cabang:
            kcp_kodes = list(KantorCabangPembantu.objects.filter(cabang_induk__kode=cabang).values_list('kode', flat=True))
            kcp_kodes.append(cabang)
            qs1 = qs1.filter(branchid__in=kcp_kodes)
            qs2 = qs2.filter(branchid__in=kcp_kodes)

        from django.db import connection
        
        # OPTIMASI: Bypass Django ORM dict hydration, read directly to Pandas via raw SQL
        query1, params1 = qs1.query.sql_with_params()
        df1 = pd.read_sql(str(query1), connection, params=params1)
        
        query2, params2 = qs2.query.sql_with_params()
        df2 = pd.read_sql(str(query2), connection, params=params2)

        if df1.empty and df2.empty:
            hasil_banding = []
            df = pd.DataFrame()
        else:
            # Rename kolom dengan suffix _t1/_t2 sebelum merge
            if not df1.empty:
                df1 = df1.rename(columns={c: f"{c}_t1" for c in df1.columns if c != 'accnbr'})
            if not df2.empty:
                df2 = df2.rename(columns={c: f"{c}_t2" for c in df2.columns if c != 'accnbr'})

            # OPTIMASI: pd.merge outer join jauh lebih cepat dari pivot_table
            if df1.empty:
                df = df2.copy()
            elif df2.empty:
                df = df1.copy()
            else:
                df = pd.merge(df1, df2, on='accnbr', how='outer')

            cols_needed = ['cifid_t1', 'cifid_t2', 'cifnm_t1', 'cifnm_t2', 'kolek_t1', 'kolek_t2',
                           'kelompok_sandi_t1', 'kelompok_sandi_t2',
                           'saldo_akhir_t1', 'saldo_akhir_t2',
                           'nilai_wajar_t1', 'nilai_wajar_t2',
                           'hr_tungg_pokok_t1', 'hr_tungg_pokok_t2',
                           'hr_tungg_margin_t1', 'hr_tungg_margin_t2',
                           'ckpn_t1', 'ckpn_t2', 'strtdt_t1', 'strtdt_t2',
                           'duedt_t1', 'duedt_t2', 'prodid_t1', 'prodid_t2',
                           'prodnm_t1', 'prodnm_t2', 'plafond_t1', 'plafond_t2',
                           'tunggakan_pokok_t1', 'tunggakan_pokok_t2',
                           'tunggakan_bunga_t1', 'tunggakan_bunga_t2',
                           'branchid_t1', 'branchid_t2']
            for c in cols_needed:
                if c not in df.columns:
                    df[c] = None

            df['cifnm'] = df['cifnm_t1'].combine_first(df['cifnm_t2']).fillna('-')
            df['cifid'] = df['cifid_t1'].combine_first(df['cifid_t2']).fillna('-')
            df['branchid'] = df['branchid_t2'].combine_first(df['branchid_t1']).fillna('-')
            df['plafond'] = df['plafond_t2'].combine_first(df['plafond_t1']).fillna(0)

            has_t1 = df['kolek_t1'].notna()
            has_t2 = df['kolek_t2'].notna()
            rating_t1_str = df['kelompok_sandi_t1'].fillna('').astype(str).str.strip().str.upper()
            rating_t2_str = df['kelompok_sandi_t2'].fillna('').astype(str).str.strip().str.upper()

            import numpy as np
            # OPTIMASI: Vectorized numpy, tidak ada loop Python per-baris
            hierarki_map = {'1': 1, '2A': 2, '2B': 3, '2C': 4, '3': 5, '4': 6, '5': 7}
            val1 = rating_t1_str.map(hierarki_map)
            val2 = rating_t2_str.map(hierarki_map)

            df['kategori'] = 'baru'
            df.loc[has_t1 & ~has_t2, 'kategori'] = 'lunas'

            mask_has_both = has_t1 & has_t2
            if mask_has_both.any():
                conds = [
                    (val1 == val2) & val1.notna(),
                    val1.isna() | val2.isna(),
                    val1 > val2,
                    val1 < val2,
                ]
                choices = ['tetap', 'berbeda', 'membaik', 'memburuk']
                df.loc[mask_has_both, 'kategori'] = np.select(
                    [c[mask_has_both] for c in conds], choices, default='tetap'
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

            # --- SUMMARY MOVEMENT TABLE (before filtering) ---
            import math
            def safe_float(v):
                if pd.isna(v) or math.isinf(v) or math.isnan(v):
                    return 0.0
                return float(v)

            def _build_summary(df_full, kategori):
                df_k = df_full[df_full['kategori'] == kategori].copy()
                if df_k.empty:
                    return {'rows': [], 'grand_noa': 0, 'grand_nilai': 0, 'saldo_akhir': 0, 'nilai_wajar': 0}
                grouped = df_k.groupby('perubahan_label').agg(
                    noa=('accnbr', 'count'),
                    sum_nilai=('nilai_wajar_t2', lambda x: safe_float(x.sum())),
                ).reset_index()
                grouped = grouped.sort_values('noa', ascending=False)
                rows = []
                for _, row in grouped.iterrows():
                    rows.append({
                        'pergerakan': row['perubahan_label'],
                        'noa': int(row['noa']),
                        'sum_nilai': row['sum_nilai'],
                    })
                grand_noa = int(grouped['noa'].sum())
                grand_nilai = safe_float(grouped['sum_nilai'].sum())
                saldo_akhir = safe_float(df_k['saldo_akhir_t2'].sum())
                nilai_wajar = safe_float(df_k['nilai_wajar_t2'].sum())
                return {'rows': rows, 'grand_noa': grand_noa, 'grand_nilai': grand_nilai,
                        'saldo_akhir': saldo_akhir, 'nilai_wajar': nilai_wajar}

            summary_membaik = _build_summary(df, 'membaik')
            summary_tetap = _build_summary(df, 'tetap')
            summary_memburuk = _build_summary(df, 'memburuk')
            # --- END SUMMARY MOVEMENT TABLE ---

            if filter_kat:
                df = df[df['kategori'] == filter_kat]
            if filter_rating:
                df = df[df['perubahan_label'] == filter_rating]

            def _format_disp_columns(target_df):
                tdf = target_df.copy()
                tdf['kolek_t1_disp']   = np.where(tdf['kolek_t1'].notna(), tdf['kolek_t1'].fillna(0).astype(int).astype(str), '-')
                tdf['kolek_t2_disp']   = np.where(tdf['kolek_t2'].notna(), tdf['kolek_t2'].fillna(0).astype(int).astype(str), '-')
                tdf['rating_t1_disp']  = tdf['kelompok_sandi_t1'].fillna('-').astype(str)
                tdf['rating_t2_disp']  = tdf['kelompok_sandi_t2'].fillna('-').astype(str)
                tdf['saldo_t1_disp']   = tdf['saldo_akhir_t1'].fillna('-')
                tdf['saldo_t2_disp']   = tdf['saldo_akhir_t2'].fillna('-')
                tdf['nilai_wajar_t1_disp'] = tdf['nilai_wajar_t1'].fillna('-')
                tdf['nilai_wajar_t2_disp'] = tdf['nilai_wajar_t2'].fillna('-')
                
                tdf['ckpn_t2_disp']    = tdf['ckpn_t2'].fillna('-')
                tdf['strtdt_t2_disp']  = tdf['strtdt_t2'].fillna('-')
                tdf['duedt_t2_disp']   = tdf['duedt_t2'].fillna('-')
                tdf['prodid_t2_disp']  = tdf['prodid_t2'].fillna('-')
                tdf['prodnm_t2_disp']  = tdf['prodnm_t2'].fillna('-')
                tdf['tunggakan_pokok_t2_disp'] = tdf['tunggakan_pokok_t2'].fillna('-')
                tdf['tunggakan_bunga_t2_disp'] = tdf['tunggakan_bunga_t2'].fillna('-')

                tdf['hari_tunggakan_t2'] = tdf[['hr_tungg_pokok_t2', 'hr_tungg_margin_t2']].fillna(0).astype(int).max(axis=1)
                return tdf

            # --- ECHARTS DATA PREPARATION ---

            # 1. Horizontal Bar Chart (replaces Donut) — NOA per kategori
            hbar_data = [
                {'name': 'Tetap', 'value': ringkasan['tetap'], 'color': '#94a3b8'},
                {'name': 'Membaik', 'value': ringkasan['membaik'], 'color': '#10b981'},
                {'name': 'Memburuk', 'value': ringkasan['memburuk'], 'color': '#ef4444'},
                {'name': 'Lunas / Tutup', 'value': ringkasan['lunas'], 'color': '#3b82f6'},
                {'name': 'Fasilitas Baru', 'value': ringkasan['baru'], 'color': '#8b5cf6'},
            ]

            # 2. Faceted Panel Charts — Saldo Akhir (T1 vs T2) & Nilai Wajar (T1 vs T2)
            bar_categories_list = ['tetap', 'membaik', 'memburuk', 'baru']
            bar_saldo_t1 = []
            bar_saldo_t2 = []
            bar_nilai_t1 = []
            bar_nilai_t2 = []
            for cat in bar_categories_list:
                df_cat = df[df['kategori'] == cat]
                bar_saldo_t1.append(safe_float(df_cat['saldo_akhir_t1'].sum()))
                bar_saldo_t2.append(safe_float(df_cat['saldo_akhir_t2'].sum()))
                bar_nilai_t1.append(safe_float(df_cat['nilai_wajar_t1'].sum()))
                bar_nilai_t2.append(safe_float(df_cat['nilai_wajar_t2'].sum()))

            echarts_data = {
                'hbar_data': json.dumps(hbar_data),
                'bar_categories': json.dumps(['Tetap', 'Membaik', 'Memburuk', 'Baru']),
                'bar_saldo_t1': json.dumps(bar_saldo_t1),
                'bar_saldo_t2': json.dumps(bar_saldo_t2),
                'bar_nilai_t1': json.dumps(bar_nilai_t1),
                'bar_nilai_t2': json.dumps(bar_nilai_t2),
            }
            # --- END ECHARTS DATA ---

            if request.GET.get('export') == 'excel':
                is_syariah = extra_ctx and extra_ctx.get('bank') == 'syariah'
                sandi_label = 'Kelompok Sandi' if is_syariah else 'Rating Kolek'
                perubahan_label_text = 'Perubahan Sandi' if is_syariah else 'Perubahan Rating'

                if is_syariah:
                    export_cols = {
                        'rating_t2_disp': f'KELOMPOK_SANDI ({tanggal2_display})',
                        'accnbr': 'ACCNBR',
                        'cifid': 'CIFID',
                        'cifnm': 'CIFNM',
                        'branchid': 'BRANCHID',
                        'plafond': 'PLAFOND',
                        'saldo_t2_disp': f'SALDO_AKHIR ({tanggal2_display})',
                        'nilai_wajar_t2_disp': f'NILAI_WAJAR ({tanggal2_display})',
                        'ckpn_t2_disp': 'AMTCKPNPSAK',
                        'strtdt_t2_disp': 'OPENDT',
                        'duedt_t2_disp': 'DUEDT',
                        'prodnm_t2_disp': 'PRODNM',
                        'prodid_t2_disp': 'PRODID',
                        'tunggakan_pokok_t2_disp': 'TUNGGAKAN_POKOK',
                        'tunggakan_bunga_t2_disp': 'TUNGGAKAN_MARGIN',
                        'hr_tungg_pokok_t2': 'HARI_TUNGGAKAN_POKOK',
                        'hr_tungg_margin_t2': 'HARI_TUNGGAKAN_MARGIN',
                        'kolek_t2_disp': f'KOLEK ({tanggal2_display})',
                        'perubahan_label': perubahan_label_text,
                    }
                else:
                    export_cols = {
                        'rating_t2_disp': f'RATING_KOLEK ({tanggal2_display})',
                        'accnbr': 'REK_KREDIT',
                        'cifid': 'CIFID',
                        'cifnm': 'NAMA',
                        'branchid': 'CABANG',
                        'plafond': 'PLAFOND',
                        'saldo_t2_disp': f'SALDO_AKHIR ({tanggal2_display})',
                        'nilai_wajar_t2_disp': f'NILAI_WAJAR ({tanggal2_display})',
                        'ckpn_t2_disp': 'CKPN',
                        'strtdt_t2_disp': 'STRTDT',
                        'duedt_t2_disp': 'DUEDT',
                        'prodid_t2_disp': 'PRODID',
                        'prodnm_t2_disp': 'PRODNM',
                        'tunggakan_pokok_t2_disp': 'TUNGGAKAN_POKOK',
                        'tunggakan_bunga_t2_disp': 'TUNGGAKAN_BUNGA',
                        'hr_tungg_pokok_t2': 'HR_TUNGG_POKOK',
                        'hr_tungg_margin_t2': 'HR_TUNGG_BUNGA',
                        'kolek_t2_disp': f'KOLEK ({tanggal2_display})',
                        'perubahan_label': perubahan_label_text,
                    }


            if request.GET.get('export') == 'excel':
                df = _format_disp_columns(df)
                is_syariah = extra_ctx and extra_ctx.get('bank') == 'syariah'
                sandi_label = 'Kelompok Sandi' if is_syariah else 'Rating Kolek'
                perubahan_label_text = 'Perubahan Sandi' if is_syariah else 'Perubahan Rating'

                export_cols = {
                    'rating_t2_disp': f'{sandi_label} ({tanggal2_display})',
                    'accnbr': 'No. Rekening',
                    'cifid': 'CIF ID',
                    'cifnm': 'Nama Debitur',
                    'branchid': 'Cabang',
                    'plafond': 'Plafond',
                    'saldo_t2_disp': f'Saldo Akhir ({tanggal2_display})',
                    'nilai_wajar_t2_disp': f'Nilai Wajar ({tanggal2_display})',
                    'ckpn_t2_disp': 'CKPN',
                    'strtdt_t2_disp': 'STRTDT',
                    'duedt_t2_disp': 'DUEDT',
                    'prodid_t2_disp': 'PRODID',
                    'prodnm_t2_disp': 'PRODNM',
                    'tunggakan_pokok_t2_disp': 'Tunggakan Pokok',
                    'tunggakan_bunga_t2_disp': 'Tunggakan Bunga',
                    'hr_tungg_pokok_t2': 'Hr Tunggakan Pokok',
                    'hr_tungg_margin_t2': 'Hr Tunggakan Bunga',
                    'kolek_t2_disp': f'Kolek ({tanggal2_display})',
                    'perubahan_label': perubahan_label_text,
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
                df_export['accnbr'] = df_export['accnbr'].astype(str)
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

            total_records = len(df)

            class DummyList:
                def __init__(self, length):
                    self.length = length
                def __len__(self):
                    return self.length
                def __getitem__(self, key):
                    if isinstance(key, slice):
                        return [None] * len(range(*key.indices(self.length)))
                    return None

            paginator = Paginator(DummyList(total_records), per_page)
            try:
                page_num = int(request.GET.get('page', 1))
            except ValueError:
                page_num = 1
                
            page_obj = paginator.get_page(page_num)

            if total_records > 0:
                start_idx = page_obj.start_index() - 1
                end_idx = page_obj.end_index()
                df_page = df.iloc[start_idx:end_idx]
                
                df_page = _format_disp_columns(df_page)
                
                page_obj.object_list = df_page[[
                    'accnbr', 'cifnm', 'branchid',
                    'rating_t1_disp', 'rating_t2_disp',
                    'kolek_t1_disp', 'kolek_t2_disp',
                    'saldo_t1_disp', 'saldo_t2_disp',
                    'nilai_wajar_t2_disp',
                    'ckpn_t2_disp', 'strtdt_t2_disp', 'duedt_t2_disp', 'prodid_t2_disp', 'prodnm_t2_disp', 'tunggakan_pokok_t2_disp', 'tunggakan_bunga_t2_disp',
                    'hari_tunggakan_t2',
                    'perubahan_label', 'kategori',
                ]].to_dict('records')
                hasil_banding = page_obj.object_list
            else:
                page_obj.object_list = []
                hasil_banding = []

    ctx = {
        'tanggal1'          : tanggal1,
        'tanggal2'          : tanggal2,
        'tanggal1_display'  : tanggal1_display,
        'tanggal2_display'  : tanggal2_display,
        'tanggal_list'      : tanggal_list,
        'hasil_banding'     : hasil_banding,
        'page_obj'          : page_obj,
        'ringkasan'         : ringkasan,
        'filter_kat'        : filter_kat,
        'filter_rating'     : filter_rating,
        'per_page'          : per_page,
        'perubahan_list'    : perubahan_list,
        'cabang'            : cabang,
        'kcp'               : kcp,
    }

    show_syariah = extra_ctx.get('bank') == 'syariah' if extra_ctx else False
    ctx.update(_get_cabang_context(show_syariah=show_syariah))

    if hasil_banding is not None and 'echarts_data' in locals():
        ctx.update(echarts_data)
    if hasil_banding is not None and 'summary_membaik' in locals():
        ctx['summary_membaik'] = json.dumps(summary_membaik)
        ctx['summary_tetap'] = json.dumps(summary_tetap)
        ctx['summary_memburuk'] = json.dumps(summary_memburuk)

    if extra_ctx:
        ctx.update(extra_ctx)
    return render(request, template_name, ctx)


# ══════════════════════════════════════════════════════════════
# VIEWS — BANK KONVENSIONAL
# ══════════════════════════════════════════════════════════════

@login_required
@require_otp
def kolek_konvensional_view(request):
    data        = PergerakanKolekKonvensional.objects.all()
    rating_list = ['1', '2A', '2B', '2C', '3', '4', '5']
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
    
    per_page_raw = request.GET.get('per_page', '20')
    try:
        per_page = int(per_page_raw)
        if per_page not in [20, 50, 100]:
            per_page = 20
    except ValueError:
        per_page = 20

    paginator = Paginator(data, per_page)
    page_obj  = paginator.get_page(request.GET.get('page', 1))

    ctx = {
        'page_obj'     : page_obj,
        'summary'      : summary,
        'total'        : data.count(),
        'rating_list'  : rating_list,
        'tanggal_list' : tanggal_list,
        'tanggal_aktif': tanggal,
        'per_page'     : per_page,
        'bank'         : 'konvensional',
    }
    ctx.update(_get_cabang_context(show_syariah=False))
    return render(request, 'kolek/konvensional/pergerakan.html', ctx)


@login_required
@require_otp
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
@require_otp
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
@require_otp
def kolek_syariah_view(request):
    data        = PergerakanKolekSyariah.objects.all()
    rating_list = ['1', '2A', '2B', '2C', '3', '4', '5']
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
    
    per_page_raw = request.GET.get('per_page', '20')
    try:
        per_page = int(per_page_raw)
        if per_page not in [20, 50, 100]:
            per_page = 20
    except ValueError:
        per_page = 20

    paginator = Paginator(data, per_page)
    page_obj  = paginator.get_page(request.GET.get('page', 1))

    ctx = {
        'page_obj'     : page_obj,
        'summary'      : summary,
        'total'        : data.count(),
        'rating_list'  : rating_list,
        'tanggal_list' : tanggal_list,
        'tanggal_aktif': tanggal,
        'per_page'     : per_page,
        'bank'         : 'syariah',
    }
    ctx.update(_get_cabang_context(show_syariah=True))
    return render(request, 'kolek/syariah/pergerakan.html', ctx)


@login_required
@require_otp
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
@require_otp
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


# ══════════════════════════════════════════════════════════════
# HELPER: Summary per Cabang
# ══════════════════════════════════════════════════════════════
def _summary_per_cabang(ModelKelas, tanggal1, tanggal2):
    import numpy as np
    import math

    COLS = ['accnbr', 'branchid', 'kolek', 'kelompok_sandi', 'saldo_akhir']
    qs1 = ModelKelas.objects.filter(tanggal_upload=tanggal1).values(*COLS)
    qs2 = ModelKelas.objects.filter(tanggal_upload=tanggal2).values(*COLS)

    from django.db import connection
    query1, params1 = qs1.query.sql_with_params()
    df1 = pd.read_sql(str(query1), connection, params=params1)
    query2, params2 = qs2.query.sql_with_params()
    df2 = pd.read_sql(str(query2), connection, params=params2)

    if df1.empty and df2.empty:
        return [], {}

    if not df1.empty:
        df1 = df1.rename(columns={
            'branchid': 'branchid_t1', 'kolek': 'kolek_t1',
            'saldo_akhir': 'saldo_t1', 'kelompok_sandi': 'kelompok_sandi_t1'
        })
    if not df2.empty:
        df2 = df2.rename(columns={
            'branchid': 'branchid_t2', 'kolek': 'kolek_t2',
            'saldo_akhir': 'saldo_t2', 'kelompok_sandi': 'kelompok_sandi_t2'
        })

    if df1.empty:
        df = df2.copy()
        for c in ['branchid_t1', 'kolek_t1', 'saldo_t1', 'kelompok_sandi_t1']:
            df[c] = None
    elif df2.empty:
        df = df1.copy()
        for c in ['branchid_t2', 'kolek_t2', 'saldo_t2', 'kelompok_sandi_t2']:
            df[c] = None
    else:
        df = pd.merge(df1, df2, on='accnbr', how='outer')

    # Pastikan semua kolom ada setelah merge
    for col in ['branchid_t1', 'branchid_t2', 'kolek_t1', 'kolek_t2',
                'saldo_t1', 'saldo_t2', 'kelompok_sandi_t1', 'kelompok_sandi_t2']:
        if col not in df.columns:
            df[col] = None

    df['branchid'] = df['branchid_t2'].combine_first(df['branchid_t1'])
    df['saldo_t2_fill'] = pd.to_numeric(df['saldo_t2'], errors='coerce').fillna(0)

    has_t1 = df['kolek_t1'].notna()
    has_t2 = df['kolek_t2'].notna()

    ks1 = df['kelompok_sandi_t1'].fillna('').astype(str).str.strip().str.upper()
    ks2 = df['kelompok_sandi_t2'].fillna('').astype(str).str.strip().str.upper()

    hierarki_map = {'1': 1, '2A': 2, '2B': 3, '2C': 4, '3': 5, '4': 6, '5': 7}
    val1 = ks1.map(hierarki_map)
    val2 = ks2.map(hierarki_map)

    df['kategori'] = 'baru'
    df.loc[has_t1 & ~has_t2, 'kategori'] = 'tutup'

    mask_both = has_t1 & has_t2
    if mask_both.any():
        conds = [
            (val1 == val2) & val1.notna(),
            val1 > val2,
            (val1 < val2) & (val2 <= 4),
            (val1 < val2) & (val2 >= 5),
        ]
        choices = ['tetap', 'membaik', 'memburuk', 'jatuh_npl']
        df.loc[mask_both, 'kategori'] = np.select(
            [c[mask_both] for c in conds], choices, default='tetap'
        )

    kc_qs = KantorCabang.objects.filter(is_aktif=True)
    kcp_qs = KantorCabangPembantu.objects.select_related('cabang_induk').filter(is_aktif=True)
    
    branch_to_induk = {}
    induk_map = {}
    for kc in kc_qs:
        try:
            k = str(int(float(kc.kode)))
            branch_to_induk[k] = k
            induk_map[k] = kc.nama
        except (ValueError, TypeError):
            pass
            
    for kcp in kcp_qs:
        try:
            k = str(int(float(kcp.kode)))
            ik = str(int(float(kcp.cabang_induk.kode)))
            branch_to_induk[k] = ik
        except (ValueError, TypeError, AttributeError):
            pass

    def get_induk(br_id):
        try:
            k = str(int(float(br_id))) if pd.notna(br_id) else '0'
            return branch_to_induk.get(k, k)
        except:
            return str(br_id)
            
    df['induk_kode'] = df['branchid'].apply(get_induk)

    def safe_sum(series):
        v = float(pd.to_numeric(series, errors='coerce').fillna(0).sum())
        return 0.0 if (math.isnan(v) or math.isinf(v)) else v

    CATS = ['membaik', 'tetap', 'memburuk', 'jatuh_npl', 'tutup', 'baru']
    result = {}

    for br_key, g in df.groupby('induk_kode'):
        if br_key not in induk_map:
            final_key = '999'
            final_nama = 'CABANG LAINNYA'
        else:
            final_key = br_key
            final_nama = induk_map[br_key]
            
        if final_key not in result:
            result[final_key] = {'kode': final_key, 'nama': final_nama, 'total_noa': 0, 'total_baldi': 0.0}
            for cat in CATS:
                result[final_key][f'{cat}_noa'] = 0
                result[final_key][f'{cat}_baldi'] = 0.0
                
        entry = result[final_key]
        for cat in CATS:
            g_cat = g[g['kategori'] == cat]
            noa = len(g_cat)
            baldi = safe_sum(g_cat['saldo_t2_fill'])
            entry[f'{cat}_noa'] += noa
            entry[f'{cat}_baldi'] += baldi
            entry['total_noa'] += noa
            entry['total_baldi'] += baldi

    rows = sorted(result.values(), key=lambda x: int(x['kode']) if x['kode'].isdigit() else 9999)
    for i, row in enumerate(rows, start=1):
        row['no'] = i

    grand = {cat: {'noa': 0, 'baldi': 0.0} for cat in CATS}
    grand['total'] = {'noa': 0, 'baldi': 0.0}
    for row in rows:
        for cat in CATS:
            grand[cat]['noa'] += row[f'{cat}_noa']
            grand[cat]['baldi'] += row[f'{cat}_baldi']
        grand['total']['noa'] += row['total_noa']
        grand['total']['baldi'] += row['total_baldi']

    return rows, grand


def _summary_cabang_view(request, ModelKelas, template_name, extra_ctx=None):
    tanggal1 = request.GET.get('tanggal1', '')
    tanggal2 = request.GET.get('tanggal2', '')
    rows, grand = [], {}
    tanggal1_display = tanggal2_display = error_msg = ''

    BULAN_ID = {1:'Januari',2:'Februari',3:'Maret',4:'April',5:'Mei',6:'Juni',
                7:'Juli',8:'Agustus',9:'September',10:'Oktober',11:'November',12:'Desember'}

    tanggal_list = (
        ModelKelas.objects.values_list('tanggal_upload', flat=True)
        .distinct().order_by('tanggal_upload')
    )

    if tanggal1 and tanggal2:
        try:
            d1 = datetime.strptime(tanggal1, '%Y-%m-%d').date()
            d2 = datetime.strptime(tanggal2, '%Y-%m-%d').date()
            tanggal1_display = f"{d1.day} {BULAN_ID[d1.month]} {d1.year}"
            tanggal2_display = f"{d2.day} {BULAN_ID[d2.month]} {d2.year}"
            if d2 <= d1:
                error_msg = 'Tanggal 2 harus lebih baru dari Tanggal 1.'
            elif (d2 - d1).days > 366:
                error_msg = 'Jarak perbandingan maksimal adalah 366 hari.'
            else:
                rows, grand = _summary_per_cabang(ModelKelas, tanggal1, tanggal2)
        except ValueError:
            error_msg = 'Format tanggal tidak valid.'

    if request.GET.get('export') == 'csv' and rows:
        import csv as _csv
        from django.http import HttpResponse
        bank_label = (extra_ctx or {}).get('bank_label', 'Bank')
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = (
            f'attachment; filename="SummaryCabang_{bank_label}_{tanggal1}_vs_{tanggal2}.csv"'
        )
        tok = request.GET.get('export_token')
        if tok:
            response.set_cookie(f'export_done_{tok}', 'true', max_age=60)
        w = _csv.writer(response, delimiter=';')
        w.writerow(['NO','KODE','NAMA CABANG',
                    'MEMBAIK NOA','MEMBAIK BAKI DEBET',
                    'TETAP NOA','TETAP BAKI DEBET',
                    'MEMBURUK NOA','MEMBURUK BAKI DEBET',
                    'JATUH NPL NOA','JATUH NPL BAKI DEBET',
                    'TUTUP NOA',
                    'BARU NOA','BARU BAKI DEBET',
                    'TOTAL NOA','TOTAL BAKI DEBET'])
        for r in rows:
            w.writerow([r['no'],r['kode'],r['nama'],
                        r['membaik_noa'],int(r['membaik_baldi']),
                        r['tetap_noa'],int(r['tetap_baldi']),
                        r['memburuk_noa'],int(r['memburuk_baldi']),
                        r['jatuh_npl_noa'],int(r['jatuh_npl_baldi']),
                        r['tutup_noa'],
                        r['baru_noa'],int(r['baru_baldi']),
                        r['total_noa'],int(r['total_baldi'])])
        if grand:
            w.writerow(['','TOTAL','',
                        grand['membaik']['noa'],int(grand['membaik']['baldi']),
                        grand['tetap']['noa'],int(grand['tetap']['baldi']),
                        grand['memburuk']['noa'],int(grand['memburuk']['baldi']),
                        grand['jatuh_npl']['noa'],int(grand['jatuh_npl']['baldi']),
                        grand['tutup']['noa'],
                        grand['baru']['noa'],int(grand['baru']['baldi']),
                        grand['total']['noa'],int(grand['total']['baldi'])])
        return response

    ctx = {
        'tanggal1': tanggal1, 'tanggal2': tanggal2,
        'tanggal1_display': tanggal1_display,
        'tanggal2_display': tanggal2_display,
        'tanggal_list': tanggal_list,
        'rows': rows, 'grand': grand,
        'error_msg': error_msg,
    }
    if extra_ctx:
        ctx.update(extra_ctx)
    return render(request, template_name, ctx)


# ── Public views ──────────────────────────────────────────────
@login_required
@require_otp
def summary_cabang_konvensional_view(request):
    return _summary_cabang_view(
        request,
        ModelKelas=PergerakanKolekKonvensional,
        template_name='kolek/konvensional/summary_cabang.html',
        extra_ctx={'bank':'konvensional','bank_label':'Konvensional'},
    )


@login_required
@require_otp
def summary_cabang_syariah_view(request):
    return _summary_cabang_view(
        request,
        ModelKelas=PergerakanKolekSyariah,
        template_name='kolek/syariah/summary_cabang.html',
        extra_ctx={'bank':'syariah','bank_label':'Syariah'},
    )
