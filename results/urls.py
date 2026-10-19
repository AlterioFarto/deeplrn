from django.urls import path

from results import views

app_name = "results"

urlpatterns = [
    path("", views.ResultListView.as_view(), name="result_list"),
    path("entry/", views.ResultsEntryListView.as_view(), name="entry_list"),
    path("entry/<int:exam_pk>/", views.ResultsEntryView.as_view(), name="entry"),
    path("<int:pk>/delete/", views.ResultDeleteView.as_view(), name="result_delete"),
]
