from django.urls import path

from . import views

app_name = "approval"

urlpatterns = [
    path("", views.approval_list, name="approval_list"),
    path("detail/<int:pk>/", views.detail_approval, name="detail_approval"),
    path("kirim/<int:pk>/", views.kirim_approval, name="kirim_approval"),
    path("proses/<int:approval_id>/", views.proses_approval, name="proses_approval"),
]
