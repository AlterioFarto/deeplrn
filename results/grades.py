"""Single pure grade-derivation function; the only source of grade letters."""

GRADE_BANDS: tuple[tuple[str, int], ...] = (
    ("A+", 90),
    ("A", 80),
    ("B", 70),
    ("C", 60),
    ("D", 50),
)
GRADE_CHOICES: tuple[str, ...] = (*tuple(band for band, _ in GRADE_BANDS), "F")


def grade_for(marks: float, max_marks: float) -> str:
    """Pure grade derivation from a percentage; used everywhere grades appear."""
    if max_marks <= 0:
        raise ValueError("max_marks must be greater than zero.")
    percentage = (marks / max_marks) * 100
    for grade, threshold in GRADE_BANDS:
        if percentage >= threshold:
            return grade
    return "F"
