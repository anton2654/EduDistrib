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