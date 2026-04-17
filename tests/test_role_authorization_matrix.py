from __future__ import annotations

from datetime import datetime, timedelta
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


@pytest.mark.asyncio
async def test_teacher_list_supports_search_query_filter() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        response = await client.get("/api/v1/enrollment/teachers?search_query=ivan")

    assert response.status_code == 200
    rows = response.json()
    assert isinstance(rows, list)
    for row in rows:
        assert "ivan" in row["full_name"].lower()


@pytest.mark.asyncio
async def test_student_can_leave_review_only_after_completed_booking() -> None:
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

        student_payload, student_headers = await _register_student(client)

        create_booking_response = await client.post(
            "/api/v1/enrollment/bookings",
            headers=student_headers,
            json={
                "student_id": student_payload["student_id"],
                "slot_id": target_slot["slot_id"],
            },
        )
        if create_booking_response.status_code != 201:
            pytest.skip("Could not create booking for review flow test.")

        booking_id = create_booking_response.json()["id"]

        review_before_complete = await client.post(
            "/api/v1/enrollment/reviews",
            headers=student_headers,
            json={
                "booking_id": booking_id,
                "rating": 5,
                "comment": "Great lesson",
            },
        )
        assert review_before_complete.status_code == 409

        complete_response = await client.post(
            f"/api/v1/teacher/slots/{target_slot['slot_id']}/bookings/{booking_id}/complete",
            headers=teacher_headers,
        )
        assert complete_response.status_code == 200

        review_after_complete = await client.post(
            "/api/v1/enrollment/reviews",
            headers=student_headers,
            json={
                "booking_id": booking_id,
                "rating": 5,
                "comment": "Great lesson",
            },
        )
        assert review_after_complete.status_code == 201
        assert review_after_complete.json()["rating"] == 5

        duplicate_review_response = await client.post(
            "/api/v1/enrollment/reviews",
            headers=student_headers,
            json={
                "booking_id": booking_id,
                "rating": 4,
                "comment": "Second review",
            },
        )
        assert duplicate_review_response.status_code == 409


@pytest.mark.asyncio
async def test_student_can_update_own_profile_password_and_city() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        suffix = uuid4().hex[:8]

        cities_response = await client.get("/api/v1/enrollment/cities")
        assert cities_response.status_code == 200
        cities = cities_response.json()
        if len(cities) < 2:
            pytest.skip("At least two cities are required for profile city update test.")

        initial_city_id = cities[0]["id"]
        updated_city_id = cities[1]["id"]
        initial_password = "student123"
        new_password = "student456"
        username = f"student_profile_{suffix}"
        updated_username = f"student_profile_updated_{suffix}"
        updated_full_name = f"Updated Student {suffix}"
        updated_email = f"student-profile-updated-{suffix}@example.com"

        register_response = await client.post(
            "/api/v1/auth/register/student",
            json={
                "username": username,
                "password": initial_password,
                "full_name": f"Profile Student {suffix}",
                "email": f"student-profile-{suffix}@example.com",
                "city_id": initial_city_id,
            },
        )
        assert register_response.status_code == 201

        token = register_response.json()["access_token"]
        student_headers = {"Authorization": f"Bearer {token}"}

        update_response = await client.patch(
            "/api/v1/auth/me",
            headers=student_headers,
            json={
                "username": updated_username,
                "full_name": updated_full_name,
                "email": updated_email,
                "city_id": updated_city_id,
                "current_password": initial_password,
                "new_password": new_password,
            },
        )
        assert update_response.status_code == 200
        assert update_response.json()["username"] == updated_username
        assert update_response.json()["full_name"] == updated_full_name
        assert update_response.json()["email"] == updated_email
        assert update_response.json()["city_id"] == updated_city_id

        login_response = await client.post(
            "/api/v1/auth/login",
            json={"username": updated_username, "password": new_password},
        )

    assert login_response.status_code == 200


@pytest.mark.asyncio
async def test_student_registration_rejects_typo_email_domain() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        suffix = uuid4().hex[:8]

        cities_response = await client.get("/api/v1/enrollment/cities")
        assert cities_response.status_code == 200
        cities = cities_response.json()
        if not cities:
            pytest.skip("No cities available. Seed demo data before running this test.")

        for index, email in enumerate(
            [
                f"student-typo-{suffix}@gmail.co",
                f"student-typo-{suffix}@gmail.comm",
                f"student-typo-{suffix}@gmail.commm",
            ],
            start=1,
        ):
            register_response = await client.post(
                "/api/v1/auth/register/student",
                json={
                    "username": f"student_typo_{suffix}_{index}",
                    "password": "student123",
                    "full_name": f"Student Typo {suffix}",
                    "email": email,
                    "city_id": cities[0]["id"],
                },
            )
            assert register_response.status_code == 422


@pytest.mark.asyncio
async def test_account_update_rejects_invalid_or_typo_email() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        payload, student_headers = await _register_student(client)
        assert payload["access_token"]

        invalid_format_response = await client.patch(
            "/api/v1/auth/me",
            headers=student_headers,
            json={"email": "invalid-email"},
        )
        assert invalid_format_response.status_code == 422

        typo_domain_response = await client.patch(
            "/api/v1/auth/me",
            headers=student_headers,
            json={"email": "updated@gmail.co"},
        )
        assert typo_domain_response.status_code == 422

        typo_domain_comm_response = await client.patch(
            "/api/v1/auth/me",
            headers=student_headers,
            json={"email": "updated@gmail.comm"},
        )
        assert typo_domain_comm_response.status_code == 422

        typo_domain_commm_response = await client.patch(
            "/api/v1/auth/me",
            headers=student_headers,
            json={"email": "updated@gmail.commm"},
        )

    assert typo_domain_commm_response.status_code == 422


@pytest.mark.asyncio
async def test_teacher_email_is_persisted_and_can_be_updated() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        admin_token = await _ensure_admin_token(client)
        if admin_token is None:
            pytest.skip("Unable to authenticate admin with default bootstrap credentials.")

        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        suffix = uuid4().hex[:8]

        cities_response = await client.get("/api/v1/enrollment/cities")
        assert cities_response.status_code == 200
        cities = cities_response.json()
        if not cities:
            pytest.skip("No cities available. Seed demo data before running this test.")

        teacher_create_response = await client.post(
            "/api/v1/enrollment/teachers",
            headers=admin_headers,
            json={
                "full_name": f"Teacher Profile {suffix}",
                "city_id": cities[0]["id"],
            },
        )
        assert teacher_create_response.status_code == 201
        teacher_id = teacher_create_response.json()["id"]

        username = f"teacher_profile_{suffix}"
        password = "teacher123"
        initial_email = f"teacher-profile-{suffix}@example.com"

        register_response = await client.post(
            "/api/v1/auth/register/teacher",
            headers=admin_headers,
            json={
                "username": username,
                "password": password,
                "teacher_id": teacher_id,
                "email": initial_email,
            },
        )
        assert register_response.status_code == 201
        assert register_response.json()["email"] == initial_email

        teacher_login_response = await client.post(
            "/api/v1/auth/login",
            json={"username": username, "password": password},
        )
        assert teacher_login_response.status_code == 200
        teacher_headers = {
            "Authorization": f"Bearer {teacher_login_response.json()['access_token']}"
        }

        me_response = await client.get("/api/v1/auth/me", headers=teacher_headers)
        assert me_response.status_code == 200
        assert me_response.json()["email"] == initial_email

        updated_email = f"teacher-profile-updated-{suffix}@example.com"
        update_response = await client.patch(
            "/api/v1/auth/me",
            headers=teacher_headers,
            json={"email": updated_email},
        )
        assert update_response.status_code == 200
        assert update_response.json()["email"] == updated_email

        me_after_response = await client.get("/api/v1/auth/me", headers=teacher_headers)

    assert me_after_response.status_code == 200
    assert me_after_response.json()["email"] == updated_email


@pytest.mark.asyncio
async def test_teacher_slot_update_is_restricted_when_active_bookings_exist() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        teacher_headers = await _ensure_teacher_headers(client)
        if teacher_headers is None:
            pytest.skip("Seeded teacher account is required for this test.")

        slots_response = await client.get("/api/v1/teacher/slots/", headers=teacher_headers)
        assert slots_response.status_code == 200
        slots = slots_response.json()

        target_slot = next(
            (
                slot
                for slot in slots
                if slot["is_active"] and slot["available_seats"] >= 2 and slot["capacity"] >= 2
            ),
            None,
        )
        if target_slot is None:
            pytest.skip("Need an active slot with at least 2 free seats for this test.")

        student_a_payload, student_a_headers = await _register_student(client)
        student_b_payload, student_b_headers = await _register_student(client)

        booking_a_response = await client.post(
            "/api/v1/enrollment/bookings",
            headers=student_a_headers,
            json={
                "student_id": student_a_payload["student_id"],
                "slot_id": target_slot["slot_id"],
            },
        )
        booking_b_response = await client.post(
            "/api/v1/enrollment/bookings",
            headers=student_b_headers,
            json={
                "student_id": student_b_payload["student_id"],
                "slot_id": target_slot["slot_id"],
            },
        )
        if booking_a_response.status_code != 201 or booking_b_response.status_code != 201:
            pytest.skip("Could not create enough active bookings for slot update restriction test.")

        reduce_capacity_response = await client.put(
            f"/api/v1/teacher/slots/{target_slot['slot_id']}",
            headers=teacher_headers,
            json={"capacity": 1},
        )
        assert reduce_capacity_response.status_code == 409

        starts_at = datetime.fromisoformat(target_slot["starts_at"].replace("Z", "+00:00"))
        ends_at = datetime.fromisoformat(target_slot["ends_at"].replace("Z", "+00:00"))

        move_time_response = await client.put(
            f"/api/v1/teacher/slots/{target_slot['slot_id']}",
            headers=teacher_headers,
            json={
                "starts_at": (starts_at + timedelta(hours=1)).isoformat(),
                "ends_at": (ends_at + timedelta(hours=1)).isoformat(),
            },
        )

    assert move_time_response.status_code == 409


@pytest.mark.asyncio
async def test_teacher_can_complete_all_bookings_for_slot() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        teacher_headers = await _ensure_teacher_headers(client)
        if teacher_headers is None:
            pytest.skip("Seeded teacher account is required for this test.")

        slots_response = await client.get("/api/v1/teacher/slots/", headers=teacher_headers)
        assert slots_response.status_code == 200
        slots = slots_response.json()
        target_slot = next(
            (slot for slot in slots if slot["is_active"] and slot["available_seats"] > 0),
            None,
        )
        if target_slot is None:
            pytest.skip("No suitable active slot found for complete-all test.")

        student_payload, student_headers = await _register_student(client)
        booking_response = await client.post(
            "/api/v1/enrollment/bookings",
            headers=student_headers,
            json={
                "student_id": student_payload["student_id"],
                "slot_id": target_slot["slot_id"],
            },
        )
        if booking_response.status_code != 201:
            pytest.skip("Could not create booking for complete-all test.")

        booking_id = booking_response.json()["id"]

        complete_all_response = await client.post(
            f"/api/v1/teacher/slots/{target_slot['slot_id']}/bookings/complete-all",
            headers=teacher_headers,
        )
        assert complete_all_response.status_code == 200
        assert complete_all_response.json()["updated_bookings"] >= 1

        bookings_response = await client.get(
            f"/api/v1/teacher/slots/{target_slot['slot_id']}/bookings",
            headers=teacher_headers,
        )
        assert bookings_response.status_code == 200
        booking_row = next(
            (row for row in bookings_response.json() if row["booking_id"] == booking_id),
            None,
        )

    assert booking_row is not None
    assert booking_row["status"] == "completed"


@pytest.mark.asyncio
async def test_teacher_slot_delete_soft_cancels_active_bookings() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        teacher_headers = await _ensure_teacher_headers(client)
        if teacher_headers is None:
            pytest.skip("Seeded teacher account is required for this test.")

        slots_response = await client.get("/api/v1/teacher/slots/", headers=teacher_headers)
        assert slots_response.status_code == 200
        slots = slots_response.json()
        target_slot = next(
            (slot for slot in slots if slot["is_active"] and slot["available_seats"] > 0),
            None,
        )
        if target_slot is None:
            pytest.skip("No suitable active slot found for soft-delete test.")

        student_payload, student_headers = await _register_student(client)
        booking_response = await client.post(
            "/api/v1/enrollment/bookings",
            headers=student_headers,
            json={
                "student_id": student_payload["student_id"],
                "slot_id": target_slot["slot_id"],
            },
        )
        if booking_response.status_code != 201:
            pytest.skip("Could not create booking for soft-delete test.")

        booking_id = booking_response.json()["id"]

        delete_response = await client.delete(
            f"/api/v1/teacher/slots/{target_slot['slot_id']}",
            headers=teacher_headers,
        )
        assert delete_response.status_code == 204

        updated_slots_response = await client.get(
            "/api/v1/teacher/slots/",
            headers=teacher_headers,
        )
        assert updated_slots_response.status_code == 200
        updated_slot = next(
            (
                slot
                for slot in updated_slots_response.json()
                if slot["slot_id"] == target_slot["slot_id"]
            ),
            None,
        )

        student_bookings_response = await client.get(
            "/api/v1/enrollment/bookings",
            headers=student_headers,
        )
        assert student_bookings_response.status_code == 200
        updated_booking = next(
            (
                booking
                for booking in student_bookings_response.json()
                if booking["booking_id"] == booking_id
            ),
            None,
        )

    assert updated_slot is not None
    assert updated_slot["is_active"] is False
    assert updated_booking is not None
    assert updated_booking["status"] == "cancelled"


@pytest.mark.asyncio
async def test_student_can_leave_multiple_reviews_for_same_teacher_on_different_bookings() -> None:
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

        base_slot = next(
            (
                slot
                for slot in teacher_slots
                if slot["is_active"] and slot["available_seats"] > 0
            ),
            None,
        )
        if base_slot is None:
            pytest.skip("No active teacher slot found for multi-review test.")

        base_ends_at = datetime.fromisoformat(base_slot["ends_at"].replace("Z", "+00:00"))
        second_slot_starts_at = base_ends_at + timedelta(hours=1)
        second_slot_ends_at = second_slot_starts_at + timedelta(hours=1)

        create_second_slot_response = await client.post(
            "/api/v1/teacher/slots/",
            headers=teacher_headers,
            json={
                "discipline_id": base_slot["discipline_id"],
                "starts_at": second_slot_starts_at.isoformat(),
                "ends_at": second_slot_ends_at.isoformat(),
                "capacity": 2,
                "is_active": True,
            },
        )
        if create_second_slot_response.status_code != 201:
            pytest.skip("Could not create second slot for multi-review test.")

        second_slot_id = create_second_slot_response.json()["id"]

        student_payload, student_headers = await _register_student(client)
        student_id = student_payload["student_id"]

        booking_one_response = await client.post(
            "/api/v1/enrollment/bookings",
            headers=student_headers,
            json={"student_id": student_id, "slot_id": base_slot["slot_id"]},
        )
        booking_two_response = await client.post(
            "/api/v1/enrollment/bookings",
            headers=student_headers,
            json={"student_id": student_id, "slot_id": second_slot_id},
        )
        if booking_one_response.status_code != 201 or booking_two_response.status_code != 201:
            pytest.skip("Could not create two bookings for multi-review test.")

        booking_one_id = booking_one_response.json()["id"]
        booking_two_id = booking_two_response.json()["id"]

        complete_one_response = await client.post(
            f"/api/v1/teacher/slots/{base_slot['slot_id']}/bookings/{booking_one_id}/complete",
            headers=teacher_headers,
        )
        complete_two_response = await client.post(
            f"/api/v1/teacher/slots/{second_slot_id}/bookings/{booking_two_id}/complete",
            headers=teacher_headers,
        )
        assert complete_one_response.status_code == 200
        assert complete_two_response.status_code == 200

        review_one_response = await client.post(
            "/api/v1/enrollment/reviews",
            headers=student_headers,
            json={
                "booking_id": booking_one_id,
                "rating": 5,
                "comment": "First completed lesson",
            },
        )
        review_two_response = await client.post(
            "/api/v1/enrollment/reviews",
            headers=student_headers,
            json={
                "booking_id": booking_two_id,
                "rating": 4,
                "comment": "Second completed lesson",
            },
        )
        assert review_one_response.status_code == 201
        assert review_two_response.status_code == 201

        reviews_list_response = await client.get(
            f"/api/v1/enrollment/reviews?teacher_id={base_slot['teacher_id']}",
        )

    assert reviews_list_response.status_code == 200
    reviews = reviews_list_response.json()
    assert any(row["booking_id"] == booking_one_id for row in reviews)
    assert any(row["booking_id"] == booking_two_id for row in reviews)