import random
from decimal import Decimal

import factory

from academics.factories import ExamFactory
from results.grades import grade_for
from results.models import Result
from students.factories import StudentFactory


class ResultFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Result

    student = factory.SubFactory(StudentFactory)
    exam = factory.SubFactory(ExamFactory)
    marks = factory.LazyAttribute(
        lambda o: Decimal(o.exam.max_marks)
        * Decimal(random.randint(4, 10))  # noqa: S311 - test data only
        / Decimal(10)
    )
    grade = factory.LazyAttribute(lambda o: grade_for(float(o.marks), o.exam.max_marks))
