import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import JSON, event
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database import Base, get_db
from app.main import app
from app.models.outlet import Outlet
from app.models.staff import Staff
from app.utils.security import create_access_token, hash_password

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

# Register JSONB -> JSON type adaptation for SQLite
from sqlalchemy.ext.compiler import compiles

@compiles(JSONB, "sqlite")
def compile_jsonb_sqlite(type_, compiler, **kw):
    return compiler.visit_JSON(JSON(), **kw)


@pytest_asyncio.fixture()
async def db_engine():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture()
async def db_session(db_engine):
    session_factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session


@pytest_asyncio.fixture()
async def client(db_engine):
    session_factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac
    app.dependency_overrides.clear()


# ---- Seed data helpers ----

OUTLET_ID = uuid.uuid4()
ADMIN_ID = uuid.uuid4()
MANAGER_ID = uuid.uuid4()
CASHIER_ID = uuid.uuid4()
WAITER_ID = uuid.uuid4()
KITCHEN_ID = uuid.uuid4()


@pytest_asyncio.fixture()
async def seed_outlet(db_session: AsyncSession):
    outlet = Outlet(
        id=OUTLET_ID,
        name="Test Restaurant",
        address="123 Test St",
        phone="+60123456789",
        currency="MYR",
        tax_rate=6.0,
        service_charge_rate=10.0,
        timezone="Asia/Kuala_Lumpur",
    )
    db_session.add(outlet)
    await db_session.commit()
    return outlet


@pytest_asyncio.fixture()
async def seed_staff(db_session: AsyncSession, seed_outlet):
    staff_members = []
    for sid, role, name, email, pin in [
        (ADMIN_ID, "admin", "Admin User", "admin@test.com", "0000"),
        (MANAGER_ID, "manager", "Manager User", "manager@test.com", "1111"),
        (CASHIER_ID, "cashier", "Cashier User", "cashier@test.com", "2222"),
        (WAITER_ID, "waiter", "Waiter User", "waiter@test.com", "3333"),
        (KITCHEN_ID, "kitchen", "Kitchen User", "kitchen@test.com", "4444"),
    ]:
        s = Staff(
            id=sid,
            outlet_id=OUTLET_ID,
            email=email,
            hashed_password=hash_password("password123"),
            full_name=name,
            role=role,
            pin_code=pin,
        )
        db_session.add(s)
        staff_members.append(s)
    await db_session.commit()
    return staff_members


def make_token(staff_id: uuid.UUID, role: str) -> str:
    return create_access_token({
        "sub": str(staff_id),
        "role": role,
        "outlet_id": str(OUTLET_ID),
    })


def admin_headers():
    return {"Authorization": f"Bearer {make_token(ADMIN_ID, 'admin')}"}


def manager_headers():
    return {"Authorization": f"Bearer {make_token(MANAGER_ID, 'manager')}"}


def cashier_headers():
    return {"Authorization": f"Bearer {make_token(CASHIER_ID, 'cashier')}"}


def waiter_headers():
    return {"Authorization": f"Bearer {make_token(WAITER_ID, 'waiter')}"}


def kitchen_headers():
    return {"Authorization": f"Bearer {make_token(KITCHEN_ID, 'kitchen')}"}
