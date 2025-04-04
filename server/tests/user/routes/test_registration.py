import logging
import pytest
from httpx import AsyncClient
from app.core.schemas import UserRegistration

logging.basicConfig(level="DEBUG")
logger = logging.getLogger(__name__)


@pytest.mark.asyncio
async def test_successful_user_creation(client: AsyncClient):
    payload = UserRegistration(
        email="test@example.com",
        password="securepassword123",
        username="testuser",
        full_name="Justing Testing",
    ).model_dump()

    response = await client.post("/users/register", json=payload)

    assert response.status_code == 201
