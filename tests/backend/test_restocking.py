"""
Tests for restocking API endpoints.
"""
import pytest


class TestRestockingRecommendations:
    """Test suite for GET /api/restocking/recommendations."""

    def test_returns_recommendations_within_budget(self, client):
        """Total cost never exceeds the budget and remaining budget adds up."""
        response = client.get("/api/restocking/recommendations", params={"budget": 5000})
        assert response.status_code == 200

        data = response.json()
        assert data["budget"] == 5000
        assert data["total_cost"] <= data["budget"]
        assert data["remaining_budget"] == pytest.approx(data["budget"] - data["total_cost"], abs=0.01)
        assert isinstance(data["lead_time_days"], int)

    def test_units_equal_forecast_minus_stock(self, client):
        """Each recommended item orders only the shortfall, and cost matches units x unit_cost."""
        response = client.get("/api/restocking/recommendations", params={"budget": 100000})
        data = response.json()
        assert len(data["items"]) > 0

        for item in data["items"]:
            assert item["units"] > 0
            assert item["units"] == item["forecasted_demand"] - item["current_stock"]
            assert item["total_cost"] == pytest.approx(item["units"] * item["unit_cost"], abs=0.01)

    def test_zero_budget_recommends_nothing(self, client):
        """A zero budget cannot afford any item, so the list is empty."""
        response = client.get("/api/restocking/recommendations", params={"budget": 0})
        assert response.status_code == 200
        assert response.json()["items"] == []

    def test_negative_budget_rejected(self, client):
        """Negative budgets fail validation rather than producing nonsense results."""
        response = client.get("/api/restocking/recommendations", params={"budget": -1})
        assert response.status_code == 422

    def test_missing_budget_rejected(self, client):
        """Budget is required."""
        response = client.get("/api/restocking/recommendations")
        assert response.status_code == 422


class TestCreateRestockingOrder:
    """Test suite for POST /api/restocking/orders."""

    def test_creates_submitted_order_with_server_prices(self, client):
        """Order is created as Submitted, priced from inventory, and has a lead time."""
        response = client.post("/api/restocking/orders", json={
            "items": [{"sku": "PSU-501", "quantity": 10}]
        })
        assert response.status_code == 201

        order = response.json()
        assert order["status"] == "Submitted"
        assert order["customer"] == "Internal Restocking"
        assert order["items"][0]["sku"] == "PSU-501"
        assert order["items"][0]["quantity"] == 10
        assert order["total_value"] == pytest.approx(10 * order["items"][0]["unit_price"], abs=0.01)
        assert isinstance(order["lead_time_days"], int)
        assert order["lead_time_days"] > 0

    def test_submitted_order_appears_in_orders_list(self, client):
        """A submitted order is visible through the existing orders endpoint."""
        created = client.post("/api/restocking/orders", json={
            "items": [{"sku": "PSU-501", "quantity": 3}]
        }).json()

        response = client.get("/api/orders", params={"status": "Submitted"})
        assert response.status_code == 200
        assert created["id"] in [o["id"] for o in response.json()]

    def test_unknown_sku_rejected(self, client):
        """SKUs that are not in inventory are rejected with 400."""
        response = client.post("/api/restocking/orders", json={
            "items": [{"sku": "NOPE-000", "quantity": 1}]
        })
        assert response.status_code == 400

    def test_zero_quantity_rejected(self, client):
        """Quantities must be greater than zero."""
        response = client.post("/api/restocking/orders", json={
            "items": [{"sku": "PSU-501", "quantity": 0}]
        })
        assert response.status_code == 422

    def test_empty_items_rejected(self, client):
        """An order needs at least one line item."""
        response = client.post("/api/restocking/orders", json={"items": []})
        assert response.status_code == 422
