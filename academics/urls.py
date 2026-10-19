from django.urls import path

from academics import views

app_name = "academics"

urlpatterns = [
    path("groups/", views.GroupListView.as_view(), name="group_list"),
    path("groups/new/", views.GroupCreateView.as_view(), name="group_create"),
    path("groups/<int:pk>/", views.GroupDetailView.as_view(), name="group_detail"),
    path("groups/<int:pk>/edit/", views.GroupUpdateView.as_view(), name="group_update"),
    path("groups/<int:pk>/delete/", views.GroupDeleteView.as_view(), name="group_delete"),
    path("subjects/", views.SubjectListView.as_view(), name="subject_list"),
    path("subjects/new/", views.SubjectCreateView.as_view(), name="subject_create"),
    path("subjects/<int:pk>/edit/", views.SubjectUpdateView.as_view(), name="subject_update"),
    path("subjects/<int:pk>/delete/", views.SubjectDeleteView.as_view(), name="subject_delete"),
    path("timeslots/", views.TimeSlotListView.as_view(), name="timeslot_list"),
    path("timeslots/new/", views.TimeSlotCreateView.as_view(), name="timeslot_create"),
    path("timeslots/<int:pk>/edit/", views.TimeSlotUpdateView.as_view(), name="timeslot_update"),
    path("timeslots/<int:pk>/delete/", views.TimeSlotDeleteView.as_view(), name="timeslot_delete"),
    path("schedule/", views.ScheduleListView.as_view(), name="schedule_list"),
    path("schedule/new/", views.ScheduleCreateView.as_view(), name="schedule_create"),
    path("schedule/<int:pk>/edit/", views.ScheduleUpdateView.as_view(), name="schedule_update"),
    path("schedule/<int:pk>/delete/", views.ScheduleDeleteView.as_view(), name="schedule_delete"),
    path("exams/", views.ExamListView.as_view(), name="exam_list"),
    path("exams/new/", views.ExamCreateView.as_view(), name="exam_create"),
    path("exams/<int:pk>/", views.ExamDetailView.as_view(), name="exam_detail"),
    path("exams/<int:pk>/edit/", views.ExamUpdateView.as_view(), name="exam_update"),
    path("exams/<int:pk>/delete/", views.ExamDeleteView.as_view(), name="exam_delete"),
]
