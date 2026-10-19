from django.urls import path

from attendance import views

app_name = "attendance"

urlpatterns = [
    path("", views.AttendanceListView.as_view(), name="attendance_list"),
    path("record/", views.AttendanceRecordView.as_view(), name="record"),
]
