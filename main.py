"""
VIEWS Conflict Forecasting API

A FastAPI service that provides access to global conflict forecasts
with uncertainty quantification at 0.5° grid resolution.
"""

from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from typing import List, Optional, Dict, Any
import pandas as pd
from pathlib import Path
import logging

from models.schemas import (
    ForecastResponse,
    GridCellData,
    BasicInfoResponse,
    ErrorResponse,
    MetricSelection
)
from services.data_service import DataService
from services.forecast_service import ForecastService
from utils.exceptions import DataNotFoundError, ValidationError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="VIEWS Conflict Forecasting API",
    description="Global conflict forecasting system with uncertainty quantification",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware for dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for dashboard
app.mount("/static", StaticFiles(directory="static"), name="static")

# Initialize services
data_service = DataService()
forecast_service = ForecastService(data_service)


@app.on_event("startup")
async def startup_event():
    """Initialize data on startup."""
    try:
        data_service.load_data()
        logger.info("Data loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load data: {e}")
        raise


@app.get("/", response_class=HTMLResponse)
async def dashboard():
    """Serve the main dashboard."""
    dashboard_path = Path("static/dashboard.html")
    if dashboard_path.exists():
        return HTMLResponse(content=dashboard_path.read_text(encoding='utf-8'))
    else:
        # If dashboard file doesn't exist, return a simple redirect to docs
        return HTMLResponse(content="""
        <html>
            <head><title>VIEWS API</title></head>
            <body>
                <h1>VIEWS Conflict Forecasting API</h1>
                <p>Dashboard file not found. Available endpoints:</p>
                <ul>
                    <li><a href="/docs">API Documentation (Swagger)</a></li>
                    <li><a href="/redoc">API Documentation (ReDoc)</a></li>
                    <li><a href="/api/info">API Information</a></li>
                </ul>
                <p>To set up the dashboard, create a file at <code>static/dashboard.html</code></p>
            </body>
        </html>
        """)


def get_simple_dashboard():
    """Return a simple working dashboard."""
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>VIEWS Conflict Forecasting Dashboard</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
            .container { max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            .header { text-align: center; margin-bottom: 30px; }
            .controls { background: #f8f9fa; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
            .form-row { display: flex; gap: 20px; margin-bottom: 15px; flex-wrap: wrap; }
            .form-col { flex: 1; min-width: 200px; }
            label { display: block; margin-bottom: 5px; font-weight: bold; }
            input, select, button { width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px; }
            button { background: #007bff; color: white; cursor: pointer; font-weight: bold; }
            button:hover { background: #0056b3; }
            .results { margin-top: 20px; }
            .error { background: #f8d7da; color: #721c24; padding: 15px; border-radius: 4px; margin: 10px 0; }
            .success { background: #d4edda; color: #155724; padding: 15px; border-radius: 4px; margin: 10px 0; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>VIEWS Conflict Forecasting Dashboard</h1>
                <p>Global conflict predictions with uncertainty quantification</p>
                <div id="apiStatus">API Status: <span id="statusText">Checking...</span></div>
            </div>

            <div class="controls">
                <div class="form-row">
                    <div class="form-col">
                        <label for="queryType">Query Type:</label>
                        <select id="queryType">
                            <option value="info">API Information</option>
                            <option value="countries">List Countries</option>
                            <option value="month">Query by Month</option>
                        </select>
                    </div>
                    <div class="form-col">
                        <label for="monthId">Month ID:</label>
                        <input type="number" id="monthId" value="548" placeholder="e.g., 548">
                    </div>
                    <div class="form-col" style="display: flex; align-items: end;">
                        <button onclick="executeQuery()">Execute Query</button>
                    </div>
                </div>
            </div>

            <div class="results" id="resultsSection" style="display: none;">
                <h3>Results</h3>
                <div id="resultsContent"></div>
            </div>
        </div>

        <script>
            let apiBaseUrl = '/api';

            // Check API status on load
            checkAPIStatus();

            async function checkAPIStatus() {
                try {
                    const response = await fetch(apiBaseUrl + '/info');
                    const statusText = document.getElementById('statusText');
                    if (response.ok) {
                        statusText.textContent = 'Online';
                        statusText.style.color = 'green';
                    } else {
                        statusText.textContent = 'Error';
                        statusText.style.color = 'red';
                    }
                } catch (error) {
                    document.getElementById('statusText').textContent = 'Offline';
                    document.getElementById('statusText').style.color = 'red';
                }
            }

            async function executeQuery() {
                const queryType = document.getElementById('queryType').value;
                const monthId = document.getElementById('monthId').value;
                const resultsSection = document.getElementById('resultsSection');
                const resultsContent = document.getElementById('resultsContent');
                
                resultsContent.innerHTML = '<p>Loading...</p>';
                resultsSection.style.display = 'block';

                try {
                    let url = '';
                    switch (queryType) {
                        case 'info':
                            url = apiBaseUrl + '/info';
                            break;
                        case 'countries':
                            url = apiBaseUrl + '/countries';
                            break;
                        case 'month':
                            url = apiBaseUrl + '/forecasts/month/' + monthId + '?include_map=true&include_thresholds=true';
                            break;
                    }

                    const response = await fetch(url);
                    if (!response.ok) throw new Error('HTTP ' + response.status);
                    
                    const data = await response.json();
                    displayResults(data, queryType);
                    
                } catch (error) {
                    resultsContent.innerHTML = '<div class="error">Error: ' + error.message + '</div>';
                }
            }

            function displayResults(data, queryType) {
                const resultsContent = document.getElementById('resultsContent');
                
                if (queryType === 'info') {
                    resultsContent.innerHTML = `
                        <div class="success">
                            <h4>API Information</h4>
                            <p><strong>Available Months:</strong> ${data.available_months.length} months</p>
                            <p><strong>Total Grid Cells:</strong> ${data.total_grid_cells}</p>
                            <p><strong>Countries:</strong> ${data.countries_available}</p>
                            <p><strong>Date Range:</strong> ${data.date_range.start} to ${data.date_range.end}</p>
                        </div>
                    `;
                } else if (queryType === 'countries') {
                    const countriesList = data.map(c => 
                        `<li>${c.country} (ID: ${c.country_id}, Grids: ${c.grid_cells_count || 'N/A'})</li>`
                    ).join('');
                    resultsContent.innerHTML = `
                        <div class="success">
                            <h4>Available Countries</h4>
                            <ul>${countriesList}</ul>
                        </div>
                    `;
                } else if (queryType === 'month') {
                    const summary = `
                        <div class="success">
                            <h4>Forecast Summary</h4>
                            <p><strong>Grid Cells:</strong> ${data.total_cells}</p>
                            <p><strong>Months Covered:</strong> ${data.months_covered}</p>
                            <p><strong>Sample Data:</strong></p>
                            <ul>
                                ${data.data.slice(0, 5).map(d => 
                                    `<li>Grid ${d.grid_id}: Risk ${(d.main_mean || 0).toFixed(4)}, Country: ${d.country_name || 'Unknown'}</li>`
                                ).join('')}
                            </ul>
                            ${data.data.length > 5 ? '<p>... and ' + (data.data.length - 5) + ' more</p>' : ''}
                        </div>
                    `;
                    resultsContent.innerHTML = summary;
                }
            }
        </script>
    </body>
    </html>
    """


@app.get("/dashboard/", response_class=HTMLResponse)
async def dashboard_alt():
    """Alternative dashboard route."""
    return await dashboard()


@app.get("/api/info", response_model=BasicInfoResponse)
async def get_basic_info():
    """Get basic information about available data."""
    try:
        info = forecast_service.get_basic_info()
        return BasicInfoResponse(**info)
    except Exception as e:
        logger.error(f"Error getting basic info: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/forecasts/country/{country_id}", response_model=ForecastResponse)
async def get_forecasts_by_country(
    country_id: int,
    month_start: Optional[int] = Query(None, description="Start month ID"),
    month_end: Optional[int] = Query(None, description="End month ID"),
    metrics: MetricSelection = Depends()
):
    """Get forecasts for all grid cells in a country."""
    try:
        forecasts = forecast_service.get_forecasts_by_country(
            country_id=country_id,
            month_start=month_start,
            month_end=month_end,
            metrics=metrics
        )
        return ForecastResponse(
            data=forecasts,
            total_cells=len(forecasts),
            months_covered=len(set(f.month_id for f in forecasts)) if forecasts else 0
        )
    except DataNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting country forecasts: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/forecasts/grid", response_model=ForecastResponse)
async def get_forecasts_by_grid(
    grid_ids: List[int] = Query(..., description="Grid cell IDs"),
    month_start: Optional[int] = Query(None, description="Start month ID"),
    month_end: Optional[int] = Query(None, description="End month ID"),
    metrics: MetricSelection = Depends()
):
    """Get forecasts for specific grid cells."""
    try:
        forecasts = forecast_service.get_forecasts_by_grid(
            grid_ids=grid_ids,
            month_start=month_start,
            month_end=month_end,
            metrics=metrics
        )
        return ForecastResponse(
            data=forecasts,
            total_cells=len(forecasts),
            months_covered=len(set(f.month_id for f in forecasts)) if forecasts else 0
        )
    except DataNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting grid forecasts: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/forecasts/month/{month_id}", response_model=ForecastResponse)
async def get_forecasts_by_month(
    month_id: int,
    country_id: Optional[int] = Query(None, description="Filter by country"),
    metrics: MetricSelection = Depends()
):
    """Get all forecasts for a specific month."""
    try:
        forecasts = forecast_service.get_forecasts_by_month(
            month_id=month_id,
            country_id=country_id,
            metrics=metrics
        )
        return ForecastResponse(
            data=forecasts,
            total_cells=len(forecasts),
            months_covered=1
        )
    except DataNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting month forecasts: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/debug/coordinates")
async def debug_coordinates():
    """Debug endpoint to check coordinate data."""
    try:
        # Get some sample coordinate data
        coord_data = data_service.get_coordinates([])  # Get all coordinates
        
        if coord_data.empty:
            return {"error": "No coordinate data found"}
        
        sample_coords = coord_data.head(10).to_dict('records')
        
        return {
            "total_coordinates": len(coord_data),
            "columns": list(coord_data.columns),
            "sample_data": sample_coords,
            "unique_grids": len(coord_data['priogrid_id'].unique()) if 'priogrid_id' in coord_data.columns else 0
        }
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/debug/files")
async def debug_files():
    """Debug endpoint to check what data files exist."""
    try:
        from pathlib import Path
        files_status = {}
        
        # Check each expected file
        expected_files = [
            "data/fatalities002_2025_07_t01_pgm.csv",
            "data/fatalities002_2025_07_t01_cm.csv", 
            "data/sample_preds_001_90.csv.gz",
            "data/sample_preds_001.csv.gz"
        ]
        
        for file_path in expected_files:
            path = Path(file_path)
            files_status[file_path] = {
                "exists": path.exists(),
                "size": path.stat().st_size if path.exists() else 0,
                "readable": path.is_file() if path.exists() else False
            }
        
        # Also check the data service state
        return {
            "files": files_status,
            "data_service_state": {
                "is_loaded": data_service.is_loaded,
                "pgm_data_loaded": data_service.pgm_data is not None,
                "country_data_loaded": data_service.country_data is not None,
                "hdi_data_loaded": data_service.hdi_data is not None,
                "timeseries_data_loaded": data_service.timeseries_data is not None,
            }
        }
    except Exception as e:
        return {"error": str(e)}
async def debug_hdi():
    """Debug endpoint to check HDI data."""
    try:
        # Get some sample HDI data
        hdi_data = data_service.get_hdi_data([])  # Get all HDI data
        
        if hdi_data.empty:
            return {"error": "No HDI data found"}
        
        sample_hdi = hdi_data.head(10).to_dict('records')
        
        return {
            "total_hdi_records": len(hdi_data),
            "columns": list(hdi_data.columns),
            "sample_data": sample_hdi,
            "unique_grids": len(hdi_data['priogrid_id'].unique()) if 'priogrid_id' in hdi_data.columns else 0,
            "months_available": sorted(hdi_data['month_id'].unique().tolist()) if 'month_id' in hdi_data.columns else []
        }
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/debug/status")
async def debug_status():
    """Simple debug endpoint to check data service status."""
    try:
        return {
            "data_service_loaded": data_service.is_loaded,
            "hdi_data_exists": data_service.hdi_data is not None,
            "hdi_data_length": len(data_service.hdi_data) if data_service.hdi_data is not None else 0,
            "hdi_data_columns": list(data_service.hdi_data.columns) if data_service.hdi_data is not None else []
        }
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/debug/hdi")
async def debug_hdi():
    """Debug endpoint to check HDI data."""
    try:
        # Access HDI data directly from data service
        if data_service.hdi_data is None or data_service.hdi_data.empty:
            return {"error": "No HDI data found"}
        
        hdi_data = data_service.hdi_data
        sample_hdi = hdi_data.head(10).to_dict('records')
        
        return {
            "total_hdi_records": len(hdi_data),
            "columns": list(hdi_data.columns),
            "sample_data": sample_hdi,
            "unique_grids": len(hdi_data['priogrid_id'].unique()) if 'priogrid_id' in hdi_data.columns else 0,
            "months_available": sorted(hdi_data['month_id'].unique().tolist()) if 'month_id' in hdi_data.columns else []
        }
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/countries", response_model=List[Dict[str, Any]])
async def get_countries():
    """Get list of available countries."""
    try:
        countries = forecast_service.get_countries()
        return countries
    except Exception as e:
        logger.error(f"Error getting countries: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)