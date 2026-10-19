from django.urls import path

from dashboard import views

app_name = "dashboard"

urlpatterns = [
    path("", views.HomeView.as_view(), name="home"),
    path("reports/", views.ReportsListView.as_view(), name="report_list"),
    path("reports/<int:pk>/download/", views.ReportDownloadView.as_view(), name="report_download"),
]
