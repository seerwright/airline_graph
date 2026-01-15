#!/usr/bin/env python3
"""
Build a NetworkX graph from flight connection data.

This script creates a directed multigraph with:
- Nodes: Flights (and optionally Aircraft/Crew in Model 2)
- Edges: Resource connections between flights (AIRCRAFT_TURN, CREW_PILOT, CREW_FA)
- All attributes follow the schema defined in docs/feature__operations_resource_graph.md
"""

import sys
import csv
import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Tuple, Optional

import networkx as nx

# Add parent directory to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import the datetime parsing function from load_sample_data.py
try:
    from scripts.load_sample_data import parse_iso8601_datetime
except ImportError:
    # Fallback: import directly if running as module
    import importlib.util
    load_sample_data_path = project_root / 'scripts' / 'load_sample_data.py'
    spec = importlib.util.spec_from_file_location("load_sample_data", load_sample_data_path)
    load_sample_data = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(load_sample_data)
    parse_iso8601_datetime = load_sample_data.parse_iso8601_datetime


def parse_flight_id(flight_id: str) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str], Optional[str]]:
    """
    Parse flight ID format: "WN1234_2026-01-01_ATL_LGA"
    
    Returns: (carrier, flight_number, flight_date, origin, destination)
    """
    if not flight_id or not flight_id.strip():
        return (None, None, None, None, None)
    
    try:
        # Format: "{carrier}{flight_number}_{date}_{origin}_{destination}"
        parts = flight_id.split('_')
        if len(parts) != 4:
            print(f"  ⚠️  Invalid flight ID format: {flight_id} (expected 4 parts separated by '_')")
            return (None, None, None, None, None)
        
        carrier_flight = parts[0]  # e.g., "WN1234"
        flight_date = parts[1]    # e.g., "2026-01-01"
        origin = parts[2]          # e.g., "ATL"
        destination = parts[3]     # e.g., "LGA"
        
        # Extract carrier and flight number
        # Assume carrier is 2-3 characters, rest is flight number
        if len(carrier_flight) < 3:
            print(f"  ⚠️  Invalid carrier/flight format: {carrier_flight}")
            return (None, None, None, None, None)
        
        # Try 2-char carrier first (most common)
        if carrier_flight[2].isdigit():
            carrier = carrier_flight[:2]
            flight_number = carrier_flight[2:]
        elif len(carrier_flight) >= 3 and carrier_flight[3].isdigit():
            carrier = carrier_flight[:3]
            flight_number = carrier_flight[3:]
        else:
            print(f"  ⚠️  Could not parse carrier/flight from: {carrier_flight}")
            return (None, None, None, None, None)
        
        return (carrier, flight_number, flight_date, origin, destination)
    
    except Exception as e:
        print(f"  ⚠️  Error parsing flight ID '{flight_id}': {e}")
        return (None, None, None, None, None)


def parse_dt(s: str) -> Optional[datetime]:
    """
    Parse datetime string: "2026-01-06 15:00:00.000" or "2026-01-06T15:00:00Z"
    
    Handles formats with/without milliseconds, with space or T separator.
    Returns None for empty/invalid strings.
    """
    if not s or not s.strip():
        return None
    
    try:
        # Try ISO 8601 format first (with T and Z)
        if 'T' in s or s.endswith('Z'):
            return parse_iso8601_datetime(s)
        
        # Try space-separated format: "2026-01-06 15:00:00.000"
        # Remove milliseconds if present
        s_clean = s.strip()
        if '.' in s_clean:
            s_clean = s_clean.split('.')[0]
        
        # Parse as ISO format
        dt_str = s_clean.replace(' ', 'T')
        if not dt_str.endswith('Z') and '+' not in dt_str and '-' not in dt_str[-6:]:
            dt_str += 'Z'
        
        return parse_iso8601_datetime(dt_str)
    
    except Exception as e:
        print(f"  ⚠️  Error parsing datetime '{s}': {e}")
        return None


def ensure_flight_node(G: nx.MultiDiGraph, flight_id: str, prefix: str, row: Dict) -> None:
    """
    Create or update a Flight node with parsed attributes.
    
    Args:
        G: NetworkX graph
        flight_id: Flight ID in format "WN1234_2026-01-01_ATL_LGA"
        prefix: "source" or "target" to pick appropriate time columns
        row: CSV row dictionary
    """
    if not flight_id or flight_id not in G.nodes():
        # Parse flight ID
        carrier, flight_number, flight_date, origin, destination = parse_flight_id(flight_id)
        
        if not carrier or not flight_number:
            print(f"  ⚠️  Skipping invalid flight ID: {flight_id}")
            return
        
        # Get temporal attributes from row
        sch_dep_key = f"{prefix}_flt_sch_dprt_gmt"
        sch_arr_key = f"{prefix}_flt_sch_arr_gmt"
        act_arr_key = f"{prefix}_flt_actl_arr_gmt"
        
        sch_dep_str = row.get(sch_dep_key, '').strip()
        sch_arr_str = row.get(sch_arr_key, '').strip()
        act_arr_str = row.get(act_arr_key, '').strip()
        
        # Parse datetimes
        sch_dep = parse_dt(sch_dep_str)
        sch_arr = parse_dt(sch_arr_str)
        act_arr = parse_dt(act_arr_str)
        
        # Convert to ISO 8601 strings for storage
        sch_dep_iso = sch_dep.isoformat() if sch_dep else None
        sch_arr_iso = sch_arr.isoformat() if sch_arr else None
        act_arr_iso = act_arr.isoformat() if act_arr else None
        
        # Create node attributes
        node_attributes = {
            'label': 'Flight',
            'flight_id': flight_id,
            'flight_number': flight_number,
            'carrier': carrier,
            'origin': origin,
            'destination': destination,
            'flight_date': flight_date,
            'sch_dep_gmt': sch_dep_iso,
            'sch_arr_gmt': sch_arr_iso,
            'act_arr_gmt': act_arr_iso,
        }
        
        # Remove None values
        node_attributes = {k: v for k, v in node_attributes.items() if v is not None}
        
        G.add_node(flight_id, **node_attributes)


def get_edge_type_code(edge_code: str) -> str:
    """
    Map edge code to full edge type name.
    
    "AC" -> "AIRCRAFT_TURN"
    "P" -> "CREW_PILOT"
    "F" -> "CREW_FA"
    Other -> "UNKNOWN_{code}"
    """
    edge_type_map = {
        'AC': 'AIRCRAFT_TURN',
        'P': 'CREW_PILOT',
        'F': 'CREW_FA',
    }
    
    edge_code_upper = edge_code.strip().upper() if edge_code else ''
    return edge_type_map.get(edge_code_upper, f'UNKNOWN_{edge_code_upper}')


def add_flight_connection_edge(
    G: nx.MultiDiGraph,
    src_flight_id: str,
    tgt_flight_id: str,
    edge_type: str,
    edge_label: str,
    edge_activity: str,
    row: Dict
) -> None:
    """
    Create typed edge from source Flight to target Flight.
    
    Uses edge key (edge type + label) to support multiple parallel edges.
    """
    if not src_flight_id or not tgt_flight_id:
        return
    
    # Ensure both flight nodes exist
    ensure_flight_node(G, src_flight_id, 'source', row)
    ensure_flight_node(G, tgt_flight_id, 'target', row)
    
    # Get edge type code
    edge_type_full = get_edge_type_code(edge_type)
    
    # Create edge key: combination of edge type and label for uniqueness
    edge_key = f"{edge_type_full}_{edge_label}"
    
    # Get temporal attributes from row
    source_sch_dep = row.get('source_flt_sch_dprt_gmt', '').strip()
    source_sch_arr = row.get('source_flt_sch_arr_gmt', '').strip()
    source_act_arr = row.get('source_flt_actl_arr_gmt', '').strip()
    target_sch_dep = row.get('target_flt_sch_dprt_gmt', '').strip()
    target_sch_arr = row.get('target_flt_sch_arr_gmt', '').strip()
    target_act_arr = row.get('target_flt_actl_arr_gmt', '').strip()
    
    # Parse datetimes
    source_sch_dep_dt = parse_dt(source_sch_dep)
    source_sch_arr_dt = parse_dt(source_sch_arr)
    source_act_arr_dt = parse_dt(source_act_arr)
    target_sch_dep_dt = parse_dt(target_sch_dep)
    target_sch_arr_dt = parse_dt(target_sch_arr)
    target_act_arr_dt = parse_dt(target_act_arr)
    
    # Convert to ISO 8601 strings
    edge_attributes = {
        'type': edge_type_full,
        'edge_code': edge_type.strip().upper(),
        'edge_label': edge_label.strip() if edge_label else '',
        'edge_activity': edge_activity.strip() if edge_activity else '',
        'source_flt_sch_dprt_gmt': source_sch_dep_dt.isoformat() if source_sch_dep_dt else None,
        'source_flt_sch_arr_gmt': source_sch_arr_dt.isoformat() if source_sch_arr_dt else None,
        'source_flt_actl_arr_gmt': source_act_arr_dt.isoformat() if source_act_arr_dt else None,
        'target_flt_sch_dprt_gmt': target_sch_dep_dt.isoformat() if target_sch_dep_dt else None,
        'target_flt_sch_arr_gmt': target_sch_arr_dt.isoformat() if target_sch_arr_dt else None,
        'target_flt_actl_arr_gmt': target_act_arr_dt.isoformat() if target_act_arr_dt else None,
    }
    
    # Remove None values
    edge_attributes = {k: v for k, v in edge_attributes.items() if v is not None}
    
    # Validate temporal consistency: source arrival should be before target departure
    if source_act_arr_dt and target_sch_dep_dt:
        if source_act_arr_dt > target_sch_dep_dt:
            print(f"  ⚠️  Warning: Temporal inconsistency for {src_flight_id} -> {tgt_flight_id}: "
                  f"source arrives {source_act_arr_dt} but target departs {target_sch_dep_dt}")
    
    # Add edge with key for multigraph support
    G.add_edge(src_flight_id, tgt_flight_id, key=edge_key, **edge_attributes)


def build_graph(csv_path: Path = None, model: str = "flights-only") -> nx.MultiDiGraph:
    """
    Build the operations resource graph from CSV data.
    
    Args:
        csv_path: Path to flight_connections_sample.csv
        model: "flights-only" (default) or "with-resources"
    
    Returns:
        NetworkX MultiDiGraph with flights as nodes and resource connections as edges.
    """
    if csv_path is None:
        project_root = Path(__file__).parent.parent
        csv_path = project_root / 'data' / 'raw' / 'flight_connections_sample.csv'
    
    if not csv_path.exists():
        raise FileNotFoundError(f"Flight connections CSV not found: {csv_path}")
    
    print("🚀 Building Operations Resource Graph")
    print("=" * 60)
    print(f"📁 Loading data from: {csv_path}")
    print(f"📊 Model: {model}")
    
    # Create graph
    G = nx.MultiDiGraph()
    
    # Set graph metadata
    G.graph["name"] = "OpsConnections"
    G.graph["model"] = model
    G.graph["source_file"] = str(csv_path)
    G.graph["directed"] = True
    G.graph["created_utc"] = datetime.now(timezone.utc).isoformat()
    
    # Load CSV
    edges_added = 0
    errors = []
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for row_num, row in enumerate(reader, start=2):  # Start at 2 (header is row 1)
            try:
                source_flt = row.get('source_flt', '').strip()
                target_flt = row.get('target_flt', '').strip()
                edge = row.get('edge', '').strip()
                edge_label = row.get('edge_label', '').strip()
                edge_activity = row.get('edge_activity', '').strip()
                
                if not source_flt or not target_flt:
                    errors.append(f"Row {row_num}: Missing source_flt or target_flt")
                    continue
                
                if not edge:
                    errors.append(f"Row {row_num}: Missing edge code")
                    continue
                
                # Add edge
                add_flight_connection_edge(
                    G, source_flt, target_flt, edge, edge_label, edge_activity, row
                )
                edges_added += 1
                
            except Exception as e:
                errors.append(f"Row {row_num}: {e}")
    
    # Print summary
    print(f"\n✅ Graph built successfully!")
    print(f"  📊 Nodes (Flights): {G.number_of_nodes()}")
    print(f"  🔗 Edges (Connections): {G.number_of_edges()}")
    print(f"  📈 Unique edges added: {edges_added}")
    
    if errors:
        print(f"\n⚠️  {len(errors)} errors encountered:")
        for error in errors[:10]:  # Show first 10 errors
            print(f"  - {error}")
        if len(errors) > 10:
            print(f"  ... and {len(errors) - 10} more errors")
    
    return G


def save_graph(G: nx.MultiDiGraph, output_path: Path) -> None:
    """
    Save graph to JSON file using node-link format.
    
    Compatible with NetworkX's node_link_data format.
    """
    print(f"\n💾 Saving graph to: {output_path}")
    
    # Convert to node-link format
    graph_data = nx.node_link_data(G)
    
    # Write to JSON
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(graph_data, f, indent=2, ensure_ascii=False)
    
    print(f"  ✅ Graph saved successfully!")
    print(f"  📊 Nodes: {G.number_of_nodes()}")
    print(f"  🔗 Edges: {G.number_of_edges()}")
    print(f"  📈 Model: {G.graph.get('model', 'unknown')}")


def load_graph(file_path: Path) -> nx.MultiDiGraph:
    """
    Load graph from JSON file.
    
    Returns NetworkX MultiDiGraph.
    """
    print(f"\n📂 Loading graph from: {file_path}")
    
    if not file_path.exists():
        raise FileNotFoundError(f"Graph file not found: {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        graph_data = json.load(f)
    
    # Convert from node-link format
    G = nx.node_link_graph(graph_data, directed=True, multigraph=True)
    
    print(f"  ✅ Graph loaded successfully!")
    print(f"  📊 Nodes: {G.number_of_nodes()}")
    print(f"  🔗 Edges: {G.number_of_edges()}")
    print(f"  📈 Model: {G.graph.get('model', 'unknown')}")
    
    return G


def main():
    """Main entry point for the script."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Build operations resource graph from flight connections CSV'
    )
    parser.add_argument(
        '--csv',
        type=Path,
        default=None,
        help='Path to flight_connections_sample.csv (default: data/raw/flight_connections_sample.csv)'
    )
    parser.add_argument(
        '--model',
        choices=['flights-only', 'with-resources'],
        default='flights-only',
        help='Graph model: flights-only (default) or with-resources'
    )
    parser.add_argument(
        '--save',
        type=Path,
        default=None,
        help='Save graph to JSON file (default: data/processed/ops_graph.json)'
    )
    parser.add_argument(
        '--load',
        type=Path,
        default=None,
        help='Load graph from JSON file instead of building'
    )
    
    args = parser.parse_args()
    
    if args.load:
        # Load existing graph
        G = load_graph(args.load)
        print("\n📊 Graph Summary:")
        print(f"  Name: {G.graph.get('name', 'unknown')}")
        print(f"  Model: {G.graph.get('model', 'unknown')}")
        print(f"  Created: {G.graph.get('created_utc', 'unknown')}")
    else:
        # Build new graph
        G = build_graph(csv_path=args.csv, model=args.model)
        
        # Save if requested
        if args.save:
            save_graph(G, args.save)
        elif args.model == 'flights-only':
            # Auto-save to default location
            project_root = Path(__file__).parent.parent
            default_output = project_root / 'data' / 'processed' / 'ops_graph.json'
            save_graph(G, default_output)


if __name__ == '__main__':
    main()
