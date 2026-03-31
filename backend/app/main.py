from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import (
    auth,
    delivery,
    ewallet,
    floor_areas,
    inventory,
    kitchen,
    menu,
    orders,
    outlets,
    payments,
    promotions,
    register,
    reports,
    reservations,
    staff,
    tables,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(
    title="ServePOS",
    description="Restaurant POS & Kitchen Management System",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Phase 1: Core
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(outlets.router, prefix="/api/v1/outlets", tags=["Outlets"])
app.include_router(staff.router, prefix="/api/v1/staff", tags=["Staff"])

# Phase 2: Menu & Orders
app.include_router(menu.router, prefix="/api/v1/menu", tags=["Menu"])
app.include_router(orders.router, prefix="/api/v1/orders", tags=["Orders"])

# Phase 3: Tables & Kitchen
app.include_router(tables.router, prefix="/api/v1/tables", tags=["Tables"])
app.include_router(floor_areas.router, prefix="/api/v1/floor-areas", tags=["Floor Areas"])
app.include_router(kitchen.router, prefix="/api/v1/kitchen", tags=["Kitchen Display"])

# Phase 4: Payments & Register
app.include_router(payments.router, prefix="/api/v1/payments", tags=["Payments"])
app.include_router(ewallet.router, prefix="/api/v1/ewallet", tags=["E-Wallet"])
app.include_router(register.router, prefix="/api/v1/register", tags=["Register"])

# Phase 5: Inventory
app.include_router(inventory.router, prefix="/api/v1/inventory", tags=["Inventory"])

# Phase 6: Reports
app.include_router(reports.router, prefix="/api/v1/reports", tags=["Reports"])

# Phase 8: Delivery
app.include_router(delivery.router, prefix="/api/v1/delivery", tags=["Delivery"])

# Phase 9: Advanced
app.include_router(promotions.router, prefix="/api/v1/promotions", tags=["Promotions"])
app.include_router(reservations.router, prefix="/api/v1/reservations", tags=["Reservations"])


@app.get("/api/v1/health")
async def health_check():
    return {"status": "ok", "service": "servepos"}


# WebSocket endpoints
from app.routers.kitchen import kitchen_ws  # noqa: E402

app.add_api_websocket_route("/ws/kitchen", kitchen_ws)
