from datetime import date, datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import Date, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies.auth import require_roles
from app.models.inventory import InventoryItem, InventoryTransaction
from app.models.menu import MenuCategory, MenuItem
from app.models.order import Order, OrderItem
from app.models.payment import Payment
from app.models.staff import Staff

router = APIRouter()


@router.get("/daily-sales")
async def daily_sales(
    date_from: date = Query(default=None),
    date_to: date = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: Staff = Depends(require_roles("admin", "owner", "manager")),
):
    query = select(
        cast(Order.created_at, Date).label("date"),
        func.count(Order.id).label("order_count"),
        func.coalesce(func.sum(Order.subtotal), 0).label("subtotal"),
        func.coalesce(func.sum(Order.tax_amount), 0).label("tax"),
        func.coalesce(func.sum(Order.service_charge), 0).label("service_charge"),
        func.coalesce(func.sum(Order.discount_amount), 0).label("discounts"),
        func.coalesce(func.sum(Order.total), 0).label("total"),
    ).where(
        Order.outlet_id == current_user.outlet_id,
        Order.is_void == False,
    ).group_by(cast(Order.created_at, Date)).order_by(cast(Order.created_at, Date).desc())

    if date_from:
        query = query.where(cast(Order.created_at, Date) >= date_from)
    if date_to:
        query = query.where(cast(Order.created_at, Date) <= date_to)

    result = await db.execute(query)
    rows = result.all()
    return [
        {
            "date": str(r.date),
            "order_count": r.order_count,
            "subtotal": float(r.subtotal),
            "tax": float(r.tax),
            "service_charge": float(r.service_charge),
            "discounts": float(r.discounts),
            "total": float(r.total),
        }
        for r in rows
    ]


@router.get("/sales-by-item")
async def sales_by_item(
    date_from: date = Query(default=None),
    date_to: date = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: Staff = Depends(require_roles("admin", "owner", "manager")),
):
    query = (
        select(
            OrderItem.item_name,
            func.sum(OrderItem.quantity).label("total_qty"),
            func.sum(OrderItem.subtotal).label("total_revenue"),
        )
        .join(Order)
        .where(
            Order.outlet_id == current_user.outlet_id,
            Order.is_void == False,
            OrderItem.is_void == False,
        )
        .group_by(OrderItem.item_name)
        .order_by(func.sum(OrderItem.subtotal).desc())
    )
    if date_from:
        query = query.where(cast(Order.created_at, Date) >= date_from)
    if date_to:
        query = query.where(cast(Order.created_at, Date) <= date_to)

    result = await db.execute(query)
    return [
        {"item_name": r.item_name, "total_qty": int(r.total_qty), "total_revenue": float(r.total_revenue)}
        for r in result.all()
    ]


@router.get("/sales-by-category")
async def sales_by_category(
    date_from: date = Query(default=None),
    date_to: date = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: Staff = Depends(require_roles("admin", "owner", "manager")),
):
    query = (
        select(
            MenuCategory.name.label("category"),
            func.sum(OrderItem.quantity).label("total_qty"),
            func.sum(OrderItem.subtotal).label("total_revenue"),
        )
        .join(MenuItem, OrderItem.menu_item_id == MenuItem.id)
        .join(MenuCategory, MenuItem.category_id == MenuCategory.id)
        .join(Order, OrderItem.order_id == Order.id)
        .where(
            Order.outlet_id == current_user.outlet_id,
            Order.is_void == False,
            OrderItem.is_void == False,
        )
        .group_by(MenuCategory.name)
        .order_by(func.sum(OrderItem.subtotal).desc())
    )
    if date_from:
        query = query.where(cast(Order.created_at, Date) >= date_from)
    if date_to:
        query = query.where(cast(Order.created_at, Date) <= date_to)

    result = await db.execute(query)
    return [
        {"category": r.category, "total_qty": int(r.total_qty), "total_revenue": float(r.total_revenue)}
        for r in result.all()
    ]


@router.get("/sales-by-staff")
async def sales_by_staff(
    date_from: date = Query(default=None),
    date_to: date = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: Staff = Depends(require_roles("admin", "owner", "manager")),
):
    query = (
        select(
            Staff.full_name,
            func.count(Order.id).label("order_count"),
            func.coalesce(func.sum(Order.total), 0).label("total_sales"),
        )
        .join(Order, Order.staff_id == Staff.id)
        .where(
            Order.outlet_id == current_user.outlet_id,
            Order.is_void == False,
        )
        .group_by(Staff.full_name)
        .order_by(func.sum(Order.total).desc())
    )
    if date_from:
        query = query.where(cast(Order.created_at, Date) >= date_from)
    if date_to:
        query = query.where(cast(Order.created_at, Date) <= date_to)

    result = await db.execute(query)
    return [
        {"staff_name": r.full_name, "order_count": r.order_count, "total_sales": float(r.total_sales)}
        for r in result.all()
    ]


@router.get("/hourly-sales")
async def hourly_sales(
    target_date: date = Query(default=None, alias="date"),
    db: AsyncSession = Depends(get_db),
    current_user: Staff = Depends(require_roles("admin", "owner", "manager")),
):
    from sqlalchemy import extract

    query = (
        select(
            extract("hour", Order.created_at).label("hour"),
            func.count(Order.id).label("order_count"),
            func.coalesce(func.sum(Order.total), 0).label("total_sales"),
        )
        .where(
            Order.outlet_id == current_user.outlet_id,
            Order.is_void == False,
        )
        .group_by(extract("hour", Order.created_at))
        .order_by(extract("hour", Order.created_at))
    )
    if target_date:
        query = query.where(cast(Order.created_at, Date) == target_date)

    result = await db.execute(query)
    return [
        {"hour": int(r.hour), "order_count": r.order_count, "total_sales": float(r.total_sales)}
        for r in result.all()
    ]


@router.get("/payment-methods")
async def payment_methods_report(
    date_from: date = Query(default=None),
    date_to: date = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: Staff = Depends(require_roles("admin", "owner", "manager")),
):
    query = (
        select(
            Payment.payment_method,
            func.count(Payment.id).label("count"),
            func.coalesce(func.sum(Payment.amount), 0).label("total"),
        )
        .join(Order)
        .where(
            Order.outlet_id == current_user.outlet_id,
            Payment.status == "completed",
        )
        .group_by(Payment.payment_method)
        .order_by(func.sum(Payment.amount).desc())
    )
    if date_from:
        query = query.where(cast(Payment.created_at, Date) >= date_from)
    if date_to:
        query = query.where(cast(Payment.created_at, Date) <= date_to)

    result = await db.execute(query)
    return [
        {"payment_method": r.payment_method, "count": r.count, "total": float(r.total)}
        for r in result.all()
    ]


@router.get("/inventory")
async def inventory_report(
    db: AsyncSession = Depends(get_db),
    current_user: Staff = Depends(require_roles("admin", "owner", "manager")),
):
    result = await db.execute(
        select(InventoryItem)
        .where(InventoryItem.outlet_id == current_user.outlet_id, InventoryItem.is_active == True)
        .order_by(InventoryItem.name)
    )
    items = result.scalars().all()
    return [
        {
            "name": i.name,
            "sku": i.sku,
            "unit": i.unit,
            "quantity": float(i.quantity),
            "min_quantity": float(i.min_quantity),
            "cost_per_unit": float(i.cost_per_unit) if i.cost_per_unit else None,
            "total_value": float(i.quantity) * float(i.cost_per_unit) if i.cost_per_unit else None,
            "is_low_stock": float(i.quantity) <= float(i.min_quantity),
        }
        for i in items
    ]


@router.get("/waste")
async def waste_report(
    date_from: date = Query(default=None),
    date_to: date = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: Staff = Depends(require_roles("admin", "owner", "manager")),
):
    query = (
        select(
            InventoryItem.name,
            func.sum(func.abs(InventoryTransaction.quantity_change)).label("total_waste"),
            InventoryItem.unit,
            InventoryItem.cost_per_unit,
        )
        .join(InventoryItem)
        .where(
            InventoryItem.outlet_id == current_user.outlet_id,
            InventoryTransaction.transaction_type == "waste",
        )
        .group_by(InventoryItem.name, InventoryItem.unit, InventoryItem.cost_per_unit)
        .order_by(func.sum(func.abs(InventoryTransaction.quantity_change)).desc())
    )
    if date_from:
        query = query.where(cast(InventoryTransaction.created_at, Date) >= date_from)
    if date_to:
        query = query.where(cast(InventoryTransaction.created_at, Date) <= date_to)

    result = await db.execute(query)
    return [
        {
            "item_name": r.name,
            "total_waste": float(r.total_waste),
            "unit": r.unit,
            "estimated_cost": float(r.total_waste) * float(r.cost_per_unit) if r.cost_per_unit else None,
        }
        for r in result.all()
    ]


@router.get("/profit-margin")
async def profit_margin(
    date_from: date = Query(default=None),
    date_to: date = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: Staff = Depends(require_roles("admin", "owner", "manager")),
):
    query = (
        select(
            MenuItem.name,
            MenuItem.price,
            MenuItem.cost_price,
            func.sum(OrderItem.quantity).label("total_qty"),
            func.sum(OrderItem.subtotal).label("total_revenue"),
        )
        .join(OrderItem, MenuItem.id == OrderItem.menu_item_id)
        .join(Order, OrderItem.order_id == Order.id)
        .where(
            Order.outlet_id == current_user.outlet_id,
            Order.is_void == False,
            OrderItem.is_void == False,
            MenuItem.cost_price.isnot(None),
        )
        .group_by(MenuItem.name, MenuItem.price, MenuItem.cost_price)
        .order_by(func.sum(OrderItem.subtotal).desc())
    )
    if date_from:
        query = query.where(cast(Order.created_at, Date) >= date_from)
    if date_to:
        query = query.where(cast(Order.created_at, Date) <= date_to)

    result = await db.execute(query)
    return [
        {
            "item_name": r.name,
            "price": float(r.price),
            "cost_price": float(r.cost_price),
            "margin": float(r.price) - float(r.cost_price),
            "margin_pct": round((float(r.price) - float(r.cost_price)) / float(r.price) * 100, 1) if float(r.price) > 0 else 0,
            "total_qty": int(r.total_qty),
            "total_revenue": float(r.total_revenue),
            "total_cost": int(r.total_qty) * float(r.cost_price),
            "total_profit": float(r.total_revenue) - int(r.total_qty) * float(r.cost_price),
        }
        for r in result.all()
    ]


@router.get("/peak-hours")
async def peak_hours(
    date_from: date = Query(default=None),
    date_to: date = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: Staff = Depends(require_roles("admin", "owner", "manager")),
):
    from sqlalchemy import extract

    query = (
        select(
            extract("dow", Order.created_at).label("day_of_week"),
            extract("hour", Order.created_at).label("hour"),
            func.count(Order.id).label("order_count"),
            func.coalesce(func.sum(Order.total), 0).label("total_sales"),
        )
        .where(
            Order.outlet_id == current_user.outlet_id,
            Order.is_void == False,
        )
        .group_by(
            extract("dow", Order.created_at),
            extract("hour", Order.created_at),
        )
        .order_by(func.count(Order.id).desc())
    )
    if date_from:
        query = query.where(cast(Order.created_at, Date) >= date_from)
    if date_to:
        query = query.where(cast(Order.created_at, Date) <= date_to)

    result = await db.execute(query)
    day_names = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
    return [
        {
            "day_of_week": day_names[int(r.day_of_week)],
            "hour": int(r.hour),
            "order_count": r.order_count,
            "total_sales": float(r.total_sales),
        }
        for r in result.all()
    ]


@router.get("/export")
async def export_report(
    type: str = Query(...),
    date_from: date = Query(default=None, alias="from"),
    date_to: date = Query(default=None, alias="to"),
    format: str = Query(default="csv"),
    db: AsyncSession = Depends(get_db),
    current_user: Staff = Depends(require_roles("admin", "owner", "manager")),
):
    import csv
    import io as sio

    # Get the data based on report type
    report_funcs = {
        "daily_sales": daily_sales,
        "sales_by_item": sales_by_item,
        "sales_by_staff": sales_by_staff,
        "payment_methods": payment_methods_report,
    }

    func_to_call = report_funcs.get(type)
    if func_to_call is None:
        return {"error": f"Unknown report type: {type}"}

    data = await func_to_call(date_from=date_from, date_to=date_to, db=db, current_user=current_user)

    if format == "csv" and data:
        output = sio.StringIO()
        writer = csv.DictWriter(output, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)
        csv_content = output.getvalue()

        return StreamingResponse(
            iter([csv_content]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={type}_report.csv"},
        )

    return data
