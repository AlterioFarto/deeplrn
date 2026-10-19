from .exams import ExamCreateView, ExamDeleteView, ExamDetailView, ExamListView, ExamUpdateView
from .groups import (
    GroupCreateView,
    GroupDeleteView,
    GroupDetailView,
    GroupListView,
    GroupUpdateView,
)
from .reference import (
    SubjectCreateView,
    SubjectDeleteView,
    SubjectListView,
    SubjectUpdateView,
    TimeSlotCreateView,
    TimeSlotDeleteView,
    TimeSlotListView,
    TimeSlotUpdateView,
)
from .schedule import ScheduleCreateView, ScheduleDeleteView, ScheduleListView, ScheduleUpdateView

__all__ = [
    "ExamCreateView",
    "ExamDeleteView",
    "ExamDetailView",
    "ExamListView",
    "ExamUpdateView",
    "GroupCreateView",
    "GroupDeleteView",
    "GroupDetailView",
    "GroupListView",
    "GroupUpdateView",
    "ScheduleCreateView",
    "ScheduleDeleteView",
    "ScheduleListView",
    "ScheduleUpdateView",
    "SubjectCreateView",
    "SubjectDeleteView",
    "SubjectListView",
    "SubjectUpdateView",
    "TimeSlotCreateView",
    "TimeSlotDeleteView",
    "TimeSlotListView",
    "TimeSlotUpdateView",
]
