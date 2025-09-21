# VIEWS Conflict Forecasting API

A FastAPI-based service that provides access to global conflict forecasts with uncertainty quantification at 0.5° grid resolution.

## Features

-   **RESTful API** for querying conflict forecasts
-   **Interactive Dashboard** with maps and charts
-   **Grid-based predictions** at 0.5° resolution globally
-   **Uncertainty quantification** with confidence intervals
-   **Flexible querying** by country, grid cells, or time periods
-   **Metric selection** to choose specific forecast values
-   **Production-ready** with full typing, testing, and documentation

## Quick Start (≤15 minutes)

### Prerequisites

-   Python 3.9+ (tested with Python 3.13)
-   Windows, macOS, or Linux

### Installation

1. **Clone or download the project files**
2. **Set up the environment:**

```bash
# Create virtual environment (recommended)
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
make install-dev
# Or manually:
pip install -r requirements-dev.txt
```

3. **Initialize the project:**

```bash
make setup
```

4. **Start the server:**

```bash
make run
```

5. **Open your browser to:**
    - Dashboard: http://localhost:8000
    - API Documentation: http://localhost:8000/docs
    - Alternative docs: http://localhost:8000/redoc

That's it! The API will automatically create synthetic test data on first run.

## API Endpoints

### Basic Information

-   `GET /api/info` - Get API metadata and available data ranges
-   `GET /api/countries` - List available countries

### Forecast Queries

-   `GET /api/forecasts/country/{country_id}` - Get forecasts for all grid cells in a country
-   `GET /api/forecasts/grid?grid_ids=...` - Get forecasts for specific grid cells
-   `GET /api/forecasts/month/{month_id}` - Get all forecasts for a specific month

### Query Parameters

-   `month_start`, `month_end` - Filter by date range
-   `country_id` - Filter by country (for month queries)
-   `include_map`, `include_hdi_90`, `include_thresholds` - Select metrics to return

## Data Structure

Each forecast contains up to 13 values per grid cell per month:

### Core Predictions

-   **MAP (Mean)**: Point prediction of conflict risk
-   **Binary threshold**: Probability of exceeding conflict threshold

### Confidence Intervals

-   **50% HDI**: 50% Highest Density Interval bounds
-   **90% HDI**: 90% Highest Density Interval bounds (available)
-   **99% HDI**: 99% Highest Density Interval bounds

### Threshold Probabilities

-   **Multiple thresholds**: Probabilities of exceeding different severity levels

### Metadata

-   **Grid ID**: PRIO Grid identifier
-   **Coordinates**: Latitude/longitude of grid centroid
-   **Country ID**: UN M49 country code
-   **Time**: Year and month information

## Example Requests

### Get country forecasts with confidence intervals

```bash
curl "http://localhost:8000/api/forecasts/country/1?include_hdi_90=true&month_start=548&month_end=550"
```

### Get specific grid cells for one month

```bash
curl "http://localhost:8000/api/forecasts/grid?grid_ids=62356&grid_ids=62357&include_map=true"
```

### Get basic API information

```bash
curl "http://localhost:8000/api/info"
```

## Dashboard Features

The interactive dashboard provides:

-   **Risk visualization** on an interactive map
-   **Time series charts** showing forecast trends
-   **Query builder** with dropdown menus
-   **Results table** with detailed forecast data
-   **Real-time API status** monitoring

## Development

### Available Commands

```bash
make help          # Show all available commands
make setup         # Set up project directories and dependencies
make run           # Start development server
make test          # Run test suite
make lint          # Check code style
make format        # Format code
make validate      # Run all checks (lint, format, type-check, test)
make clean         # Clean up temporary files
make demo          # Create sample data and start demo
```

### Project Structure

```
views-api/
├── main.py                 # FastAPI application entry point
├── models/
│   └── schemas.py         # Pydantic models and schemas
├── services/
│   ├── data_service.py    # Data loading and management
│   └── forecast_service.py # Business logic for forecasts
├── utils/
│   └── exceptions.py      # Custom exception classes
├── static/
│   └── dashboard.html     # Interactive dashboard
├── tests/
│   └── test_*.py         # Test suite
├── data/                  # Data files (auto-generated)
├── requirements*.txt      # Dependencies
├── Makefile              # Development commands
└── README.md             # This file
```

### Data Sources

The API supports multiple data formats:

1. **Grid-level data** (`fatalities002_*_pgm.csv`)
2. **Country-level data** (`fatalities002_*_cm.csv`)
3. **HDI confidence intervals** (`*_hdi.csv`)
4. **Time series with coordinates** (`timeseries_*.csv`)

If data files are not present, the system automatically generates synthetic test data.

### Testing

Run the complete test suite:

```bash
make test
```

Run with coverage report:

```bash
make test-coverage
```

### Code Quality

The project enforces high code quality standards:

-   **Type hints** throughout (Pydantic models)
-   **Linting** with Ruff
-   **Formatting** with Ruff formatter
-   **Type checking** with MyPy
-   **Testing** with Pytest
-   **Documentation** with docstrings

Run all quality checks:

```bash
make validate
```

## Configuration

### Environment Variables

-   `API_HOST`: Server host (default: 0.0.0.0)
-   `API_PORT`: Server port (default: 8000)
-   `LOG_LEVEL`: Logging level (default: INFO)

### Data Paths

Data file paths can be configured in `services/data_service.py`:

```python
@dataclass
class DataPaths:
    pgm_data: str = "data/fatalities002_2025_07_t01_pgm.csv"
    country_data: str = "data/fatalities002_2025_07_t01_cm.csv"
    # ... other paths
```

## Production Deployment

### Using Uvicorn

```bash
make run-prod
```

### Using Docker

```bash
make docker-build
make docker-run
```

### Environment Setup

For production deployment:

1. Set appropriate environment variables
2. Use a reverse proxy (nginx, traefik)
3. Configure proper logging
4. Set up monitoring and health checks

## API Design Principles

-   **Clean Architecture**: Separation of concerns between data, business logic, and API layers
-   **Dependency Inversion**: Services depend on abstractions, not implementations
-   **Type Safety**: Full typing with Pydantic validation
-   **Error Handling**: Proper HTTP status codes and error responses
-   **Extensibility**: Designed to easily add new features (admin boundaries, aggregations, etc.)

## Limitations & Future Enhancements

### Current Limitations

-   Confidence intervals limited to 90% HDI (others are synthetic for demo)
-   Threshold probabilities limited to 1-2 real values
-   No authentication system
-   No data aggregation endpoints

### Planned Enhancements

-   Multiple confidence interval levels
-   Additional threshold probabilities
-   Admin boundary integration
-   Bulk export capabilities
-   Authentication and rate limiting
-   Caching layer for performance

## Troubleshooting

### Common Issues

**API not starting:**

-   Check if port 8000 is available
-   Verify Python version (3.9+ required)
-   Install dependencies: `make install-dev`

**No data returned:**

-   API automatically creates synthetic data on first run
-   Check logs for data loading errors
-   Try: `make create-sample-data`

**Tests failing:**

-   Ensure all dependencies installed: `make install-dev`
-   Run individual test files to isolate issues

**Dashboard not loading:**

-   Check that server is running on http://localhost:8000
-   Verify static files are properly served
-   Check browser console for JavaScript errors

## Contributing

1. Follow the established code style (Ruff formatting)
2. Add tests for new functionality
3. Update documentation
4. Ensure all quality checks pass: `make validate`

## License

This project is provided for educational and research purposes. Please refer to the VIEWS project for licensing information regarding the underlying conflict forecasting models and data.

## Support

For issues and questions:

1. Check this README
2. Review API documentation at `/docs`
3. Run `make help` for available commands
4. Check the test suite for usage examples
