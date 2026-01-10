# Flight Graph Data Schema

## Overview

This document defines the data schema for modeling airline flight data as a graph database. The model uses **airports as nodes** and **flights as edges**, with temporal attributes to enable time-series analysis.

## Graph Model: Airports → Flights → Airports

```
[Airport Node] --(Flight Edge)--> [Airport Node]
     (Origin)                        (Destination)
```

## Node Schema: Airport

### Node Identifier
- **Type**: `Airport`
- **Unique ID**: Airport code (3-4 character ICAO/IATA code from `Dep_LOCID` / `Arr_LOCID`)

### Node Attributes

#### Core Identification
| Attribute | Source Field | Type | Description |
|-----------|--------------|------|-------------|
| `airport_code` | `Dep_LOCID` / `Arr_LOCID` | String | 3-char (domestic) or 4-char (ICAO) airport identifier |
| `airport_type` | Derived | String | "origin" or "destination" (context-dependent) |

#### Operational Metrics (Aggregated)
*Note: These are aggregated values computed from all flights associated with this airport*

| Attribute | Source Field | Type | Description |
|-----------|--------------|------|-------------|
| `total_departures` | `SchDep` / `FacDep` | Integer | Total number of departures |
| `total_arrivals` | `SchArr` / `FacArr` | Integer | Total number of arrivals |
| `avg_departure_delay` | `DlaSchOff`, `DlaFPOff` | Float | Average departure delay (minutes) |
| `avg_arrival_delay` | `DlaSchArr`, `DlaFPArr` | Float | Average arrival delay (minutes) |
| `on_time_departure_pct` | `OTSchDepP`, `OTFPOffP` | Float | Percentage of on-time departures |
| `on_time_arrival_pct` | `OTSchArrP`, `OTFPArrP` | Float | Percentage of on-time arrivals |
| `departure_score` | `DepScore` | Float | Airport departure efficiency score |
| `arrival_score` | `ARRSCORE` | Float | Airport arrival efficiency score |
| `efficiency_score` | `ArptScore` | Float | Overall airport efficiency score |

#### Infrastructure Attributes
| Attribute | Source Field | Type | Description |
|-----------|--------------|------|-------------|
| `arrival_rate` | `AAR` | Float | Airport-supplied arrival rate (aircraft/hour) |
| `departure_rate` | `ADR` | Float | Airport-supplied departure rate (aircraft/hour) |
| `effective_arrival_rate` | `Eff_AAR` | Float | Effective arrival rate (considering GDP) |

#### Equipment Type Counts (Aggregated)
| Attribute | Source Field | Type | Description |
|-----------|--------------|------|-------------|
| `jet_arrivals` | `JetArr` | Integer | Count of jet arrivals |
| `jet_departures` | `JetDep` | Integer | Count of jet departures |
| `piston_arrivals` | `PistArr` | Integer | Count of piston arrivals |
| `piston_departures` | `PistDep` | Integer | Count of piston departures |
| `turbo_arrivals` | `TurboArr` | Integer | Count of turbo propeller arrivals |
| `turbo_departures` | `TurboDep` | Integer | Count of turbo propeller departures |

#### Temporal Attributes (Time-Windowed Aggregates)
*Note: Using Approach 1 - Time-Windowed Attributes. All dates include full datetime values (not just time).*

| Attribute | Type | Description |
|-----------|------|-------------|
| `last_updated` | DateTime (GMT) | Full timestamp (date + time) of last data update |
| `time_windowed_metrics` | Dict | Dictionary keyed by period (YYYYMM) containing metrics with full date ranges |
| `time_snapshots` | List | Alternative: List of time-stamped metric snapshots (each with period_start_date and period_end_date) |

*For detailed temporal attribute structure, see the "Temporal Node Modeling" section below.*

### Node Example (NetworkX)
*Note: This shows a simplified example. For full temporal structure with dates, see "Temporal Node Modeling" section below.*

```python
from datetime import datetime, timezone

# Simplified node example (current/latest metrics)
airport_node = {
    'airport_code': 'JFK',
    'total_departures': 1250,
    'total_arrivals': 1280,
    'avg_departure_delay': 12.5,
    'avg_arrival_delay': 8.3,
    'efficiency_score': 85.2,
    'last_updated': datetime(2024, 2, 1, 10, 30, 0, tzinfo=timezone.utc)
}

# Full temporal structure with time-windowed metrics (see below)
```

---

## Edge Schema: Flight

### Edge Relationship
- **Type**: `FLIES_TO` or `OPERATED_FLIGHT`
- **Direction**: Directed edge from origin airport to destination airport
- **Multi-edge support**: Multiple edges allowed between same airports (different flights)

### Edge Attributes

#### Core Flight Identification
| Attribute | Source Field | Type | Description |
|-----------|--------------|------|-------------|
| `flight_id` | Composite Key | String | Unique identifier: `{FAACarrier}{FLTNO}_{date}_{origin}_{destination}` |
| `flight_number` | `FLTNO` | String/Integer | Flight number (1-9999) |
| `carrier` | `FAACarrier` | String | Airline/carrier code (2-3 characters) |
| `flight_type` | `FLTTYPE` | String | "D" (Domestic dep, foreign arr), "N" (Domestic dep and arr), "A" (Foreign dep, domestic arr) |
| `tail_number` | `TAILNO` | String | Aircraft tail number (if available) |
| `equipment` | `Equip` | String | Aircraft type (e.g., "B737", "MD80") |
| `equipment_class` | `Equip_Class` | String | "P" (piston), "J" (jet), "T" (turbo), "-" (unknown) |

#### Temporal Attributes (GMT Datetime)
*All times converted from GMT seconds since 1/1/80 to Python datetime objects*

| Attribute | Source Field | Type | Description | Conversion |
|-----------|--------------|------|-------------|------------|
| `scheduled_departure_gate` | `OAG_S_DEP` (SchOutSec) | DateTime (GMT) | Scheduled gate departure time | Epoch: 1980-01-01 00:00:00 GMT |
| `scheduled_arrival_gate` | `OAG_S_ARR` (SchInSec) | DateTime (GMT) | Scheduled gate arrival time | Epoch: 1980-01-01 00:00:00 GMT |
| `actual_departure_gate` | `OOOI_DEP` (ActOutSec) | DateTime (GMT) | Actual gate departure time | Epoch: 1980-01-01 00:00:00 GMT |
| `actual_arrival_gate` | `OOOI_ARR` (ActInSec) | DateTime (GMT) | Actual gate arrival time | Epoch: 1980-01-01 00:00:00 GMT |
| `scheduled_wheels_off` | `OAG_OFF` (SchOffSec) | DateTime (GMT) | Scheduled wheels off time | Epoch: 1980-01-01 00:00:00 GMT |
| `actual_wheels_off` | `WHEELS_OFF` (ActOffSec) | DateTime (GMT) | Actual wheels off time | Epoch: 1980-01-01 00:00:00 GMT |
| `actual_wheels_on` | `WHEELS_ON` (ActOnSec) | DateTime (GMT) | Actual wheels on time | Epoch: 1980-01-01 00:00:00 GMT |
| `flight_plan_departure` | `FILED_PTIM` (FPDepSec) | DateTime (GMT) | Flight plan gate departure time | Epoch: 1980-01-01 00:00:00 GMT |
| `flight_plan_wheels_off` | `PTIM_OFF` (FPOffSec) | DateTime (GMT) | Flight plan wheels off time | Epoch: 1980-01-01 00:00:00 GMT |
| `flight_plan_arrival` | `ADJ_OAG_ARR` (FPInSec) | DateTime (GMT) | Flight plan gate arrival time | Epoch: 1980-01-01 00:00:00 GMT |
| `scheduled_block_time` | `OAG_S_G2G` (SchBlock) | Integer | Scheduled block time (gate-to-gate minutes) | Already in minutes |
| `actual_block_time` | `OOOI_G2G` (ActBlock) | Integer | Actual block time (gate-to-gate minutes) | Already in minutes |

#### Derived Temporal Attributes
| Attribute | Type | Description | Calculation |
|-----------|------|-------------|-------------|
| `departure_delay_minutes` | Integer | Departure delay vs scheduled | `(actual_departure_gate - scheduled_departure_gate).total_seconds() / 60` |
| `arrival_delay_minutes` | Integer | Arrival delay vs scheduled | `(actual_arrival_gate - scheduled_arrival_gate).total_seconds() / 60` |
| `flight_date` | Date | Date of flight (GMT) | Extracted from `scheduled_departure_gate` |
| `flight_month_year` | String | YYYYMM format | Derived from `flight_date` |
| `flight_hour` | Integer | Hour of scheduled departure (GMT) | 0-23 |

#### Operational Metrics
| Attribute | Source Field | Type | Description |
|-----------|--------------|------|-------------|
| `airborne_minutes` | `AIRBORNE` (ActAir) | Integer | Actual airborne time (minutes) |
| `estimated_enroute` | `FILED_ETE` (FPETE) | Integer | Estimated minutes enroute from flight plan |
| `taxi_out_minutes` | `TAXI_OUT` (ActTO) | Integer | Actual taxi-out time (minutes) |
| `taxi_in_minutes` | `TAXI_IN` (ActTI) | Integer | Actual taxi-in time (minutes) |
| `unimpeded_taxi_out` | `NOM_TO` | Integer | Unimpeded taxi-out time (minutes) |
| `unimpeded_taxi_in` | `NOM_TI` | Integer | Unimpeded taxi-in time (minutes) |

#### Delay Metrics
| Attribute | Source Field | Type | Description |
|-----------|--------------|------|-------------|
| `gate_delay_minutes` | `GATE_DELAY` (DlaFPOut) | Integer | Gate delay (flight plan based, minutes) |
| `airborne_delay_minutes` | `DELAY_AIR` (DlaAir) | Integer | Airborne delay (ActAir - FPETE, minutes) |
| `taxi_out_delay_minutes` | `DELAY_TO` (DlaTO) | Integer | Taxi-out delay (minutes) |
| `taxi_in_delay_minutes` | `DELAY_TI` (DlaTI) | Integer | Taxi-in delay (minutes) |
| `block_delay_minutes` | `DIF_G2G` (DlaBlock) | Integer | Block delay (gate-to-gate, minutes) |

#### Status and Metadata
| Attribute | Source Field | Type | Description |
|-----------|--------------|------|-------------|
| `cancelled` | `CancCode` | Boolean | True if flight was cancelled |
| `cancellation_code` | `CancCode` | String | "A" (Carrier), "B" (Weather), "C" (NAS), "D" (Security), "" (Not cancelled) |
| `cancellation_add_flag` | `Add_Flag` | Integer | 1 = Add to cancelled count, 0 = Don't add |
| `data_source` | `Rec_Type` | String | "A" (ASQP) or "R" (ETMS) |
| `oag_present` | `OAG` | Boolean | True if OAG schedule data present |
| `oooi_present` | `OOOI` | Boolean | True if OOOI actual data present |
| `etms_present` | `ETMS` | Boolean | True if ETMS data present |

#### Weather Conditions (At Origin Airport)
| Attribute | Source Field | Type | Description |
|-----------|--------------|------|-------------|
| `temperature_f` | `Temp` | Float | Temperature in Fahrenheit |
| `visibility_nm` | `Visibility` | Float | Visibility in nautical miles ("M" = missing) |
| `wind_speed_kts` | `WindSpeed` | Float | Wind speed in knots ("M" = missing) |
| `wind_angle_deg` | `WindAngle` | Float | Wind angle from magnetic north (degrees, "M" = missing) |
| `ceiling_hundreds_ft` | `Ceiling` | Integer | Ceiling in hundreds of feet |
| `meteorological_conditions` | `MC` | String | "I" (Instrument) or "V" (Visual) |

#### Passenger and Crew Information
**Note**: The definitions.md file does not contain explicit fields for passenger count, pilot count, or flight attendant count. These would need to be:
- Added from a separate data source, or
- Estimated based on aircraft type and capacity, or
- Omitted if not available in your dataset

If available from another source, include:
| Attribute | Source Field | Type | Description |
|-----------|--------------|------|-------------|
| `passengers_onboard` | External source | Integer | Number of passengers onboard |
| `pilots_onboard` | External source | Integer | Number of pilots onboard (typically 2) |
| `flight_attendants_onboard` | External source | Integer | Number of flight attendants onboard |

### Edge Example (NetworkX)
```python
flight_edge = {
    'flight_id': 'AA123_2024-01-15_JFK_LAX',
    'flight_number': '123',
    'carrier': 'AA',
    'scheduled_departure_gate': datetime(2024, 1, 15, 8, 30, tzinfo=timezone.utc),
    'actual_departure_gate': datetime(2024, 1, 15, 8, 45, tzinfo=timezone.utc),
    'scheduled_arrival_gate': datetime(2024, 1, 15, 11, 30, tzinfo=timezone.utc),
    'actual_arrival_gate': datetime(2024, 1, 15, 11, 40, tzinfo=timezone.utc),
    'departure_delay_minutes': 15,
    'arrival_delay_minutes': 10,
    'airborne_minutes': 305,
    'equipment': 'B737',
    'equipment_class': 'J',
    'cancelled': False,
    'flight_date': date(2024, 1, 15),
    'flight_month_year': '202401'
}
```

---

## Temporal Graph Modeling

**Decision: We will use Approach 1 (Time-Stamped Attributes) for both edges and nodes.**

Since you want to show how the graph changes over time, the following approaches are documented for reference. However, **Approach 1 is selected for both edges and nodes** to maintain consistency and enable efficient temporal queries.

### Approach 1: Time-Stamped Edges (Selected for Implementation)
**Strategy**: Each edge includes temporal attributes, and queries filter by time windows. **This is the approach we will use for edges.**

**Pros**:
- Single graph structure
- Flexible time queries
- Efficient for temporal analysis

**Implementation**:
```python
# Edges include time attributes
G.add_edge('JFK', 'LAX', 
           flight_id='AA123_2024-01-15',
           scheduled_departure_gate=datetime(2024, 1, 15, 8, 30),
           ...)
```

**Querying**:
```python
# Get all flights in a time window
edges_in_window = [
    (u, v, data) for u, v, data in G.edges(data=True)
    if window_start <= data['scheduled_departure_gate'] <= window_end
]
```

### Approach 2: Graph Snapshots
**Strategy**: Create separate graph instances for different time periods (hourly, daily, monthly).

**Pros**:
- Fast queries for specific time periods
- Easy to visualize changes over time
- Good for comparing different periods

**Cons**:
- Higher memory usage
- More complex to maintain consistency

**Implementation**:
```python
# Create daily snapshots
daily_graphs = {}
for date in date_range:
    daily_graphs[date] = nx.DiGraph()
    # Add edges for this date only
    for flight in flights_on_date(date):
        daily_graphs[date].add_edge(...)
```

### Approach 3: Time-Indexed Subgraph Extraction
**Strategy**: Maintain one master graph with all flights, but extract time-filtered subgraphs on demand.

**Pros**:
- Single source of truth
- On-demand temporal views
- Efficient storage

**Implementation**:
```python
def get_graph_for_period(G, start_date, end_date):
    """Extract subgraph for a specific time period"""
    subgraph = G.edge_subgraph([
        (u, v) for u, v, data in G.edges(data=True)
        if start_date <= data['flight_date'] <= end_date
    ])
    return subgraph
```

### Recommended: Approach 1 (Time-Stamped Attributes)
**We will use Approach 1 for both edges and nodes.** This approach uses time-stamped attributes on a single graph structure, with both edges and nodes containing temporal information as attributes. Helper functions can extract time-indexed subgraphs on demand when needed for analysis.

---

## Temporal Node Modeling

**Yes, nodes (airports) should also be timestamped!** Airport attributes change over time (efficiency scores, operational metrics, demand, infrastructure capacity). Unlike edges (flights) which are inherently time-bound events, nodes (airports) are persistent entities with time-varying properties.

### Approach 1: Event-Level Node Snapshots (Selected for Implementation)
**Strategy**: Create a new node snapshot on every flight departure or arrival event. This provides fine-grained temporal tracking at the event level, not at the day or period level.

**Pros**:
- Single node per airport (avoids node proliferation)
- Event-level granularity (not day or period level)
- Tracks both incremental changes (delta) and cumulative values (totals)
- Chronologically ordered snapshots enable precise time-series analysis
- Maintains airport identity across time
- Snapshots only created when attributes actually change (event-driven)

**Implementation**:
```python
# Node with event-level snapshots (list-based, chronologically ordered)
airport_node = {
    'airport_code': 'ATL',
    'time_snapshots': [
        {
            'timestamp': '2026-01-01T08:00:00Z',  # Event time (ISO 8601 GMT)
            'event_type': 'departure',  # or 'arrival'
            'event_flight_id': 'WN1234_2026-01-01_ATL_LGA',
            'incremental': {
                'departures': 1,  # +1 departure at this time
                'departure_delay_minutes': 0  # delay for this event
                # Note: Only includes values that changed (departures=1), 
                #       not unchanged values (arrivals=0 omitted)
            },
            'cumulative': {
                'total_departures': 1,  # total up to this point in time
                'total_arrivals': 0,    # total up to this point in time
                'avg_departure_delay': 0.0,  # average up to this point
                'avg_arrival_delay': 0.0,
                'on_time_departure_pct': 100.0,
                'on_time_arrival_pct': 0.0
            }
        },
        {
            'timestamp': '2026-01-01T08:00:00Z',  # Another departure at same time
            'event_type': 'departure',
            'event_flight_id': 'WN567_2026-01-01_ATL_LGA',
            'incremental': {
                'departures': 1,
                'departure_delay_minutes': 0
            },
            'cumulative': {
                'total_departures': 2,  # Now 2 total departures
                'total_arrivals': 0,
                'avg_departure_delay': 0.0,
                'avg_arrival_delay': 0.0,
                'on_time_departure_pct': 100.0,
                'on_time_arrival_pct': 0.0
            }
        },
        {
            'timestamp': '2026-01-01T10:43:00Z',  # Arrival event
            'event_type': 'arrival',
            'event_flight_id': 'WN890_2026-01-01_LGA_ATL',
            'incremental': {
                'arrivals': 1,  # +1 arrival at this time
                'arrival_delay_minutes': 3  # delay for this arrival
            },
            'cumulative': {
                'total_departures': 2,  # Still 2 departures (no change)
                'total_arrivals': 1,    # Now 1 arrival
                'avg_departure_delay': 0.0,
                'avg_arrival_delay': 3.0,  # Updated with new arrival
                'on_time_departure_pct': 100.0,
                'on_time_arrival_pct': 100.0  # On-time (< 15 min)
            }
        }
    ],
    'last_updated': '2026-01-01T10:43:00Z'  # ISO 8601 string
}
```

**Key Points**:
- **Event-driven**: Snapshots created only when a departure or arrival occurs
- **Chronologically ordered**: Snapshots list is ordered by timestamp
- **Incremental changes**: Only tracks what changed at this event (e.g., `departures: 1`)
- **Cumulative values**: Tracks running totals and averages up to this point in time
- **JSON compatible**: All datetime fields stored as ISO 8601 strings (e.g., `"2026-01-01T08:00:00Z"`)

**Note**: All datetime fields are stored as ISO 8601 strings in JSON for compatibility, but converted to Python `datetime` objects when working with NetworkX.

### Approach 2: Time-Stamped Node Instances
**Strategy**: Create separate node instances for different time periods (e.g., `JFK_202401`, `JFK_202402`).

**Pros**:
- Clear temporal separation
- Easy to query specific time periods
- Natural alignment with graph snapshots

**Cons**:
- Node proliferation (many nodes per airport)
- Need to maintain identity relationships
- More complex queries for cross-period analysis

**Implementation**:
```python
# Different nodes for different periods
G.add_node('JFK_202401', airport_code='JFK', period='202401', ...)
G.add_node('JFK_202402', airport_code='JFK', period='202402', ...)

# Edges connect time-specific nodes
G.add_edge('JFK_202401', 'LAX_202401', ...)
```

### Approach 3: Current Values with Historical Tracking
**Strategy**: Node stores current/aggregate values, with separate historical tracking structure.

**Pros**:
- Fast queries for current state
- Historical data available when needed
- Clean separation of current vs. historical

**Implementation**:
```python
airport_node = {
    'airport_code': 'JFK',
    # Current/aggregate values (fast access)
    'current_total_departures': 1250,
    'current_avg_departure_delay': 12.5,
    'current_efficiency_score': 85.2,
    'period': '202402',  # Current period
    # Historical tracking (accessed when needed)
    'historical_metrics': {
        '202401': {...},
        '202402': {...}
    }
}
```

### Recommended: Approach 1 (Event-Level Snapshots) - Confirmed
**We will use Approach 1 for nodes with event-level snapshots**, which aligns with using Approach 1 for edges. This approach:
- Maintains single nodes per airport (avoids node proliferation)
- **Event-level granularity**: Snapshots created on every departure/arrival (not day or period level)
- Tracks both incremental changes (delta) and cumulative values (totals)
- Chronologically ordered snapshots enable precise time-series analysis
- Snapshots only created when attributes actually change (event-driven)
- Compatible with JSON serialization (dates stored as ISO 8601 strings)
- Consistent with the edge temporal approach (both use Approach 1 with time-stamped attributes)

### Node Temporal Attributes (Event-Level)
Each snapshot in `time_snapshots` includes:

| Attribute | Type | Description | JSON Format |
|-----------|------|-------------|-------------|
| `timestamp` | DateTime (GMT) | Exact event time (departure or arrival) | ISO 8601 string (e.g., "2026-01-01T08:00:00Z") |
| `event_type` | String | "departure" or "arrival" | String |
| `event_flight_id` | String | Flight ID that triggered this event | String |
| `incremental` | Dict | Changes at this event (only changed values) | Dict |
| `cumulative` | Dict | Running totals and averages up to this point | Dict |

**Incremental Changes** (`incremental` dict):
- Only includes values that changed (e.g., `departures: 1`)
- Unchanged values are omitted (e.g., if `arrivals: 0`, it's not included)
- Fields: `departures` (int), `arrivals` (int), `departure_delay_minutes` (int or None), `arrival_delay_minutes` (int or None)

**Cumulative Values** (`cumulative` dict):
- Running totals and averages up to this point in time
- Fields: `total_departures` (int), `total_arrivals` (int), `avg_departure_delay` (float), `avg_arrival_delay` (float), `on_time_departure_pct` (float), `on_time_arrival_pct` (float)

**Node-Level Attributes**:
| Attribute | Type | Description | JSON Format |
|-----------|------|-------------|-------------|
| `time_snapshots` | List | Chronologically ordered list of event snapshots | List of dicts |
| `last_updated` | DateTime (GMT) | Timestamp of most recent event | ISO 8601 string |

**Important**: All dates are stored as **full datetime values** (not just time), ensuring proper temporal ordering and precise event-based queries.

### Querying Event-Level Snapshots

```python
from datetime import datetime, timezone

def get_airport_snapshots_for_time_range(G, airport_code, start_time, end_time):
    """Get airport snapshots within a specific time range"""
    node = G.nodes[airport_code]
    results = []
    
    if 'time_snapshots' in node:
        # Parse ISO 8601 strings to datetime if needed
        if isinstance(start_time, str):
            start_time = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
        if isinstance(end_time, str):
            end_time = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
        
        for snapshot in node['time_snapshots']:
            snapshot_time_str = snapshot.get('timestamp', '')
            if snapshot_time_str:
                snapshot_time = datetime.fromisoformat(snapshot_time_str.replace('Z', '+00:00'))
                if start_time <= snapshot_time <= end_time:
                    results.append(snapshot)
    
    return results

def get_airport_state_at_time(G, airport_code, target_time):
    """Get airport cumulative state at a specific point in time (last snapshot before or at target_time)"""
    node = G.nodes[airport_code]
    
    if 'time_snapshots' not in node or not node['time_snapshots']:
        return None
    
    # Parse ISO 8601 string to datetime if needed
    if isinstance(target_time, str):
        target_time = datetime.fromisoformat(target_time.replace('Z', '+00:00'))
    
    # Find the last snapshot before or at target_time
    last_snapshot = None
    for snapshot in node['time_snapshots']:
        snapshot_time_str = snapshot.get('timestamp', '')
        if snapshot_time_str:
            snapshot_time = datetime.fromisoformat(snapshot_time_str.replace('Z', '+00:00'))
            if snapshot_time <= target_time:
                last_snapshot = snapshot
            else:
                break  # Snapshots are ordered, so we can break early
    
    return last_snapshot['cumulative'] if last_snapshot else None

def get_airport_events_by_type(G, airport_code, event_type='departure'):
    """Get all events of a specific type (departure or arrival) for an airport"""
    node = G.nodes[airport_code]
    results = []
    
    if 'time_snapshots' in node:
        for snapshot in node['time_snapshots']:
            if snapshot.get('event_type') == event_type:
                results.append(snapshot)
    
    return results

def get_airport_latest_state(G, airport_code):
    """Get the latest cumulative state for an airport"""
    node = G.nodes[airport_code]
    
    if 'time_snapshots' not in node or not node['time_snapshots']:
        return None
    
    # Last snapshot contains the latest cumulative state
    last_snapshot = node['time_snapshots'][-1]
    return last_snapshot.get('cumulative')
```

---

## GMT Time Conversion

All time fields in the source data use **GMT seconds since 1980-01-01 00:00:00**. Convert to Python datetime:

```python
from datetime import datetime, timezone, timedelta

EPOCH_1980 = datetime(1980, 1, 1, 0, 0, 0, tzinfo=timezone.utc)

def gmt_seconds_to_datetime(seconds_since_1980):
    """Convert GMT seconds since 1980-01-01 to datetime"""
    if seconds_since_1980 is None or seconds_since_1980 == '':
        return None
    return EPOCH_1980 + timedelta(seconds=int(seconds_since_1980))
```

---

## Graph Data Model Summary

### Node Structure (Airport)
```
Airport Node
├── airport_code (key)
├── Core Attributes (static)
│   ├── airport_name
│   ├── city
│   ├── state
│   └── country
└── Temporal Attributes (Approach 1: Event-Level Snapshots)
    ├── time_snapshots (list, chronologically ordered)
    │   └── Each event snapshot includes:
    │       ├── timestamp (full GMT datetime - event time)
    │       ├── event_type ("departure" or "arrival")
    │       ├── event_flight_id (flight that triggered event)
    │       ├── incremental (changes at this event)
    │       │   ├── departures (int, if changed)
    │       │   ├── arrivals (int, if changed)
    │       │   ├── departure_delay_minutes (int or None, if changed)
    │       │   └── arrival_delay_minutes (int or None, if changed)
    │       └── cumulative (running totals up to this point)
    │           ├── total_departures (int)
    │           ├── total_arrivals (int)
    │           ├── avg_departure_delay (float)
    │           ├── avg_arrival_delay (float)
    │           ├── on_time_departure_pct (float)
    │           └── on_time_arrival_pct (float)
    └── last_updated (GMT datetime - ISO 8601 string)
```

### Edge Structure (Flight)
```
Flight Edge: origin_airport → destination_airport
├── flight_id (unique identifier)
├── Flight Identification
├── Temporal Attributes (all GMT datetime)
│   ├── scheduled_departure_gate
│   ├── actual_departure_gate
│   ├── scheduled_arrival_gate
│   ├── actual_arrival_gate
│   ├── flight_date
│   └── flight_month_year (YYYYMM)
├── Operational Metrics
├── Delay Metrics
├── Status and Metadata
├── Weather Conditions
└── Passenger/Crew (if available)
```

### Temporal Dimension (Approach 1 for Both Edges and Nodes - Event-Level)
- **Edges (Flights)**: Approach 1 - Time-stamped attributes on single graph structure
  - Each flight edge includes full datetime attributes (scheduled/actual departure/arrival times)
  - All dates stored as full datetime values (GMT timezone, ISO 8601 strings in JSON)
  - Queryable by time windows using edge attributes
  - Edge timestamps remain unchanged (already event-level)
  
- **Nodes (Airports)**: Approach 1 - Event-level snapshots on single node per airport
  - **Event-level granularity**: Snapshots created on every departure/arrival event (not day or period level)
  - Each snapshot includes timestamp, event type, flight ID, incremental changes, and cumulative values
  - Snapshots are chronologically ordered and only created when attributes actually change
  - Tracks both incremental changes (delta) and cumulative values (running totals)
  - All timestamps stored as full datetime values (GMT timezone, ISO 8601 strings in JSON)
  - Queryable by exact time, time range, event type, or flight ID
  
- **Consistent Approach**: Both edges and nodes use event-level temporal tracking, enabling:
  - Single graph structure with fine-grained temporal filtering
  - Event-based queries on both nodes and edges
  - Precise time-series analysis at the event level (not day or period level)
  - Time-series analysis and visualization of network structure and airport performance over time
  - JSON serialization compatible (dates stored as ISO 8601 strings)
  - Synchronized simulation: All flights can depart at the same time (e.g., 2026-01-01T08:00:00Z) for easier development and analysis

---

## Implementation Considerations

### NetworkX Implementation
```python
import networkx as nx
from datetime import datetime, timezone

G = nx.DiGraph()  # Directed graph

# Add airport node
G.add_node('JFK', 
           airport_code='JFK',
           total_departures=0,
           total_arrivals=0)

# Add flight edge
G.add_edge('JFK', 'LAX',
           flight_id='AA123_2024-01-15_JFK_LAX',
           scheduled_departure_gate=datetime(2024, 1, 15, 8, 30, tzinfo=timezone.utc),
           actual_departure_gate=datetime(2024, 1, 15, 8, 45, tzinfo=timezone.utc),
           ...)
```

### Neo4j Implementation (Future)
```cypher
// Create airport node
CREATE (a:Airport {code: 'JFK', name: 'John F. Kennedy International Airport'})

// Create flight relationship
MATCH (origin:Airport {code: 'JFK'})
MATCH (dest:Airport {code: 'LAX'})
CREATE (origin)-[f:FLIES_TO {
    flight_id: 'AA123_2024-01-15_JFK_LAX',
    scheduled_departure_gate: datetime('2024-01-15T08:30:00Z'),
    actual_departure_gate: datetime('2024-01-15T08:45:00Z'),
    ...
}]->(dest)
```

### Data Validation Rules
1. All datetime fields must be in GMT/UTC timezone
2. Airport codes must match format (3-char domestic, 4-char ICAO)
3. Flight IDs must be unique
4. Departure time must be before arrival time
5. Delay calculations should be consistent across metrics

---

## Next Steps

1. **Data Loading**: Create ETL pipeline to convert raw data to graph format
2. **Time Conversion**: Implement GMT seconds to datetime conversion utility
3. **Graph Construction**: Build functions to create nodes and edges
4. **Temporal Queries**: Implement time-window filtering functions
5. **Visualization**: Create time-animated graph visualizations
6. **Analytics**: Build queries for common analyses (delays, routes, connectivity)

---

## References

- Source data definitions: `docs/definitions.md`
- Graph database recommendations: `docs/graph_database_recommendations.md`
