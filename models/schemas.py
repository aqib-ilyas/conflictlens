"""
Pydantic models for VIEWS API request/response schemas.
"""

from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from enum import Enum


class MetricType(str, Enum):
    """Available metric types."""
    MAP = "map"
    HDI_50 = "hdi_50"
    HDI_90 = "hdi_90"
    HDI_99 = "hdi_99"
    THRESHOLD_1 = "threshold_1"
    THRESHOLD_2 = "threshold_2"
    THRESHOLD_3 = "threshold_3"
    THRESHOLD_4 = "threshold_4"
    THRESHOLD_5 = "threshold_5"
    THRESHOLD_6 = "threshold_6"


class ConflictType(str, Enum):
    """Types of conflict violence."""
    STATE_BASED = "sb"  # State-based violence
    NON_STATE = "ns"    # Non-state violence
    ONE_SIDED = "os"    # One-sided violence


class MetricSelection(BaseModel):
    """Metric selection for forecast queries."""
    include_map: bool = Field(True, description="Include MAP (mean) values")
    include_hdi_50: bool = Field(False, description="Include 50% HDI bounds")
    include_hdi_90: bool = Field(True, description="Include 90% HDI bounds")
    include_hdi_99: bool = Field(False, description="Include 99% HDI bounds")
    include_thresholds: bool = Field(True, description="Include threshold probabilities")
    conflict_types: List[ConflictType] = Field(
        default=[ConflictType.STATE_BASED],
        description="Types of violence to include"
    )


class GridCellData(BaseModel):
    """Data for a single grid cell at a specific month."""
    grid_id: int = Field(..., description="PRIO Grid ID")
    month_id: int = Field(..., description="Month identifier")
    country_id: Optional[int] = Field(None, description="UN M49 country code")
    latitude: Optional[float] = Field(None, description="Grid cell centroid latitude")
    longitude: Optional[float] = Field(None, description="Grid cell centroid longitude")
    
    # Main predictions
    main_mean: Optional[float] = Field(None, description="Point prediction (MAP)")
    main_mean_ln: Optional[float] = Field(None, description="Log-transformed prediction")
    main_dich: Optional[float] = Field(None, description="Binary threshold probability")
    
    # HDI bounds (90% available, others synthetic for demo)
    hdi_50_lower: Optional[float] = Field(None, description="50% HDI lower bound")
    hdi_50_upper: Optional[float] = Field(None, description="50% HDI upper bound")
    hdi_90_lower: Optional[float] = Field(None, description="90% HDI lower bound")
    hdi_90_upper: Optional[float] = Field(None, description="90% HDI upper bound")
    hdi_99_lower: Optional[float] = Field(None, description="99% HDI lower bound")
    hdi_99_upper: Optional[float] = Field(None, description="99% HDI upper bound")
    
    # Threshold probabilities (1 real, others synthetic for demo)
    threshold_1: Optional[float] = Field(None, description="Probability > threshold 1")
    threshold_2: Optional[float] = Field(None, description="Probability > threshold 2")
    threshold_3: Optional[float] = Field(None, description="Probability > threshold 3")
    threshold_4: Optional[float] = Field(None, description="Probability > threshold 4")
    threshold_5: Optional[float] = Field(None, description="Probability > threshold 5")
    threshold_6: Optional[float] = Field(None, description="Probability > threshold 6")
    
    # Conflict type specific data
    conflict_type: Optional[ConflictType] = Field(None, description="Type of violence")
    
    # Additional metadata
    country_name: Optional[str] = Field(None, description="Country name")
    year: Optional[int] = Field(None, description="Year")
    month: Optional[int] = Field(None, description="Month (1-12)")

    @validator('latitude')
    def validate_latitude(cls, v):
        if v is not None and not -90 <= v <= 90:
            raise ValueError('Latitude must be between -90 and 90')
        return v

    @validator('longitude')
    def validate_longitude(cls, v):
        if v is not None and not -180 <= v <= 180:
            raise ValueError('Longitude must be between -180 and 180')
        return v


class ForecastResponse(BaseModel):
    """Response model for forecast queries."""
    data: List[GridCellData] = Field(..., description="Forecast data for grid cells")
    total_cells: int = Field(..., description="Number of grid cells returned")
    months_covered: int = Field(..., description="Number of months covered")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class BasicInfoResponse(BaseModel):
    """Response model for basic API information."""
    available_months: List[int] = Field(..., description="List of available month IDs")
    total_grid_cells: int = Field(..., description="Total number of grid cells")
    countries_available: int = Field(..., description="Number of countries with data")
    date_range: Dict[str, str] = Field(..., description="Date range of forecasts")
    api_version: str = Field(..., description="API version")
    data_version: Optional[str] = Field(None, description="Data version identifier")


class CountryInfo(BaseModel):
    """Country information model."""
    country_id: int = Field(..., description="UN M49 country code")
    country_name: str = Field(..., description="Country name")
    iso_code: Optional[str] = Field(None, description="ISO country code")
    grid_cells_count: int = Field(..., description="Number of grid cells in country")


class ErrorResponse(BaseModel):
    """Error response model."""
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")


class HealthCheckResponse(BaseModel):
    """Health check response model."""
    status: str = Field(..., description="Service status")
    timestamp: str = Field(..., description="Check timestamp")
    version: str = Field(..., description="API version")
    data_status: str = Field(..., description="Data loading status")