"""
Data service layer for VIEWS API.
Handles data loading, caching, and basic data operations.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import logging
import json
from dataclasses import dataclass
from utils.exceptions import DataNotFoundError

logger = logging.getLogger(__name__)


@dataclass
class DataPaths:
    """Configuration for data file paths."""
    pgm_data: str = "data/fatalities002_2025_07_t01_pgm.csv"
    country_data: str = "data/fatalities002_2025_07_t01_cm.csv"
    hdi_data: str = "data/sample_preds_001_90.csv.gz"
    timeseries_data: str = "data/sample_preds_001.csv.gz"


class DataService:
    """Service for data loading and management."""
    
    def __init__(self, data_paths: Optional[DataPaths] = None):
        """Initialize data service."""
        self.data_paths = data_paths or DataPaths()
        self.pgm_data: Optional[pd.DataFrame] = None
        self.country_data: Optional[pd.DataFrame] = None
        self.hdi_data: Optional[pd.DataFrame] = None
        self.timeseries_data: Optional[pd.DataFrame] = None
        self.country_grid_mapping: Dict[int, List[int]] = {}
        self.is_loaded = False
    
    def load_data(self) -> None:
        """Load all data files."""
        try:
            self._load_pgm_data()
            self._load_country_data()
            self._load_hdi_data()
            self._load_timeseries_data()
            self._create_mappings()
            self.is_loaded = True
            logger.info("All data loaded successfully")
        except Exception as e:
            logger.error(f"Error loading data: {e}")
            raise
    
    def _load_pgm_data(self) -> None:
        """Load PRIO-GRID monthly data."""
        if not Path(self.data_paths.pgm_data).exists():
            self._create_synthetic_pgm_data()
        else:
            self.pgm_data = pd.read_csv(self.data_paths.pgm_data)
        
        logger.info(f"Loaded PGM data: {len(self.pgm_data)} records")
    
    def _load_country_data(self) -> None:
        """Load country monthly data."""
        if not Path(self.data_paths.country_data).exists():
            self._create_synthetic_country_data()
        else:
            self.country_data = pd.read_csv(self.data_paths.country_data)
        
        logger.info(f"Loaded country data: {len(self.country_data)} records")
    
    def _load_hdi_data(self) -> None:
        """Load HDI confidence interval data."""
        if not Path(self.data_paths.hdi_data).exists():
            logger.warning(f"HDI data file not found: {self.data_paths.hdi_data}")
            self._create_synthetic_hdi_data()
        else:
            try:
                self.hdi_data = pd.read_csv(self.data_paths.hdi_data)
                logger.info(f"Successfully loaded HDI data: {len(self.hdi_data)} records")
                logger.info(f"HDI data columns: {list(self.hdi_data.columns)}")
            except Exception as e:
                logger.error(f"Error loading HDI data: {e}")
                self._create_synthetic_hdi_data()
        
        if self.hdi_data is not None:
            logger.info(f"Final HDI data: {len(self.hdi_data)} records")
        else:
            logger.error("HDI data is None after loading")
    
    def _load_timeseries_data(self) -> None:
        """Load time series data with coordinates."""
        if not Path(self.data_paths.timeseries_data).exists():
            self._create_synthetic_timeseries_data()
        else:
            try:
                # Try to parse the actual timeseries file
                # First try reading as standard CSV (pandas handles .gz automatically)
                self.timeseries_data = pd.read_csv(self.data_paths.timeseries_data)
                logger.info(f"Loaded timeseries data as standard CSV: {len(self.timeseries_data)} records")
            except Exception as csv_error:
                logger.warning(f"Failed to load as standard CSV: {csv_error}")
                try:
                    # Fallback: Try special handling for complex array format
                    import gzip

                    # Open gzipped file properly
                    if self.data_paths.timeseries_data.endswith('.gz'):
                        with gzip.open(self.data_paths.timeseries_data, 'rt', encoding='utf-8') as f:
                            first_line = f.readline()
                    else:
                        with open(self.data_paths.timeseries_data, 'r', encoding='utf-8') as f:
                            first_line = f.readline()

                    # Check if it's the array format you showed
                    if '[' in first_line and ']' in first_line:
                        # This is the complex array format - extract just the metadata
                        data = []

                        if self.data_paths.timeseries_data.endswith('.gz'):
                            with gzip.open(self.data_paths.timeseries_data, 'rt', encoding='utf-8') as f:
                                lines = f.readlines()
                        else:
                            with open(self.data_paths.timeseries_data, 'r', encoding='utf-8') as f:
                                lines = f.readlines()

                        # Skip header if present
                        start_idx = 1 if 'pred_ln_sb_best' in lines[0] else 0

                        for line in lines[start_idx:]:
                            parts = line.strip().split(',')
                            if len(parts) >= 10:  # Ensure we have enough columns
                                try:
                                    # Extract the metadata columns (country_id, lat, lon, row, col, month_id, priogrid_id)
                                    # Based on your format: ..., country_id, lat, lon, row, col, month_id, priogrid_id
                                    country_id = int(parts[-7])
                                    lat = float(parts[-6])
                                    lon = float(parts[-5])
                                    row = int(parts[-4])
                                    col = int(parts[-3])
                                    month_id = int(parts[-2])
                                    priogrid_id = int(parts[-1])

                                    data.append({
                                        'priogrid_id': priogrid_id,
                                        'latitude': lat,
                                        'longitude': lon,
                                        'country_id': country_id,
                                        'row': row,
                                        'col': col,
                                        'month_id': month_id
                                    })
                                except (ValueError, IndexError) as e:
                                    logger.warning(f"Skipping malformed line: {e}")
                                    continue

                        self.timeseries_data = pd.DataFrame(data)
                        logger.info(f"Parsed timeseries data: {len(self.timeseries_data)} records")
                    else:
                        # Standard CSV format - try pandas read_csv again with explicit encoding
                        self.timeseries_data = pd.read_csv(self.data_paths.timeseries_data, encoding='utf-8')

                except Exception as e:
                    logger.warning(f"Failed to load timeseries data: {e}, creating synthetic data")
                    self._create_synthetic_timeseries_data()
        
        # If we have no coordinate data, create synthetic coordinates for the grid cells we do have
        if self.timeseries_data is None or self.timeseries_data.empty:
            self._create_synthetic_coordinates_from_pgm()
        
        logger.info(f"Loaded timeseries data: {len(self.timeseries_data)} records")
    
    def _create_synthetic_coordinates_from_pgm(self) -> None:
        """Create synthetic coordinates for grid cells from PGM data."""
        if self.pgm_data is None:
            return
            
        unique_grids = self.pgm_data['pg_id'].unique()
        np.random.seed(42)  # For reproducible coordinates
        
        data = []
        for i, grid_id in enumerate(unique_grids):
            # Generate realistic global coordinates
            lat = np.random.uniform(-60, 70)  # Avoid extreme polar regions
            lon = np.random.uniform(-180, 180)
            
            data.append({
                'priogrid_id': grid_id,
                'latitude': lat,
                'longitude': lon,
                'country_id': (i % 5) + 1,  # Assign to 5 synthetic countries
                'row': 100 + i // 10,
                'col': 400 + i % 10
            })
        
        self.timeseries_data = pd.DataFrame(data)
        logger.info(f"Created synthetic coordinates for {len(unique_grids)} grid cells")
    
    def _create_mappings(self) -> None:
        """Create lookup mappings for efficient querying."""
        if self.pgm_data is None:
            return
        
        # Check if country_id exists in PGM data
        if 'country_id' in self.pgm_data.columns:
            # Create country to grid mapping from PGM data
            country_groups = self.pgm_data.groupby('country_id')['pg_id'].apply(list)
            self.country_grid_mapping = country_groups.to_dict()
        else:
            # Create mapping using timeseries data (which has country_id)
            if self.timeseries_data is not None and 'country_id' in self.timeseries_data.columns:
                # Map from timeseries data using priogrid_id
                country_grid_df = self.timeseries_data[['country_id', 'priogrid_id']].drop_duplicates()
                country_groups = country_grid_df.groupby('country_id')['priogrid_id'].apply(list)
                self.country_grid_mapping = country_groups.to_dict()
                logger.info("Created country mapping from timeseries data")
            else:
                # Fallback: create synthetic mapping
                logger.warning("No country_id found, creating synthetic country mapping")
                unique_grids = self.pgm_data['pg_id'].unique()
                # Assign grids to synthetic countries
                grids_per_country = len(unique_grids) // 5  # 5 synthetic countries
                for i in range(5):
                    start_idx = i * grids_per_country
                    end_idx = start_idx + grids_per_country if i < 4 else len(unique_grids)
                    self.country_grid_mapping[i + 1] = unique_grids[start_idx:end_idx].tolist()
        
        # Remove None/NaN countries
        self.country_grid_mapping = {
            k: v for k, v in self.country_grid_mapping.items() 
            if pd.notna(k)
        }
        
        logger.info(f"Created mappings for {len(self.country_grid_mapping)} countries")
    
    def _create_synthetic_pgm_data(self) -> None:
        """Create synthetic PGM data for testing."""
        np.random.seed(42)
        
        # Generate grid cells and months
        grid_ids = range(62356, 62456)  # 100 grid cells
        month_ids = range(548, 584)     # 36 months
        
        data = []
        for grid_id in grid_ids:
            for month_id in month_ids:
                data.append({
                    'pg_id': grid_id,
                    'month_id': month_id,
                    'main_mean_ln': np.random.exponential(0.01),
                    'main_dich': np.random.beta(2, 20),
                    'main_mean': np.random.exponential(0.01),
                    'country_id': np.random.choice([1, 2, 3, 4, 5])
                })
        
        self.pgm_data = pd.DataFrame(data)
        
        # Save for future use
        Path("data").mkdir(exist_ok=True)
        self.pgm_data.to_csv(self.data_paths.pgm_data, index=False)
    
    def _create_synthetic_country_data(self) -> None:
        """Create synthetic country data for testing."""
        countries = [
            {'country_id': 1, 'country': 'Testland', 'isoab': 'TST', 'gwcode': 100},
            {'country_id': 2, 'country': 'Democracia', 'isoab': 'DEM', 'gwcode': 101},
            {'country_id': 3, 'country': 'Republica', 'isoab': 'REP', 'gwcode': 102},
            {'country_id': 4, 'country': 'Federation', 'isoab': 'FED', 'gwcode': 103},
            {'country_id': 5, 'country': 'Kingdom', 'isoab': 'KNG', 'gwcode': 104},
        ]
        
        month_ids = range(548, 584)
        data = []
        
        for country in countries:
            for month_id in month_ids:
                data.append({
                    **country,
                    'month_id': month_id,
                    'year': 2025 + (month_id - 548) // 12,
                    'month': ((month_id - 548) % 12) + 1,
                    'main_mean': np.random.exponential(0.05),
                    'main_dich': np.random.beta(2, 20),
                    'main_mean_ln': np.random.exponential(0.05),
                })
        
        self.country_data = pd.DataFrame(data)
        
        # Save for future use
        Path("data").mkdir(exist_ok=True)
        self.country_data.to_csv(self.data_paths.country_data, index=False)
    
    def _create_synthetic_hdi_data(self) -> None:
        """Create synthetic HDI data for testing."""
        np.random.seed(42)
        
        grid_ids = range(62356, 62456)
        month_ids = range(548, 584)
        
        data = []
        for grid_id in grid_ids:
            for month_id in month_ids:
                base_prob = np.random.beta(2, 20)
                data.append({
                    'priogrid_id': grid_id,
                    'month_id': month_id,
                    'pred_ln_sb_best_hdi_lower': 0.0,
                    'pred_ln_sb_best_hdi_upper': 0.0,
                    'pred_ln_ns_best_hdi_lower': 0.0,
                    'pred_ln_ns_best_hdi_upper': 0.0,
                    'pred_ln_os_best_hdi_lower': 0.0,
                    'pred_ln_os_best_hdi_upper': 0.0,
                    'pred_ln_sb_prob_hdi_lower': max(0, base_prob - 0.01),
                    'pred_ln_sb_prob_hdi_upper': min(1, base_prob + 0.01),
                    'pred_ln_ns_prob_hdi_lower': max(0, base_prob - 0.005),
                    'pred_ln_ns_prob_hdi_upper': min(1, base_prob + 0.005),
                    'pred_ln_os_prob_hdi_lower': max(0, base_prob - 0.02),
                    'pred_ln_os_prob_hdi_upper': min(1, base_prob + 0.02),
                })
        
        self.hdi_data = pd.DataFrame(data)
        
        # Save for future use
        Path("data").mkdir(exist_ok=True)
        self.hdi_data.to_csv(self.data_paths.hdi_data, index=False)
    
    def _create_synthetic_timeseries_data(self) -> None:
        """Create synthetic timeseries data with coordinates."""
        np.random.seed(42)
        
        grid_ids = range(62356, 62456)
        
        data = []
        for i, grid_id in enumerate(grid_ids):
            # Generate realistic coordinates
            lat = np.random.uniform(-60, 70)
            lon = np.random.uniform(-180, 180)
            
            data.append({
                'priogrid_id': grid_id,
                'latitude': lat,
                'longitude': lon,
                'country_id': np.random.choice([1, 2, 3, 4, 5]),
                'row': 100 + i // 10,
                'col': 400 + i % 10
            })
        
        self.timeseries_data = pd.DataFrame(data)
    
    def get_grid_data(self, grid_ids: List[int], month_ids: Optional[List[int]] = None) -> pd.DataFrame:
        """Get data for specific grid cells and months."""
        if not self.is_loaded:
            raise DataNotFoundError("Data not loaded")
        
        query = self.pgm_data['pg_id'].isin(grid_ids)
        
        if month_ids:
            query &= self.pgm_data['month_id'].isin(month_ids)
        
        result = self.pgm_data[query].copy()
        
        if result.empty:
            raise DataNotFoundError(f"No data found for grid IDs: {grid_ids}")
        
        return result
    
    def get_country_grids(self, country_id: int) -> List[int]:
        """Get all grid IDs for a country."""
        if not self.is_loaded:
            raise DataNotFoundError("Data not loaded")
        
        grid_ids = self.country_grid_mapping.get(country_id, [])
        
        if not grid_ids:
            raise DataNotFoundError(f"No grid cells found for country ID: {country_id}")
        
        return grid_ids
    
    def get_month_data(self, month_id: int, country_id: Optional[int] = None) -> pd.DataFrame:
        """Get all data for a specific month, optionally filtered by country."""
        if not self.is_loaded:
            raise DataNotFoundError("Data not loaded")
        
        query = self.pgm_data['month_id'] == month_id
        
        if country_id:
            # Check if country_id column exists in pgm_data
            if 'country_id' in self.pgm_data.columns:
                query &= self.pgm_data['country_id'] == country_id
            else:
                # Filter by grid IDs that belong to the country
                try:
                    grid_ids = self.get_country_grids(country_id)
                    query &= self.pgm_data['pg_id'].isin(grid_ids)
                except DataNotFoundError:
                    # Country not found, return empty result
                    logger.warning(f"Country {country_id} not found in mappings")
                    return pd.DataFrame()
        
        result = self.pgm_data[query].copy()
        
        if result.empty:
            raise DataNotFoundError(f"No data found for month ID: {month_id}")
        
        return result
    
    def get_hdi_data(self, grid_ids: List[int], month_ids: Optional[List[int]] = None) -> pd.DataFrame:
        """Get HDI data for specific grids and months."""
        if self.hdi_data is None:
            return pd.DataFrame()
        
        query = self.hdi_data['priogrid_id'].isin(grid_ids)
        
        if month_ids:
            query &= self.hdi_data['month_id'].isin(month_ids)
        
        return self.hdi_data[query].copy()
    
    def get_coordinates(self, grid_ids: List[int]) -> pd.DataFrame:
        """Get coordinates for grid cells."""
        if self.timeseries_data is None or self.timeseries_data.empty:
            return pd.DataFrame()
        
        if not grid_ids:  # If no specific grid_ids requested, return all
            return self.timeseries_data.copy()
        
        # Match by priogrid_id (the coordinate data uses this field name)
        query = self.timeseries_data['priogrid_id'].isin(grid_ids)
        result = self.timeseries_data[query].copy()
        
        # Debug logging
        logger.info(f"Coordinate lookup: requested {len(grid_ids)} grids, found {len(result)} matches")
        if len(result) == 0 and len(self.timeseries_data) > 0:
            sample_coord_ids = self.timeseries_data['priogrid_id'].head(5).tolist()
            sample_request_ids = grid_ids[:5]
            logger.warning(f"No coordinate matches found. Sample coord IDs: {sample_coord_ids}, Sample request IDs: {sample_request_ids}")
        
        return result
    
    def get_available_months(self) -> List[int]:
        """Get list of available month IDs."""
        if not self.is_loaded or self.pgm_data is None:
            return []
        
        return sorted(self.pgm_data['month_id'].unique().tolist())
    
    def get_available_countries(self) -> List[Dict]:
        """Get list of available countries."""
        if not self.is_loaded:
            return []
        
        # First try to get countries from country_data (which should have country names)
        if self.country_data is not None:
            countries = self.country_data[['country_id', 'country', 'isoab']].drop_duplicates()
            return countries.rename(columns={'isoab': 'iso_code'}).to_dict('records')
        
        # Fallback: get countries from country mapping (might not have names)
        elif self.country_grid_mapping:
            countries = []
            for country_id in self.country_grid_mapping.keys():
                countries.append({
                    'country_id': country_id,
                    'country': f'Country {country_id}',  # Generic name
                    'iso_code': None
                })
            return countries
        
        # Last resort: return empty list
        return []
    
    def get_total_grid_cells(self) -> int:
        """Get total number of grid cells."""
        if not self.is_loaded or self.pgm_data is None:
            return 0
        
        return self.pgm_data['pg_id'].nunique()