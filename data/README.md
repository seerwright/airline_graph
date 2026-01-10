# Data Directory

This directory contains raw and processed data files for the airline graph project.

## Structure

- `raw/` - Raw source data files (CSV, JSON, etc.)
- `processed/` - Processed/cleaned data ready for graph construction

## Sample Data Files

### flights_sample.csv
Contains 10 sample flights operating between ATL, LGA, and SLC airports on 2024-01-15.

**Minimum Required Fields for Basic Flight Modeling:**
- `carrier` - Airline code (e.g., DL, AA)
- `flight_number` - Flight number
- `origin` - Origin airport code (Dep_LOCID equivalent)
- `destination` - Destination airport code (Arr_LOCID equivalent)
- `scheduled_departure_gate` - Scheduled gate departure time (ISO 8601 GMT)
- `scheduled_arrival_gate` - Scheduled gate arrival time (ISO 8601 GMT)
- `actual_departure_gate` - Actual gate departure time (ISO 8601 GMT)
- `actual_arrival_gate` - Actual gate arrival time (ISO 8601 GMT)
- `equipment` - Aircraft type (e.g., B737, A320)
- `equipment_class` - Equipment class (J=jet, T=turbo, P=piston)
- `flight_date` - Flight date (YYYY-MM-DD)
- `flight_month_year` - Period identifier (YYYYMM)

**Notes:**
- All times are in GMT/UTC (ISO 8601 format with 'Z' suffix)
- Dates/times can be converted from GMT seconds since 1980-01-01 using the conversion function in the schema documentation
- Additional fields from the full schema can be added as needed

### airports_sample.csv
Contains basic airport information for the three airports used in sample flights.

**Fields:**
- `airport_code` - Airport identifier (3-4 character code)
- `airport_name` - Full airport name
- `city` - City name
- `state` - State/Province code
- `country` - Country code

**Notes:**
- Airport metrics (delays, efficiency scores, etc.) are aggregated from flight data and stored in graph nodes
- This file provides basic reference information only

## Data Format

### CSV Files
- Comma-separated values
- First row contains headers
- UTF-8 encoding
- ISO 8601 datetime format for timestamps (e.g., `2024-01-15T08:00:00Z`)

### Future Extensions
When adding more data:
1. Place raw data files in `raw/` directory
2. Processed/transformed data goes in `processed/` directory
3. Update this README with file descriptions

## Usage

These sample files can be used to:
1. Test graph construction code
2. Validate the data schema
3. Develop ETL pipelines
4. Create initial visualizations
5. Test temporal queries

## Schema Reference

See `docs/data_schema.md` for complete schema definitions and field mappings.
