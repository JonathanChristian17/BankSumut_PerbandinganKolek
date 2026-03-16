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