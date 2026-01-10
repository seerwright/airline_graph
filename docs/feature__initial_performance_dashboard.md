# Feature: Initial Performance Dashboard

## Intent & Purpose

The initial performance dashboard provides real-time visualization of airline operations throughout the simulation period. It enables users to monitor and analyze the state of flights, airports, delays, volume, and network performance as events unfold over time.

### Goals
- **Real-time Monitoring**: View the network state at any point in time during the simulation
- **Event-Level Granularity**: Track changes at the event level (every departure and arrival)
- **Performance Analysis**: Analyze delays, on-time performance, and network efficiency
- **Network Visualization**: Visualize the flight network topology and flow between airports
- **Temporal Analysis**: Understand how the network evolves over time
- **Operational Insights**: Identify bottlenecks, delays, and performance issues

### Use Cases
- Development & Testing: Monitor simulation execution in real-time
- Performance Analysis: Identify patterns in delays and network efficiency
- Operational Review: Review airport performance and flight status
- Troubleshooting: Debug issues in flight scheduling and execution
- Presentation: Demonstrate network behavior to stakeholders

---

## Technical Stack

### Primary Framework: **Streamlit**

**Rationale:**
- Fast to prototype with Python
- Excellent for time-series and interactive visualizations
- Built-in widgets (sliders, selectors, play controls) perfect for time navigation
- Easy integration with NetworkX graphs and pandas DataFrames
- Simple deployment and sharing
- Good for dashboard-style applications

### Visualization Libraries

**Plotly** (Primary):
- Interactive network graphs (`plotly.graph_objects`)
- Time-series charts (`plotly.express`)
- Heatmaps and geographic visualizations
- Real-time animations
- Excellent interactivity (hover, zoom, pan)

**NetworkX** (Graph Structure):
- Access to graph data structure
- Network layout algorithms (spring, circular, etc.)
- Graph metrics and analysis

**Pandas** (Data Manipulation):
- Time-series data processing
- Aggregation and filtering
- DataFrame operations for charts

### Package Dependencies

```python
# Core dashboard framework
streamlit>=1.28.0

# Visualization
plotly>=5.17.0
networkx>=3.0  # Already in requirements.txt

# Data processing
pandas>=2.0  # Already in requirements.txt
numpy>=1.24  # Already in requirements.txt

# Interactive tables (sortable, filterable)
streamlit-aggrid>=0.3.0
```

---

## Dashboard Visualizations

### 1. Time Control Panel (Top Navigation)

**Purpose**: Navigate through simulation time and control playback

**Components**:
- **Time Slider**: 
  - Range: First departure to last arrival
  - Granularity: 1-minute increments
  - Visual timeline with event markers
  - Current time display (large, prominent GMT timestamp)
  
- **Playback Controls**:
  - Play/Pause button
  - Step Forward/Backward (1-minute steps)
  - Jump to Start/End buttons
  - Speed control (1x, 2x, 5x, 10x, 60x)
  - Loop mode toggle
  
- **Time Range Selector**:
  - Start time picker
  - End time picker
  - Quick preset buttons (Full Range, First Hour, Last Hour, etc.)

**Interactivity**: 
- Slider updates all visualizations in real-time
- Playback animates time progression
- Speed control adjusts animation rate

---

### 2. Network Graph Visualization (Main View)

**Purpose**: Visualize the flight network topology and state on a geographic map of the United States

**Layout**: Interactive geographic map overlay using Plotly Geo (`plotly.graph_objects.Scattergeo`)

**Geographic Mapping**:
- **Base Map**: United States map with state boundaries
- **Airport Coordinates**: Airport nodes positioned at their actual geographic locations (latitude/longitude from `airports_sample.csv`)
  - **ATL**: Atlanta, Georgia (Hartsfield-Jackson Atlanta International Airport)
  - **LGA**: New York, New York (LaGuardia Airport)
  - **SLC**: Salt Lake City, Utah (Salt Lake City International Airport)
- **Projection**: Albers Equal Area Conic or Mercator projection suitable for continental US

**Node Representation (Airports)**:
- **Position**: Geographic coordinates (latitude/longitude) - NOT NetworkX layout
- **Size**: Proportional to activity (total departures + arrivals) at current time
- **Color**: Color-coded by delay status
  - Green: On-time (avg delay < 15 min)
  - Yellow: Moderate delays (15-30 min)
  - Red: Significant delays (> 30 min)
- **Label**: Airport code (ATL, LGA, SLC) with airport name
- **Marker**: Circular markers, size varies with activity level
- **Tooltip**: 
  - Airport name and location
  - Current state metrics (departures, arrivals, delays, on-time %)
  - Total events count

**Edge Representation (Flights/Routes)**:
- **Lines**: Geodesic or great-circle routes between airports on the map
- **Width**: Number of flights on route (at current time)
- **Color**: 
  - Blue: Active flights (in the air at current time)
  - Gray: Completed flights (arrived before current time)
  - Orange: Scheduled flights (not yet departed)
  - Red: Delayed flights (delay > 15 min)
- **Direction**: Directed lines/arcs showing flight direction
- **Opacity**: Fade completed flights, highlight active flights
- **Tooltip**:
  - Route (origin → destination)
  - Number of flights on route
  - Average delay on route
  - Flight IDs (list of active flights)

**Interactive Features**:
- Geographic zoom and pan (zoom to specific regions)
- Click to select airport/flight for details
- Hover for tooltips with geographic and metric information
- Toggle visibility (show/hide completed flights)
- Animation: Routes appear/disappear as flights depart/arrive
- Map controls (zoom in/out, reset view, toggle state boundaries)

**Data Requirements**:
- Airport latitude/longitude coordinates must be added to `airports_sample.csv`:
  - Columns: `latitude`, `longitude` (decimal degrees)
  - Coordinates for ATL, LGA, SLC must be accurate for geographic positioning

---

### 3. Airport Status Table

**Purpose**: Display current state metrics for all airports in a sortable and filterable table

**Layout**: Single interactive data table using `streamlit-aggrid`

**Table Component**: `streamlit-aggrid` (AgGrid component)
- **Built-in Features**: Sortable columns, filterable rows, search functionality
- **No Custom Code Required**: All functionality provided out-of-the-box
- **Performance**: Optimized for large datasets (efficient rendering)

**Table Structure**:
- **Rows**: One row per airport (ATL, LGA, SLC)
- **Columns** (at selected time):
  - **Airport**: Airport code (ATL, LGA, SLC)
  - **Airport Name**: Full airport name
  - **Departures**: Total departures (cumulative count, integer)
  - **Arrivals**: Total arrivals (cumulative count, integer)
  - **Active Flights**: Flights currently in the air (integer)
  - **Avg Dep Delay**: Average departure delay (minutes, float, 1 decimal)
  - **Avg Arr Delay**: Average arrival delay (minutes, float, 1 decimal)
  - **On-Time Dep %**: On-time departure percentage (float, 1 decimal)
  - **On-Time Arr %**: On-time arrival percentage (float, 1 decimal)

**Table Features**:
- **Sorting**: Click column headers to sort ascending/descending
- **Filtering**: Filter rows by any column value
- **Search**: Search across all columns
- **Color-Coding**: Color-code cells based on values (green=good, yellow=moderate, red=poor)
  - Delay columns: Green < 15 min, Yellow 15-30 min, Red > 30 min
  - On-Time % columns: Green ≥ 95%, Yellow 80-95%, Red < 80%
- **Auto-Update**: Table updates when time slider changes
- **Export**: Export filtered/sorted data to CSV (built-in AgGrid feature)

**Visual Design**:
- Clean, professional table layout
- Alternating row colors for readability
- Header row with sort indicators
- Compact, scannable format
- Responsive width (uses container width)

---

### 4. Flight Activity Charts (Main Content Area)

**Purpose**: Show flight volume and activity over time

#### A. Flight Volume Timeline

**Chart Type**: Multi-Line Chart (Plotly)

**X-Axis**: Time (GMT, from first departure to last arrival)

**Y-Axis**: 
- Left Y-Axis: Count (for flights enroute)
- Right Y-Axis: Total Delay Minutes (for cumulative delays)

**Lines** (All metrics shown simultaneously):
1. **Flights Enroute** (Blue line, left Y-axis)
   - Number of flights currently in the air at each point in time
   - Real-time count of active flights
   - Peaks when multiple flights are airborne simultaneously

2. **Cumulative Outbound Delay** (Red line, right Y-axis)
   - Total minutes of departure delay accumulated up to that point in time
   - Sum of `departure_delay_minutes` for all flights that have departed by that time
   - Monotonically increasing (never decreases)
   - Shows cumulative impact of departure delays

3. **Cumulative Inbound Delay** (Orange line, right Y-axis)
   - Total minutes of arrival delay accumulated up to that point in time
   - Sum of `arrival_delay_minutes` for all flights that have arrived by that time
   - Monotonically increasing (never decreases)
   - Shows cumulative impact of arrival delays

**Chart Features**:
- **Dual Y-Axes**: Left axis for count (flights enroute), right axis for delay minutes (cumulative delays)
- **Hover Tooltips**: Show exact values for all metrics at any time
- **Vertical Line Indicator**: Red dashed line showing current time position (synced with slider)
- **Legend**: Clickable legend to show/hide individual lines
- **Zoom and Pan**: Interactive chart navigation
- **Time Navigation**: Click on chart to jump to specific time (optional)
- **Color-Coded Lines**: 
  - Blue: Flights enroute
  - Red: Cumulative outbound delay
  - Orange: Cumulative inbound delay

**Data Calculation**:
- **Flights Enroute**: Count flights where `departure_time <= current_time < arrival_time`
- **Cumulative Outbound Delay**: Sum of `departure_delay_minutes` for all flights where `departure_time <= current_time`
- **Cumulative Inbound Delay**: Sum of `arrival_delay_minutes` for all flights where `arrival_time <= current_time`

---

#### B. Active Flights Count Over Time

**Chart Type**: Stacked Area Chart (Plotly)

**X-Axis**: Time (GMT)

**Y-Axis**: Number of Active Flights (flights in the air)

**Stacking**:
- Each route gets a color segment
- Stacked by route (ATL→LGA, LGA→ATL, ATL→SLC, etc.)
- Shows which routes have flights in air at any moment
- Total height = total active flights

**Features**:
- Interactive legend (click to show/hide routes)
- Tooltip shows route and flight count at hover time
- Vertical line indicator for current time
- Animation shows flights entering/leaving air

---

#### C. Delay Distribution Over Time

**Chart Type**: Multi-Line Chart (Plotly)

**X-Axis**: Time (GMT)

**Y-Axis**: Average Delay (minutes)

**Lines**:
- Blue line: Average Departure Delay (across all airports)
- Orange line: Average Arrival Delay (across all airports)
- Optional: Individual airport delay lines (toggleable)

**Features**:
- Negative delays shown (early flights)
- Zero-delay reference line
- Color thresholds (green < 15 min, yellow 15-30 min, red > 30 min)
- Tooltip shows exact delay values and airport breakdown
- Click to filter by airport

---

#### D. On-Time Performance Over Time

**Chart Type**: Area Chart or Line Chart (Plotly)

**X-Axis**: Time (GMT)

**Y-Axis**: On-Time Percentage (0-100%)

**Areas**:
- Green area: Departure On-Time % (green fill)
- Blue area: Arrival On-Time % (blue fill)
- 95% target line (dashed reference line)
- Optional: Per-airport breakdown (toggleable)

**Features**:
- Threshold coloring (above/below 95%)
- Tooltip shows exact percentages and sample sizes
- Vertical line indicator for current time
- Filter by airport or route

---

### 5. Route Analysis Panel

**Purpose**: Analyze performance by route

#### A. Route Volume Table

**Chart Type**: Interactive Data Table (Streamlit/Plotly)

**Columns**:
- Route (Origin → Destination)
- Total Flights (count)
- Average Departure Delay (minutes, color-coded)
- Average Arrival Delay (minutes, color-coded)
- On-Time % (percentage, color-coded)
- Status Badge (On-Time / Delayed / At-Risk)

**Features**:
- Sortable columns
- Filterable by route, delay threshold
- Color-coded cells (green/yellow/red)
- Click row to highlight on network graph
- Export to CSV

---

#### B. Route Delay Heatmap

**Chart Type**: Heatmap (Plotly)

**X-Axis**: Time Periods (10-minute buckets)

**Y-Axis**: Routes (ATL→LGA, LGA→ATL, etc.)

**Color Intensity**: Average delay severity
- Green: On-time (< 15 min delay)
- Yellow: Moderate (15-30 min delay)
- Red: Significant (> 30 min delay)
- White: No flights in period

**Features**:
- Interactive tooltip shows route, time, delay details
- Click cell to filter main visualizations to that time period
- Zoom to specific time ranges
- Toggle between departure and arrival delays

---

#### C. Route Network Flow

**Chart Type**: Sankey Diagram (Plotly) - Optional Enhancement

**Purpose**: Show flow of flights between airports

**Components**:
- Left nodes: Origin airports
- Right nodes: Destination airports
- Flows: Directed edges showing flight volume
- Width: Proportional to number of flights
- Color: Average delay (green/yellow/red)

**Features**:
- Interactive: click to filter other views
- Animation: flows update with time
- Hover tooltip shows route details

---

### 6. Event Timeline Panel (Bottom Section)

**Purpose**: Chronological log of all departure and arrival events

#### A. Event Log Table

**Chart Type**: Interactive Data Table using `streamlit-aggrid`

**Layout**: Sortable and filterable table of all events (departures AND arrivals)

**Table Component**: Same `streamlit-aggrid` component as Airport Status table
- **Built-in Features**: Sortable columns, filterable rows, search functionality
- **No Custom Code Required**: All functionality provided out-of-the-box

**Table Structure**:
- **Rows**: One row per event (departure or arrival)
- **Columns**:
  - **Timestamp**: Full timestamp (YYYY-MM-DD HH:MM:SS GMT)
  - **Time**: Time portion (HH:MM:SS GMT) for quick reference
  - **Event Type**: Departure or Arrival (text badge)
  - **Airport**: Airport code (ATL, LGA, SLC)
  - **Flight ID**: Flight identifier (e.g., WN1234_2026-01-01_ATL_LGA)
  - **Route**: Origin → Destination (e.g., ATL → LGA)
  - **Delay**: Delay in minutes (departure delay for departures, arrival delay for arrivals)
  - **Status**: On-Time, Delayed, or Early (based on delay threshold, typically ±15 minutes)

**Table Features**:
- **Sorting**: Click column headers to sort by any column (timestamp, airport, delay, etc.)
- **Filtering**: Filter rows by:
  - **Event Type**: Filter to show only departures, only arrivals, or both
  - **Airport**: Filter by airport code (ATL, LGA, SLC)
  - **Delay**: Filter by delay threshold (e.g., delays > 15 minutes)
  - **Time Range**: Filter by timestamp range
  - **Flight ID**: Search by flight identifier
- **Search**: Global search across all columns
- **Color-Coding**: Color-code rows based on status
  - Green: On-time (delay within ±15 minutes)
  - Yellow: Moderate delays (15-30 minutes)
  - Red: Significant delays (> 30 minutes)
  - Blue: Early (negative delay, arrived/departed ahead of schedule)
- **Time Window**: Default shows events in ±30 minute window around current time
- **Auto-Update**: Table updates when time slider changes (updates time window)
- **Highlight Current Time**: Optionally highlight events at current time
- **Export**: Export filtered/sorted data to CSV (built-in AgGrid feature)

**Visual Design**:
- Chronological order (sorted by timestamp by default)
- Color-coded rows for quick status identification
- Compact, scannable format
- Alternating row colors for readability
- Icons or badges for event type (optional visual enhancement)
- Responsive width (uses container width)

---

#### B. Event Distribution

**Chart Type**: Stacked Bar Chart (Plotly)

**X-Axis**: Time Periods (10-minute buckets)

**Y-Axis**: Event Count

**Bars**:
- Blue segment: Departures in period
- Orange segment: Arrivals in period
- Total height: Total events in period

**Features**:
- Tooltip shows exact counts
- Click bar to filter to that time period
- Vertical line indicator for current time
- Animated bars as time progresses

---

### 7. Metrics Summary Cards (Top Row)

**Purpose**: Key performance indicators at a glance

**Layout**: Horizontal row of metric cards

**KPI Cards** (6-8 cards):

1. **Total Flights Completed**
   - Large number
   - Subtitle: "Out of X scheduled"
   - Trend indicator: ↑/↓ from previous period

2. **Average Network Delay**
   - Large number (minutes)
   - Subtitle: "Across all airports"
   - Color-coded badge (green/yellow/red)
   - Trend indicator

3. **On-Time Performance**
   - Large percentage
   - Subtitle: "Network-wide"
   - Progress bar (0-100%)
   - Trend indicator

4. **Active Flights**
   - Large number
   - Subtitle: "Currently in air"
   - Animated counter
   - Route breakdown (tooltip)

5. **Network Efficiency Score**
   - Large number (0-100)
   - Subtitle: "Composite metric"
   - Gauge chart (optional)
   - Trend indicator

6. **Total Passengers** (if available)
   - Large number
   - Subtitle: "Across all flights"
   - Trend indicator

7. **Equipment Utilization** (if available)
   - Large percentage
   - Subtitle: "Aircraft utilization"
   - Trend indicator

8. **Routes Operated**
   - Large number
   - Subtitle: "Unique routes"
   - Route list (tooltip)

**Visual Design**:
- Large, readable numbers
- Color-coded backgrounds (green/yellow/red)
- Trend arrows (↑/↓/→)
- Compact, scannable layout
- Responsive grid (adjusts to screen size)

---

### 8. Delay Analysis Panel (Optional/Expandable)

**Purpose**: Detailed delay analysis and distribution

#### A. Delay Distribution Histogram

**Chart Type**: Histogram (Plotly)

**X-Axis**: Delay Minutes (buckets: -30 to +60 minutes)

**Y-Axis**: Flight Count

**Bars**:
- Blue bars: Departure delays
- Orange bars: Arrival delays
- Vertical reference line at 0 (on-time)

**Features**:
- Interactive: click bar to filter flights with that delay range
- Filterable by airport, route, time period
- Tooltip shows exact counts
- Cumulative distribution overlay (optional)

---

#### B. Cumulative Delay Impact

**Chart Type**: Stacked Area Chart (Plotly)

**X-Axis**: Time (GMT)

**Y-Axis**: Cumulative Delay Minutes

**Stacking**:
- Blue area: Cumulative departure delay minutes
- Orange area: Cumulative arrival delay minutes
- Total = total delay impact on network

**Features**:
- Shows total delay burden over time
- Tooltip shows exact delay minutes at any time
- Slopes indicate delay rate
- Vertical line indicator for current time

---

### 9. Airport Comparison View (Expandable Section)

**Purpose**: Side-by-side comparison of airport performance

#### A. Airport Metrics Comparison

**Chart Type**: Grouped Bar Chart or Parallel Coordinate Plot (Plotly)

**Layout**: Compare ATL, LGA, SLC side-by-side

**Metrics Compared**:
- Total Operations (departures + arrivals)
- Average Delays (departure and arrival)
- On-Time Performance % (departure and arrival)
- Efficiency Scores (if calculated)

**Visualization Options**:
- **Option 1**: Grouped bar chart (metrics on X, airports as grouped bars)
- **Option 2**: Parallel coordinate plot (airports as lines, metrics as axes)
- **Option 3**: Radar/spider chart (airports as separate charts)

**Features**:
- Toggleable metrics
- Time-filtered (compare at specific time vs. all-time)
- Export to image/PDF
- Tooltip with exact values

---

## User Interaction & Viewing

### Accessing the Dashboard

**Local Development**:
```bash
# Activate virtual environment
source agraph_env/bin/activate

# Install dependencies (if not already installed)
pip install streamlit plotly

# Run dashboard
streamlit run scripts/dashboard.py
```

**Access URL**: 
- Default: `http://localhost:8501`
- Opens automatically in default web browser

**Deployment Options** (Future):
- Streamlit Cloud (free hosting)
- Docker container
- Local network server (for team sharing)
- Self-hosted Streamlit server

---

### Dashboard Navigation

**Initial View**:
- Dashboard loads with graph data from saved JSON file (or builds graph on startup)
- Default time set to first departure (2026-01-01T08:00:00Z)
- All visualizations show initial state (all zeros)

**Time Navigation**:
1. **Time Slider**: Drag to any point in time
   - All visualizations update instantly
   - Network graph shows state at that time
   - Airport panels update to current state
   - Charts highlight current time position
   
2. **Playback Controls**:
   - Click **Play** to start animation
   - Time advances automatically at selected speed
   - Visualizations update in real-time
   - Click **Pause** to stop
   - Use **Step Forward/Backward** for manual navigation
   
3. **Jump Controls**:
   - **Jump to Start**: First departure event
   - **Jump to End**: Last arrival event
   - **Jump to Event**: Select from dropdown of major events
   - **Custom Time**: Enter specific GMT timestamp

**Interactive Elements**:
- **Hover**: Tooltips appear on all charts showing details
- **Click**: 
  - Airport nodes: Filter/highlight flights from that airport
  - Flight edges: Show flight details panel
  - Chart elements: Filter other views to that selection
  - Table rows: Highlight on network graph
- **Zoom/Pan**: Click and drag on network graph, double-click to reset
- **Filters**: Use sidebar filters to narrow down views
- **Export**: Download current view as image/PDF

---

### Dashboard Layout Structure

```
┌─────────────────────────────────────────────────────────────────────┐
│  Header: "Airline Network Performance Dashboard"                    │
│  [Time Control Panel: Slider, Play/Pause, Speed, Current Time]     │
├─────────────────────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────┐  ┌─────────────────────────┐ │
│  │                                  │  │  KPI Summary Cards      │ │
│  │  Network Graph Visualization     │  │  [6-8 metric cards]     │ │
│  │  (Interactive, main view)        │  │                         │ │
│  │                                  │  │  • Total Flights        │ │
│  │  [ATL] ──→ [LGA]                 │  │  • Avg Delay            │ │
│  │    │        ↑                    │  │  • On-Time %            │ │
│  │    └──→ [SLC]                    │  │  • Active Flights       │ │
│  │                                  │  │  • Efficiency           │ │
│  └──────────────────────────────────┘  └─────────────────────────┘ │
│                                                                      │
│  ┌──────────────────────────────────┐  ┌─────────────────────────┐ │
│  │  Flight Volume Timeline          │  │  Airport Status Panel   │ │
│  │  [Line chart: Departures/Arrivals]│ │                         │ │
│  ├──────────────────────────────────┤  │  ATL:                   │ │
│  │  Active Flights Over Time        │  │  • Departures: 3        │ │
│  │  [Stacked area chart]            │  │  • Arrivals: 2          │ │
│  ├──────────────────────────────────┤  │  • Avg Delay: 0.0 min   │ │
│  │  Delay Trends                    │  │  • On-Time: 100%        │ │
│  │  [Multi-line chart]              │  │  [Mini charts below]    │ │
│  ├──────────────────────────────────┤  │                         │ │
│  │  On-Time Performance             │  │  LGA:                   │ │
│  │  [Area chart]                    │  │  • Departures: 3        │ │
│  └──────────────────────────────────┘  │  • Arrivals: 3          │ │
│                                        │  • Avg Delay: 2.5 min   │ │
│  ┌──────────────────────────────────┐  │  • On-Time: 95%         │ │
│  │  Route Analysis                  │  │  [Mini charts below]    │ │
│  │  [Route Table + Heatmap]         │  │                         │ │
│  └──────────────────────────────────┘  │  SLC:                   │ │
│                                        │  • Departures: 2        │ │
│                                        │  • Arrivals: 2          │ │
│                                        │  • Avg Delay: 4.0 min   │ │
│                                        │  • On-Time: 90%         │ │
│                                        │  [Mini charts below]    │ │
│                                        └─────────────────────────┘ │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │  Event Timeline                                                │ │
│  │  [Event Log Stream: Chronological list]                        │ │
│  │  [Event Distribution: Bar chart]                               │ │
│  └────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

---

### Sidebar Controls (Streamlit Sidebar)

**Time Controls**:
- Time range selector (start/end)
- Playback speed slider
- Auto-scroll toggle
- Loop mode toggle

**Filters**:
- Airport selector (multi-select: ATL, LGA, SLC)
- Route selector (multi-select)
- Delay threshold slider (show flights with delay > X minutes)
- Event type filter (departure/arrival/both)

**View Options**:
- Show/hide completed flights (on map)
- Show/hide delayed flights only (on map)
- Map projection selector (Albers, Mercator, etc.)
- Chart style selector (theme)
- Refresh data button

**Data Options**:
- Load graph from file (file picker)
- Reload graph from CSV (rebuild)
- Export current view (download button)
- Clear filters button

---

## Data Queries & Functions

### Core Query Functions Needed

1. **`get_airport_state_at_time(G, airport_code, target_time)`**
   - Returns: Cumulative airport state at specific time
   - Uses: Event-level snapshots (last snapshot before/at target_time)

2. **`get_active_flights_at_time(G, target_time)`**
   - Returns: List of flights in the air at target time
   - Uses: Edge temporal attributes (departure < target_time < arrival)

3. **`get_completed_flights_up_to_time(G, target_time)`**
   - Returns: List of flights that have arrived by target time
   - Uses: Edge temporal attributes (arrival <= target_time)

4. **`get_events_in_time_range(G, start_time, end_time)`**
   - Returns: All departure AND arrival events in time range
   - Uses: Event-level snapshots (filtered by timestamp and event_type)
   - Includes: Both departure and arrival events (must include both types)
   - Returns: List of events with timestamp, event_type, airport, flight_id, delay info

5. **`get_flights_enroute_over_time(G, start_time, end_time, interval_minutes)`**
   - Returns: Time series of flights enroute count at each interval
   - Uses: Edge temporal attributes (count flights where departure <= time < arrival)
   - Returns: DataFrame with time and enroute_count columns

6. **`get_cumulative_delay_over_time(G, start_time, end_time, interval_minutes, delay_type='departure')`**
   - Returns: Time series of cumulative delay minutes (total, not average)
   - Parameters:
     - `delay_type='departure'`: Sum of departure_delay_minutes for departed flights
     - `delay_type='arrival'`: Sum of arrival_delay_minutes for arrived flights
   - Uses: Edge attributes (sum of delay_minutes for completed flights up to each time)
   - Returns: DataFrame with time and cumulative_delay_minutes columns
   - Note: Values are monotonically increasing (cumulative sum)

7. **`get_route_metrics_at_time(G, target_time)`**
   - Returns: Route performance metrics (volume, delays) at target time
   - Uses: Edge attributes filtered by time

8. **`get_network_metrics_at_time(G, target_time)`**
   - Returns: Network-wide KPIs (totals, averages) at target time
   - Uses: Aggregated from all airports and routes

9. **`get_airport_coordinates(G)`**
   - Returns: Dictionary mapping airport codes to (latitude, longitude) tuples
   - Uses: Airport node attributes (latitude/longitude from airports_sample.csv)
   - Returns: `{airport_code: (lat, lon), ...}` for geographic mapping

10. **`extract_time_series_data(G, start_time, end_time, metric_type, interval_minutes)`**
    - Returns: Time series DataFrame for plotting
    - Uses: Aggregated data at regular intervals
    - Supports: flights_enroute, cumulative_outbound_delay, cumulative_inbound_delay, etc.

---

## Performance Considerations

### Data Loading
- **Option 1**: Load pre-built graph from JSON file (`data/processed/graph.json`)
  - Faster startup
  - No computation needed
  - Requires graph to be built separately
  
- **Option 2**: Build graph on dashboard startup from CSV files
  - Slower startup (few seconds)
  - Always up-to-date
  - Requires data processing

**Recommendation**: Start with Option 1, add Option 2 as fallback

### Caching Strategy
- **Streamlit Caching**: Use `@st.cache_data` for:
  - Graph loading (if built from CSV)
  - Time-series data extraction (cache by time range)
  - Aggregated metrics (cache by time point)
  
- **Query Optimization**:
  - Pre-compute common queries
  - Cache airport states at time intervals (every minute)
  - Use efficient data structures for time lookups

### Update Frequency
- **Real-time Mode**: Updates on every time slider change (instant)
- **Animation Mode**: Updates at selected playback speed (1-60x)
- **Efficient Rendering**: Only update changed visualizations
- **Debouncing**: For rapid slider changes, debounce updates

---

## User Experience Flow

### Typical User Journey

1. **Launch Dashboard**
   - User runs `streamlit run scripts/dashboard.py`
   - Dashboard loads graph data (from file or CSV)
   - Initial state: Time = first departure, all visualizations show initial state

2. **Explore Initial State**
   - User sees network graph with airports (no flights yet)
   - Airport panels show zeros
   - Charts show initial points
   - Metrics cards show initial values

3. **Navigate Through Time**
   - User moves time slider forward
   - Visualizations update to show events as they occur
   - Network graph shows flights appearing
   - Airport panels update with cumulative metrics
   - Charts show lines progressing

4. **Watch Animation**
   - User clicks "Play"
   - Time advances automatically
   - All visualizations animate in sync
   - User watches network evolve in real-time

5. **Analyze Specific Period**
   - User sets time range filter
   - Focuses on specific time window
   - Examines delay patterns during that period
   - Compares airport performance

6. **Drill Down**
   - User clicks on airport node
   - Filters views to that airport
   - Examines route performance from that airport
   - Reviews event timeline for that airport

7. **Export Results**
   - User captures current state
   - Exports chart as image
   - Downloads data for further analysis
   - Saves dashboard configuration

---

## Implementation Phases

### Phase 1: Basic Dashboard (MVP)
- Time slider and basic navigation
- Network graph visualization (static layout)
- Airport status panels (basic metrics)
- Flight volume timeline chart
- Event timeline log

### Phase 2: Interactive Features
- Time slider with playback controls
- Interactive network graph (zoom, pan, hover)
- Active flights chart
- Delay trends chart
- Route analysis table

### Phase 3: Advanced Visualizations
- On-time performance charts
- Route delay heatmap
- Delay distribution histogram
- Airport comparison views
- Sankey diagram (route flow)

### Phase 4: Enhancements
- Geographic map view (optional)
- Advanced filtering and search
- Export functionality
- Performance optimizations
- Customizable layouts

---

## Future Enhancements

### Potential Additions
- **Geographic Map View**: Show flights on actual map with airport locations
- **Predictive Analytics**: Forecast delays based on current state
- **Alert System**: Visual alerts for delays exceeding thresholds
- **Comparative Analysis**: Compare multiple simulation runs side-by-side
- **Export & Reporting**: Generate PDF reports, CSV exports
- **Real-Time Updates**: Connect to live data stream (future)
- **Multi-Carrier View**: Filter by carrier when multiple carriers added
- **Weather Overlay**: Show weather conditions if data available
- **Equipment Analysis**: Visualize aircraft utilization and routing

### Integration Opportunities
- Connect to Neo4j (when migrated)
- API endpoints for programmatic access
- Scheduled reports (email/PDF)
- Webhooks for event notifications
- Database integration for historical data

---

## Success Metrics

### Dashboard Effectiveness
- **Usability**: Users can navigate and understand visualizations without training
- **Performance**: Dashboard loads in < 3 seconds, updates in < 500ms
- **Accuracy**: Visualizations match actual graph data
- **Completeness**: All key metrics visible and accessible

### User Feedback Targets
- Clear understanding of network state at any time
- Easy identification of delays and performance issues
- Intuitive navigation through simulation time
- Useful insights for decision-making

---

## References

- Graph Data Schema: `docs/data_schema.md`
- Graph Database Recommendations: `docs/graph_database_recommendations.md`
- Example Usage Script: `scripts/example_usage.py` (reference for query patterns)
- Sample Data: `data/raw/flights_sample.csv`, `data/raw/airports_sample.csv`
- Graph JSON Format: `data/processed/t1.json`

---

## Notes

### Updated Requirements (Confirmed)

**Geographic Mapping**:
- Network graph overlaid on US map with airports positioned at actual geographic coordinates
- Airport coordinates (latitude/longitude) must be added to `airports_sample.csv`
- Use Plotly Geo (`Scattergeo`) for map visualization

**Airport Status**:
- Changed from individual cards to single sortable/filterable table
- Use `streamlit-aggrid` component (no custom code required)
- Table shows all airports as rows with metrics as columns

**Flight Volume Timeline**:
- **Replaced** previous metrics with new ones:
  - Flights enroute (count at each point in time)
  - Cumulative inbound delay (total minutes, not average)
  - Cumulative outbound delay (total minutes, not average)
- Dual Y-axes: Left for count, right for delay minutes

**Event Timeline**:
- Must show **both** departures AND arrivals (not just arrivals)
- Use same `streamlit-aggrid` component as Airport Status table
- Sortable and filterable by all columns
- Filterable by event type (departure/arrival/both)

### Implementation Notes

- This feature document will be updated as the dashboard is implemented
- Visualization specifications may be refined based on initial testing
- Additional visualizations may be added based on user feedback
- Performance optimizations will be applied as data volume grows
- Airport coordinates must be accurate for proper geographic positioning
- Cumulative delays are monotonically increasing (never decrease)