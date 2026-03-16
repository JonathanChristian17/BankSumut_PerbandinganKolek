from django.contrib import admin
from .models import PergerakanKolekKonvensional, PergerakanKolekSyariah


@admin.register(PergerakanKolekKonvensional)
class KonvensionalAdmin(admin.ModelAdmin):
    list_display  = ('accnbr', 'cifnm', 'kelompok_sandi', 'kolek', 'branchid', 'tanggal_upload')
    list_filter   = ('kelompok_sandi', 'kolek', 'tanggal_upload')
    search_fields = ('cifnm', 'cifid')


@admin.register(PergerakanKolekSyariah)
class SyariahAdmin(admin.ModelAdmin):
    list_display  = ('accnbr', 'cifnm', 'kelompok_sandi', 'kolek', 'branchid', 'tanggal_upload')
    list_filter   = ('kelompok_sandi', 'kolek', 'tanggal_upload')
    search_fields = ('cifnm', 'cifid')
