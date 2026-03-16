from django.contrib import admin
from django.urls import path, include  # 'include' untuk mendelegasikan URL ke app
from django.views.generic import RedirectView  # untuk redirect halaman root ke URL tujuan

urlpatterns = [

    # ------------------------------------------------------------------
    # URL Root: /
    # Redirect otomatis dari homepage ke halaman utama aplikasi kolek.
    # Sehingga http://localhost:8000/ langsung ke /kolek/konvensional/pergerakan/
    # ------------------------------------------------------------------
    path(
        '',                                                               # URL root kosong
        RedirectView.as_view(url='/kolek/konvensional/pergerakan/', permanent=False)  # redirect ke halaman utama konvensional
    ),

    # ------------------------------------------------------------------
    # URL Admin Django: /admin/
    # Panel admin bawaan Django untuk manajemen data lewat browser.
    # Akses: http://localhost:8000/admin/
    # ------------------------------------------------------------------
    path(
        'admin/',           # Prefix URL untuk halaman admin
        admin.site.urls     # Modul URL bawaan Django admin
    ),

    # ------------------------------------------------------------------
    # URL Aplikasi Kolek: /kolek/...
    # Semua URL yang diawali 'kolek/' akan diteruskan ke kolek/urls.py.
    # 'include' membaca daftar URL dari file urls.py milik app 'kolek'.
    #
    # Contoh hasil URL yang tersedia:
    #   → http://localhost:8000/kolek/pergerakan/
    # ------------------------------------------------------------------
    path(
        'kolek/',                    # Prefix URL untuk semua halaman app kolek
        include('kolek.urls')        # Delegasikan ke kolek/urls.py
    ),

]