from django.urls import path

from students import views

app_name = "students"

urlpatterns = [
    path("", views.StudentListView.as_view(), name="student_list"),
    path("new/", views.StudentCreateView.as_view(), name="student_create"),
    path("<int:pk>/", views.StudentDetailView.as_view(), name="student_detail"),
    path("<int:pk>/edit/", views.StudentUpdateView.as_view(), name="student_update"),
    path("<int:pk>/delete/", views.StudentDeleteView.as_view(), name="student_delete"),
    path("<int:pk>/restore/", views.StudentRestoreView.as_view(), name="student_restore"),
    path("<int:pk>/guardians/link/", views.GuardianLinkView.as_view(), name="guardian_link"),
    path("guardians/", views.GuardianListView.as_view(), name="guardian_list"),
    path("guardians/new/", views.GuardianCreateView.as_view(), name="guardian_create"),
    path("guardians/<int:pk>/edit/", views.GuardianUpdateView.as_view(), name="guardian_update"),
    path("guardians/<int:pk>/delete/", views.GuardianDeleteView.as_view(), name="guardian_delete"),
    path("links/<int:link_pk>/unlink/", views.GuardianUnlinkView.as_view(), name="guardian_unlink"),
]
