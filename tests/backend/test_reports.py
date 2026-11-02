"""
Tests for report endpoints and their global filter support.
"""
import pytest


class TestReportFilters:
    """Report endpoints must honor the global filter bar, like /api/orders."""

    @pytest.mark.parametrize("path", ["/api/reports/quarterly", "/api/reports/monthly-trends"])
    def test_unfiltered_request_succeeds(self, client, path):
        response = client.get(path)
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    @pytest.mark.parametrize("path", ["/api/reports/quarterly", "/api/reports/monthly-trends"])
    def test_all_values_are_ignored(self, client, path):
        """'all' means no filter, so it must match the unfiltered result."""
        unfiltered = client.get(path).json()
        filtered = client.get(path, params={
            "warehouse": "all", "category": "all", "status": "all", "month": "all"
        }).json()
        assert filtered == unfiltered

    @pytest.mark.parametrize("path", ["/api/reports/quarterly", "/api/reports/monthly-trends"])
    def test_warehouse_filter_reduces_totals(self, client, path):
        unfiltered = client.get(path).json()
        filtered = client.get(path, params={"warehouse": "Tokyo"}).json()

        def total_orders(rows):
            key = "total_orders" if "total_orders" in (rows[0] if rows else {}) else "order_count"
            return sum(row[key] for row in rows)

        assert total_orders(filtered) <= total_orders(unfiltered)

    def test_month_filter_returns_only_that_month(self, client):
        rows = client.get("/api/reports/monthly-trends", params={"month": "2025-01"}).json()
        assert all(row["month"] == "2025-01" for row in rows)

    def test_quarter_filter_returns_only_that_quarter(self, client):
        rows = client.get("/api/reports/quarterly", params={"month": "Q1-2025"}).json()
        assert all(row["quarter"] == "Q1-2025" for row in rows)

    def test_status_filter_matches_delivered_only(self, client):
        """With status=Delivered every order counted must be delivered, so fulfillment is 100%."""
        rows = client.get("/api/reports/quarterly", params={"status": "Delivered"}).json()
        assert rows, "expected delivered orders in mock data"
        assert all(row["fulfillment_rate"] == 100.0 for row in rows)
