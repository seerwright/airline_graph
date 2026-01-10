#!/usr/bin/env python3
"""
Example usage of the flight graph.

This script demonstrates:
1. Network status every 10 minutes from first departure to last arrival
2. Final airport statistics using event-level snapshots
"""

import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta

# Add parent directory to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    import networkx as nx
    from scripts.build_graph import build_graph
except ImportError as e:
    print(f"❌ Error importing required modules: {e}")
    print("\nPlease make sure you have:")
    print("1. Activated your virtual environment:")
    print("   source agraph_env/bin/activate  # On macOS/Linux")
    print("2. Installed dependencies:")
    print("   pip install -r requirements.txt")
    sys.exit(1)


def parse_iso8601_datetime(date_str):
    """Parse ISO 8601 datetime string to datetime object."""
    if not date_str or date_str.strip() == '':
        return None
    try:
        if date_str.endswith('Z'):
            date_str = date_str[:-1] + '+00:00'
        dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, AttributeError):
        return None


def get_airport_state_at_time(G, airport_code, target_time):
    """Get airport cumulative state at a specific point in time."""
    node = G.nodes[airport_code]
    
    if 'time_snapshots' not in node or not node['time_snapshots']:
        return None
    
    # Parse ISO 8601 string to datetime if needed
    if isinstance(target_time, str):
        target_time = parse_iso8601_datetime(target_time)
    
    if not target_time:
        return None
    
    # Find the last snapshot before or at target_time
    last_snapshot = None
    for snapshot in node['time_snapshots']:
        snapshot_time_str = snapshot.get('timestamp', '')
        if snapshot_time_str:
            snapshot_time = parse_iso8601_datetime(snapshot_time_str)
            if snapshot_time and snapshot_time <= target_time:
                last_snapshot = snapshot
            else:
                break  # Snapshots are ordered, so we can break early
    
    return last_snapshot['cumulative'] if last_snapshot else {
        'total_departures': 0,
        'total_arrivals': 0,
        'avg_departure_delay': 0.0,
        'avg_arrival_delay': 0.0,
        'on_time_departure_pct': 0.0,
        'on_time_arrival_pct': 0.0
    }


def get_active_flights_at_time(G, target_time):
    """Get flights that are in the air (departed but not yet arrived) at a specific time."""
    if isinstance(target_time, str):
        target_time = parse_iso8601_datetime(target_time)
    
    if not target_time:
        return []
    
    active_flights = []
    # MultiDiGraph edges include a key parameter: (u, v, key, data)
    for origin, destination, key, data in G.edges(data=True, keys=True):
        dep_time_str = data.get('actual_departure_gate') or data.get('scheduled_departure_gate')
        arr_time_str = data.get('actual_arrival_gate') or data.get('scheduled_arrival_gate')
        
        if not dep_time_str or not arr_time_str:
            continue
        
        dep_time = parse_iso8601_datetime(dep_time_str)
        arr_time = parse_iso8601_datetime(arr_time_str)
        
        if dep_time and arr_time and dep_time <= target_time < arr_time:
            active_flights.append({
                'flight_id': data.get('flight_id', 'unknown'),
                'origin': origin,
                'destination': destination,
                'departure': dep_time,
                'arrival': arr_time,
                'carrier': data.get('carrier', ''),
                'flight_number': data.get('flight_number', ''),
                'edge_key': key  # Store the edge key for reference
            })
    
    return active_flights


def get_events_in_window(G, start_time, end_time):
    """Get all events (departures and arrivals) that occurred in a time window."""
    if isinstance(start_time, str):
        start_time = parse_iso8601_datetime(start_time)
    if isinstance(end_time, str):
        end_time = parse_iso8601_datetime(end_time)
    
    if not start_time or not end_time:
        return []
    
    events = []
    for airport_code in G.nodes():
        node_data = G.nodes[airport_code]
        if 'time_snapshots' in node_data:
            for snapshot in node_data['time_snapshots']:
                snapshot_time_str = snapshot.get('timestamp', '')
                if snapshot_time_str:
                    snapshot_time = parse_iso8601_datetime(snapshot_time_str)
                    if snapshot_time and start_time <= snapshot_time <= end_time:
                        events.append({
                            'airport': airport_code,
                            'timestamp': snapshot_time,
                            'event_type': snapshot.get('event_type', 'unknown'),
                            'flight_id': snapshot.get('event_flight_id', 'unknown')
                        })
    
    return sorted(events, key=lambda e: e['timestamp'])


def show_network_status_every_10_minutes(G):
    """Show network status every 10 minutes from first departure to last arrival."""
    print("\n" + "=" * 80)
    print("Network Status: Every 10 Minutes")
    print("=" * 80)
    
    # Find first departure and last arrival times
    first_departure = None
    last_arrival = None
    
    # MultiDiGraph edges include a key parameter: (u, v, key, data)
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
    
    if not first_departure or not last_arrival:
        print("❌ Could not find first departure or last arrival time.")
        return
    
    print(f"\n📅 Time Range: {first_departure.strftime('%Y-%m-%d %H:%M:%S')} UTC to {last_arrival.strftime('%Y-%m-%d %H:%M:%S')} UTC")
    duration_minutes = (last_arrival - first_departure).total_seconds() / 60
    print(f"⏱️  Total Duration: {duration_minutes:.1f} minutes\n")
    
    # Create 10-minute intervals
    current_time = first_departure
    interval_minutes = 10
    interval_count = 0
    
    while current_time <= last_arrival:
        interval_count += 1
        interval_end = current_time + timedelta(minutes=interval_minutes)
        
        print(f"\n{'─' * 80}")
        print(f"⏰ Time: {current_time.strftime('%Y-%m-%d %H:%M:%S')} UTC")
        print(f"   Interval: +{interval_count * interval_minutes} minutes from start")
        print(f"{'─' * 80}")
        
        # Get airport states at this time
        print("\n📍 Airport States:")
        for airport_code in sorted(G.nodes()):
            node_data = G.nodes[airport_code]
            state = get_airport_state_at_time(G, airport_code, current_time)
            airport_name = node_data.get('airport_name', 'Unknown')
            
            if state:
                print(f"  {airport_code} ({airport_name}):")
                print(f"    - Departures: {state['total_departures']}")
                print(f"    - Arrivals: {state['total_arrivals']}")
                if state['total_departures'] > 0:
                    print(f"    - Avg Departure Delay: {state['avg_departure_delay']:.1f} min")
                    print(f"    - On-Time Departure %: {state['on_time_departure_pct']:.1f}%")
                if state['total_arrivals'] > 0:
                    print(f"    - Avg Arrival Delay: {state['avg_arrival_delay']:.1f} min")
                    print(f"    - On-Time Arrival %: {state['on_time_arrival_pct']:.1f}%")
            else:
                print(f"  {airport_code} ({airport_name}): No activity yet")
        
        # Get active flights (in the air) at this time
        active_flights = get_active_flights_at_time(G, current_time)
        print(f"\n✈️  Active Flights (in the air): {len(active_flights)}")
        if active_flights:
            for flight in sorted(active_flights, key=lambda f: f['departure']):
                flight_id = flight['flight_id']
                carrier = flight['carrier']
                flight_num = flight['flight_number']
                elapsed = (current_time - flight['departure']).total_seconds() / 60
                remaining = (flight['arrival'] - current_time).total_seconds() / 60
                print(f"    - {carrier}{flight_num}: {flight['origin']} → {flight['destination']}")
                print(f"      {flight_id} | Elapsed: {elapsed:.1f} min | Remaining: {remaining:.1f} min")
        else:
            print("    (No flights in the air at this time)")
        
        # Get events in this 10-minute window
        events = get_events_in_window(G, current_time, interval_end)
        if events:
            print(f"\n📊 Events in this 10-minute window: {len(events)}")
            for event in events:
                event_time_str = event['timestamp'].strftime('%H:%M:%S')
                print(f"    - {event_time_str} UTC: {event['airport']} - {event['event_type'].upper()}")
                print(f"      Flight: {event['flight_id']}")
        else:
            print(f"\n📊 Events in this 10-minute window: 0")
        
        # Move to next interval
        current_time = interval_end
    
    print(f"\n{'─' * 80}")
    print(f"✅ Network status reporting complete ({interval_count} intervals)")
    print(f"{'─' * 80}")


def show_final_airport_stats(G):
    """Show final airport statistics after all flights complete."""
    print("\n" + "=" * 80)
    print("Final Airport Statistics")
    print("=" * 80)
    
    # Get the latest state for each airport (last snapshot)
    for airport_code in sorted(G.nodes()):
        node_data = G.nodes[airport_code]
        airport_name = node_data.get('airport_name', 'Unknown')
        city = node_data.get('city', '')
        state = node_data.get('state', '')
        
        print(f"\n🏢 {airport_code} - {airport_name}")
        if city or state:
            print(f"   Location: {city}, {state}")
        
        if 'time_snapshots' not in node_data or not node_data['time_snapshots']:
            print("   No flight activity recorded")
            continue
        
        # Get latest snapshot (last one in the list)
        last_snapshot = node_data['time_snapshots'][-1]
        cumulative = last_snapshot.get('cumulative', {})
        
        # Get total number of events
        total_events = len(node_data['time_snapshots'])
        departures = len([s for s in node_data['time_snapshots'] if s.get('event_type') == 'departure'])
        arrivals = len([s for s in node_data['time_snapshots'] if s.get('event_type') == 'arrival'])
        
        # Get first and last event times
        first_event = node_data['time_snapshots'][0]
        last_event = node_data['time_snapshots'][-1]
        first_time = parse_iso8601_datetime(first_event.get('timestamp', ''))
        last_time = parse_iso8601_datetime(last_event.get('timestamp', ''))
        
        print(f"   Total Events: {total_events} ({departures} departures, {arrivals} arrivals)")
        if first_time:
            print(f"   First Event: {first_time.strftime('%Y-%m-%d %H:%M:%S')} UTC ({first_event.get('event_type', 'unknown')})")
        if last_time:
            print(f"   Last Event: {last_time.strftime('%Y-%m-%d %H:%M:%S')} UTC ({last_event.get('event_type', 'unknown')})")
        
        print(f"\n   📊 Cumulative Statistics (Final):")
        print(f"      Total Departures: {cumulative.get('total_departures', 0)}")
        print(f"      Total Arrivals: {cumulative.get('total_arrivals', 0)}")
        
        if cumulative.get('total_departures', 0) > 0:
            print(f"      Average Departure Delay: {cumulative.get('avg_departure_delay', 0.0):.2f} minutes")
            print(f"      On-Time Departure Rate: {cumulative.get('on_time_departure_pct', 0.0):.2f}%")
        
        if cumulative.get('total_arrivals', 0) > 0:
            print(f"      Average Arrival Delay: {cumulative.get('avg_arrival_delay', 0.0):.2f} minutes")
            print(f"      On-Time Arrival Rate: {cumulative.get('on_time_arrival_pct', 0.0):.2f}%")
        
        # Show event timeline (first few and last few)
        print(f"\n   📅 Event Timeline:")
        if total_events <= 6:
            # Show all events if 6 or fewer
            for snapshot in node_data['time_snapshots']:
                event_time = parse_iso8601_datetime(snapshot.get('timestamp', ''))
                event_time_str = event_time.strftime('%H:%M:%S') if event_time else 'unknown'
                print(f"      {event_time_str} UTC - {snapshot.get('event_type', 'unknown').upper()}: {snapshot.get('event_flight_id', 'unknown')}")
        else:
            # Show first 3 and last 3
            for snapshot in node_data['time_snapshots'][:3]:
                event_time = parse_iso8601_datetime(snapshot.get('timestamp', ''))
                event_time_str = event_time.strftime('%H:%M:%S') if event_time else 'unknown'
                print(f"      {event_time_str} UTC - {snapshot.get('event_type', 'unknown').upper()}: {snapshot.get('event_flight_id', 'unknown')}")
            print(f"      ... ({total_events - 6} more events) ...")
            for snapshot in node_data['time_snapshots'][-3:]:
                event_time = parse_iso8601_datetime(snapshot.get('timestamp', ''))
                event_time_str = event_time.strftime('%H:%M:%S') if event_time else 'unknown'
                print(f"      {event_time_str} UTC - {snapshot.get('event_type', 'unknown').upper()}: {snapshot.get('event_flight_id', 'unknown')}")
    
    print(f"\n{'=' * 80}")


def main():
    """Main function demonstrating network status over time."""
    print("🚀 Flight Graph Network Status Analysis")
    print("=" * 80)
    
    # Build the graph
    print("\n📊 Building graph from sample data...")
    try:
        G = build_graph()
    except Exception as e:
        print(f"❌ Error building graph: {e}")
        print("\nMake sure you have:")
        print("1. Activated virtual environment")
        print("2. Installed dependencies (pip install -r requirements.txt)")
        print("3. Sample data files exist in data/raw/")
        import traceback
        traceback.print_exc()
        return
    
    if G.number_of_nodes() == 0:
        print("❌ Graph is empty. Check data files.")
        return
    
    # Show network status every 10 minutes
    show_network_status_every_10_minutes(G)
    
    # Show final airport statistics
    show_final_airport_stats(G)
    
    print("\n✅ Analysis completed!")
    print("\n💡 Next steps:")
    print("  - Visualize the graph using NetworkX and matplotlib")
    print("  - Export to Neo4j for production use")
    print("  - Build custom analytics and queries")
    print("  - Add more data and expand the graph")
    
    return G


if __name__ == '__main__':
    G = main()
