"""Grades and results domain tests."""

from decimal import Decimal

import pytest

from academics.factories import ExamFactory, GroupFactory
from common.exceptions import ConflictError
from results import services
from results.grades import grade_for
from results.models import Result
from students.factories import StudentFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def exam(mentor_group):
    return ExamFactory(group=mentor_group, max_marks=100, date="2025-01-10")


@pytest.mark.parametrize(
    "marks,max_marks,grade",
    [
        (90, 100, "A+"),
        (80, 100, "A"),
        (79.9, 100, "B"),
        (70, 100, "B"),
        (60, 100, "C"),
        (50, 100, "D"),
        (0, 100, "F"),
        (8, 10, "A"),
    ],
)
def test_grade_bands(marks, max_marks, grade):
    assert grade_for(marks, max_marks) == grade


def test_grade_for_rejects_zero_max():
    with pytest.raises(ValueError):
        grade_for(10, 0)


def test_bulk_upsert_overwrites(student, exam, admin):
    services.bulk_record_results(
        exam=exam, marks_by_student_id={student.pk: Decimal(80)}, actor=admin
    )
    second = services.bulk_record_results(
        exam=exam, marks_by_student_id={student.pk: Decimal(95)}, actor=admin
    )
    assert Result.objects.filter(student=student, exam=exam).count() == 1
    assert Result.objects.get(student=student, exam=exam).marks == Decimal(95)
    assert second >= 1


def test_rejects_marks_over_max(student, exam, admin):
    with pytest.raises(ConflictError):
        services.bulk_record_results(
            exam=exam, marks_by_student_id={student.pk: Decimal(101)}, actor=admin
        )


def test_rejects_foreign_students(student, exam, admin):
    other = StudentFactory(group=GroupFactory(name="Res External"))
    with pytest.raises(ConflictError):
        services.bulk_record_results(
            exam=exam,
            marks_by_student_id={other.pk: Decimal(90)},
            actor=admin,
        )


def test_delete_result(student, exam, admin):
    services.bulk_record_results(
        exam=exam, marks_by_student_id={student.pk: Decimal(70)}, actor=admin
    )
    rows = Result.objects.filter(student=student, exam=exam)
    assert rows.count() == 1
    services.delete_result(result=rows.first(), actor=admin)
    assert Result.objects.filter(student=student, exam=exam).count() == 0
