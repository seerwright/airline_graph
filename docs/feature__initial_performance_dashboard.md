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

# Optional: For geographic maps (future enhancement)
# folium>=0.14.0
# streamlit-folium>=0.15.0
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

**Purpose**: Visualize the flight network topology and state

**Layout**: Interactive directed graph using Plotly

**Node Representation (Airports)**:
- **Size**: Proportional to activity (total departures + arrivals) at current time
- **Color**: Color-coded by delay status
  - Green: On-time (avg delay < 15 min)
  - Yellow: Moderate delays (15-30 min)
  - Red: Significant delays (> 30 min)
- **Label**: Airport code (ATL, LGA, SLC)
- **Position**: NetworkX layout (spring or force-directed)
- **Tooltip**: 
  - Airport name
  - Current state metrics (departures, arrivals, delays, on-time %)
  - Total events count

**Edge Representation (Flights)**:
- **Width**: Number of flights on route (at current time)
- **Color**: 
  - Blue: Active flights (in the air at current time)
  - Gray: Completed flights (arrived before current time)
  - Orange: Scheduled flights (not yet departed)
  - Red: Delayed flights (delay > 15 min)
- **Direction**: Directed arrows showing flight direction
- **Opacity**: Fade completed flights, highlight active flights
- **Tooltip**:
  - Route (origin → destination)
  - Number of flights on route
  - Average delay on route
  - Flight IDs (list of active flights)

**Interactive Features**:
- Zoom and pan
- Click to select airport/flight for details
- Hover for tooltips
- Toggle visibility (show/hide completed flights)
- Animation: Edges appear/disappear as flights depart/arrive

---

### 3. Airport Status Panel (Sidebar)

**Purpose**: Display current state metrics for each airport

**Layout**: Side-by-side cards for each airport (ATL, LGA, SLC)

**For Each Airport Card**:
- **Header**: Airport code and name
- **Current State Metrics** (at selected time):
  - Total Departures (cumulative count, large number)
  - Total Arrivals (cumulative count, large number)
  - Active Flights (flights in air, color-coded badge)
  - Average Departure Delay (minutes, color-coded: green/yellow/red)
  - Average Arrival Delay (minutes, color-coded: green/yellow/red)
  - On-Time Departure % (percentage with progress bar)
  - On-Time Arrival % (percentage with progress bar)
  
- **Mini Time-Series Charts** (below metrics):
  - **Departures Over Time**: Step chart showing cumulative departures
  - **Arrivals Over Time**: Step chart showing cumulative arrivals
  - **Delay Trends**: Line chart showing average delay evolution
  - All charts synchronized with main time slider

**Visual Design**:
- Color-coded metrics (green=good, yellow=moderate, red=poor)
- Progress bars for percentages
- Compact, scannable layout
- Expandable cards for detailed view

---

### 4. Flight Activity Charts (Main Content Area)

**Purpose**: Show flight volume and activity over time

#### A. Flight Volume Timeline

**Chart Type**: Line Chart (Plotly)

**X-Axis**: Time (GMT, from first departure to last arrival)

**Y-Axis**: Cumulative Flight Count

**Lines**:
- Blue line: Total Departures (cumulative)
- Orange line: Total Arrivals (cumulative)
- Green line: Total Flights (departures + arrivals)
- Vertical markers: Individual departure/arrival events

**Features**:
- Hover tooltip shows exact counts at any time
- Vertical line indicator for current time (synced with slider)
- Click to jump to specific time
- Zoom and pan

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

**Purpose**: Chronological log of all events

#### A. Event Log Stream

**Chart Type**: Scrollable Timeline/Log View (Streamlit)

**Layout**: Chronological list of events

**Columns**:
- Timestamp (HH:MM:SS GMT)
- Event Type (Departure/Arrival badge)
- Airport (ATL/LGA/SLC)
- Flight ID (e.g., WN1234_2026-01-01_ATL_LGA)
- Delay (minutes, color-coded)
- Status (On-Time/Delayed/Early)

**Features**:
- Auto-scroll to current time (optional)
- Filterable by:
  - Airport (multi-select)
  - Event type (departure/arrival)
  - Delay threshold (slider)
  - Time range
- Search by flight ID
- Highlight current event (bold/color)
- Click event to jump to that time

**Visual Design**:
- Color-coded rows (green=on-time, red=delayed)
- Icons for departure (✈️) and arrival (🛬)
- Compact, scannable format
- Expandable rows for detailed event information

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
- Show/hide completed flights
- Show/hide delayed flights only
- Network layout selector (spring, circular, force-directed)
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
   - Returns: All departure/arrival events in time range
   - Uses: Event-level snapshots (filtered by timestamp)

5. **`get_delay_metrics_over_time(G, start_time, end_time, interval_minutes)`**
   - Returns: Time series of delay metrics (average delays at intervals)
   - Uses: Event-level snapshots aggregated at intervals

6. **`get_route_metrics_at_time(G, target_time)`**
   - Returns: Route performance metrics (volume, delays) at target time
   - Uses: Edge attributes filtered by time

7. **`get_network_metrics_at_time(G, target_time)`**
   - Returns: Network-wide KPIs (totals, averages) at target time
   - Uses: Aggregated from all airports and routes

8. **`extract_time_series_data(G, start_time, end_time, metric_type, interval_minutes)`**
   - Returns: Time series DataFrame for plotting
   - Uses: Aggregated data at regular intervals
   - Supports: departures, arrivals, delays, on-time %, active flights, etc.

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

- This feature document will be updated as the dashboard is implemented
- Visualization specifications may be refined based on initial testing
- Additional visualizations may be added based on user feedback
- Performance optimizations will be applied as data volume grows
