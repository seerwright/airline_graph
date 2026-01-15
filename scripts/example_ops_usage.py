#!/usr/bin/env python3
"""
Example usage of the Operations Resource Graph.

This script demonstrates:
- Building the operations graph
- Querying resource connections
- Analyzing resource utilization
- Temporal queries for resource availability
"""

import sys
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Set

# Add parent directory to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scripts.build_operations_graph import build_graph, load_graph, save_graph
from scripts.load_sample_data import parse_iso8601_datetime
import networkx as nx


def get_active_connections_at_time(G: nx.MultiDiGraph, target_time: datetime) -> List[tuple]:
    """
    Get all resource connections active at a specific time.
    
    A connection is active if:
    - Source flight has arrived (actual or scheduled)
    - Target flight hasn't departed yet (scheduled)
    """
    if isinstance(target_time, str):
        target_time = parse_iso8601_datetime(target_time)
    
    if not target_time:
        return []
    
    active = []
    
    for src_flight, tgt_flight, key, data in G.edges(keys=True, data=True):
        src_node = G.nodes[src_flight]
        tgt_node = G.nodes[tgt_flight]
        
        # Get source flight arrival time (prefer actual, fallback to scheduled)
        src_arr_str = src_node.get('act_arr_gmt') or src_node.get('sch_arr_gmt')
        src_arr = parse_iso8601_datetime(src_arr_str) if src_arr_str else None
        
        # Get target flight departure time (scheduled)
        tgt_dep_str = tgt_node.get('sch_dep_gmt')
        tgt_dep = parse_iso8601_datetime(tgt_dep_str) if tgt_dep_str else None
        
        if src_arr and tgt_dep:
            # Connection is active if source has arrived and target hasn't departed
            if src_arr <= target_time < tgt_dep:
                active.append((src_flight, tgt_flight, key, data))
    
    return active


def get_flights_by_resource(
    G: nx.MultiDiGraph,
    resource_type: str,
    resource_id: str,
    start_time: datetime = None,
    end_time: datetime = None
) -> Set[str]:
    """
    Get all flights connected via a specific resource in a time window.
    
    Args:
        G: Operations graph
        resource_type: Edge type (e.g., "AIRCRAFT_TURN", "CREW_PILOT", "CREW_FA")
        resource_id: Resource identifier (e.g., tail number "8231", crew ID "P1001")
        start_time: Optional start time filter
        end_time: Optional end time filter
    
    Returns:
        Set of flight IDs using this resource
    """
    if isinstance(start_time, str):
        start_time = parse_iso8601_datetime(start_time)
    if isinstance(end_time, str):
        end_time = parse_iso8601_datetime(end_time)
    
    flights = set()
    
    for src_flight, tgt_flight, key, data in G.edges(keys=True, data=True):
        if data.get('type') == resource_type and data.get('edge_label') == resource_id:
            src_node = G.nodes[src_flight]
            tgt_node = G.nodes[tgt_flight]
            
            # Get flight times
            src_dep_str = src_node.get('sch_dep_gmt')
            src_dep = parse_iso8601_datetime(src_dep_str) if src_dep_str else None
            tgt_arr_str = tgt_node.get('act_arr_gmt') or tgt_node.get('sch_arr_gmt')
            tgt_arr = parse_iso8601_datetime(tgt_arr_str) if tgt_arr_str else None
            
            # Apply time window filter if provided
            if start_time or end_time:
                if src_dep:
                    if start_time and src_dep < start_time:
                        continue
                    if end_time and src_dep > end_time:
                        continue
                if tgt_arr:
                    if start_time and tgt_arr < start_time:
                        continue
                    if end_time and tgt_arr > end_time:
                        continue
            
            flights.add(src_flight)
            flights.add(tgt_flight)
    
    return flights


def get_resource_connections_for_flight(G: nx.MultiDiGraph, flight_id: str) -> Dict[str, List]:
    """
    Get all resource connections for a specific flight.
    
    Returns:
        Dictionary with keys: 'incoming' (resources arriving at this flight)
                              'outgoing' (resources departing from this flight)
    """
    incoming = []
    outgoing = []
    
    # Incoming edges (resources arriving at this flight)
    for src_flight, tgt_flight, key, data in G.in_edges(flight_id, keys=True, data=True):
        incoming.append({
            'source_flight': src_flight,
            'resource_type': data.get('type', 'unknown'),
            'resource_id': data.get('edge_label', ''),
            'activity': data.get('edge_activity', ''),
        })
    
    # Outgoing edges (resources departing from this flight)
    for src_flight, tgt_flight, key, data in G.out_edges(flight_id, keys=True, data=True):
        outgoing.append({
            'target_flight': tgt_flight,
            'resource_type': data.get('type', 'unknown'),
            'resource_id': data.get('edge_label', ''),
            'activity': data.get('edge_activity', ''),
        })
    
    return {
        'incoming': incoming,
        'outgoing': outgoing,
    }


def get_delayed_flights_affecting_resources(G: nx.MultiDiGraph, delay_threshold_minutes: int = 15) -> Dict[str, List]:
    """
    Find flights with delays that could affect downstream flights via resource connections.
    
    Returns:
        Dictionary mapping delayed flight IDs to list of potentially affected flights
    """
    affected_flights = {}
    
    for flight_id in G.nodes():
        node = G.nodes[flight_id]
        
        # Check if flight has delay
        sch_arr_str = node.get('sch_arr_gmt')
        act_arr_str = node.get('act_arr_gmt')
        
        if not sch_arr_str or not act_arr_str:
            continue
        
        sch_arr = parse_iso8601_datetime(sch_arr_str)
        act_arr = parse_iso8601_datetime(act_arr_str)
        
        if not sch_arr or not act_arr:
            continue
        
        delay_minutes = (act_arr - sch_arr).total_seconds() / 60
        
        if delay_minutes > delay_threshold_minutes:
            # Find all downstream flights via resource connections
            downstream = []
            for src_flight, tgt_flight, key, data in G.out_edges(flight_id, keys=True, data=True):
                downstream.append({
                    'flight_id': tgt_flight,
                    'resource_type': data.get('type', 'unknown'),
                    'resource_id': data.get('edge_label', ''),
                })
            
            if downstream:
                affected_flights[flight_id] = {
                    'delay_minutes': delay_minutes,
                    'downstream_flights': downstream,
                }
    
    return affected_flights


def print_graph_summary(G: nx.MultiDiGraph):
    """Print a summary of the operations graph."""
    print("\n" + "=" * 60)
    print("📊 Operations Resource Graph Summary")
    print("=" * 60)
    
    print(f"\n📈 Graph Statistics:")
    print(f"  Nodes (Flights): {G.number_of_nodes()}")
    print(f"  Edges (Connections): {G.number_of_edges()}")
    print(f"  Model: {G.graph.get('model', 'unknown')}")
    
    # Count edges by type
    edge_types = {}
    for src, tgt, key, data in G.edges(keys=True, data=True):
        edge_type = data.get('type', 'unknown')
        edge_types[edge_type] = edge_types.get(edge_type, 0) + 1
    
    print(f"\n🔗 Edge Types:")
    for edge_type, count in sorted(edge_types.items()):
        print(f"  {edge_type}: {count}")
    
    # Show sample flights
    print(f"\n✈️  Sample Flights (first 5):")
    for i, flight_id in enumerate(list(G.nodes())[:5], 1):
        node = G.nodes[flight_id]
        print(f"  {i}. {flight_id}")
        print(f"     Route: {node.get('origin', '?')} → {node.get('destination', '?')}")
        print(f"     Dep: {node.get('sch_dep_gmt', '?')}")
        print(f"     Arr: {node.get('act_arr_gmt', '?') or node.get('sch_arr_gmt', '?')}")


def main():
    """Main example usage."""
    project_root = Path(__file__).parent.parent
    data_dir = project_root / 'data' / 'raw'
    processed_dir = project_root / 'data' / 'processed'
    
    # Try to load existing graph, or build new one
    ops_graph_file = processed_dir / 'ops_graph.json'
    
    if ops_graph_file.exists():
        print("📂 Loading existing operations graph...")
        G = load_graph(ops_graph_file)
    else:
        print("🚀 Building operations graph...")
        G = build_graph()
        save_graph(G, ops_graph_file)
    
    # Print summary
    print_graph_summary(G)
    
    # Example 1: Get resource connections for a specific flight
    print("\n" + "=" * 60)
    print("Example 1: Resource Connections for Flight")
    print("=" * 60)
    
    sample_flight = list(G.nodes())[0] if G.nodes() else None
    if sample_flight:
        connections = get_resource_connections_for_flight(G, sample_flight)
        print(f"\nFlight: {sample_flight}")
        print(f"\n  Incoming resources: {len(connections['incoming'])}")
        for conn in connections['incoming']:
            print(f"    - {conn['resource_type']} {conn['resource_id']} from {conn['source_flight']}")
        
        print(f"\n  Outgoing resources: {len(connections['outgoing'])}")
        for conn in connections['outgoing']:
            print(f"    - {conn['resource_type']} {conn['resource_id']} to {conn['target_flight']}")
    
    # Example 2: Get flights using a specific aircraft
    print("\n" + "=" * 60)
    print("Example 2: Flights Using Specific Aircraft")
    print("=" * 60)
    
    aircraft_id = "8231"  # Example aircraft
    flights = get_flights_by_resource(G, "AIRCRAFT_TURN", aircraft_id)
    print(f"\nAircraft {aircraft_id} is used by {len(flights)} flights:")
    for flight_id in sorted(flights):
        node = G.nodes[flight_id]
        print(f"  - {flight_id}: {node.get('origin', '?')} → {node.get('destination', '?')}")
    
    # Example 3: Find delayed flights affecting downstream flights
    print("\n" + "=" * 60)
    print("Example 3: Delay Cascade Analysis")
    print("=" * 60)
    
    delayed = get_delayed_flights_affecting_resources(G, delay_threshold_minutes=0)
    print(f"\nFound {len(delayed)} delayed flights with downstream connections:")
    for flight_id, info in list(delayed.items())[:3]:  # Show first 3
        print(f"\n  Flight: {flight_id}")
        print(f"    Delay: {info['delay_minutes']:.1f} minutes")
        print(f"    Affects {len(info['downstream_flights'])} downstream flights:")
        for downstream in info['downstream_flights']:
            print(f"      - {downstream['flight_id']} (via {downstream['resource_type']} {downstream['resource_id']})")
    
    # Example 4: Active connections at a specific time
    print("\n" + "=" * 60)
    print("Example 4: Active Connections at Specific Time")
    print("=" * 60)
    
    # Use a time in the middle of the flight schedule
    target_time_str = "2026-01-01T10:00:00Z"
    target_time = parse_iso8601_datetime(target_time_str)
    
    active = get_active_connections_at_time(G, target_time)
    print(f"\nActive connections at {target_time_str}: {len(active)}")
    for src, tgt, key, data in active[:5]:  # Show first 5
        print(f"  {src} --[{data.get('type', '?')} {data.get('edge_label', '?')}]--> {tgt}")


if __name__ == '__main__':
    main()
