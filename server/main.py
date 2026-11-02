from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
from mock_data import inventory_items, orders, demand_forecasts, backlog_items, spending_summary, monthly_spending, category_spending, recent_transactions, purchase_orders

app = FastAPI(title="Factory Inventory Management System")

# Quarter mapping for date filtering
QUARTER_MAP = {
    'Q1-2025': ['2025-01', '2025-02', '2025-03'],
    'Q2-2025': ['2025-04', '2025-05', '2025-06'],
    'Q3-2025': ['2025-07', '2025-08', '2025-09'],
    'Q4-2025': ['2025-10', '2025-11', '2025-12']
}

def filter_by_month(items: list, month: Optional[str]) -> list:
    """Filter items by month/quarter based on order_date field"""
    if not month or month == 'all':
        return items

    if month.startswith('Q'):
        # Handle quarters
        if month in QUARTER_MAP:
            months = QUARTER_MAP[month]
            return [item for item in items if any(m in item.get('order_date', '') for m in months)]
    else:
        # Direct month match
        return [item for item in items if month in item.get('order_date', '')]

    return items

def apply_filters(items: list, warehouse: Optional[str] = None, category: Optional[str] = None,
                 status: Optional[str] = None) -> list:
    """Apply common filters to a list of items"""
    filtered = items

    if warehouse and warehouse != 'all':
        filtered = [item for item in filtered if item.get('warehouse') == warehouse]

    if category and category != 'all':
        filtered = [item for item in filtered if item.get('category', '').lower() == category.lower()]

    if status and status != 'all':
        filtered = [item for item in filtered if item.get('status', '').lower() == status.lower()]

    return filtered

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Data models
class InventoryItem(BaseModel):
    id: str
    sku: str
    name: str
    category: str
    warehouse: str
    quantity_on_hand: int
    reorder_point: int
    unit_cost: float
    location: str
    last_updated: str

class Order(BaseModel):
    id: str
    order_number: str
    customer: str
    items: List[dict]
    status: str
    order_date: str
    expected_delivery: str
    total_value: float
    actual_delivery: Optional[str] = None
    warehouse: Optional[str] = None
    category: Optional[str] = None
    # Only set on orders created through /api/restocking/orders
    lead_time_days: Optional[int] = None

class RestockingRecommendation(BaseModel):
    sku: str
    name: str
    current_stock: int
    forecasted_demand: int
    units: int
    unit_cost: float
    total_cost: float

class RestockingRecommendationsResponse(BaseModel):
    budget: float
    total_cost: float
    remaining_budget: float
    lead_time_days: int
    items: List[RestockingRecommendation]

class RestockingOrderItem(BaseModel):
    sku: str
    quantity: int = Field(gt=0)

class CreateRestockingOrderRequest(BaseModel):
    items: List[RestockingOrderItem] = Field(min_length=1)

class DemandForecast(BaseModel):
    id: str
    item_sku: str
    item_name: str
    current_demand: int
    forecasted_demand: int
    trend: str
    period: str

class BacklogItem(BaseModel):
    id: str
    order_id: str
    item_sku: str
    item_name: str
    quantity_needed: int
    quantity_available: int
    days_delayed: int
    priority: str
    has_purchase_order: Optional[bool] = False

class PurchaseOrder(BaseModel):
    id: str
    backlog_item_id: str
    supplier_name: str
    quantity: int
    unit_cost: float
    expected_delivery_date: str
    status: str
    created_date: str
    notes: Optional[str] = None

class CreatePurchaseOrderRequest(BaseModel):
    backlog_item_id: str
    supplier_name: str
    quantity: int
    unit_cost: float
    expected_delivery_date: str
    notes: Optional[str] = None

# API endpoints
@app.get("/")
def root():
    return {"message": "Factory Inventory Management System API", "version": "1.0.0"}

@app.get("/api/inventory", response_model=List[InventoryItem])
def get_inventory(
    warehouse: Optional[str] = None,
    category: Optional[str] = None
):
    """Get all inventory items with optional filtering"""
    return apply_filters(inventory_items, warehouse, category)

@app.get("/api/inventory/{item_id}", response_model=InventoryItem)
def get_inventory_item(item_id: str):
    """Get a specific inventory item"""
    item = next((item for item in inventory_items if item["id"] == item_id), None)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item

@app.get("/api/orders", response_model=List[Order])
def get_orders(
    warehouse: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
    month: Optional[str] = None
):
    """Get all orders with optional filtering"""
    filtered_orders = apply_filters(orders, warehouse, category, status)
    filtered_orders = filter_by_month(filtered_orders, month)
    return filtered_orders

@app.get("/api/orders/{order_id}", response_model=Order)
def get_order(order_id: str):
    """Get a specific order"""
    order = next((order for order in orders if order["id"] == order_id), None)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order

@app.get("/api/demand", response_model=List[DemandForecast])
def get_demand_forecasts():
    """Get demand forecasts"""
    return demand_forecasts

@app.get("/api/backlog", response_model=List[BacklogItem])
def get_backlog():
    """Get backlog items with purchase order status"""
    # Add has_purchase_order flag to each backlog item
    result = []
    for item in backlog_items:
        item_dict = dict(item)
        # Check if this backlog item has a purchase order
        has_po = any(po["backlog_item_id"] == item["id"] for po in purchase_orders)
        item_dict["has_purchase_order"] = has_po
        result.append(item_dict)
    return result

@app.get("/api/dashboard/summary")
def get_dashboard_summary(
    warehouse: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
    month: Optional[str] = None
):
    """Get summary statistics for dashboard with optional filtering"""
    # Filter inventory
    filtered_inventory = apply_filters(inventory_items, warehouse, category)

    # Filter orders
    filtered_orders = apply_filters(orders, warehouse, category, status)
    filtered_orders = filter_by_month(filtered_orders, month)

    total_inventory_value = sum(item["quantity_on_hand"] * item["unit_cost"] for item in filtered_inventory)
    low_stock_items = len([item for item in filtered_inventory if item["quantity_on_hand"] <= item["reorder_point"]])
    pending_orders = len([order for order in filtered_orders if order["status"] in ["Processing", "Backordered"]])
    total_backlog_items = len(backlog_items)

    return {
        "total_inventory_value": round(total_inventory_value, 2),
        "low_stock_items": low_stock_items,
        "pending_orders": pending_orders,
        "total_backlog_items": total_backlog_items,
        "total_orders_value": sum(order["total_value"] for order in filtered_orders)
    }

@app.get("/api/spending/summary")
def get_spending_summary():
    """Get spending summary statistics"""
    return spending_summary

@app.get("/api/spending/monthly")
def get_monthly_spending():
    """Get monthly spending breakdown"""
    return monthly_spending

@app.get("/api/spending/categories")
def get_category_spending():
    """Get spending by category"""
    return category_spending

@app.get("/api/spending/transactions")
def get_recent_transactions():
    """Get recent transactions"""
    return recent_transactions

@app.get("/api/reports/quarterly")
def get_quarterly_reports(
    warehouse: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
    month: Optional[str] = None
):
    """Get quarterly performance reports, honoring the global filter bar"""
    # Calculate quarterly statistics from orders
    quarters = {}

    # Filter first so the quarter buckets only contain matching orders
    filtered = apply_filters(orders, warehouse, category, status)
    filtered = filter_by_month(filtered, month)

    for order in filtered:
        order_date = order.get('order_date', '')
        # Determine quarter
        if '2025-01' in order_date or '2025-02' in order_date or '2025-03' in order_date:
            quarter = 'Q1-2025'
        elif '2025-04' in order_date or '2025-05' in order_date or '2025-06' in order_date:
            quarter = 'Q2-2025'
        elif '2025-07' in order_date or '2025-08' in order_date or '2025-09' in order_date:
            quarter = 'Q3-2025'
        elif '2025-10' in order_date or '2025-11' in order_date or '2025-12' in order_date:
            quarter = 'Q4-2025'
        else:
            continue

        if quarter not in quarters:
            quarters[quarter] = {
                'quarter': quarter,
                'total_orders': 0,
                'total_revenue': 0,
                'delivered_orders': 0,
                'avg_order_value': 0
            }

        quarters[quarter]['total_orders'] += 1
        quarters[quarter]['total_revenue'] += order.get('total_value', 0)
        if order.get('status') == 'Delivered':
            quarters[quarter]['delivered_orders'] += 1

    # Calculate averages and fulfillment rate
    result = []
    for q, data in quarters.items():
        if data['total_orders'] > 0:
            data['avg_order_value'] = round(data['total_revenue'] / data['total_orders'], 2)
            data['fulfillment_rate'] = round((data['delivered_orders'] / data['total_orders']) * 100, 1)
        result.append(data)

    # Sort by quarter
    result.sort(key=lambda x: x['quarter'])
    return result

@app.get("/api/reports/monthly-trends")
def get_monthly_trends(
    warehouse: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
    month: Optional[str] = None
):
    """Get month-over-month trends, honoring the global filter bar"""
    months = {}

    # Filter first so month buckets only contain matching orders
    filtered = apply_filters(orders, warehouse, category, status)
    filtered = filter_by_month(filtered, month)

    for order in filtered:
        order_date = order.get('order_date', '')
        if not order_date:
            continue

        # Extract month (format: YYYY-MM-DD)
        month = order_date[:7]  # Gets YYYY-MM

        if month not in months:
            months[month] = {
                'month': month,
                'order_count': 0,
                'revenue': 0,
                'delivered_count': 0
            }

        months[month]['order_count'] += 1
        months[month]['revenue'] += order.get('total_value', 0)
        if order.get('status') == 'Delivered':
            months[month]['delivered_count'] += 1

    # Convert to list and sort
    result = list(months.values())
    result.sort(key=lambda x: x['month'])
    return result

def average_lead_time_days() -> int:
    """Average delivery lead time, in whole days, across historical orders.

    Lead time is expected_delivery - order_date. Orders with missing or
    unparseable dates are skipped so one bad record cannot break restocking.
    Falls back to 14 days if no usable history exists.
    """
    durations = []
    for order in orders:
        try:
            ordered = datetime.fromisoformat(order["order_date"])
            expected = datetime.fromisoformat(order["expected_delivery"])
        except (KeyError, TypeError, ValueError):
            continue
        durations.append((expected - ordered).total_seconds() / 86400)

    if not durations:
        return 14
    # Round to nearest day so every order shows a whole-day lead time
    return round(sum(durations) / len(durations))

def find_inventory_by_sku(sku: str) -> Optional[dict]:
    """Return the first inventory row for a SKU, or None."""
    return next((item for item in inventory_items if item["sku"] == sku), None)

@app.get("/api/restocking/recommendations", response_model=RestockingRecommendationsResponse)
def get_restocking_recommendations(budget: float = Query(ge=0)):
    """Recommend forecast items to restock that fit within the budget.

    Units per item = forecasted_demand - current stock (floored at 0), so only
    the shortfall is ordered. Items are taken in order of largest shortfall
    first. Greedy selection: an item is skipped if it would exceed the
    remaining budget, but later, cheaper items can still be added.
    """
    candidates = []
    for forecast in demand_forecasts:
        inventory = find_inventory_by_sku(forecast["item_sku"])
        if not inventory:
            # Forecast has no matching inventory row, so no cost is known
            continue

        # Stock is summed across warehouses; cost comes from the first row
        current_stock = sum(
            item["quantity_on_hand"] for item in inventory_items
            if item["sku"] == forecast["item_sku"]
        )
        units = max(0, forecast["forecasted_demand"] - current_stock)
        if units == 0:
            continue

        candidates.append({
            "sku": forecast["item_sku"],
            "name": forecast["item_name"],
            "current_stock": current_stock,
            "forecasted_demand": forecast["forecasted_demand"],
            "units": units,
            "unit_cost": inventory["unit_cost"],
        })

    candidates.sort(key=lambda c: c["units"], reverse=True)

    selected = []
    spent = 0.0
    for candidate in candidates:
        cost = round(candidate["units"] * candidate["unit_cost"], 2)
        if spent + cost > budget:
            continue
        spent += cost
        selected.append(RestockingRecommendation(**candidate, total_cost=cost))

    total = round(spent, 2)
    return RestockingRecommendationsResponse(
        budget=budget,
        total_cost=total,
        remaining_budget=round(budget - total, 2),
        lead_time_days=average_lead_time_days(),
        items=selected,
    )

@app.post("/api/restocking/orders", response_model=Order, status_code=201)
def create_restocking_order(request: CreateRestockingOrderRequest):
    """Submit a restocking order and add it to the in-memory orders list.

    Prices come from the server's inventory unit_cost, never from the client,
    so the total cannot be tampered with. The order is kept in memory only and
    resets when the server restarts, like the other mock data.
    """
    line_items = []
    for requested in request.items:
        inventory = find_inventory_by_sku(requested.sku)
        if not inventory:
            raise HTTPException(status_code=400, detail=f"Unknown SKU {requested.sku}")
        line_items.append({
            "sku": requested.sku,
            "name": inventory["name"],
            "quantity": requested.quantity,
            "unit_price": inventory["unit_cost"],
        })

    lead_time = average_lead_time_days()
    order_date = datetime.now().replace(microsecond=0)
    expected = order_date + timedelta(days=lead_time)
    next_id = max((int(o["id"]) for o in orders), default=0) + 1

    new_order = {
        "id": str(next_id),
        "order_number": f"RST-{order_date.year}-{next_id:04d}",
        "customer": "Internal Restocking",
        "items": line_items,
        "status": "Submitted",
        "warehouse": None,
        "category": None,
        "order_date": order_date.isoformat(),
        "expected_delivery": expected.isoformat(),
        "total_value": round(sum(i["quantity"] * i["unit_price"] for i in line_items), 2),
        "actual_delivery": None,
        "lead_time_days": lead_time,
    }
    orders.append(new_order)
    return new_order

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
