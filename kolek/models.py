from django.db import models


# ─────────────────────────────────────────────────────────────
# MODEL: Bank Konvensional
# Tabel: kolek_pergerakan_konvensional
# ─────────────────────────────────────────────────────────────
class PergerakanKolekKonvensional(models.Model):
    tanggal_upload   = models.DateField()
    kelompok_sandi   = models.CharField(max_length=50)     # RATING_KOLEK
    accnbr           = models.BigIntegerField()             # REK_KREDIT
    cifid            = models.CharField(max_length=50)
    cifnm            = models.TextField()                   # NAMA
    branchid         = models.IntegerField()                # CABANG
    plafond          = models.DecimalField(max_digits=18, decimal_places=2)
    saldo_akhir      = models.DecimalField(max_digits=18, decimal_places=2)
    nilai_wajar      = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    ckpn             = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    strtdt           = models.CharField(max_length=50, blank=True, null=True)
    duedt            = models.CharField(max_length=50, blank=True, null=True)
    prodid           = models.CharField(max_length=50, blank=True, null=True)
    prodnm           = models.TextField(blank=True, null=True)
    tunggakan_pokok  = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    tunggakan_bunga  = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    hr_tungg_pokok   = models.IntegerField(default=0)
    hr_tungg_margin  = models.IntegerField(default=0)       # HR_TUNGG_BUNGA
    kolek            = models.IntegerField(default=0)

    class Meta:
        unique_together = [('accnbr', 'tanggal_upload')]
        ordering = ['tanggal_upload', 'accnbr']
        verbose_name = 'Pergerakan Kolek Konvensional'
        verbose_name_plural = 'Pergerakan Kolek Konvensional'

    def __str__(self):
        return f"[KONVENSIONAL] {self.accnbr} | {self.tanggal_upload} | Kolek {self.kolek}"


# ─────────────────────────────────────────────────────────────
# MODEL: Bank Syariah
# Tabel: kolek_pergerakan_syariah
# ─────────────────────────────────────────────────────────────
class PergerakanKolekSyariah(models.Model):
    tanggal_upload   = models.DateField()
    kelompok_sandi   = models.CharField(max_length=50)     # KELOMPOK_SANDI
    accnbr           = models.BigIntegerField()             # ACCNBR
    cifid            = models.CharField(max_length=50)
    cifnm            = models.TextField()                   # CIFNM
    branchid         = models.IntegerField()                # BRANCHID
    plafond          = models.DecimalField(max_digits=18, decimal_places=2)
    saldo_akhir      = models.DecimalField(max_digits=18, decimal_places=2)
    nilai_wajar      = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    ckpn             = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    strtdt           = models.CharField(max_length=50, blank=True, null=True)
    duedt            = models.CharField(max_length=50, blank=True, null=True)
    prodid           = models.CharField(max_length=50, blank=True, null=True)
    prodnm           = models.TextField(blank=True, null=True)
    tunggakan_pokok  = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    tunggakan_bunga  = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    hr_tungg_pokok   = models.IntegerField(default=0)
    hr_tungg_margin  = models.IntegerField(default=0)       # HR_TUNGG_MARGIN
    kolek            = models.IntegerField(default=0)

    class Meta:
        unique_together = [('accnbr', 'tanggal_upload')]
        ordering = ['tanggal_upload', 'accnbr']
        verbose_name = 'Pergerakan Kolek Syariah'
        verbose_name_plural = 'Pergerakan Kolek Syariah'

    def __str__(self):
        return f"[SYARIAH] {self.accnbr} | {self.tanggal_upload} | Kolek {self.kolek}"


# ─────────────────────────────────────────────────────────────
# MODEL: Kantor Cabang (KC) — Induk
# ─────────────────────────────────────────────────────────────
class KantorCabang(models.Model):
    kode  = models.CharField(max_length=10, unique=True)
    nama  = models.CharField(max_length=150)
    jenis = models.CharField(max_length=70)   # CABANG / CABANG KOORDINATOR MEDAN / CABANG SYARIAH
    is_aktif = models.BooleanField(default=True)

    class Meta:
        ordering = ['kode']
        verbose_name = 'Kantor Cabang'
        verbose_name_plural = 'Kantor Cabang'

    def __str__(self):
        return f"{self.kode} — {self.nama}"


# ─────────────────────────────────────────────────────────────
# MODEL: Kantor Cabang Pembantu (KCP) — Anak dari KantorCabang
# ─────────────────────────────────────────────────────────────
class KantorCabangPembantu(models.Model):
    cabang_induk = models.ForeignKey(
        KantorCabang,
        on_delete=models.CASCADE,
        related_name='cabang_pembantu'
    )
    kode  = models.CharField(max_length=10, unique=True)
    nama  = models.CharField(max_length=150)
    jenis = models.CharField(max_length=70)   # CABANG PEMBANTU KONVENSIONAL / SYARIAH / KANTOR KAS
    is_aktif = models.BooleanField(default=True)

    class Meta:
        ordering = ['kode']
        verbose_name = 'Kantor Cabang Pembantu'
        verbose_name_plural = 'Kantor Cabang Pembantu'

    def __str__(self):
        return f"{self.kode} — {self.nama} (KCP {self.cabang_induk.kode})"