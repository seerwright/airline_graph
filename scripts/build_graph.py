#!/usr/bin/env python3
"""
Build a NetworkX graph from flight and airport data.

This script creates a directed graph with:
- Nodes: Airports (ATL, LGA, SLC)
- Edges: Flights between airports
- All attributes follow the schema defined in docs/data_schema.md
"""

import sys
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List

import networkx as nx

# Add parent directory to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import the data loading functions from load_sample_data.py
# Handle import path issues
try:
    from scripts.load_sample_data import load_airports, load_flights, parse_iso8601_datetime
except ImportError:
    # Fallback: import directly if running as module
    import importlib.util
    load_sample_data_path = project_root / 'scripts' / 'load_sample_data.py'
    spec = importlib.util.spec_from_file_location("load_sample_data", load_sample_data_path)
    load_sample_data = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(load_sample_data)
    load_airports = load_sample_data.load_airports
    load_flights = load_sample_data.load_flights
    parse_iso8601_datetime = load_sample_data.parse_iso8601_datetime


def create_airport_nodes(G: nx.MultiDiGraph, airports: Dict[str, Dict]) -> None:
    """
    Add airport nodes to the graph.
    
    Uses Approach 1: Time-Windowed Attributes
    Nodes are persistent entities with time-windowed metrics.
    """
    print("\n🏢 Creating airport nodes...")
    
    for airport_code, airport_data in airports.items():
        # Create node with core attributes
        # For now, we'll add basic attributes and can aggregate metrics later
        node_attributes = {
            'airport_code': airport_code,
            'airport_name': airport_data.get('airport_name', ''),
            'city': airport_data.get('city', ''),
            'state': airport_data.get('state', ''),
            'country': airport_data.get('country', ''),
            'last_updated': datetime.now(timezone.utc).isoformat(),  # ISO 8601 string for JSON
            # Event-level snapshots will be added later when we process flights chronologically
            'time_snapshots': []
        }
        
        G.add_node(airport_code, **node_attributes)
        print(f"  ✓ Added airport node: {airport_code} ({airport_data.get('airport_name', '')})")
    
    print(f"  ✅ Created {len(airports)} airport nodes")


def create_flight_edges(G: nx.MultiDiGraph, flights: List[Dict]) -> None:
    """
    Add flight edges to the graph.
    
    Uses Approach 1: Time-Stamped Attributes
    Each edge includes temporal attributes with full datetime values.
    """
    print("\n✈️  Creating flight edges...")
    
    edges_added = 0
    
    for flight in flights:
        origin = flight.get('origin')
        destination = flight.get('destination')
        
        if not origin or not destination:
            print(f"  ⚠️  Skipping flight with missing origin/destination: {flight.get('flight_id', 'unknown')}")
            continue
        
        # Build edge attributes following the schema
        # All datetime values stored as ISO 8601 strings for JSON serialization
        edge_attributes = {
            'flight_id': flight.get('flight_id', ''),
            'flight_number': flight.get('flight_number', ''),
            'carrier': flight.get('carrier', ''),
            'equipment': flight.get('equipment', ''),
            'equipment_class': flight.get('equipment_class', ''),
            
            # Temporal attributes (stored as ISO 8601 strings)
            'scheduled_departure_gate': flight.get('scheduled_departure_gate').isoformat() if flight.get('scheduled_departure_gate') else None,
            'actual_departure_gate': flight.get('actual_departure_gate').isoformat() if flight.get('actual_departure_gate') else None,
            'scheduled_arrival_gate': flight.get('scheduled_arrival_gate').isoformat() if flight.get('scheduled_arrival_gate') else None,
            'actual_arrival_gate': flight.get('actual_arrival_gate').isoformat() if flight.get('actual_arrival_gate') else None,
            
            # Derived temporal attributes
            'flight_date': str(flight.get('flight_date')) if flight.get('flight_date') else None,
            'flight_month_year': flight.get('flight_month_year', ''),
            'departure_delay_minutes': flight.get('departure_delay_minutes'),
            'arrival_delay_minutes': flight.get('arrival_delay_minutes'),
        }
        
        # Remove None values to keep the graph clean
        edge_attributes = {k: v for k, v in edge_attributes.items() if v is not None}
        
        # Add edge (MultiDiGraph allows multiple edges between same airports)
        # Each flight is a separate edge, even if origin/destination are the same
        G.add_edge(origin, destination, **edge_attributes)
        edges_added += 1
        
        print(f"  ✓ Added edge: {origin} → {destination} ({flight.get('carrier', '')}{flight.get('flight_number', '')})")
    
    print(f"  ✅ Created {edges_added} flight edges")


def create_event_level_snapshots(G: nx.MultiDiGraph, flights: List[Dict]) -> None:
    """
    Create event-level snapshots for airport nodes.
    
    Uses event-level temporal tracking: snapshots created on every departure and arrival.
    Each snapshot tracks both incremental changes (delta) and cumulative values (totals).
    """
    print(f"\n📊 Creating event-level snapshots for airport nodes...")
    
    from collections import defaultdict
    
    # Track cumulative metrics per airport (updated as events occur)
    airport_cumulative = defaultdict(lambda: {
        'total_departures': 0,
        'total_arrivals': 0,
        'departure_delays': [],
        'arrival_delays': []
    })
    
    # Collect all events (departures and arrivals) with timestamps
    events = []
    
    for flight in flights:
        origin = flight.get('origin')
        destination = flight.get('destination')
        flight_id = flight.get('flight_id', '')
        
        if not origin or not destination:
            continue
        
        # Departure event (use actual departure time, fallback to scheduled)
        dep_time = flight.get('actual_departure_gate') or flight.get('scheduled_departure_gate')
        if dep_time:
            if isinstance(dep_time, str):
                dep_time = parse_iso8601_datetime(dep_time)
            if dep_time and isinstance(dep_time, datetime):
                events.append({
                    'airport': origin,
                    'event_type': 'departure',
                    'timestamp': dep_time,
                    'flight_id': flight_id,
                    'flight': flight
                })
        
        # Arrival event (use actual arrival time, fallback to scheduled)
        arr_time = flight.get('actual_arrival_gate') or flight.get('scheduled_arrival_gate')
        if arr_time:
            if isinstance(arr_time, str):
                arr_time = parse_iso8601_datetime(arr_time)
            if arr_time and isinstance(arr_time, datetime):
                events.append({
                    'airport': destination,
                    'event_type': 'arrival',
                    'timestamp': arr_time,
                    'flight_id': flight_id,
                    'flight': flight
                })
    
    # Sort events by timestamp
    events.sort(key=lambda e: e['timestamp'])
    
    # Process events chronologically and create snapshots
    for event in events:
        airport_code = event['airport']
        event_type = event['event_type']
        timestamp = event['timestamp']
        flight_id = event['flight_id']
        flight = event['flight']
        
        if airport_code not in G.nodes():
            continue
        
        # Initialize time_snapshots list if not exists
        if 'time_snapshots' not in G.nodes[airport_code]:
            G.nodes[airport_code]['time_snapshots'] = []
        
        # Calculate incremental changes (only what changed at this event)
        incremental = {}
        if event_type == 'departure':
            incremental['departures'] = 1
            if flight.get('departure_delay_minutes') is not None:
                incremental['departure_delay_minutes'] = flight['departure_delay_minutes']
        elif event_type == 'arrival':
            incremental['arrivals'] = 1
            if flight.get('arrival_delay_minutes') is not None:
                incremental['arrival_delay_minutes'] = flight['arrival_delay_minutes']
        
        # Update cumulative metrics
        if event_type == 'departure':
            airport_cumulative[airport_code]['total_departures'] += 1
            if flight.get('departure_delay_minutes') is not None:
                airport_cumulative[airport_code]['departure_delays'].append(flight['departure_delay_minutes'])
        elif event_type == 'arrival':
            airport_cumulative[airport_code]['total_arrivals'] += 1
            if flight.get('arrival_delay_minutes') is not None:
                airport_cumulative[airport_code]['arrival_delays'].append(flight['arrival_delay_minutes'])
        
        # Calculate cumulative values
        cumulative = airport_cumulative[airport_code]
        total_dep = cumulative['total_departures']
        total_arr = cumulative['total_arrivals']
        
        # Calculate average delays
        dep_delays = cumulative['departure_delays']
        arr_delays = cumulative['arrival_delays']
        avg_dep_delay = sum(dep_delays) / len(dep_delays) if dep_delays else 0.0
        avg_arr_delay = sum(arr_delays) / len(arr_delays) if arr_delays else 0.0
        
        # Count on-time flights
        on_time_dep = sum(1 for d in dep_delays if abs(d) < 15) if dep_delays else 0
        on_time_arr = sum(1 for d in arr_delays if abs(d) < 15) if arr_delays else 0
        on_time_dep_pct = (on_time_dep / total_dep * 100) if total_dep > 0 else 0.0
        on_time_arr_pct = (on_time_arr / total_arr * 100) if total_arr > 0 else 0.0
        
        # Create snapshot
        snapshot = {
            'timestamp': timestamp.isoformat(),  # ISO 8601 string for JSON
            'event_type': event_type,
            'event_flight_id': flight_id,
            'incremental': incremental,  # Already filtered to only changed values
            'cumulative': {
                'total_departures': total_dep,
                'total_arrivals': total_arr,
                'avg_departure_delay': round(avg_dep_delay, 2),
                'avg_arrival_delay': round(avg_arr_delay, 2),
                'on_time_departure_pct': round(on_time_dep_pct, 2),
                'on_time_arrival_pct': round(on_time_arr_pct, 2)
            }
        }
        
        # Add snapshot to list (ordered by timestamp)
        G.nodes[airport_code]['time_snapshots'].append(snapshot)
        G.nodes[airport_code]['last_updated'] = timestamp.isoformat()
    
    # Print summary
    for airport_code in sorted(airport_cumulative.keys()):
        snapshots_count = len(G.nodes[airport_code].get('time_snapshots', []))
        cumulative = airport_cumulative[airport_code]
        print(f"  ✓ {airport_code}: {snapshots_count} snapshots ({cumulative['total_departures']} departures, {cumulative['total_arrivals']} arrivals)")
    
    print(f"  ✅ Created event-level snapshots for {len(airport_cumulative)} airports")


def build_graph(data_dir: Path = None) -> nx.MultiDiGraph:
    """
    Build the complete graph from flight and airport data.
    
    Returns:
        NetworkX MultiDiGraph with airports as nodes and flights as edges.
        MultiDiGraph allows multiple edges between the same airports (multiple flights).
    """
    if data_dir is None:
        project_root = Path(__file__).parent.parent
        data_dir = project_root / 'data' / 'raw'
    
    print("🚀 Building Flight Graph")
    print("=" * 60)
    
    # Load data
    airports_file = data_dir / 'airports_sample.csv'
    flights_file = data_dir / 'flights_sample.csv'
    
    print("\n📁 Loading data files...")
    airports = load_airports(airports_file)
    flights = load_flights(flights_file, airports)
    
    if not airports or not flights:
        print("❌ Failed to load data. Cannot build graph.")
        return nx.MultiDiGraph()
    
    # Create directed multigraph (allows multiple edges between same airports)
    G = nx.MultiDiGraph()
    
    # Add nodes (airports)
    create_airport_nodes(G, airports)
    
    # Add edges (flights)
    create_flight_edges(G, flights)
    
    # Create event-level snapshots for airports (event-based temporal tracking)
    create_event_level_snapshots(G, flights)
    
    # Print graph summary
    print("\n" + "=" * 60)
    print("📊 Graph Summary")
    print("=" * 60)
    print(f"Nodes (Airports): {G.number_of_nodes()}")
    print(f"Edges (Flights): {G.number_of_edges()}")
    print(f"Is Directed: {G.is_directed()}")
    print(f"Is Multigraph: {G.is_multigraph()}")
    
    # Show airport nodes
    print(f"\nAirport Nodes:")
    for node in sorted(G.nodes()):
        node_data = G.nodes[node]
        print(f"  - {node}: {node_data.get('airport_name', 'N/A')}")
        if 'time_snapshots' in node_data:
            snapshots_count = len(node_data['time_snapshots'])
            print(f"    Event snapshots: {snapshots_count}")
            if snapshots_count > 0:
                first_snapshot = node_data['time_snapshots'][0]
                last_snapshot = node_data['time_snapshots'][-1]
                print(f"    First event: {first_snapshot.get('timestamp', 'N/A')} ({first_snapshot.get('event_type', 'N/A')})")
                print(f"    Last event: {last_snapshot.get('timestamp', 'N/A')} ({last_snapshot.get('event_type', 'N/A')})")
                # Show cumulative totals from last snapshot
                if 'cumulative' in last_snapshot:
                    cum = last_snapshot['cumulative']
                    print(f"    Totals: {cum.get('total_departures', 0)} departures, {cum.get('total_arrivals', 0)} arrivals")
    
    # Show routes
    print(f"\nRoutes (Edges):")
    routes = {}
    # MultiDiGraph edges include a key parameter: (u, v, key, data)
    for origin, destination, key, data in G.edges(data=True, keys=True):
        route = f"{origin} → {destination}"
        if route not in routes:
            routes[route] = []
        routes[route].append(data.get('flight_id', 'unknown'))
    
    for route, flight_ids in sorted(routes.items()):
        print(f"  - {route}: {len(flight_ids)} flight(s)")
        for flight_id in flight_ids[:3]:  # Show first 3 flight IDs
            print(f"    * {flight_id}")
        if len(flight_ids) > 3:
            print(f"    ... and {len(flight_ids) - 3} more")
    
    print("\n" + "=" * 60)
    print("✅ Graph construction completed successfully!")
    print("=" * 60)
    
    return G


def save_graph(G: nx.MultiDiGraph, output_file: Path) -> None:
    """Save graph to file in JSON-compatible format."""
    print(f"\n💾 Saving graph to: {output_file}")
    
    # NetworkX can save to various formats
    # For JSON compatibility, we'll use node-link format
    # MultiDiGraph is automatically detected and saved with multigraph: true
    import json
    
    # Ensure output directory exists
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Convert to node-link format (JSON serializable)
    graph_data = nx.node_link_data(G)
    
    # Write to JSON file
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(graph_data, f, indent=2, ensure_ascii=False)
    
    file_size_kb = output_file.stat().st_size / 1024
    print(f"  ✅ Graph saved successfully ({file_size_kb:.2f} KB)")
    print(f"     Nodes: {len(graph_data.get('nodes', []))}")
    print(f"     Edges: {len(graph_data.get('edges', []))}")
    print(f"     Multigraph: {graph_data.get('multigraph', False)}")


def load_graph(input_file: Path) -> nx.MultiDiGraph:
    """Load graph from JSON file."""
    import json
    
    print(f"\n📂 Loading graph from: {input_file}")
    
    if not input_file.exists():
        raise FileNotFoundError(f"Graph file not found: {input_file}")
    
    # Read JSON file
    with open(input_file, 'r', encoding='utf-8') as f:
        graph_data = json.load(f)
    
    # Convert from node-link format
    # NetworkX automatically detects multigraph from the JSON data
    # If multigraph: true in JSON, it creates MultiDiGraph; otherwise DiGraph
    G = nx.node_link_graph(graph_data)
    
    print(f"  ✅ Graph loaded successfully")
    print(f"     Nodes: {G.number_of_nodes()}")
    print(f"     Edges: {G.number_of_edges()}")
    print(f"     Multigraph: {G.is_multigraph()}")
    
    return G


def main():
    """Main function to build and optionally save the graph."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Build flight graph from sample data')
    parser.add_argument('--save', '-s', type=str, help='Save graph to JSON file')
    parser.add_argument('--load', '-l', type=str, help='Load graph from JSON file (instead of building)')
    parser.add_argument('--data-dir', '-d', type=str, help='Directory containing data files')
    
    args = parser.parse_args()
    
    # Load existing graph or build new one
    if args.load:
        input_file = Path(args.load)
        G = load_graph(input_file)
    else:
        # Build graph
        data_dir = Path(args.data_dir) if args.data_dir else None
        G = build_graph(data_dir)
    
    # Save if requested
    if args.save:
        output_file = Path(args.save)
        save_graph(G, output_file)
    
    return G


if __name__ == '__main__':
    G = main()
