from django.urls import path
from django.views.generic import RedirectView
from . import views

app_name = 'kolek'

urlpatterns = [
    # ── Redirect root /kolek/ ──────────────────────────────────
    path('', RedirectView.as_view(url='konvensional/pergerakan/', permanent=False), name='kolek_root'),

    # ── Redirect old URLs for backward compatibility ──────────
    path('pergerakan/', RedirectView.as_view(url='/kolek/konvensional/pergerakan/', permanent=False)),
    path('upload/', RedirectView.as_view(url='/kolek/konvensional/upload/', permanent=False)),
    path('bandingkan/', RedirectView.as_view(url='/kolek/konvensional/bandingkan/', permanent=False)),


    # ── Bank Konvensional ──────────────────────────────────────
    path('konvensional/pergerakan/',  views.kolek_konvensional_view,       name='konvensional_pergerakan'),
    path('konvensional/upload/',      views.upload_konvensional_view,       name='konvensional_upload'),
    path('konvensional/bandingkan/',  views.bandingkan_konvensional_view,   name='konvensional_bandingkan'),

    # ── Bank Syariah ───────────────────────────────────────────
    path('syariah/pergerakan/',       views.kolek_syariah_view,             name='syariah_pergerakan'),
    path('syariah/upload/',           views.upload_syariah_view,            name='syariah_upload'),
    path('syariah/bandingkan/',       views.bandingkan_syariah_view,        name='syariah_bandingkan'),
]
