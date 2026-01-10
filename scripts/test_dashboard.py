#!/usr/bin/env python3
"""
Test script to validate dashboard functionality without running Streamlit server.
Tests core functions and data loading.
"""

import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta

# Add parent directory to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    import networkx as nx
    from scripts.build_graph import load_graph, build_graph
    from scripts.example_usage import (
        parse_iso8601_datetime,
        get_airport_state_at_time,
        get_active_flights_at_time,
        get_events_in_window,
    )
    print("✅ All imports successful")
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)

# Import dashboard functions (but not streamlit parts)
sys.path.insert(0, str(project_root / 'scripts'))

# Test helper functions from dashboard
def test_get_time_range():
    """Test time range extraction."""
    print("\n📅 Testing time range extraction...")
    
    graph_file = project_root / 'data' / 'processed' / 't1.json'
    if not graph_file.exists():
        print("❌ Graph file not found. Building graph from CSV...")
        G = build_graph()
    else:
        print(f"✅ Loading graph from {graph_file}")
        G = load_graph(graph_file)
    
    # Get first departure and last arrival
    first_departure = None
    last_arrival = None
    
    for origin, destination, key, data in G.edges(data=True, keys=True):
        dep_time_str = data.get('actual_departure_gate') or data.get('scheduled_departure_gate')
        arr_time_str = data.get('actual_arrival_gate') or data.get('scheduled_arrival_gate')
        
        if dep_time_str:
            dep_time = parse_iso8601_datetime(dep_time_str)
            if dep_time and (first_departure is None or dep_time < first_departure):
                first_departure = dep_time
        
        if arr_time_str:
            arr_time = parse_iso8601_datetime(arr_time_str)
            if arr_time and (last_arrival is None or arr_time > last_arrival):
                last_arrival = arr_time
    
    if first_departure and last_arrival:
        print(f"✅ First departure: {first_departure.strftime('%Y-%m-%d %H:%M:%S')} UTC")
        print(f"✅ Last arrival: {last_arrival.strftime('%Y-%m-%d %H:%M:%S')} UTC")
        duration = (last_arrival - first_departure).total_seconds() / 60
        print(f"✅ Total duration: {duration:.1f} minutes")
        return G, first_departure, last_arrival
    else:
        print("❌ Could not determine time range")
        return G, None, None


def test_airport_state(G, current_time):
    """Test airport state retrieval."""
    print(f"\n📍 Testing airport state at {current_time.strftime('%H:%M:%S')} UTC...")
    
    airports = sorted(G.nodes())
    for airport_code in airports:
        state = get_airport_state_at_time(G, airport_code, current_time)
        if state:
            print(f"  {airport_code}: {state['total_departures']} dep, {state['total_arrivals']} arr")
        else:
            print(f"  {airport_code}: No activity yet")


def test_active_flights(G, current_time):
    """Test active flights retrieval."""
    print(f"\n✈️  Testing active flights at {current_time.strftime('%H:%M:%S')} UTC...")
    
    active_flights = get_active_flights_at_time(G, current_time)
    print(f"  Active flights: {len(active_flights)}")
    
    for flight in active_flights[:5]:  # Show first 5
        print(f"    - {flight['carrier']}{flight['flight_number']}: {flight['origin']} → {flight['destination']}")
    
    if len(active_flights) > 5:
        print(f"    ... and {len(active_flights) - 5} more")


def test_events_window(G, start_time, end_time):
    """Test events in time window."""
    print(f"\n📅 Testing events from {start_time.strftime('%H:%M:%S')} to {end_time.strftime('%H:%M:%S')} UTC...")
    
    events = get_events_in_window(G, start_time, end_time)
    print(f"  Events in window: {len(events)}")
    
    for event in events[:10]:  # Show first 10
        print(f"    - {event['timestamp'].strftime('%H:%M:%S')} UTC: {event['airport']} - {event['event_type'].upper()}")
    
    if len(events) > 10:
        print(f"    ... and {len(events) - 10} more")


def test_flight_volume_timeline(G, start_time, end_time):
    """Test flight volume timeline calculation."""
    print(f"\n📊 Testing flight volume timeline...")
    
    # Pre-compute all departure and arrival times
    departure_times = []
    arrival_times = []
    
    for origin, destination, key, data in G.edges(data=True, keys=True):
        dep_time_str = data.get('actual_departure_gate') or data.get('scheduled_departure_gate')
        arr_time_str = data.get('actual_arrival_gate') or data.get('scheduled_arrival_gate')
        
        if dep_time_str:
            dep_time = parse_iso8601_datetime(dep_time_str)
            if dep_time:
                departure_times.append(dep_time)
        
        if arr_time_str:
            arr_time = parse_iso8601_datetime(arr_time_str)
            if arr_time:
                arrival_times.append(arr_time)
    
    departure_times.sort()
    arrival_times.sort()
    
    print(f"  Total departures: {len(departure_times)}")
    print(f"  Total arrivals: {len(arrival_times)}")
    
    # Sample a few time points
    current_time = start_time
    sample_count = 0
    max_samples = 5
    
    while current_time <= end_time and sample_count < max_samples:
        # Count events up to current_time
        departures = sum(1 for dt in departure_times if dt <= current_time)
        arrivals = sum(1 for at in arrival_times if at <= current_time)
        
        print(f"  {current_time.strftime('%H:%M:%S')} UTC: {departures} dep, {arrivals} arr")
        
        current_time += timedelta(minutes=10)  # Sample every 10 minutes
        sample_count += 1


def main():
    """Run all tests."""
    print("=" * 60)
    print("🧪 Dashboard Functionality Test")
    print("=" * 60)
    
    # Test 1: Load graph and get time range
    G, first_departure, last_arrival = test_get_time_range()
    
    if not first_departure or not last_arrival:
        print("\n❌ Cannot continue tests without valid time range")
        return
    
    # Test 2: Airport state at initial time
    test_airport_state(G, first_departure)
    
    # Test 3: Airport state at mid-point
    mid_time = first_departure + (last_arrival - first_departure) / 2
    test_airport_state(G, mid_time)
    
    # Test 4: Airport state at end
    test_airport_state(G, last_arrival)
    
    # Test 5: Active flights at different times
    test_active_flights(G, first_departure)
    test_active_flights(G, mid_time)
    test_active_flights(G, last_arrival)
    
    # Test 6: Events in a window
    window_start = first_departure
    window_end = first_departure + timedelta(minutes=20)
    test_events_window(G, window_start, window_end)
    
    # Test 7: Flight volume timeline
    test_flight_volume_timeline(G, first_departure, last_arrival)
    
    print("\n" + "=" * 60)
    print("✅ All tests completed successfully!")
    print("=" * 60)
    print(f"\nGraph Summary:")
    print(f"  Nodes: {G.number_of_nodes()}")
    print(f"  Edges: {G.number_of_edges()}")
    print(f"  Multigraph: {G.is_multigraph()}")
    print(f"\n💡 To run the dashboard:")
    print(f"   streamlit run scripts/dashboard.py")


if __name__ == '__main__':
    main()
