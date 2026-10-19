"""Result records for exams; grade is denormalised with a DB check constraint."""

from django.db import models
from django.db.models import Q

from common.models import TimeStampedModel
from results.grades import GRADE_CHOICES


class Result(TimeStampedModel):
    student = models.ForeignKey(
        "students.Student", on_delete=models.PROTECT, related_name="results"
    )
    exam = models.ForeignKey("academics.Exam", on_delete=models.PROTECT, related_name="results")
    marks = models.DecimalField(max_digits=6, decimal_places=2)
    grade = models.CharField(max_length=4)

    class Meta:
        ordering = ["-exam__date", "student__admission_no"]
        constraints = [
            models.UniqueConstraint(fields=["student", "exam"], name="uniq_result_student_exam"),
            models.CheckConstraint(condition=Q(marks__gte=0), name="result_marks_nonnegative"),
            models.CheckConstraint(condition=Q(grade__in=GRADE_CHOICES), name="result_grade_valid"),
        ]
        indexes = [
            models.Index(fields=["exam"], name="result_exam_idx"),
            models.Index(fields=["student"], name="result_student_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.student} - {self.exam}: {self.marks} ({self.grade})"
