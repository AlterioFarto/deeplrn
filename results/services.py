"""Result mutations: validated single and bulk entry, single grade source."""

from decimal import Decimal
from typing import Any

from django.db import transaction

from academics.models import Exam
from accounts.models import User
from common.audit import log_action
from common.exceptions import ConflictError
from common.scoping import assert_can_access, assert_can_manage_group
from results.grades import grade_for
from results.models import Result


def validate_marks(marks: Decimal, exam: Exam) -> None:
    if marks < 0:
        raise ConflictError("Marks cannot be negative.")
    if marks > exam.max_marks:
        raise ConflictError(f"Marks cannot exceed the exam maximum ({exam.max_marks}).")


@transaction.atomic
def record_result(*, student: Any, exam: Exam, marks: Decimal, actor: User | None = None) -> Result:
    assert_can_access(actor, student)
    assert_can_manage_group(actor, exam.group)
    validate_marks(marks, exam)
    result, created = Result.objects.update_or_create(
        student=student,
        exam=exam,
        defaults={"marks": marks, "grade": grade_for(float(marks), exam.max_marks)},
    )
    log_action(actor=actor, action="update" if not created else "create", obj=result)
    return result


@transaction.atomic
def bulk_record_results(
    *, exam: Exam, marks_by_student_id: dict[int, Decimal], actor: User | None = None
) -> int:
    """Enter/overwrite results for many students in one transaction.

    Idempotent: repeats with the same input converge to the same rows via a
    conflict-aware bulk upsert on (student, exam).
    """
    assert_can_manage_group(actor, exam.group)
    if not marks_by_student_id:
        raise ConflictError("No marks submitted.")
    group_ids = set(
        exam.group.students.filter(deleted_at__isnull=True).values_list("pk", flat=True)
    )
    foreign = set(marks_by_student_id) - group_ids
    if foreign:
        raise ConflictError("Some students do not belong to this exam's group.")
    for marks in marks_by_student_id.values():
        validate_marks(marks, exam)
    grades = {
        student_id: grade_for(float(marks), exam.max_marks)
        for student_id, marks in marks_by_student_id.items()
    }
    now_rows = [
        Result(student_id=student_id, exam=exam, marks=marks, grade=grades[student_id])
        for student_id, marks in marks_by_student_id.items()
    ]
    Result.objects.bulk_create(
        now_rows,
        update_conflicts=True,
        unique_fields=["student", "exam"],
        update_fields=["marks", "grade", "updated_at"],
        batch_size=500,
    )
    log_action(
        actor=actor,
        action="bulk_results",
        diff={"exam": str(exam), "rows": len(now_rows)},
    )
    return len(now_rows)


@transaction.atomic
def delete_result(*, result: Result, actor: User | None = None) -> None:
    assert_can_manage_group(actor, result.exam.group)
    log_action(actor=actor, action="soft_delete", obj=result)
    result.delete()


def recompute_grades() -> int:
    """Recompute path for the denormalised grade column (management command)."""
    rows = []
    for result in Result.objects.select_related("exam").iterator(chunk_size=500):
        grade = grade_for(float(result.marks), result.exam.max_marks)
        if result.grade != grade:
            result.grade = grade
            rows.append(result)
    if rows:
        Result.objects.bulk_update(rows, ["grade", "updated_at"], batch_size=500)
    return len(rows)
