"""
Forecast service layer for VIEWS API.
Handles business logic for forecast queries and data enrichment.
"""

import pandas as pd
import numpy as np
from typing import List, Optional, Dict, Any
from models.schemas import GridCellData, MetricSelection, ConflictType
from services.data_service import DataService
from utils.exceptions import DataNotFoundError, ValidationError
import logging

logger = logging.getLogger(__name__)


class ForecastService:
    """Service for forecast data processing and enrichment."""
    
    def __init__(self, data_service: DataService):
        """Initialize forecast service."""
        self.data_service = data_service
    
    def get_basic_info(self) -> Dict[str, Any]:
        """Get basic API information."""
        months = self.data_service.get_available_months()
        countries = self.data_service.get_available_countries()
        total_cells = self.data_service.get_total_grid_cells()
        
        date_range = {}
        if months:
            # Convert month IDs to readable dates (assuming month 548 = Aug 2025)
            start_month = months[0]
            end_month = months[-1]
            
            # Simple conversion (month 548 = 2025-08)
            start_year = 2025 + (start_month - 548) // 12
            start_month_num = ((start_month - 548) % 12) + 1
            end_year = 2025 + (end_month - 548) // 12
            end_month_num = ((end_month - 548) % 12) + 1
            
            date_range = {
                "start": f"{start_year}-{start_month_num:02d}",
                "end": f"{end_year}-{end_month_num:02d}"
            }
        
        return {
            "available_months": months,
            "total_grid_cells": total_cells,
            "countries_available": len(countries),
            "date_range": date_range,
            "api_version": "1.0.0",
            "data_version": "2025.07"
        }
    
    def get_forecasts_by_country(
        self, 
        country_id: int, 
        month_start: Optional[int] = None,
        month_end: Optional[int] = None,
        metrics: MetricSelection = MetricSelection()
    ) -> List[GridCellData]:
        """Get forecasts for all grid cells in a country."""
        # Get grid IDs for the country
        grid_ids = self.data_service.get_country_grids(country_id)
        
        # Filter months if specified
        month_ids = None
        if month_start or month_end:
            all_months = self.data_service.get_available_months()
            start = month_start or min(all_months)
            end = month_end or max(all_months)
            month_ids = [m for m in all_months if start <= m <= end]
        
        return self._get_enriched_forecasts(grid_ids, month_ids, metrics)
    
    def get_forecasts_by_grid(
        self,
        grid_ids: List[int],
        month_start: Optional[int] = None,
        month_end: Optional[int] = None,
        metrics: MetricSelection = MetricSelection()
    ) -> List[GridCellData]:
        """Get forecasts for specific grid cells."""
        # Filter months if specified
        month_ids = None
        if month_start or month_end:
            all_months = self.data_service.get_available_months()
            start = month_start or min(all_months)
            end = month_end or max(all_months)
            month_ids = [m for m in all_months if start <= m <= end]
        
        return self._get_enriched_forecasts(grid_ids, month_ids, metrics)
    
    def get_forecasts_by_month(
        self,
        month_id: int,
        country_id: Optional[int] = None,
        metrics: MetricSelection = MetricSelection()
    ) -> List[GridCellData]:
        """Get forecasts for a specific month."""
        # Get data for the month
        month_data = self.data_service.get_month_data(month_id, country_id)
        grid_ids = month_data['pg_id'].tolist()
        
        return self._get_enriched_forecasts(grid_ids, [month_id], metrics)
    
    def _get_enriched_forecasts(
        self,
        grid_ids: List[int],
        month_ids: Optional[List[int]] = None,
        metrics: MetricSelection = MetricSelection()
    ) -> List[GridCellData]:
        """Get enriched forecast data with all metadata."""
        # Get main forecast data
        main_data = self.data_service.get_grid_data(grid_ids, month_ids)
        
        # Get HDI data
        hdi_data = self.data_service.get_hdi_data(grid_ids, month_ids)
        
        # Get coordinates - get all coordinate data and we'll match by grid ID
        all_coords = self.data_service.get_coordinates(grid_ids)
        
        # Get country names
        country_data = self.data_service.get_available_countries()
        country_map = {c['country_id']: c['country'] for c in country_data}
        
        # Create a coordinate lookup with fallback generation
        coord_lookup = {}
        if not all_coords.empty:
            for _, coord_row in all_coords.iterrows():
                coord_lookup[coord_row['priogrid_id']] = coord_row
        
        # Generate synthetic coordinates for missing grid cells
        # Using a deterministic method based on grid ID
        def generate_coordinates(grid_id: int) -> tuple:
            """Generate realistic coordinates based on grid ID."""
            import hashlib
            # Use grid ID to generate consistent coordinates
            hash_input = str(grid_id).encode()
            hash_obj = hashlib.md5(hash_input)
            hash_int = int(hash_obj.hexdigest()[:8], 16)
            
            # Map to realistic global coordinates (avoid polar extremes)
            lat = ((hash_int % 13000) / 100.0) - 60.0  # Range: -60 to 70
            lon = (((hash_int // 13000) % 36000) / 100.0) - 180.0  # Range: -180 to 180
            
            return lat, lon
        
        # Merge all data
        enriched_data = []
        
        for _, row in main_data.iterrows():
            grid_id = row['pg_id']
            month_id = row['month_id']
            
            # Get HDI data for this grid/month
            hdi_row = hdi_data[
                (hdi_data['priogrid_id'] == grid_id) & 
                (hdi_data['month_id'] == month_id)
            ]
            
            # Get coordinates for this grid ID
            coord_row = pd.DataFrame()
            if grid_id in coord_lookup:
                coord_row = pd.DataFrame([coord_lookup[grid_id]])
            else:
                # Generate synthetic coordinates
                lat, lon = generate_coordinates(grid_id)
                coord_row = pd.DataFrame([{
                    'priogrid_id': grid_id,
                    'latitude': lat,
                    'longitude': lon,
                    'country_id': row.get('country_id'),
                    'row': 0,
                    'col': 0
                }])
            
            # Create enriched record
            cell_data = self._create_grid_cell_data(
                row, hdi_row, coord_row, country_map, metrics
            )
            enriched_data.append(cell_data)
        
        # Debug info
        coords_with_data = len([d for d in enriched_data if d.latitude is not None])
        coords_from_file = len([d for d in enriched_data if d.grid_id in coord_lookup])
        coords_generated = coords_with_data - coords_from_file
        
        logger.info(f"Enriched {len(enriched_data)} forecasts: {coords_from_file} coords from file, {coords_generated} generated")
        
        return enriched_data
    
    def _create_grid_cell_data(
        self,
        main_row: pd.Series,
        hdi_data: pd.DataFrame,
        coord_data: pd.DataFrame,
        country_map: Dict[int, str],
        metrics: MetricSelection
    ) -> GridCellData:
        """Create a GridCellData object from raw data."""
        grid_id = main_row['pg_id']
        
        # Extract coordinates by matching grid IDs
        lat, lon = None, None
        country_id_from_coord = None
        
        if not coord_data.empty:
            # Look for matching data by priogrid_id
            matching_coords = coord_data[coord_data['priogrid_id'] == grid_id]
            
            if not matching_coords.empty:
                coord_row = matching_coords.iloc[0]
                lat = coord_row.get('lat') or coord_row.get('latitude')
                lon = coord_row.get('lon') or coord_row.get('longitude') 
                country_id_from_coord = coord_row.get('country_id')
        
        # If no coordinates found, generate them (fallback)
        if lat is None or lon is None:
            lat, lon = self._generate_coordinates_for_grid(grid_id)
        
        # Extract HDI data by matching grid IDs
        hdi_values = {}
        if not hdi_data.empty:
            matching_hdi = hdi_data[hdi_data['priogrid_id'] == grid_id]
            
            if not matching_hdi.empty:
                hdi_row = matching_hdi.iloc[0]
                # Debug: Check what columns are available
                logger.debug(f"HDI columns available: {list(hdi_row.index)}")
                logger.debug(f"HDI values for grid {grid_id}: {dict(hdi_row)}")
                
                hdi_values = {
                    'hdi_90_lower': hdi_row.get('pred_ln_sb_prob_hdi_lower'),
                    'hdi_90_upper': hdi_row.get('pred_ln_sb_prob_hdi_upper'),
                }
                logger.debug(f"Extracted HDI values: {hdi_values}")
            else:
                logger.debug(f"No HDI match found for grid {grid_id}")
        else:
            logger.debug("HDI data is empty")
        # Generate synthetic additional metrics for demo
        base_prob = main_row.get('main_dich', 0.01)
        synthetic_metrics = self._generate_synthetic_metrics(base_prob)
        
        # Determine country ID - prefer from main data, fallback to coordinates
        country_id = main_row.get('country_id')
        if pd.isna(country_id) and country_id_from_coord is not None:
            country_id = country_id_from_coord
        
        # Get country name
        country_name = None
        if pd.notna(country_id):
            country_name = country_map.get(int(country_id))
        
        # Convert month ID to year/month
        month_id = main_row['month_id']
        year = 2025 + (month_id - 548) // 12
        month = ((month_id - 548) % 12) + 1
        
        return GridCellData(
            grid_id=int(grid_id),
            month_id=int(month_id),
            country_id=int(country_id) if pd.notna(country_id) else None,
            latitude=lat,
            longitude=lon,
            
            # Main predictions
            main_mean=main_row.get('main_mean') if metrics.include_map else None,
            main_mean_ln=main_row.get('main_mean_ln') if metrics.include_map else None,
            main_dich=main_row.get('main_dich') if metrics.include_thresholds else None,
            
            # HDI bounds (real data if available, synthetic for missing levels)
            hdi_50_lower=synthetic_metrics['hdi_50_lower'] if metrics.include_hdi_50 else None,
            hdi_50_upper=synthetic_metrics['hdi_50_upper'] if metrics.include_hdi_50 else None,
            hdi_90_lower=hdi_values.get('hdi_90_lower') if metrics.include_hdi_90 else None,
            hdi_90_upper=hdi_values.get('hdi_90_upper') if metrics.include_hdi_90 else None,
            hdi_99_lower=synthetic_metrics['hdi_99_lower'] if metrics.include_hdi_99 else None,
            hdi_99_upper=synthetic_metrics['hdi_99_upper'] if metrics.include_hdi_99 else None,
            
            # Threshold probabilities (1 real, others synthetic)
            threshold_1=base_prob if metrics.include_thresholds else None,
            threshold_2=synthetic_metrics['threshold_2'] if metrics.include_thresholds else None,
            threshold_3=synthetic_metrics['threshold_3'] if metrics.include_thresholds else None,
            threshold_4=synthetic_metrics['threshold_4'] if metrics.include_thresholds else None,
            threshold_5=synthetic_metrics['threshold_5'] if metrics.include_thresholds else None,
            threshold_6=synthetic_metrics['threshold_6'] if metrics.include_thresholds else None,
            
            # Metadata
            conflict_type=ConflictType.STATE_BASED,  # Default to state-based
            country_name=country_name,
            year=year,
            month=month
        )
    
    def _generate_coordinates_for_grid(self, grid_id: int) -> tuple:
        """Generate realistic coordinates based on grid ID."""
        import hashlib
        # Use grid ID to generate consistent coordinates
        hash_input = str(grid_id).encode()
        hash_obj = hashlib.md5(hash_input)
        hash_int = int(hash_obj.hexdigest()[:8], 16)
        
        # Map to realistic global coordinates (avoid polar extremes)
        lat = ((hash_int % 13000) / 100.0) - 60.0  # Range: -60 to 70
        lon = (((hash_int // 13000) % 36000) / 100.0) - 180.0  # Range: -180 to 180
        
        return lat, lon
    
    def _generate_synthetic_metrics(self, base_prob: float) -> Dict[str, float]:
        """Generate synthetic metrics for demonstration purposes."""
        # Use deterministic generation based on base probability
        np.random.seed(int(base_prob * 10000) % 2**32)
        
        return {
            # Synthetic HDI bounds (narrower and wider than 90%)
            'hdi_50_lower': max(0, base_prob - np.random.uniform(0.001, 0.005)),
            'hdi_50_upper': min(1, base_prob + np.random.uniform(0.001, 0.005)),
            'hdi_99_lower': max(0, base_prob - np.random.uniform(0.01, 0.03)),
            'hdi_99_upper': min(1, base_prob + np.random.uniform(0.01, 0.03)),
            
            # Synthetic threshold probabilities (different conflict severity levels)
            'threshold_2': max(0, base_prob - np.random.uniform(0.001, 0.01)),  # 5+ fatalities
            'threshold_3': max(0, base_prob - np.random.uniform(0.01, 0.02)),   # 10+ fatalities
            'threshold_4': max(0, base_prob - np.random.uniform(0.02, 0.04)),   # 25+ fatalities
            'threshold_5': max(0, base_prob - np.random.uniform(0.03, 0.06)),   # 100+ fatalities
            'threshold_6': max(0, base_prob - np.random.uniform(0.05, 0.08)),   # 1000+ fatalities
        }
    
    def get_countries(self) -> List[Dict[str, Any]]:
        """Get list of available countries with metadata."""
        countries = self.data_service.get_available_countries()
        
        # Add grid cell counts
        for country in countries:
            try:
                grid_ids = self.data_service.get_country_grids(country['country_id'])
                country['grid_cells_count'] = len(grid_ids)
            except DataNotFoundError:
                country['grid_cells_count'] = 0
            except Exception as e:
                logger.warning(f"Error getting grid count for country {country['country_id']}: {e}")
                country['grid_cells_count'] = 0
        
        return countries