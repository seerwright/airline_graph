#!/usr/bin/env python3
"""
Load and validate sample flight and airport data.

This script loads the sample CSV files and validates:
- Data structure and required fields
- Data types and formats
- Temporal attributes (ISO 8601 GMT dates)
- Airport codes and flight routes
- Schema compliance
"""

import csv
import sys
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Tuple, Optional

# Add parent directory to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def parse_iso8601_datetime(date_str: str) -> Optional[datetime]:
    """Parse ISO 8601 datetime string to datetime object."""
    if not date_str or date_str.strip() == '':
        return None
    
    try:
        # Handle ISO 8601 format with Z suffix (UTC)
        if date_str.endswith('Z'):
            date_str = date_str[:-1] + '+00:00'
        
        # Parse with timezone support
        dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, AttributeError) as e:
        print(f"  ⚠️  Error parsing datetime '{date_str}': {e}")
        return None


def load_airports(file_path: Path) -> Dict[str, Dict]:
    """Load airports from CSV file."""
    airports = {}
    
    if not file_path.exists():
        print(f"⚠️  Airport file not found: {file_path}")
        return airports
    
    print(f"\n📁 Loading airports from: {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for row_num, row in enumerate(reader, start=2):
            airport_code = row.get('airport_code', '').strip().upper()
            
            if not airport_code:
                print(f"  ⚠️  Row {row_num}: Missing airport_code, skipping")
                continue
            
            airports[airport_code] = {
                'airport_code': airport_code,
                'airport_name': row.get('airport_name', '').strip(),
                'city': row.get('city', '').strip(),
                'state': row.get('state', '').strip(),
                'country': row.get('country', '').strip(),
            }
    
    print(f"  ✓ Loaded {len(airports)} airports: {', '.join(sorted(airports.keys()))}")
    return airports


def load_flights(file_path: Path, airports: Dict[str, Dict]) -> List[Dict]:
    """Load flights from CSV file and validate against airports."""
    flights = []
    errors = []
    warnings = []
    
    print(f"\n📁 Loading flights from: {file_path}")
    
    if not file_path.exists():
        print(f"  ❌ Flight file not found: {file_path}")
        return flights
    
    required_fields = [
        'carrier', 'flight_number', 'origin', 'destination',
        'scheduled_departure_gate', 'scheduled_arrival_gate',
        'actual_departure_gate', 'actual_arrival_gate',
        'flight_date', 'flight_month_year'
    ]
    
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        # Validate header
        header = reader.fieldnames or []
        missing_fields = [f for f in required_fields if f not in header]
        if missing_fields:
            errors.append(f"Missing required fields in header: {', '.join(missing_fields)}")
        
        for row_num, row in enumerate(reader, start=2):
            flight = {}
            row_errors = []
            row_warnings = []
            
            # Required string fields
            carrier = row.get('carrier', '').strip().upper()
            flight_number = row.get('flight_number', '').strip()
            origin = row.get('origin', '').strip().upper()
            destination = row.get('destination', '').strip().upper()
            
            # Validate required fields
            if not carrier:
                row_errors.append("Missing carrier")
            if not flight_number:
                row_errors.append("Missing flight_number")
            if not origin:
                row_errors.append("Missing origin")
            if not destination:
                row_errors.append("Missing destination")
            
            # Validate airports exist
            if origin and origin not in airports:
                row_warnings.append(f"Origin airport '{origin}' not found in airports data")
            if destination and destination not in airports:
                row_warnings.append(f"Destination airport '{destination}' not found in airports data")
            
            # Validate route
            if origin == destination:
                row_errors.append(f"Origin and destination are the same: {origin}")
            
            # Parse temporal fields
            scheduled_departure = parse_iso8601_datetime(row.get('scheduled_departure_gate', ''))
            actual_departure = parse_iso8601_datetime(row.get('actual_departure_gate', ''))
            scheduled_arrival = parse_iso8601_datetime(row.get('scheduled_arrival_gate', ''))
            actual_arrival = parse_iso8601_datetime(row.get('actual_arrival_gate', ''))
            
            if not scheduled_departure:
                row_errors.append("Missing or invalid scheduled_departure_gate")
            if not scheduled_arrival:
                row_errors.append("Missing or invalid scheduled_arrival_gate")
            if not actual_departure:
                row_warnings.append("Missing or invalid actual_departure_gate")
            if not actual_arrival:
                row_warnings.append("Missing or invalid actual_arrival_gate")
            
            # Validate temporal logic
            if scheduled_departure and scheduled_arrival:
                if scheduled_departure >= scheduled_arrival:
                    row_errors.append("Scheduled departure must be before scheduled arrival")
            
            if actual_departure and actual_arrival:
                if actual_departure >= actual_arrival:
                    row_errors.append("Actual departure must be before actual arrival")
            
            # Parse date fields
            flight_date_str = row.get('flight_date', '').strip()
            flight_month_year = row.get('flight_month_year', '').strip()
            
            try:
                flight_date = datetime.fromisoformat(flight_date_str).date() if flight_date_str else None
            except ValueError:
                flight_date = None
                row_errors.append(f"Invalid flight_date format: {flight_date_str}")
            
            # Validate month_year format (YYYYMM)
            if flight_month_year and len(flight_month_year) != 6:
                row_warnings.append(f"flight_month_year should be YYYYMM format, got: {flight_month_year}")
            
            # Build flight dict
            flight = {
                'carrier': carrier,
                'flight_number': flight_number,
                'origin': origin,
                'destination': destination,
                'scheduled_departure_gate': scheduled_departure,
                'actual_departure_gate': actual_departure,
                'scheduled_arrival_gate': scheduled_arrival,
                'actual_arrival_gate': actual_arrival,
                'equipment': row.get('equipment', '').strip(),
                'equipment_class': row.get('equipment_class', '').strip().upper(),
                'flight_date': flight_date,
                'flight_month_year': flight_month_year,
            }
            
            # Calculate delays if both scheduled and actual times available
            if scheduled_departure and actual_departure:
                delay_seconds = (actual_departure - scheduled_departure).total_seconds()
                flight['departure_delay_minutes'] = int(delay_seconds / 60)
            else:
                flight['departure_delay_minutes'] = None
            
            if scheduled_arrival and actual_arrival:
                delay_seconds = (actual_arrival - scheduled_arrival).total_seconds()
                flight['arrival_delay_minutes'] = int(delay_seconds / 60)
            else:
                flight['arrival_delay_minutes'] = None
            
            # Generate flight_id
            if carrier and flight_number and origin and destination and flight_date:
                flight['flight_id'] = f"{carrier}{flight_number}_{flight_date}_{origin}_{destination}"
            else:
                flight['flight_id'] = None
            
            # Report errors and warnings
            if row_errors:
                errors.append(f"Row {row_num}: {', '.join(row_errors)}")
            if row_warnings:
                warnings.extend([f"Row {row_num}: {w}" for w in row_warnings])
            
            # Only add flights without critical errors
            if not row_errors:
                flights.append(flight)
            else:
                print(f"  ❌ Row {row_num}: Skipped due to errors: {', '.join(row_errors)}")
    
    print(f"  ✓ Loaded {len(flights)} valid flights")
    
    if warnings:
        print(f"  ⚠️  {len(warnings)} warnings:")
        for warning in warnings[:5]:  # Show first 5 warnings
            print(f"    - {warning}")
        if len(warnings) > 5:
            print(f"    ... and {len(warnings) - 5} more warnings")
    
    if errors:
        print(f"  ❌ {len(errors)} errors:")
        for error in errors[:5]:  # Show first 5 errors
            print(f"    - {error}")
        if len(errors) > 5:
            print(f"    ... and {len(errors) - 5} more errors")
    
    return flights


def validate_data(airports: Dict[str, Dict], flights: List[Dict]) -> Tuple[bool, List[str]]:
    """Validate loaded data for schema compliance."""
    issues = []
    
    print(f"\n🔍 Validating data schema compliance...")
    
    # Validate airports
    if len(airports) == 0:
        issues.append("No airports loaded")
    else:
        for code, airport in airports.items():
            if not airport.get('airport_code'):
                issues.append(f"Airport {code}: Missing airport_code attribute")
    
    # Validate flights
    if len(flights) == 0:
        issues.append("No flights loaded")
        return False, issues
    
    # Check route coverage
    unique_origins = set(f['origin'] for f in flights)
    unique_destinations = set(f['destination'] for f in flights)
    unique_airports_in_flights = unique_origins | unique_destinations
    
    airports_not_in_data = unique_airports_in_flights - set(airports.keys())
    if airports_not_in_data:
        issues.append(f"Flights reference airports not in airport data: {', '.join(sorted(airports_not_in_data))}")
    
    # Validate flight attributes
    for flight in flights:
        if not flight.get('flight_id'):
            issues.append(f"Flight {flight.get('carrier', '?')}{flight.get('flight_number', '?')}: Missing flight_id")
        
        if flight.get('scheduled_departure_gate') and not flight['scheduled_departure_gate'].tzinfo:
            issues.append(f"Flight {flight.get('flight_id', '?')}: scheduled_departure_gate missing timezone")
        
        if flight.get('scheduled_arrival_gate') and not flight['scheduled_arrival_gate'].tzinfo:
            issues.append(f"Flight {flight.get('flight_id', '?')}: scheduled_arrival_gate missing timezone")
    
    # Check for duplicate flight_ids
    flight_ids = [f.get('flight_id') for f in flights if f.get('flight_id')]
    duplicates = [fid for fid in set(flight_ids) if flight_ids.count(fid) > 1]
    if duplicates:
        issues.append(f"Duplicate flight_ids found: {', '.join(duplicates)}")
    
    if issues:
        print(f"  ❌ Found {len(issues)} validation issues")
        for issue in issues[:10]:  # Show first 10 issues
            print(f"    - {issue}")
        if len(issues) > 10:
            print(f"    ... and {len(issues) - 10} more issues")
        return False, issues
    else:
        print(f"  ✓ All validation checks passed")
        return True, []


def print_summary(airports: Dict[str, Dict], flights: List[Dict]):
    """Print summary statistics."""
    print(f"\n📊 Data Summary")
    print(f"=" * 60)
    
    print(f"\nAirports: {len(airports)}")
    for code, airport in sorted(airports.items()):
        print(f"  - {code}: {airport.get('airport_name', 'N/A')} ({airport.get('city', 'N/A')}, {airport.get('state', 'N/A')})")
    
    print(f"\nFlights: {len(flights)}")
    
    # Route statistics
    routes = {}
    for flight in flights:
        route = f"{flight['origin']} → {flight['destination']}"
        routes[route] = routes.get(route, 0) + 1
    
    print(f"\nRoutes ({len(routes)} unique):")
    for route, count in sorted(routes.items()):
        print(f"  - {route}: {count} flight(s)")
    
    # Carrier statistics
    carriers = {}
    for flight in flights:
        carrier = flight.get('carrier', 'UNKNOWN')
        carriers[carrier] = carriers.get(carrier, 0) + 1
    
    print(f"\nCarriers ({len(carriers)} unique):")
    for carrier, count in sorted(carriers.items()):
        print(f"  - {carrier}: {count} flight(s)")
    
    # Delay statistics
    departure_delays = [f['departure_delay_minutes'] for f in flights if f.get('departure_delay_minutes') is not None]
    arrival_delays = [f['arrival_delay_minutes'] for f in flights if f.get('arrival_delay_minutes') is not None]
    
    if departure_delays:
        avg_dep_delay = sum(departure_delays) / len(departure_delays)
        print(f"\nDeparture Delays:")
        print(f"  - Average: {avg_dep_delay:.1f} minutes")
        print(f"  - On-time (< 15 min): {sum(1 for d in departure_delays if abs(d) < 15)} flights")
        print(f"  - Delayed (> 15 min): {sum(1 for d in departure_delays if d >= 15)} flights")
        print(f"  - Early: {sum(1 for d in departure_delays if d < -1)} flights")
    
    if arrival_delays:
        avg_arr_delay = sum(arrival_delays) / len(arrival_delays)
        print(f"\nArrival Delays:")
        print(f"  - Average: {avg_arr_delay:.1f} minutes")
        print(f"  - On-time (< 15 min): {sum(1 for d in arrival_delays if abs(d) < 15)} flights")
        print(f"  - Delayed (> 15 min): {sum(1 for d in arrival_delays if d >= 15)} flights")
        print(f"  - Early: {sum(1 for d in arrival_delays if d < -1)} flights")
    
    # Temporal coverage
    flight_dates = set(f.get('flight_date') for f in flights if f.get('flight_date'))
    flight_months = set(f.get('flight_month_year') for f in flights if f.get('flight_month_year'))
    
    print(f"\nTemporal Coverage:")
    print(f"  - Dates: {len(flight_dates)} unique date(s): {', '.join(sorted(str(d) for d in flight_dates))}")
    print(f"  - Periods (YYYYMM): {len(flight_months)} unique period(s): {', '.join(sorted(flight_months))}")
    
    print(f"\n{'=' * 60}")


def main():
    """Main function to load and validate sample data."""
    print("🚀 Loading and Validating Sample Airline Data")
    print("=" * 60)
    
    # Get data directory paths
    project_root = Path(__file__).parent.parent
    data_dir = project_root / 'data' / 'raw'
    
    airports_file = data_dir / 'airports_sample.csv'
    flights_file = data_dir / 'flights_sample.csv'
    
    # Load data
    airports = load_airports(airports_file)
    flights = load_flights(flights_file, airports)
    
    # Validate data
    is_valid, issues = validate_data(airports, flights)
    
    # Print summary
    print_summary(airports, flights)
    
    # Return status
    if is_valid and len(flights) > 0:
        print(f"\n✅ Data loading and validation completed successfully!")
        print(f"   Ready for graph construction with:")
        print(f"   - {len(airports)} airports")
        print(f"   - {len(flights)} flights")
        return 0
    else:
        print(f"\n❌ Data validation failed. Please fix issues before proceeding.")
        return 1


if __name__ == '__main__':
    sys.exit(main())
