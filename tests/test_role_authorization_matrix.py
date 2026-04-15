from __future__ import annotations

from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


async def _register_student(client: AsyncClient) -> tuple[dict, dict[str, str]]:
    suffix = uuid4().hex[:8]

    cities_response = await client.get("/api/v1/enrollment/cities")
    assert cities_response.status_code == 200
    cities = cities_response.json()
    if not cities:
        pytest.skip("No cities available. Seed demo data before running this test.")

    city_id = cities[0]["id"]

    register_response = await client.post(
        "/api/v1/auth/register/student",
        json={
            "username": f"student_matrix_{suffix}",
            "password": "student123",
            "full_name": f"Student Matrix {suffix}",
            "email": f"student-matrix-{suffix}@example.com",
            "city_id": city_id,
        },
    )
    assert register_response.status_code == 201

    payload = register_response.json()
    headers = {"Authorization": f"Bearer {payload['access_token']}"}
    return payload, headers


async def _ensure_admin_token(client: AsyncClient) -> str | None:
    login_response = await client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "admin12345"},
    )
    if login_response.status_code == 200:
        return login_response.json()["access_token"]

    bootstrap_response = await client.post(
        "/api/v1/auth/bootstrap-admin",
        json={"username": "admin", "password": "admin12345"},
    )
    if bootstrap_response.status_code == 201:
        return bootstrap_response.json()["access_token"]

    retry_login_response = await client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "admin12345"},
    )
    if retry_login_response.status_code == 200:
        return retry_login_response.json()["access_token"]

    return None


async def _ensure_teacher_headers(
    client: AsyncClient,
    username: str = "teacher_ivan",
    password: str = "teacher123",
) -> dict[str, str] | None:
    login_response = await client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password},
    )
    if login_response.status_code != 200:
        return None

    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_auth_me_requires_token() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        response = await client.get("/api/v1/auth/me")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_student_cannot_access_admin_or_teacher_routes() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        _, student_headers = await _register_student(client)

        accounts_response = await client.get(
            "/api/v1/auth/accounts",
            headers=student_headers,
        )
        teacher_slots_response = await client.get(
            "/api/v1/teacher/slots/",
            headers=student_headers,
        )

    assert accounts_response.status_code == 403
    assert teacher_slots_response.status_code == 403


@pytest.mark.asyncio
async def test_teacher_cannot_access_student_booking_list_route() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        teacher_login_response = await client.post(
            "/api/v1/auth/login",
            json={"username": "teacher_ivan", "password": "teacher123"},
        )
        if teacher_login_response.status_code != 200:
            pytest.skip("Seeded teacher account is required for this test.")

        teacher_headers = {
            "Authorization": f"Bearer {teacher_login_response.json()['access_token']}"
        }
        bookings_response = await client.get(
            "/api/v1/enrollment/bookings",
            headers=teacher_headers,
        )

    assert bookings_response.status_code == 403


@pytest.mark.asyncio
async def test_admin_can_access_admin_and_student_routes() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        admin_token = await _ensure_admin_token(client)
        if admin_token is None:
            pytest.skip("Unable to authenticate admin with default bootstrap credentials.")

        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        accounts_response = await client.get(
            "/api/v1/auth/accounts",
            headers=admin_headers,
        )
        students_response = await client.get(
            "/api/v1/enrollment/students",
            headers=admin_headers,
        )

    assert accounts_response.status_code == 200
    assert isinstance(accounts_response.json(), list)
    assert students_response.status_code == 200
    assert isinstance(students_response.json(), list)


@pytest.mark.asyncio
async def test_admin_can_access_enrollment_analytics_routes() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        admin_token = await _ensure_admin_token(client)
        if admin_token is None:
            pytest.skip("Unable to authenticate admin with default bootstrap credentials.")

        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        overview_response = await client.get(
            "/api/v1/enrollment/analytics/overview",
            headers=admin_headers,
        )
        teachers_response = await client.get(
            "/api/v1/enrollment/analytics/teachers",
            headers=admin_headers,
        )
        disciplines_response = await client.get(
            "/api/v1/enrollment/analytics/disciplines",
            headers=admin_headers,
        )

    assert overview_response.status_code == 200
    overview_payload = overview_response.json()
    assert "filtered_slots_total" in overview_payload
    assert "utilization_rate_percent" in overview_payload

    assert teachers_response.status_code == 200
    assert isinstance(teachers_response.json(), list)

    assert disciplines_response.status_code == 200
    assert isinstance(disciplines_response.json(), list)


@pytest.mark.asyncio
async def test_student_cannot_access_enrollment_analytics_routes() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        _, student_headers = await _register_student(client)

        analytics_response = await client.get(
            "/api/v1/enrollment/analytics/overview",
            headers=student_headers,
        )

    assert analytics_response.status_code == 403


@pytest.mark.asyncio
async def test_student_cannot_spoof_student_id_on_booking_create() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        auth_payload, student_headers = await _register_student(client)
        student_id = auth_payload["student_id"]
        assert student_id is not None

        slots_response = await client.get("/api/v1/enrollment/slots/available")
        assert slots_response.status_code == 200
        slots = slots_response.json()
        if not slots:
            pytest.skip("No available slots found. Seed demo data before running this test.")

        slot_id = slots[0]["slot_id"]
        spoofed_student_id = int(student_id) + 9999

        create_booking_response = await client.post(
            "/api/v1/enrollment/bookings",
            headers=student_headers,
            json={"student_id": spoofed_student_id, "slot_id": slot_id},
        )
        if create_booking_response.status_code == 409:
            pytest.skip(
                "Could not create booking due to slot conflict/full state in current DB seed.",
            )

        assert create_booking_response.status_code == 201
        created_booking = create_booking_response.json()
        assert created_booking["student_id"] == student_id

        booking_id = created_booking["id"]
        cancel_response = await client.delete(
            f"/api/v1/enrollment/bookings/{booking_id}",
            headers=student_headers,
        )

    assert cancel_response.status_code == 204


@pytest.mark.asyncio
async def test_list_endpoints_support_skip_limit_pagination() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        admin_token = await _ensure_admin_token(client)
        if admin_token is None:
            pytest.skip("Unable to authenticate admin with default bootstrap credentials.")
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        accounts_response = await client.get(
            "/api/v1/auth/accounts?skip=0&limit=1",
            headers=admin_headers,
        )
        assert accounts_response.status_code == 200
        assert len(accounts_response.json()) <= 1

        teachers_response = await client.get("/api/v1/enrollment/teachers?skip=0&limit=1")
        assert teachers_response.status_code == 200
        assert len(teachers_response.json()) <= 1

        slots_response = await client.get("/api/v1/enrollment/slots/available?skip=0&limit=1")
        assert slots_response.status_code == 200
        assert len(slots_response.json()) <= 1

        _, student_headers = await _register_student(client)
        bookings_response = await client.get(
            "/api/v1/enrollment/bookings?skip=0&limit=1",
            headers=student_headers,
        )
        assert bookings_response.status_code == 200
        assert len(bookings_response.json()) <= 1


@pytest.mark.asyncio
async def test_teacher_can_view_and_manage_slot_bookings() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        teacher_headers = await _ensure_teacher_headers(client)
        if teacher_headers is None:
            pytest.skip("Seeded teacher account is required for this test.")

        teacher_slots_response = await client.get(
            "/api/v1/teacher/slots/",
            headers=teacher_headers,
        )
        assert teacher_slots_response.status_code == 200
        teacher_slots = teacher_slots_response.json()

        target_slot = next(
            (
                slot
                for slot in teacher_slots
                if slot["is_active"] and slot["available_seats"] > 0
            ),
            None,
        )
        if target_slot is None:
            pytest.skip("Teacher has no active slot with available seats.")

        slot_id = target_slot["slot_id"]

        student_payload, student_headers = await _register_student(client)
        booking_response = await client.post(
            "/api/v1/enrollment/bookings",
            headers=student_headers,
            json={"student_id": student_payload["student_id"], "slot_id": slot_id},
        )
        if booking_response.status_code != 201:
            pytest.skip("Could not create booking for teacher management test.")
        booking_id = booking_response.json()["id"]

        slot_bookings_response = await client.get(
            f"/api/v1/teacher/slots/{slot_id}/bookings",
            headers=teacher_headers,
        )
        assert slot_bookings_response.status_code == 200
        slot_bookings = slot_bookings_response.json()
        managed_booking = next(
            booking for booking in slot_bookings if booking["booking_id"] == booking_id
        )
        assert managed_booking["student_email"].endswith("@example.com")
        assert managed_booking["status"] == "active"

        cancel_response = await client.post(
            f"/api/v1/teacher/slots/{slot_id}/bookings/{booking_id}/cancel",
            headers=teacher_headers,
        )
        assert cancel_response.status_code == 200
        assert cancel_response.json()["status"] == "cancelled"


@pytest.mark.asyncio
async def test_student_cannot_book_overlapping_slots() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        teacher_headers = await _ensure_teacher_headers(client)
        if teacher_headers is None:
            pytest.skip("Seeded teacher account is required for this test.")

        teacher_slots_response = await client.get(
            "/api/v1/teacher/slots/",
            headers=teacher_headers,
        )
        assert teacher_slots_response.status_code == 200
        teacher_slots = teacher_slots_response.json()
        if not teacher_slots:
            pytest.skip("Teacher has no slots to clone for overlap testing.")

        template_slot = teacher_slots[0]

        create_slot_payload = {
            "discipline_id": template_slot["discipline_id"],
            "starts_at": template_slot["starts_at"],
            "ends_at": template_slot["ends_at"],
            "capacity": 2,
            "is_active": True,
        }

        slot_a_response = await client.post(
            "/api/v1/teacher/slots/",
            headers=teacher_headers,
            json=create_slot_payload,
        )
        slot_b_response = await client.post(
            "/api/v1/teacher/slots/",
            headers=teacher_headers,
            json=create_slot_payload,
        )
        if slot_a_response.status_code != 201 or slot_b_response.status_code != 201:
            pytest.skip("Could not create overlapping slots for conflict test.")

        slot_a_id = slot_a_response.json()["id"]
        slot_b_id = slot_b_response.json()["id"]

        student_payload, student_headers = await _register_student(client)
        student_id = student_payload["student_id"]

        first_booking_response = await client.post(
            "/api/v1/enrollment/bookings",
            headers=student_headers,
            json={"student_id": student_id, "slot_id": slot_a_id},
        )
        assert first_booking_response.status_code == 201

        second_booking_response = await client.post(
            "/api/v1/enrollment/bookings",
            headers=student_headers,
            json={"student_id": student_id, "slot_id": slot_b_id},
        )

    assert second_booking_response.status_code == 409