"""
Test suite for VIEWS Conflict Forecasting API
"""

import pytest
import pandas as pd
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
import numpy as np

from main import app
from services.data_service import DataService
from services.forecast_service import ForecastService
from models.schemas import MetricSelection, ConflictType
from utils.exceptions import DataNotFoundError, ValidationError


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_data_service():
    """Create mock data service with sample data."""
    service = Mock(spec=DataService)
    
    # Mock data
    service.get_available_months.return_value = [548, 549, 550]
    service.get_available_countries.return_value = [
        {'country_id': 1, 'country': 'Testland', 'isoab': 'TST'}
    ]
    service.get_total_grid_cells.return_value = 100
    
    # Sample grid data
    sample_data = pd.DataFrame({
        'pg_id': [62356, 62357, 62358],
        'month_id': [548, 548, 548],
        'main_mean': [0.001, 0.002, 0.003],
        'main_mean_ln': [0.001, 0.002, 0.003],
        'main_dich': [0.01, 0.02, 0.03],
        'country_id': [1, 1, 1]
    })
    service.get_grid_data.return_value = sample_data
    service.get_month_data.return_value = sample_data
    
    service.get_country_grids.return_value = [62356, 62357, 62358]
    
    # HDI data
    hdi_data = pd.DataFrame({
        'priogrid_id': [62356, 62357, 62358],
        'month_id': [548, 548, 548],
        'pred_ln_sb_prob_hdi_lower': [0.005, 0.010, 0.015],
        'pred_ln_sb_prob_hdi_upper': [0.015, 0.025, 0.035]
    })
    service.get_hdi_data.return_value = hdi_data
    
    # Coordinates
    coord_data = pd.DataFrame({
        'priogrid_id': [62356, 62357, 62358],
        'latitude': [45.0, 46.0, 47.0],
        'longitude': [12.0, 13.0, 14.0]
    })
    service.get_coordinates.return_value = coord_data
    
    service.is_loaded = True
    
    return service


@pytest.fixture
def forecast_service(mock_data_service):
    """Create forecast service with mock data service."""
    return ForecastService(mock_data_service)


class TestAPI:
    """Test API endpoints."""
    
    @patch('main.data_service')
    def test_get_basic_info(self, mock_service, client):
        """Test basic info endpoint."""
        mock_service.get_available_months.return_value = [548, 549, 550]
        mock_service.get_available_countries.return_value = [
            {'country_id': 1, 'country': 'Testland', 'isoab': 'TST'}
        ]
        mock_service.get_total_grid_cells.return_value = 100
        
        response = client.get("/api/info")
        assert response.status_code == 200
        
        data = response.json()
        assert "available_months" in data
        assert "total_grid_cells" in data
        assert data["total_grid_cells"] == 100
    
    @patch('main.forecast_service')
    def test_get_forecasts_by_country(self, mock_service, client):
        """Test country forecast endpoint."""
        mock_service.get_forecasts_by_country.return_value = []
        
        response = client.get("/api/forecasts/country/1")
        assert response.status_code == 200
        
        data = response.json()
        assert "data" in data
        assert "total_cells" in data
    
    @patch('main.forecast_service')
    def test_get_forecasts_by_grid(self, mock_service, client):
        """Test grid forecast endpoint."""
        mock_service.get_forecasts_by_grid.return_value = []
        
        response = client.get("/api/forecasts/grid?grid_ids=62356&grid_ids=62357")
        assert response.status_code == 200
    
    def test_get_forecasts_by_grid_missing_params(self, client):
        """Test grid endpoint with missing parameters."""
        response = client.get("/api/forecasts/grid")
        assert response.status_code == 422  # Validation error
    
    @patch('main.forecast_service')
    def test_get_countries(self, mock_service, client):
        """Test countries endpoint."""
        mock_service.get_countries.return_value = [
            {'country_id': 1, 'country': 'Testland', 'grid_cells_count': 10}
        ]
        
        response = client.get("/api/countries")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)


class TestDataService:
    """Test data service functionality."""
    
    def test_initialization(self):
        """Test data service initialization."""
        service = DataService()
        assert service.pgm_data is None
        assert service.is_loaded is False
    
    def test_load_data_creates_synthetic(self):
        """Test that load_data creates synthetic data when files don't exist."""
        service = DataService()
        service.load_data()
        
        assert service.is_loaded is True
        assert service.pgm_data is not None
        assert len(service.pgm_data) > 0
    
    def test_get_available_months(self):
        """Test getting available months."""
        service = DataService()
        service.load_data()
        
        months = service.get_available_months()
        assert isinstance(months, list)
        assert len(months) > 0
        assert all(isinstance(m, int) for m in months)
    
    def test_get_country_grids(self):
        """Test getting grid IDs for a country."""
        service = DataService()
        service.load_data()
        
        grid_ids = service.get_country_grids(1)
        assert isinstance(grid_ids, list)
        assert len(grid_ids) > 0
    
    def test_get_country_grids_not_found(self):
        """Test getting grids for non-existent country."""
        service = DataService()
        service.load_data()
        
        with pytest.raises(DataNotFoundError):
            service.get_country_grids(999)
    
    def test_get_grid_data(self):
        """Test getting data for specific grids."""
        service = DataService()
        service.load_data()
        
        grid_ids = [62356, 62357]
        data = service.get_grid_data(grid_ids)
        
        assert isinstance(data, pd.DataFrame)
        assert len(data) > 0
        assert all(gid in data['pg_id'].values for gid in grid_ids)
    
    def test_get_grid_data_not_found(self):
        """Test getting data for non-existent grids."""
        service = DataService()
        service.load_data()
        
        with pytest.raises(DataNotFoundError):
            service.get_grid_data([999999])


class TestForecastService:
    """Test forecast service functionality."""
    
    def test_get_basic_info(self, forecast_service):
        """Test getting basic API info."""
        info = forecast_service.get_basic_info()
        
        assert "available_months" in info
        assert "total_grid_cells" in info
        assert "api_version" in info
        assert info["total_grid_cells"] == 100
    
    def test_get_forecasts_by_country(self, forecast_service):
        """Test getting forecasts by country."""
        forecasts = forecast_service.get_forecasts_by_country(
            country_id=1,
            metrics=MetricSelection()
        )
        
        assert isinstance(forecasts, list)
        assert len(forecasts) > 0
        
        # Check first forecast
        forecast = forecasts[0]
        assert forecast.grid_id is not None
        assert forecast.month_id is not None
        assert forecast.country_id == 1
    
    def test_get_forecasts_by_grid(self, forecast_service):
        """Test getting forecasts by grid IDs."""
        forecasts = forecast_service.get_forecasts_by_grid(
            grid_ids=[62356, 62357],
            metrics=MetricSelection()
        )
        
        assert isinstance(forecasts, list)
        assert len(forecasts) > 0
    
    def test_metric_selection(self, forecast_service):
        """Test metric selection functionality."""
        metrics = MetricSelection(
            include_map=True,
            include_hdi_90=False,
            include_thresholds=True
        )
        
        forecasts = forecast_service.get_forecasts_by_country(
            country_id=1,
            metrics=metrics
        )
        
        forecast = forecasts[0]
        assert forecast.main_mean is not None  # MAP included
        assert forecast.hdi_90_lower is None   # HDI not included
        assert forecast.threshold_1 is not None  # Thresholds included
    
    def test_synthetic_metrics_generation(self, forecast_service):
        """Test that synthetic metrics are generated properly."""
        forecasts = forecast_service.get_forecasts_by_country(
            country_id=1,
            metrics=MetricSelection(include_hdi_50=True, include_hdi_99=True)
        )
        
        forecast = forecasts[0]
        
        # Check that synthetic HDI bounds are reasonable
        if forecast.hdi_50_lower and forecast.hdi_50_upper:
            assert forecast.hdi_50_lower < forecast.hdi_50_upper
            assert 0 <= forecast.hdi_50_lower <= 1
            assert 0 <= forecast.hdi_50_upper <= 1


class TestSchemas:
    """Test Pydantic schemas."""
    
    def test_metric_selection_defaults(self):
        """Test MetricSelection default values."""
        metrics = MetricSelection()
        
        assert metrics.include_map is True
        assert metrics.include_hdi_90 is True
        assert metrics.include_thresholds is True
        assert metrics.include_hdi_50 is False
        assert metrics.include_hdi_99 is False
    
    def test_grid_cell_data_validation(self):
        """Test GridCellData validation."""
        from models.schemas import GridCellData
        
        # Valid data
        data = GridCellData(
            grid_id=62356,
            month_id=548,
            latitude=45.0,
            longitude=12.0
        )
        assert data.grid_id == 62356
        assert data.latitude == 45.0
    
    def test_grid_cell_data_invalid_coordinates(self):
        """Test GridCellData with invalid coordinates."""
        from models.schemas import GridCellData
        
        with pytest.raises(ValueError):
            GridCellData(
                grid_id=62356,
                month_id=548,
                latitude=95.0  # Invalid latitude
            )


class TestUtilities:
    """Test utility functions."""
    
    def test_exceptions_inheritance(self):
        """Test that custom exceptions inherit properly."""
        from utils.exceptions import DataNotFoundError, ValidationError, ViewsAPIError
        
        assert issubclass(DataNotFoundError, ViewsAPIError)
        assert issubclass(ValidationError, ViewsAPIError)
    
    def test_data_not_found_error(self):
        """Test DataNotFoundError functionality."""
        error = DataNotFoundError("Test message")
        assert str(error) == "Test message"


class TestIntegration:
    """Integration tests."""
    
    def test_full_workflow(self, client):
        """Test complete API workflow."""
        # Test API info
        response = client.get("/api/info")
        assert response.status_code == 200
        
        # Test countries
        response = client.get("/api/countries")
        assert response.status_code == 200
        
        # Note: Full integration tests would require actual data files
        # This demonstrates the test structure for when real data is available


# Pytest configuration and fixtures for Windows compatibility
if __name__ == "__main__":
    pytest.main([__file__, "-v"])