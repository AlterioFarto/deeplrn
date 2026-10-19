"""Common layer tests: CSV sanitization, pagination caps, fail-closed scoping."""

import pytest
from django.http import HttpRequest
from django.test import override_settings

from common.csv import sanitize_cell, streaming_csv_response
from common.pagination import get_page_size
from common.roles import Role
from common.scoping import get_boundary, scoped_queryset

pytestmark = pytest.mark.django_db


def test_sanitize_csv_blocks_formula_injection():
    assert sanitize_cell("=SUM(A1:A2)").startswith("'")
    assert sanitize_cell("+1").startswith("'")
    assert sanitize_cell("-1").startswith("'")
    assert sanitize_cell("@x").startswith("'")
    assert sanitize_cell("safe") == "safe"


def _fake_request(page_size: str | None = None) -> HttpRequest:
    request = HttpRequest()
    if page_size is not None:
        request.GET = {"page_size": page_size}
    return request


@override_settings(PAGE_SIZE=10, MAX_PAGE_SIZE=100)
def test_page_size_cap():
    assert get_page_size(_fake_request()) == 10
    assert get_page_size(_fake_request("500")) == 100
    assert get_page_size(_fake_request("abc")) == 10


def test_scoping_fails_closed_for_unknown_shape(guardian):
    from accounts.models import User

    assert not scoped_queryset(User.objects.all(), guardian).exists()


def test_boundary_roles(admin, mentor):
    assert get_boundary(admin).group_ids() is None
    assert Role(admin.role) == Role.ADMIN
    assert Role(mentor.role) == Role.MENTOR


def test_streaming_csv_response_sanitize():
    response = streaming_csv_response(
        filename="x.csv", headers=["a", "b"], rows=iter([["1", "2"], ["=evil", "ok"]])
    )
    assert response.status_code == 200
    assert "attachment" in response["Content-Disposition"]
    body = b"".join(response.streaming_content).decode("utf-8-sig")
    assert "'=evil" in body
