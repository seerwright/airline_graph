#!/usr/bin/env python3
"""
Interactive Performance Dashboard for Airline Network Graph.

This Streamlit dashboard provides real-time visualization of airline operations
throughout the simulation period, enabling users to monitor and analyze the state
of flights, airports, delays, volume, and network performance as events unfold over time.

Usage:
    streamlit run scripts/dashboard.py
"""

import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple

# Add parent directory to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    import streamlit as st
    import plotly.graph_objects as go
    import plotly.express as px
    import networkx as nx
    import pandas as pd
    import numpy as np
except ImportError as e:
    print(f"❌ Error importing required modules: {e}")
    print("\nPlease make sure you have:")
    print("1. Activated your virtual environment:")
    print("   source agraph_env/bin/activate  # On macOS/Linux")
    print("2. Installed dependencies:")
    print("   pip install -r requirements.txt")
    sys.exit(1)

# Import helper functions from example_usage.py
try:
    from scripts.example_usage import (
        parse_iso8601_datetime,
        get_airport_state_at_time,
        get_active_flights_at_time,
        get_events_in_window,
    )
    from scripts.build_graph import build_graph, load_graph
except ImportError as e:
    st.error(f"❌ Error importing helper modules: {e}")
    st.stop()


# ============================================================================
# Page Configuration
# ============================================================================

st.set_page_config(
    page_title="Airline Network Performance Dashboard",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================================
# Graph Loading and Caching
# ============================================================================

@st.cache_data
def load_or_build_graph(graph_file: Optional[Path] = None, data_dir: Optional[Path] = None):
    """
    Load graph from file or build from CSV data.
    Cached by Streamlit to avoid rebuilding on every rerun.
    """
    if graph_file and graph_file.exists():
        return load_graph(graph_file)
    else:
        return build_graph(data_dir)


def get_time_range(G: nx.MultiDiGraph) -> Tuple[Optional[datetime], Optional[datetime]]:
    """Get the first departure and last arrival times from the graph."""
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
    
    return first_departure, last_arrival


# ============================================================================
# Data Query Functions
# ============================================================================

def get_completed_flights_up_to_time(G: nx.MultiDiGraph, target_time: datetime) -> List[Dict]:
    """Get flights that have arrived by target time."""
    completed_flights = []
    
    for origin, destination, key, data in G.edges(data=True, keys=True):
        arr_time_str = data.get('actual_arrival_gate') or data.get('scheduled_arrival_gate')
        
        if arr_time_str:
            arr_time = parse_iso8601_datetime(arr_time_str)
            if arr_time and arr_time <= target_time:
                completed_flights.append({
                    'flight_id': data.get('flight_id', 'unknown'),
                    'origin': origin,
                    'destination': destination,
                    'arrival': arr_time,
                    'carrier': data.get('carrier', ''),
                    'flight_number': data.get('flight_number', ''),
                    'departure_delay': data.get('departure_delay_minutes', 0),
                    'arrival_delay': data.get('arrival_delay_minutes', 0),
                    'edge_key': key
                })
    
    return completed_flights


def get_flight_volume_timeline(G: nx.MultiDiGraph, start_time: datetime, end_time: datetime, interval_minutes: int = 1) -> pd.DataFrame:
    """Extract flight volume data at regular intervals for timeline chart.
    
    Optimized approach: Pre-compute all departure and arrival times from edges,
    then count events at each time interval.
    """
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
    
    # Sort times for efficient lookup
    departure_times.sort()
    arrival_times.sort()
    
    # Build timeline by counting events up to each time point
    times = []
    departure_counts = []
    arrival_counts = []
    
    current_time = start_time
    dep_idx = 0  # Index into sorted departure_times
    arr_idx = 0  # Index into sorted arrival_times
    
    while current_time <= end_time:
        # Count departures that have occurred by current_time
        # Advance index while departures are <= current_time
        while dep_idx < len(departure_times) and departure_times[dep_idx] <= current_time:
            dep_idx += 1
        # dep_idx now points to the first departure after current_time
        # So dep_idx is the count of departures <= current_time
        departures = dep_idx
        
        # Count arrivals that have occurred by current_time
        # Advance index while arrivals are <= current_time
        while arr_idx < len(arrival_times) and arrival_times[arr_idx] <= current_time:
            arr_idx += 1
        # arr_idx now points to the first arrival after current_time
        # So arr_idx is the count of arrivals <= current_time
        arrivals = arr_idx
        
        times.append(current_time)
        departure_counts.append(departures)
        arrival_counts.append(arrivals)
        
        current_time += timedelta(minutes=interval_minutes)
    
    return pd.DataFrame({
        'time': times,
        'departures': departure_counts,
        'arrivals': arrival_counts,
        'total_flights': [d + a for d, a in zip(departure_counts, arrival_counts)]
    })


# ============================================================================
# Visualization Functions
# ============================================================================

def create_network_graph(G: nx.MultiDiGraph, current_time: datetime) -> go.Figure:
    """Create interactive network graph visualization at current time."""
    # Get active flights at current time
    active_flights = get_active_flights_at_time(G, current_time)
    completed_flights = get_completed_flights_up_to_time(G, current_time)
    
    # Create layout using NetworkX spring layout
    pos = nx.spring_layout(G, k=2, iterations=50, seed=42)
    
    # Extract node and edge positions
    node_x = []
    node_y = []
    node_text = []
    node_size = []
    node_color = []
    
    for node in G.nodes():
        x, y = pos[node]
        node_x.append(x)
        node_y.append(y)
        
        # Get airport state at current time
        state = get_airport_state_at_time(G, node, current_time)
        if state:
            activity = state['total_departures'] + state['total_arrivals']
            avg_delay = (state.get('avg_departure_delay', 0) + state.get('avg_arrival_delay', 0)) / 2
            
            node_size.append(max(20, activity * 5))  # Scale by activity
            node_text.append(f"{node}<br>Departures: {state['total_departures']}<br>Arrivals: {state['total_arrivals']}<br>Avg Delay: {avg_delay:.1f} min")
            
            # Color by delay status
            if avg_delay < 15:
                node_color.append('green')
            elif avg_delay < 30:
                node_color.append('orange')
            else:
                node_color.append('red')
        else:
            node_size.append(20)
            node_text.append(f"{node}<br>No activity yet")
            node_color.append('gray')
    
    # Extract edge positions
    edge_x = []
    edge_y = []
    edge_info = []
    
    # Group edges by route to show thickness by volume
    route_flights = {}
    for origin, destination, key, data in G.edges(data=True, keys=True):
        route = (origin, destination)
        if route not in route_flights:
            route_flights[route] = []
        route_flights[route].append({
            'key': key,
            'data': data,
            'dep': parse_iso8601_datetime(data.get('actual_departure_gate') or data.get('scheduled_departure_gate')),
            'arr': parse_iso8601_datetime(data.get('actual_arrival_gate') or data.get('scheduled_arrival_gate')),
        })
    
    for (origin, destination), flights in route_flights.items():
        # Count active flights on this route
        active_count = sum(1 for f in flights if f['dep'] and f['arr'] and f['dep'] <= current_time < f['arr'])
        completed_count = sum(1 for f in flights if f['arr'] and f['arr'] <= current_time)
        
        if active_count > 0 or completed_count > 0:
            x0, y0 = pos[origin]
            x1, y1 = pos[destination]
            
            edge_x.extend([x0, x1, None])
            edge_y.extend([y0, y1, None])
            
            # Route info
            total_flights = len(flights)
            route_info = f"{origin} → {destination}<br>Total: {total_flights}<br>Active: {active_count}<br>Completed: {completed_count}"
            edge_info.append(route_info)
    
    # Create edge trace
    edge_trace = go.Scatter(
        x=edge_x, y=edge_y,
        line=dict(width=2, color='#888'),
        hoverinfo='none',
        mode='lines'
    )
    
    # Create node trace
    node_trace = go.Scatter(
        x=node_x, y=node_y,
        mode='markers+text',
        hoverinfo='text',
        text=[node for node in G.nodes()],
        textposition="middle center",
        textfont=dict(size=14, color="white", family="Arial Black"),
        hovertext=node_text,
        marker=dict(
            showscale=False,
            size=node_size,
            color=node_color,
            line=dict(width=2, color='black')
        )
    )
    
    # Create figure
    fig = go.Figure(
        data=[edge_trace, node_trace],
        layout=go.Layout(
            title=dict(
                text=f"Network Graph at {current_time.strftime('%Y-%m-%d %H:%M:%S')} UTC",
                x=0.5,
                xanchor='center',
                font=dict(size=16)
            ),
            showlegend=False,
            hovermode='closest',
            margin=dict(b=20, l=5, r=5, t=40),
            annotations=[
                dict(
                    text="Node size = Activity level | Color = Delay status (Green: On-time, Orange: Moderate, Red: Delayed)",
                    showarrow=False,
                    xref="paper", yref="paper",
                    x=0.005, y=-0.002,
                    xanchor="left", yanchor="bottom",
                    font=dict(size=10, color="#888")
                )
            ],
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            height=600
        )
    )
    
    return fig


def create_airport_status_panel(G: nx.MultiDiGraph, airport_code: str, current_time: datetime) -> Dict:
    """Get airport status metrics for display in panel."""
    state = get_airport_state_at_time(G, airport_code, current_time)
    node_data = G.nodes[airport_code]
    
    if not state:
        return {
            'airport_code': airport_code,
            'airport_name': node_data.get('airport_name', 'Unknown'),
            'total_departures': 0,
            'total_arrivals': 0,
            'active_flights': 0,
            'avg_departure_delay': 0.0,
            'avg_arrival_delay': 0.0,
            'on_time_departure_pct': 0.0,
            'on_time_arrival_pct': 0.0,
        }
    
    # Count active flights (flights departing from this airport that are in the air)
    active_flights = get_active_flights_at_time(G, current_time)
    airport_active = sum(1 for f in active_flights if f['origin'] == airport_code)
    
    return {
        'airport_code': airport_code,
        'airport_name': node_data.get('airport_name', 'Unknown'),
        'total_departures': state.get('total_departures', 0),
        'total_arrivals': state.get('total_arrivals', 0),
        'active_flights': airport_active,
        'avg_departure_delay': state.get('avg_departure_delay', 0.0),
        'avg_arrival_delay': state.get('avg_arrival_delay', 0.0),
        'on_time_departure_pct': state.get('on_time_departure_pct', 0.0),
        'on_time_arrival_pct': state.get('on_time_arrival_pct', 0.0),
    }


def create_flight_volume_chart(df: pd.DataFrame, current_time: datetime) -> go.Figure:
    """Create flight volume timeline chart."""
    fig = go.Figure()
    
    # Ensure time column is datetime type
    if not pd.api.types.is_datetime64_any_dtype(df['time']):
        df['time'] = pd.to_datetime(df['time'])
    
    # Add departure line
    fig.add_trace(go.Scatter(
        x=df['time'],
        y=df['departures'],
        mode='lines+markers',
        name='Departures',
        line=dict(color='blue', width=2),
        marker=dict(size=4)
    ))
    
    # Add arrival line
    fig.add_trace(go.Scatter(
        x=df['time'],
        y=df['arrivals'],
        mode='lines+markers',
        name='Arrivals',
        line=dict(color='orange', width=2),
        marker=dict(size=4)
    ))
    
    # Add total line
    fig.add_trace(go.Scatter(
        x=df['time'],
        y=df['total_flights'],
        mode='lines',
        name='Total Flights',
        line=dict(color='green', width=2, dash='dash')
    ))
    
    # Add vertical line for current time using add_shape (more reliable with datetime)
    # Get y-axis range for the line
    y_max = max(df['total_flights'].max() if len(df) > 0 else 1, 1)
    
    fig.add_shape(
        type="line",
        x0=current_time,
        x1=current_time,
        y0=0,
        y1=y_max,
        line=dict(color="red", width=2, dash="dash"),
    )
    
    # Add annotation for current time
    fig.add_annotation(
        x=current_time,
        y=y_max * 0.95,
        text=f"Current: {current_time.strftime('%H:%M:%S')}",
        showarrow=False,
        bgcolor="rgba(255,255,255,0.8)",
        bordercolor="red",
        borderwidth=1,
        font=dict(size=10, color="red")
    )
    
    fig.update_layout(
        title="Flight Volume Timeline",
        xaxis_title="Time (GMT)",
        yaxis_title="Cumulative Flight Count",
        hovermode='x unified',
        height=400,
        legend=dict(x=0, y=1, traceorder="normal")
    )
    
    return fig


# ============================================================================
# Main Dashboard
# ============================================================================

def main():
    """Main dashboard function."""
    # Title and header
    st.title("✈️ Airline Network Performance Dashboard")
    st.markdown("Real-time visualization of airline operations throughout the simulation period")
    
    # Sidebar: Data loading options
    st.sidebar.header("📂 Data Source")
    
    graph_file_option = st.sidebar.selectbox(
        "Load graph from:",
        options=["Build from CSV", "Load from JSON file"],
        index=0
    )
    
    # Load or build graph
    try:
        with st.spinner("Loading graph data..."):
            if graph_file_option == "Load from JSON file":
                graph_file_path = st.sidebar.text_input(
                    "Graph file path:",
                    value="data/processed/t1.json"
                )
                if graph_file_path:
                    graph_file = project_root / graph_file_path
                    if graph_file.exists():
                        G = load_or_build_graph(graph_file=graph_file)
                    else:
                        st.error(f"❌ Graph file not found: {graph_file}")
                        st.stop()
                else:
                    st.error("❌ Please provide a graph file path.")
                    st.stop()
            else:
                data_dir = st.sidebar.text_input(
                    "Data directory (optional):",
                    value="data/raw"
                )
                data_dir_path = project_root / data_dir if data_dir else None
                G = load_or_build_graph(data_dir=data_dir_path)
        
        if G.number_of_nodes() == 0:
            st.error("❌ Graph is empty. Please check your data files.")
            st.stop()
        
        st.sidebar.success(f"✅ Graph loaded: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
    
    except Exception as e:
        st.error(f"❌ Error loading graph: {e}")
        st.stop()
    
    # Get time range
    first_departure, last_arrival = get_time_range(G)
    
    if not first_departure or not last_arrival:
        st.error("❌ Could not determine time range from graph data.")
        st.stop()
    
    # Time Control Panel
    st.header("⏰ Time Control")
    
    col1, col2, col3 = st.columns([3, 1, 1])
    
    with col1:
        # Time slider
        time_range_minutes = int((last_arrival - first_departure).total_seconds() / 60)
        minutes_from_start = st.slider(
            "Time (minutes from first departure):",
            min_value=0,
            max_value=time_range_minutes,
            value=0,
            step=1,
            key="time_slider"
        )
        current_time = first_departure + timedelta(minutes=minutes_from_start)
    
    with col2:
        st.metric("Current Time", current_time.strftime("%H:%M:%S UTC"))
    
    with col3:
        total_duration = (last_arrival - first_departure).total_seconds() / 60
        st.metric("Total Duration", f"{total_duration:.1f} min")
    
    # Network Graph Visualization
    st.header("🌐 Network Graph")
    
    with st.spinner("Generating network graph..."):
        network_fig = create_network_graph(G, current_time)
        st.plotly_chart(network_fig, use_container_width=True)
    
    # Airport Status Panels
    st.header("📍 Airport Status")
    
    airports = sorted(G.nodes())
    airport_cols = st.columns(len(airports))
    
    for idx, airport_code in enumerate(airports):
        with airport_cols[idx]:
            status = create_airport_status_panel(G, airport_code, current_time)
            
            st.subheader(f"{airport_code} - {status['airport_name']}")
            
            col_dep, col_arr = st.columns(2)
            with col_dep:
                st.metric("Departures", status['total_departures'])
            with col_arr:
                st.metric("Arrivals", status['total_arrivals'])
            
            st.metric("Active Flights", status['active_flights'])
            
            if status['total_departures'] > 0:
                st.metric("Avg Dep Delay", f"{status['avg_departure_delay']:.1f} min")
                st.progress(status['on_time_departure_pct'] / 100, text=f"On-Time Dep: {status['on_time_departure_pct']:.1f}%")
            
            if status['total_arrivals'] > 0:
                st.metric("Avg Arr Delay", f"{status['avg_arrival_delay']:.1f} min")
                st.progress(status['on_time_arrival_pct'] / 100, text=f"On-Time Arr: {status['on_time_arrival_pct']:.1f}%")
    
    # Flight Volume Timeline
    st.header("📊 Flight Volume Timeline")
    
    with st.spinner("Calculating flight volume timeline..."):
        # Sample at 1-minute intervals for performance
        volume_df = get_flight_volume_timeline(G, first_departure, last_arrival, interval_minutes=1)
        volume_fig = create_flight_volume_chart(volume_df, current_time)
        st.plotly_chart(volume_fig, use_container_width=True)
    
    # Event Timeline
    st.header("📅 Event Timeline")
    
    # Get events in a window around current time (show last 10 events and next 10)
    window_start = max(first_departure, current_time - timedelta(minutes=30))
    window_end = min(last_arrival, current_time + timedelta(minutes=30))
    
    events = get_events_in_window(G, window_start, window_end)
    
    if events:
        # Convert to DataFrame for display
        events_df = pd.DataFrame([
            {
                'Timestamp': event['timestamp'].strftime('%Y-%m-%d %H:%M:%S UTC'),
                'Time': event['timestamp'].strftime('%H:%M:%S'),
                'Airport': event['airport'],
                'Event Type': event['event_type'].upper(),
                'Flight ID': event['flight_id']
            }
            for event in events
        ])
        
        st.dataframe(events_df, use_container_width=True, hide_index=True)
    else:
        st.info("No events in this time window.")
    
    # Footer
    st.markdown("---")
    st.markdown("**Dashboard Version:** MVP (Phase 1) | **Data:** Event-level temporal snapshots")


if __name__ == '__main__':
    main()
