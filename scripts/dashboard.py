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
    from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode
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


def get_flights_enroute_over_time(G: nx.MultiDiGraph, start_time: datetime, end_time: datetime, interval_minutes: int = 1) -> pd.DataFrame:
    """Get time series of flights enroute count at regular intervals."""
    times = []
    enroute_counts = []
    
    current_time = start_time
    while current_time <= end_time:
        active_flights = get_active_flights_at_time(G, current_time)
        enroute_counts.append(len(active_flights))
        times.append(current_time)
        current_time += timedelta(minutes=interval_minutes)
    
    return pd.DataFrame({
        'time': times,
        'flights_enroute': enroute_counts
    })


def get_cumulative_delay_over_time(G: nx.MultiDiGraph, start_time: datetime, end_time: datetime, interval_minutes: int = 1, delay_type: str = 'departure') -> pd.DataFrame:
    """Get time series of cumulative delay minutes (total, not average).
    
    Args:
        delay_type: 'departure' for departure delays, 'arrival' for arrival delays
    """
    times = []
    cumulative_delays = []
    
    # Pre-compute all flights with their delays and times
    flights_data = []
    for origin, destination, key, data in G.edges(data=True, keys=True):
        if delay_type == 'departure':
            time_str = data.get('actual_departure_gate') or data.get('scheduled_departure_gate')
            delay = data.get('departure_delay_minutes', 0) or 0
        else:  # arrival
            time_str = data.get('actual_arrival_gate') or data.get('scheduled_arrival_gate')
            delay = data.get('arrival_delay_minutes', 0) or 0
        
        if time_str:
            flight_time = parse_iso8601_datetime(time_str)
            if flight_time and delay is not None:
                try:
                    delay_float = float(delay)
                    flights_data.append({
                        'time': flight_time,
                        'delay': delay_float
                    })
                except (ValueError, TypeError):
                    pass
    
    # Sort by time
    flights_data.sort(key=lambda x: x['time'])
    
    # Build cumulative sum
    current_time = start_time
    cumulative_delay = 0.0
    flight_idx = 0
    
    while current_time <= end_time:
        # Add delays for flights that have completed by current_time
        while flight_idx < len(flights_data) and flights_data[flight_idx]['time'] <= current_time:
            cumulative_delay += flights_data[flight_idx]['delay']
            flight_idx += 1
        
        times.append(current_time)
        cumulative_delays.append(cumulative_delay)
        current_time += timedelta(minutes=interval_minutes)
    
    # Use different column names based on delay type
    column_name = 'cumulative_outbound_delay' if delay_type == 'departure' else 'cumulative_inbound_delay'
    
    return pd.DataFrame({
        'time': times,
        column_name: cumulative_delays
    })


def get_airport_coordinates(G: nx.MultiDiGraph) -> Dict[str, Tuple[float, float]]:
    """Get dictionary mapping airport codes to (latitude, longitude) tuples."""
    coords = {}
    for airport_code in G.nodes():
        node_data = G.nodes[airport_code]
        lat = node_data.get('latitude')
        lon = node_data.get('longitude')
        if lat is not None and lon is not None:
            try:
                coords[airport_code] = (float(lat), float(lon))
            except (ValueError, TypeError):
                pass
    return coords


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
    """Create interactive geographic map visualization with airports and flight routes at current time."""
    # Get airport coordinates
    airport_coords = get_airport_coordinates(G)
    
    if not airport_coords:
        # Fallback to basic graph if no coordinates available
        st.warning("⚠️ No airport coordinates found. Please add latitude/longitude to airports_sample.csv")
        return create_fallback_graph(G, current_time)
    
    # Get active flights at current time
    active_flights = get_active_flights_at_time(G, current_time)
    
    # Prepare airport data for map
    airport_lats = []
    airport_lons = []
    airport_codes = []
    airport_text = []
    airport_sizes = []
    airport_colors = []
    
    for airport_code in sorted(G.nodes()):
        if airport_code in airport_coords:
            lat, lon = airport_coords[airport_code]
            airport_lats.append(lat)
            airport_lons.append(lon)
            airport_codes.append(airport_code)
            
            # Get airport state at current time
            state = get_airport_state_at_time(G, airport_code, current_time)
            node_data = G.nodes[airport_code]
            airport_name = node_data.get('airport_name', airport_code)
            
            if state:
                activity = state['total_departures'] + state['total_arrivals']
                avg_delay = (state.get('avg_departure_delay', 0) + state.get('avg_arrival_delay', 0)) / 2
                
                # Size based on activity
                size = max(10, min(50, activity * 3))
                airport_sizes.append(size)
                
                # Tooltip text
                text = f"{airport_code} - {airport_name}<br>Departures: {state['total_departures']}<br>Arrivals: {state['total_arrivals']}<br>Avg Delay: {avg_delay:.1f} min<br>Active Flights: {sum(1 for f in active_flights if f['origin'] == airport_code)}"
                airport_text.append(text)
                
                # Color by delay status
                if avg_delay < 15:
                    airport_colors.append('green')
                elif avg_delay < 30:
                    airport_colors.append('orange')
                else:
                    airport_colors.append('red')
            else:
                airport_sizes.append(10)
                airport_text.append(f"{airport_code} - {airport_name}<br>No activity yet")
                airport_colors.append('gray')
    
    # Create airport scattergeo trace
    airport_trace = go.Scattergeo(
        lat=airport_lats,
        lon=airport_lons,
        mode='markers+text',
        text=airport_codes,
        textposition="middle center",
        textfont=dict(size=12, color="white", family="Arial Black"),
        hovertext=airport_text,
        hoverinfo='text',
        marker=dict(
            size=airport_sizes,
            color=airport_colors,
            line=dict(width=2, color='black'),
            opacity=0.8
        ),
        name='Airports'
    )
    
    # Prepare flight route data
    route_data = {}
    for origin, destination, key, data in G.edges(data=True, keys=True):
        route = (origin, destination)
        if route not in route_data:
            route_data[route] = []
        
        dep_time = parse_iso8601_datetime(data.get('actual_departure_gate') or data.get('scheduled_departure_gate'))
        arr_time = parse_iso8601_datetime(data.get('actual_arrival_gate') or data.get('scheduled_arrival_gate'))
        
        if dep_time and arr_time:
            route_data[route].append({
                'dep': dep_time,
                'arr': arr_time,
                'delay': data.get('departure_delay_minutes', 0) or 0
            })
    
    # Create route traces (lines between airports)
    route_traces = []
    for (origin, dest), flights in route_data.items():
        if origin not in airport_coords or dest not in airport_coords:
            continue
        
        # Count active flights on this route
        active_count = sum(1 for f in flights if f['dep'] <= current_time < f['arr'])
        completed_count = sum(1 for f in flights if f['arr'] <= current_time)
        
        if active_count > 0 or completed_count > 0:
            origin_lat, origin_lon = airport_coords[origin]
            dest_lat, dest_lon = airport_coords[dest]
            
            # Determine color based on status
            if active_count > 0:
                line_color = 'blue'  # Active flights
                opacity = 0.7
                width = max(2, min(8, active_count))
            elif completed_count > 0:
                line_color = 'gray'  # Completed flights
                opacity = 0.3
                width = 2
            else:
                continue
            
            # Create great circle route (geodesic line)
            route_trace = go.Scattergeo(
                lat=[origin_lat, dest_lat],
                lon=[origin_lon, dest_lon],
                mode='lines',
                line=dict(width=width, color=line_color),
                opacity=opacity,
                hoverinfo='skip',
                showlegend=False
            )
            route_traces.append(route_trace)
    
    # Create figure with geographic projection
    fig = go.Figure()
    
    # Add route traces first (so airports appear on top)
    for trace in route_traces:
        fig.add_trace(trace)
    
    # Add airport trace
    fig.add_trace(airport_trace)
    
    # Update layout for US map
    fig.update_geos(
        scope='usa',
        projection_type='albers usa',
        showland=True,
        landcolor='rgb(243, 243, 243)',
        showocean=True,
        oceancolor='rgb(230, 245, 255)',
        showlakes=True,
        lakecolor='rgb(230, 245, 255)',
        showrivers=True,
        rivercolor='rgb(230, 245, 255)',
        lonaxis_range=[-130, -65],
        lataxis_range=[24, 50],
        resolution=110
    )
    
    fig.update_layout(
        title=dict(
            text=f"Network Map at {current_time.strftime('%Y-%m-%d %H:%M:%S')} UTC",
            x=0.5,
            xanchor='center',
            font=dict(size=16)
        ),
        height=600,
        margin=dict(l=0, r=0, t=40, b=0),
        annotations=[
            dict(
                text="Node size = Activity | Color = Delay status (Green: On-time, Orange: Moderate, Red: Delayed) | Blue lines = Active flights",
                showarrow=False,
                xref="paper", yref="paper",
                x=0.005, y=-0.002,
                xanchor="left", yanchor="bottom",
                font=dict(size=10, color="#888")
            )
        ]
    )
    
    return fig


def create_fallback_graph(G: nx.MultiDiGraph, current_time: datetime) -> go.Figure:
    """Fallback network graph when coordinates are not available."""
    pos = nx.spring_layout(G, k=2, iterations=50, seed=42)
    node_x = [pos[n][0] for n in G.nodes()]
    node_y = [pos[n][1] for n in G.nodes()]
    
    fig = go.Figure(
        data=[go.Scatter(
            x=node_x, y=node_y,
            mode='markers+text',
            text=list(G.nodes()),
            textposition="middle center",
            marker=dict(size=20, color='blue')
        )],
        layout=go.Layout(
            title=f"Network Graph at {current_time.strftime('%Y-%m-%d %H:%M:%S')} UTC",
            showlegend=False,
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
    """Create flight volume timeline chart with flights enroute and cumulative delays.
    
    Chart shows:
    - Flights enroute (count, left Y-axis)
    - Cumulative outbound delay (total minutes, right Y-axis)
    - Cumulative inbound delay (total minutes, right Y-axis)
    """
    fig = go.Figure()
    
    # Validate DataFrame
    if df.empty or 'time' not in df.columns:
        st.warning("No data available for flight volume timeline chart")
        return fig
    
    # Ensure time column is datetime type
    try:
        if not pd.api.types.is_datetime64_any_dtype(df['time']):
            df['time'] = pd.to_datetime(df['time'])
    except Exception as e:
        st.error(f"Error converting time column: {e}")
        return fig
    
    # Fill NaN values with 0 for safety
    df = df.fillna(0)
    
    # Calculate max values safely
    y_max_left = 1.0
    y_max_right = 1.0
    
    # Add flights enroute line (left Y-axis)
    if 'flights_enroute' in df.columns and len(df) > 0:
        enroute_values = pd.to_numeric(df['flights_enroute'], errors='coerce').fillna(0)
        # Always add trace, even if values are zero (shows tracking)
        fig.add_trace(go.Scatter(
            x=df['time'],
            y=enroute_values,
            mode='lines+markers',
            name='Flights Enroute',
            line=dict(color='blue', width=2),
            marker=dict(size=4),
            yaxis='y'
        ))
        # Calculate max safely
        try:
            y_max_left = max(float(enroute_values.max()), 1.0)
        except (ValueError, TypeError):
            y_max_left = 1.0
    
    # Add cumulative outbound delay line (right Y-axis)
    if 'cumulative_outbound_delay' in df.columns and len(df) > 0:
        outbound_values = pd.to_numeric(df['cumulative_outbound_delay'], errors='coerce').fillna(0)
        # Always add trace (cumulative delays should be tracked even if zero initially)
        fig.add_trace(go.Scatter(
            x=df['time'],
            y=outbound_values,
            mode='lines+markers',
            name='Cumulative Outbound Delay',
            line=dict(color='red', width=2),
            marker=dict(size=4),
            yaxis='y2'
        ))
        # Calculate max safely
        try:
            y_max_right = max(y_max_right, float(outbound_values.max()), 1.0)
        except (ValueError, TypeError):
            y_max_right = max(y_max_right, 1.0)
    
    # Add cumulative inbound delay line (right Y-axis)
    if 'cumulative_inbound_delay' in df.columns and len(df) > 0:
        inbound_values = pd.to_numeric(df['cumulative_inbound_delay'], errors='coerce').fillna(0)
        # Always add trace (cumulative delays should be tracked even if zero initially)
        fig.add_trace(go.Scatter(
            x=df['time'],
            y=inbound_values,
            mode='lines+markers',
            name='Cumulative Inbound Delay',
            line=dict(color='orange', width=2),
            marker=dict(size=4),
            yaxis='y2'
        ))
        # Calculate max safely
        try:
            y_max_right = max(y_max_right, float(inbound_values.max()), 1.0)
        except (ValueError, TypeError):
            y_max_right = max(y_max_right, 1.0)
    
    # Ensure we have at least one trace
    if len(fig.data) == 0:
        # Add a dummy trace if no data
        fig.add_trace(go.Scatter(
            x=[current_time],
            y=[0],
            mode='markers',
            name='No Data',
            marker=dict(size=1, opacity=0)
        ))
    
    # Add vertical line for current time (use appropriate y-axis range)
    y_max_for_line = max(y_max_left, y_max_right, 10.0)  # Ensure minimum range
    
    fig.add_shape(
        type="line",
        x0=current_time,
        x1=current_time,
        y0=0,
        y1=y_max_for_line,
        line=dict(color="red", width=2, dash="dash"),
    )
    
    # Add annotation for current time
    fig.add_annotation(
        x=current_time,
        y=y_max_for_line * 0.95,
        text=f"Current: {current_time.strftime('%H:%M:%S')}",
        showarrow=False,
        bgcolor="rgba(255,255,255,0.8)",
        bordercolor="red",
        borderwidth=1,
        font=dict(size=10, color="red")
    )
    
    # Update layout with dual Y-axes
    # Check if we have delay traces by checking if delay columns exist in DataFrame
    # (We add traces for these columns if they exist, so if columns exist, traces exist)
    has_delay_traces = (
        'cumulative_outbound_delay' in df.columns or 
        'cumulative_inbound_delay' in df.columns
    )
    
    # Build layout using explicit parameter passing
    try:
        if has_delay_traces:
            # Dual Y-axis layout
            fig.update_layout(
                title="Flight Volume Timeline",
                xaxis_title="Time (GMT)",
                yaxis=dict(
                    title=dict(text="Flights Enroute (Count)", font=dict(color='blue')),
                    side='left',
                    tickfont=dict(color='blue')
                ),
                yaxis2=dict(
                    title=dict(text="Cumulative Delay (Minutes)", font=dict(color='red')),
                    side='right',
                    overlaying='y',
                    tickfont=dict(color='red')
                ),
                hovermode='x unified',
                height=400,
                legend=dict(x=0, y=1, traceorder='normal')
            )
        else:
            # Single Y-axis layout
            fig.update_layout(
                title="Flight Volume Timeline",
                xaxis_title="Time (GMT)",
                yaxis=dict(
                    title=dict(text="Flights Enroute (Count)", font=dict(color='blue')),
                    tickfont=dict(color='blue')
                ),
                hovermode='x unified',
                height=400,
                legend=dict(x=0, y=1, traceorder='normal')
            )
    except Exception as e:
        # Fallback to minimal layout if there's an error
        st.error(f"Error configuring chart layout: {e}")
        fig.update_layout(
            title="Flight Volume Timeline",
            height=400
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
    
    # Airport Status Table
    st.header("📍 Airport Status")
    
    airports = sorted(G.nodes())
    
    # Prepare data for table
    airport_data = []
    for airport_code in airports:
        status = create_airport_status_panel(G, airport_code, current_time)
        airport_data.append({
            'Airport': status['airport_code'],
            'Airport Name': status['airport_name'],
            'Departures': status['total_departures'],
            'Arrivals': status['total_arrivals'],
            'Active Flights': status['active_flights'],
            'Avg Dep Delay': round(status['avg_departure_delay'], 1) if status['total_departures'] > 0 else None,
            'Avg Arr Delay': round(status['avg_arrival_delay'], 1) if status['total_arrivals'] > 0 else None,
            'On-Time Dep %': round(status['on_time_departure_pct'], 1) if status['total_departures'] > 0 else None,
            'On-Time Arr %': round(status['on_time_arrival_pct'], 1) if status['total_arrivals'] > 0 else None,
        })
    
    airport_df = pd.DataFrame(airport_data)
    
    # Configure AgGrid
    gb = GridOptionsBuilder.from_dataframe(airport_df)
    gb.configure_pagination(paginationAutoPageSize=False, paginationPageSize=10)
    gb.configure_default_column(filterable=True, sortable=True, resizable=True)
    gb.configure_column("Airport", pinned='left', width=80)
    gb.configure_column("Airport Name", width=200)
    gb.configure_column("Departures", type=["numericColumn", "numberColumnFilter", "customNumericFormat"], precision=0)
    gb.configure_column("Arrivals", type=["numericColumn", "numberColumnFilter", "customNumericFormat"], precision=0)
    gb.configure_column("Active Flights", type=["numericColumn", "numberColumnFilter", "customNumericFormat"], precision=0)
    gb.configure_column("Avg Dep Delay", type=["numericColumn", "numberColumnFilter", "customNumericFormat"], precision=1)
    gb.configure_column("Avg Arr Delay", type=["numericColumn", "numberColumnFilter", "customNumericFormat"], precision=1)
    gb.configure_column("On-Time Dep %", type=["numericColumn", "numberColumnFilter", "customNumericFormat"], precision=1)
    gb.configure_column("On-Time Arr %", type=["numericColumn", "numberColumnFilter", "customNumericFormat"], precision=1)
    grid_options = gb.build()
    
    # Display AgGrid table
    AgGrid(
        airport_df,
        gridOptions=grid_options,
        update_mode=GridUpdateMode.FILTERING_CHANGED | GridUpdateMode.SORTING_CHANGED,
        allow_unsafe_jscode=True,
        height=200,
        theme='streamlit'
    )
    
    # Flight Volume Timeline
    st.header("📊 Flight Volume Timeline")
    
    with st.spinner("Calculating flight volume timeline..."):
        # Get data for flights enroute and cumulative delays
        # Sample at 1-minute intervals for performance (can increase for larger datasets)
        enroute_df = get_flights_enroute_over_time(G, first_departure, last_arrival, interval_minutes=1)
        outbound_delay_df = get_cumulative_delay_over_time(G, first_departure, last_arrival, interval_minutes=1, delay_type='departure')
        inbound_delay_df = get_cumulative_delay_over_time(G, first_departure, last_arrival, interval_minutes=1, delay_type='arrival')
        
        # Merge dataframes on time (columns are already correctly named)
        # Start with enroute data as base
        volume_df = enroute_df.copy()
        
        # Merge delay dataframes if they exist and have data
        if not outbound_delay_df.empty:
            volume_df = volume_df.merge(outbound_delay_df, on='time', how='outer')
        else:
            volume_df['cumulative_outbound_delay'] = 0
        
        if not inbound_delay_df.empty:
            volume_df = volume_df.merge(inbound_delay_df, on='time', how='outer')
        else:
            volume_df['cumulative_inbound_delay'] = 0
        
        # Sort by time and fill missing values
        volume_df = volume_df.sort_values('time').reset_index(drop=True)
        
        # Forward-fill missing values for cumulative delays (they should be monotonically increasing)
        if 'cumulative_outbound_delay' in volume_df.columns:
            volume_df['cumulative_outbound_delay'] = pd.to_numeric(volume_df['cumulative_outbound_delay'], errors='coerce').ffill().fillna(0)
        if 'cumulative_inbound_delay' in volume_df.columns:
            volume_df['cumulative_inbound_delay'] = pd.to_numeric(volume_df['cumulative_inbound_delay'], errors='coerce').ffill().fillna(0)
        if 'flights_enroute' in volume_df.columns:
            volume_df['flights_enroute'] = pd.to_numeric(volume_df['flights_enroute'], errors='coerce').fillna(0)
        
        # Ensure time column is datetime
        volume_df['time'] = pd.to_datetime(volume_df['time'])
        
        volume_fig = create_flight_volume_chart(volume_df, current_time)
        st.plotly_chart(volume_fig, use_container_width=True)
    
    # Event Timeline
    st.header("📅 Event Timeline")
    
    # Show all events by default (not just a window around current time)
    # This allows users to see all departures and arrivals
    # The table can be filtered by time range using the sortable/filterable functionality
    window_start = first_departure
    window_end = last_arrival
    
    events = get_events_in_window(G, window_start, window_end)
    
    if events:
        # Build events DataFrame with route and delay information
        events_data = []
        for event in events:
            flight_id = event.get('flight_id', 'unknown')
            event_type = event.get('event_type', 'unknown').lower()
            airport = event.get('airport', '')
            timestamp = event.get('timestamp')
            
            # Find flight edge to get route and delay information
            route = 'N/A'
            delay = None
            status = 'Unknown'
            
            # Search for flight in graph edges
            for origin, destination, key, data in G.edges(data=True, keys=True):
                if data.get('flight_id') == flight_id:
                    route = f"{origin} → {destination}"
                    
                    # Get appropriate delay based on event type
                    if event_type == 'departure':
                        delay = data.get('departure_delay_minutes', 0) or 0
                    elif event_type == 'arrival':
                        delay = data.get('arrival_delay_minutes', 0) or 0
                    
                    # Determine status
                    if delay is not None:
                        if delay < -15:
                            status = 'Early'
                        elif delay <= 15:
                            status = 'On-Time'
                        elif delay <= 30:
                            status = 'Moderate Delay'
                        else:
                            status = 'Significant Delay'
                    break
            
            events_data.append({
                'Timestamp': timestamp.strftime('%Y-%m-%d %H:%M:%S UTC') if timestamp else '',
                'Time': timestamp.strftime('%H:%M:%S') if timestamp else '',
                'Event Type': event_type.upper(),
                'Airport': airport,
                'Flight ID': flight_id,
                'Route': route,
                'Delay': round(float(delay), 1) if delay is not None else None,
                'Status': status
            })
        
        events_df = pd.DataFrame(events_data)
        
        # Configure AgGrid for events table
        gb_events = GridOptionsBuilder.from_dataframe(events_df)
        gb_events.configure_pagination(paginationAutoPageSize=False, paginationPageSize=20)
        
        # Enable side bar for filter menu
        gb_events.configure_side_bar()
        
        # Set default: all columns filterable, sortable, resizable
        gb_events.configure_default_column(
            filterable=True,  # Enable filtering for all columns by default
            sortable=True, 
            resizable=True
        )
        
        # Configure each column explicitly with filterable=True
        # Explicitly configure filter for text columns to ensure they're filterable
        # Use filterParams to configure filter options
        text_columns = ["Timestamp", "Time", "Event Type", "Airport", "Flight ID", "Route", "Status"]
        for col in text_columns:
            if col == "Timestamp":
                gb_events.configure_column(col, width=200, pinned='left', filterable=True, sortable=True)
            elif col == "Time":
                gb_events.configure_column(col, width=100, filterable=True, sortable=True)
            elif col == "Event Type":
                gb_events.configure_column(col, width=100, filterable=True, sortable=True)
            elif col == "Airport":
                gb_events.configure_column(col, width=80, filterable=True, sortable=True)
            elif col == "Flight ID":
                gb_events.configure_column(col, width=200, filterable=True, sortable=True)
            elif col == "Route":
                gb_events.configure_column(col, width=120, filterable=True, sortable=True)
            elif col == "Status":
                gb_events.configure_column(col, width=150, filterable=True, sortable=True)
        
        # Delay column - numeric with numberColumnFilter (already specified in type)
        gb_events.configure_column(
            "Delay", 
            type=["numericColumn", "numberColumnFilter", "customNumericFormat"], 
            precision=1, 
            width=100,
            filterable=True,
            sortable=True
        )
        
        # Configure selection mode
        gb_events.configure_selection('single')
        grid_options_events = gb_events.build()
        
        # After building, explicitly set filter for text columns in the grid options
        # This ensures text columns have the agTextColumnFilter enabled
        if 'columnDefs' in grid_options_events:
            for col_def in grid_options_events['columnDefs']:
                field_name = col_def.get('field', '')
                # Ensure all columns are filterable
                col_def['filterable'] = True
                # For text columns (not Delay which is numeric), set explicit text filter
                if field_name != 'Delay' and field_name in text_columns:
                    col_def['filter'] = 'agTextColumnFilter'
                    # Add filter params for text columns
                    if 'filterParams' not in col_def:
                        col_def['filterParams'] = {
                            'filterOptions': ['equals', 'notEqual', 'contains', 'notContains', 'startsWith', 'endsWith']
                        }
        
        # Display AgGrid table
        AgGrid(
            events_df,
            gridOptions=grid_options_events,
            update_mode=GridUpdateMode.FILTERING_CHANGED | GridUpdateMode.SORTING_CHANGED,
            allow_unsafe_jscode=True,
            height=400,
            theme='streamlit'
        )
    else:
        st.info("No events in this time window.")
    
    # Footer
    st.markdown("---")
    st.markdown("**Dashboard Version:** MVP (Phase 1) | **Data:** Event-level temporal snapshots")


if __name__ == '__main__':
    main()
