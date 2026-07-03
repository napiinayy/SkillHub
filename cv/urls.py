from django.urls import path

from . import views

urlpatterns = [
    path("", views.builder, name="builder"),
    path("preset/<int:preset_id>/export/", views.load_preset, name="load_preset"),
    path("preset/<int:preset_id>/gdoc/", views.preset_to_gdoc, name="preset_to_gdoc"),
    path("google/authorize/", views.google_authorize, name="google_authorize"),
    path("google/callback/", views.google_callback, name="google_callback"),
]
