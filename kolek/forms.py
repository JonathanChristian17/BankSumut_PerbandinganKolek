from django import forms
from django.contrib.auth.forms import AuthenticationForm
from captcha.fields import CaptchaField

class HoneypotLoginForm(AuthenticationForm):
    """
    Custom Login Form dengan dua lapis keamanan:
    1. Honeypot (tersembunyi) — menjebak bot otomatis yang mengisi semua form
    2. Text Captcha (terlihat) — memaksa manusia mengetik ulang teks gambar, memblokir bot pintar
    """
    # Lapis 1: Jebakan bot tersembunyi (Honeypot)
    # Field ini di-hide oleh CSS. Bot akan mengisinya, manusia tidak akan melihatnya.
    website_url = forms.CharField(
        required=False,
        label='',
        widget=forms.TextInput(
            attrs={
                'class': 'h-trap',
                'autocomplete': 'off',
                'tabindex': '-1'
            }
        )
    )

    # Lapis 2: Captcha teks gambar (terlihat oleh manusia)
    # Server membuat gambar acak huruf/angka, user harus mengetiknya untuk bisa masuk.
    captcha = CaptchaField(label='Kode Keamanan')

    def clean(self):
        cleaned_data = super().clean()
        honeypot = cleaned_data.get('website_url')

        # Jika field jebakan ini terisi teks apapun, berarti yang login adalah Bot!
        if honeypot:
            raise forms.ValidationError(
                "Aktivitas mencurigakan terdeteksi. Akses ditolak."
            )

        return cleaned_data
