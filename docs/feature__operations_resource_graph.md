# Feature: Operations Resource Graph

## Intent & Purpose

The Operations Resource Graph provides a complementary view to the existing airline network graph by modeling **resource connections between flights**. While the existing graph models airports as nodes and flights as edges (showing the physical network topology), this new graph models **flights as nodes** and **resources (aircraft and crew) as edges** (showing operational dependencies and resource utilization).

### Goals
- **Resource Tracking**: Track how aircraft and crew connect flights together (turns, crew connections)
- **Operational Dependencies**: Understand which flights depend on the same resources
- **Temporal Resource Flow**: Analyze how resources flow through the network over time
- **Cascade Analysis**: Identify potential cascading delays when resources are shared between flights
- **Resource Utilization**: Analyze aircraft and crew utilization patterns
- **Operational Planning**: Support resource allocation and scheduling decisions

### Relationship to Existing Graph

The two graphs are complementary and can be used together:

| Aspect | Existing Graph (Airport Network) | New Graph (Operations Resource) |
|--------|----------------------------------|----------------------------------|
| **Nodes** | Airports | Flights |
| **Edges** | Flights (physical routes) | Resources (operational connections) |
| **Focus** | Network topology, airport performance | Resource dependencies, operational flow |
| **Temporal** | Event-level snapshots (airports), time-stamped edges (flights) | Time-stamped edges (resource connections) |
| **Use Case** | "Which airports are connected?" | "Which flights share the same aircraft/crew?" |

**Example**: 
- Airport Graph: `ATL --[Flight WN1234]--> LGA` (shows route)
- Operations Graph: `Flight WN1234 --[Aircraft N509DT]--> Flight WN5678` (shows same aircraft used for both flights)

### Use Cases
- **Delay Propagation**: When Flight A is delayed, which subsequent flights are affected because they use the same aircraft or crew?
- **Resource Optimization**: Which aircraft or crew are underutilized or overutilized?
- **Operational Planning**: What is the optimal sequence of flights for a given aircraft or crew?
- **Cascade Analysis**: Trace how delays propagate through resource connections
- **Resource Availability**: At any point in time, which resources are available, in-use, or scheduled?

---

## Graph Model: Flights → Resources → Flights

```
[Flight Node] --(Resource Edge)--> [Flight Node]
   (Source)      (Aircraft/Crew)      (Target)
```

### Two Modeling Approaches

The feature supports two graph models:

#### Model 1: "flights-only" (Default)
- **Nodes**: Only Flight nodes
- **Edges**: Typed resource connections between flights (AIRCRAFT_TURN, CREW_PILOT, CREW_FA)
- **Use Case**: Focus on flight-to-flight resource dependencies without explicit resource entities

#### Model 2: "with-resources" (Optional)
- **Nodes**: Flight nodes + Aircraft nodes + Crew nodes
- **Edges**: 
  - Flight → Flight: Resource connections (same as Model 1)
  - Aircraft → Flight: OPERATED edges (which aircraft operated which flight)
  - Crew → Flight: WORKED edges (which crew worked which flight)
- **Use Case**: Explicit resource entities enable queries like "all flights operated by aircraft N509DT" or "all flights worked by pilot crew 12345"

---

## Node Schema

### Flight Node

**Node Identifier**:
- **Type**: `"Flight"`
- **Unique ID**: `("Flight", flight_id)` where `flight_id` format matches airport graph: `"{carrier}{flight_number}_{date}_{origin}_{destination}"`
  - Example: `"WN1234_2026-01-01_ATL_LGA"` → `("Flight", "WN1234_2026-01-01_ATL_LGA")`
  - **Note**: Uses same flight_id format as airport graph for consistency and cross-graph queries

**Node Attributes**:

| Attribute | Type | Description | Example |
|-----------|------|-------------|---------|
| `label` | String | Always `"Flight"` | `"Flight"` |
| `flight_id` | String | Full flight ID (matches airport graph) | `"WN1234_2026-01-01_ATL_LGA"` |
| `flight_number` | String | Flight number | `"1234"` |
| `carrier` | String | Carrier code | `"WN"` |
| `origin` | String | Origin airport code (3-char) | `"ATL"` |
| `destination` | String | Destination airport code (3-char) | `"LGA"` |
| `flight_date` | String (ISO 8601) | Flight date | `"2026-01-01"` |
| `sch_dep_gmt` | String (ISO 8601) | Scheduled departure time (GMT) | `"2026-01-01T08:00:00Z"` |
| `sch_arr_gmt` | String (ISO 8601) | Scheduled arrival time (GMT) | `"2026-01-01T10:30:00Z"` |
| `act_arr_gmt` | String (ISO 8601) | Actual arrival time (GMT) | `"2026-01-01T10:27:00Z"` |

**Temporal Attributes**:
- All datetime fields stored as ISO 8601 strings (GMT timezone)
- Flight nodes are inherently temporal (each flight has scheduled/actual times)
- Temporal queries filter flights by their scheduled/actual times

**Note**: Flight nodes in this graph may contain a subset of attributes compared to flight edges in the Airport Network graph. The focus here is on resource connections, not full flight details.

### Aircraft Node (Model 2: "with-resources" only)

**Node Identifier**:
- **Type**: `"Aircraft"`
- **Unique ID**: `("Aircraft", tail_number)`
  - Example: `("Aircraft", "N509DT")`

**Node Attributes**:

| Attribute | Type | Description | Example |
|-----------|------|-------------|---------|
| `label` | String | Always `"Aircraft"` | `"Aircraft"` |
| `tail_number` | String | Aircraft tail number | `"N509DT"` |

**Temporal Attributes**:
- Aircraft nodes are persistent entities (not inherently temporal)
- Temporal queries on aircraft focus on when they operate flights (via OPERATED edges)

### Crew Node (Model 2: "with-resources" only)

**Node Identifier**:
- **Type**: `"Crew:{role}"` where role is `"Pilot"` or `"FA"`
- **Unique ID**: `("Crew:Pilot", crew_id)` or `("Crew:FA", crew_id)`
  - Example: `("Crew:Pilot", "12345")` or `("Crew:FA", "67890")`

**Node Attributes**:

| Attribute | Type | Description | Example |
|-----------|------|-------------|---------|
| `label` | String | Always `"Crew"` | `"Crew"` |
| `crew_id` | String | Crew identifier | `"12345"` |
| `role` | String | Crew role | `"Pilot"` or `"FA"` |

**Temporal Attributes**:
- Crew nodes are persistent entities (not inherently temporal)
- Temporal queries on crew focus on when they work flights (via WORKED edges)

---

## Edge Schema

### Resource Connection Edges (Flight → Flight)

**Edge Relationship**:
- **Type**: One of `AIRCRAFT_TURN`, `CREW_PILOT`, `CREW_FA`, or `UNKNOWN_{edge_code}`
- **Direction**: Directed edge from source flight to target flight
- **Multi-edge support**: Multiple edges allowed between same flights (different resource types)
- **Edge Key**: The edge type (e.g., `"AIRCRAFT_TURN"`) is used as the edge key in NetworkX MultiDiGraph

**Edge Attributes**:

| Attribute | Type | Description | Example |
|-----------|------|-------------|---------|
| `type` | String | Edge type | `"AIRCRAFT_TURN"`, `"CREW_PILOT"`, `"CREW_FA"` |
| `edge_label` | String | Resource identifier | Tail number (e.g., `"N509DT"`) or crew ID (e.g., `"12345"`) |
| `activity` | String | Activity code (for aircraft) | `"N"` (normal) or other codes |
| `duty_type` | String | Duty type (for crew) | `"D"`, `"I"`, `"L"` or blank |
| `resource_type` | String | Type of resource | `"Aircraft"`, `"Crew"`, or `"Unknown"` |
| `role` | String | Crew role (for crew edges) | `"Pilot"` or `"FA"` |

**Temporal Attributes**:
- Resource connection edges are temporal (they represent connections at specific times)
- Temporal queries filter edges by source/target flight times
- Edge temporal attributes inherited from source/target flight nodes:
  - `source_flt_sch_dprt_gmt`: When source flight departs
  - `source_flt_act_arr_gmt`: When source flight arrives
  - `target_flt_sch_dprt_gmt`: When target flight departs
  - `target_flt_sch_arr_gmt`: When target flight arrives
  - `target_flt_act_arr_gmt`: When target flight arrives

**Edge Semantics**:

1. **AIRCRAFT_TURN** (`edge = "AC"`):
   - Source flight and target flight are operated by the same aircraft (tail number)
   - `edge_label` = tail number (e.g., `"N509DT"`)
   - `activity` = activity code (often `"N"` for normal)
   - Represents aircraft "turning" from one flight to the next

2. **CREW_PILOT** (`edge = "P"`):
   - Source flight and target flight share the same pilot crew
   - `edge_label` = pilot crew ID (numeric string)
   - `duty_type` = duty code (e.g., `"D"`, `"I"`, `"L"`)
   - Represents pilot crew connection between flights

3. **CREW_FA** (`edge = "F"`):
   - Source flight and target flight share the same flight attendant crew
   - `edge_label` = FA crew ID (numeric string)
   - `duty_type` = duty code (often blank)
   - Represents flight attendant crew connection between flights

### Resource Participation Edges (Model 2: "with-resources" only)

**Aircraft → Flight (OPERATED)**:
- **Type**: `"OPERATED"`
- **Direction**: `("Aircraft", tail_number) → ("Flight", flight_key)`
- **Attributes**: `type="OPERATED"`

**Crew → Flight (WORKED)**:
- **Type**: `"WORKED"`
- **Direction**: `("Crew:{role}", crew_id) → ("Flight", flight_key)`
- **Attributes**: `type="WORKED"`, `role="Pilot"` or `role="FA"`

---

## Temporal Modeling

### Temporal Approach: Time-Stamped Edges (Approach 1)

**Strategy**: Resource connection edges include temporal attributes inherited from their source and target flight nodes. Temporal queries filter edges by flight times.

**Implementation**:
- Edges are time-stamped via their source/target flight temporal attributes
- All datetime fields stored as ISO 8601 strings (GMT timezone)
- Temporal queries filter by:
  - Source flight departure/arrival times
  - Target flight departure/arrival times
  - Time windows for resource availability

**Temporal Queries**:
```python
# Get all resource connections active at a specific time
def get_active_connections_at_time(G, target_time):
    """Get all resource connections where source flight has arrived and target flight hasn't departed yet"""
    active = []
    for src_flight, tgt_flight, key, data in G.edges(keys=True, data=True):
        src_node = G.nodes[src_flight]
        tgt_node = G.nodes[tgt_flight]
        
        src_arr = parse_iso8601(src_node.get('act_arr_gmt') or src_node.get('sch_arr_gmt'))
        tgt_dep = parse_iso8601(tgt_node.get('sch_dep_gmt'))
        
        if src_arr <= target_time < tgt_dep:
            active.append((src_flight, tgt_flight, key, data))
    return active

# Get all flights using a specific resource in a time window
def get_flights_by_resource(G, resource_type, resource_id, start_time, end_time):
    """Get all flights connected via a specific resource in a time window"""
    flights = set()
    for src_flight, tgt_flight, key, data in G.edges(keys=True, data=True):
        if data.get('type') == resource_type and data.get('edge_label') == resource_id:
            src_node = G.nodes[src_flight]
            tgt_node = G.nodes[tgt_flight]
            
            src_dep = parse_iso8601(src_node.get('sch_dep_gmt'))
            tgt_arr = parse_iso8601(tgt_node.get('act_arr_gmt') or tgt_node.get('sch_arr_gmt'))
            
            if start_time <= src_dep <= end_time or start_time <= tgt_arr <= end_time:
                flights.add(src_flight)
                flights.add(tgt_flight)
    return flights
```

**Temporal Consistency**:
- All datetime fields use ISO 8601 format (GMT timezone)
- Consistent with existing Airport Network graph temporal approach
- Enables cross-graph temporal queries (e.g., "airport delays affecting resource connections")

---

## CSV Data Format

### Input CSV Structure

The operations resource graph is built from a CSV file containing flight-to-flight resource connections.

**CSV File Location**: `data/raw/flight_connections_sample.csv` (to be created)

**Required Columns**:

| Column Name | Type | Description | Example |
|-------------|------|-------------|---------|
| `source_flt` | String | Source flight key | `"868/MSPSEA/06Jan2026"` |
| `target_flt` | String | Target flight key | `"1234/SEALAX/06Jan2026"` |
| `edge` | String | Edge type code | `"AC"` (aircraft), `"P"` (pilot), `"F"` (FA) |
| `edge_label` | String | Resource identifier | Tail number (e.g., `"N509DT"`) or crew ID (e.g., `"12345"`) |
| `edge_activity` | String | Activity/duty code | `"N"`, `"D"`, `"I"`, `"L"`, or blank |
| `source_flt_sch_dprt_gmt` | String (ISO 8601) | Source flight scheduled departure | `"2026-01-06 15:00:00.000"` |
| `source_flt_sch_arr_gmt` | String (ISO 8601) | Source flight scheduled arrival | `"2026-01-06 17:30:00.000"` |
| `source_flt_actl_arr_gmt` | String (ISO 8601) | Source flight actual arrival | `"2026-01-06 17:35:00.000"` |
| `target_flt_sch_dprt_gmt` | String (ISO 8601) | Target flight scheduled departure | `"2026-01-06 18:00:00.000"` |
| `target_flt_sch_arr_gmt` | String (ISO 8601) | Target flight scheduled arrival | `"2026-01-06 20:30:00.000"` |
| `target_flt_actl_arr_gmt` | String (ISO 8601) | Target flight actual arrival | `"2026-01-06 20:35:00.000"` |

**CSV Format Notes**:
- Datetime fields may include milliseconds (`.000`) or not
- Empty/missing values should be handled gracefully (return `None`)
- Flight ID format: `"{carrier}{flight_number}_{date}_{origin}_{destination}"` (e.g., `"WN1234_2026-01-01_ATL_LGA"`)
- Edge codes: `"AC"` (aircraft), `"P"` (pilot), `"F"` (flight attendant), or other codes (treated as `UNKNOWN_{code}`)
- Activity codes: `"N"` (Normal), `"D"` (Deadhead), `"I"` (Interline/Inbound), `"L"` (Layover/Local), or blank

**Example CSV Row**:
```csv
source_flt,target_flt,edge,edge_label,edge_activity,source_flt_sch_dprt_gmt,source_flt_sch_arr_gmt,source_flt_actl_arr_gmt,target_flt_sch_dprt_gmt,target_flt_sch_arr_gmt,target_flt_actl_arr_gmt
WN1234_2026-01-01_ATL_LGA,WN890_2026-01-01_LGA_ATL,AC,8231,N,2026-01-01 08:00:00.000,2026-01-01 10:30:00.000,2026-01-01 10:27:00.000,2026-01-01 08:00:00.000,2026-01-01 10:40:00.000,2026-01-01 10:43:00.000
```

---

## Implementation Details

### Graph Building Script

**Script Location**: `scripts/build_operations_graph.py` (to be created)

**Key Functions**:

1. **`parse_flight_id(flight_id: str) -> Tuple[str, str, str, str, str]`**:
   - Parses flight ID format: `"WN1234_2026-01-01_ATL_LGA"` → `("WN", "1234", "2026-01-01", "ATL", "LGA")`
   - Returns: `(carrier, flight_number, flight_date, origin, destination)`
   - Handles invalid formats gracefully (returns `None` values)
   - **Note**: Uses same format as airport graph for consistency

2. **`parse_dt(s: str) -> Optional[datetime]`**:
   - Parses datetime strings: `"2026-01-06 15:00:00.000"` → `datetime` object
   - Handles formats with/without milliseconds
   - Returns `None` for empty/invalid strings

3. **`ensure_flight_node(G, flight_id, prefix, row)`**:
   - Creates or updates a Flight node with parsed attributes
   - `flight_id` uses format `"{carrier}{flight_number}_{date}_{origin}_{destination}"` (matches airport graph)
   - `prefix` is `"source"` or `"target"` to pick appropriate time columns
   - Stores attributes as ISO 8601 strings for JSON compatibility

4. **`ensure_aircraft_node(G, tail_number)`** (Model 2 only):
   - Creates Aircraft node if it doesn't exist

5. **`ensure_crew_node(G, crew_id, role)`** (Model 2 only):
   - Creates Crew node if it doesn't exist

6. **`add_flight_connection_edge(G, src_flight_id, tgt_flight_id, edge_type, props)`**:
   - Creates typed edge from source Flight to target Flight
   - Uses edge key (edge type) to support multiple parallel edges
   - Flight IDs use format matching airport graph for cross-graph queries

7. **`build_graph(csv_path, model="flights-only") -> nx.MultiDiGraph`**:
   - Main function to build the operations graph
   - `model` parameter: `"flights-only"` or `"with-resources"`
   - Returns NetworkX MultiDiGraph

**Graph Metadata**:
```python
G.graph["name"] = "OpsConnections"
G.graph["model"] = model  # "flights-only" or "with-resources"
G.graph["source_file"] = str(csv_path)
G.graph["directed"] = True
G.graph["created_utc"] = datetime.utcnow().isoformat()
```

### Graph Storage

**Output Formats**:
- **GraphML** (`{base_name}.graphml`): Portable format (Gephi, yEd, etc.)
- **NetworkX Pickle** (`{base_name}.gpickle`): Faithful round-trip within Python

**Storage Location**: `data/processed/` (consistent with existing graph storage)

**Naming Convention**: 
- `ops_graph_flights_only.json` (or `.graphml`, `.gpickle`)
- `ops_graph_with_resources.json` (or `.graphml`, `.gpickle`)

### Integration with Existing Codebase

**Shared Utilities**:
- Reuse datetime parsing utilities from existing codebase
- Reuse ISO 8601 conversion functions
- Follow same graph storage/loading patterns as `build_graph.py`

**Script Structure**:
- Follow same patterns as `scripts/build_graph.py`
- Include command-line interface with `argparse`
- Support `--load` flag to load existing graphs
- Include validation and error handling

---

## Sample Data Generation

### Mock Data Requirements

To support development and testing, we need to create mock resource connection data that aligns with the existing flight data in `data/raw/flights_sample.csv`.

**Sample Data File**: `data/raw/flight_connections_sample.csv`

**Data Generation Strategy**:
1. **Map Existing Flights**: Use flights from `flights_sample.csv` to create flight keys
2. **Assign Resources**: 
   - Assign aircraft (tail numbers) to flight sequences
   - Assign pilot crews to flight sequences
   - Assign FA crews to flight sequences
3. **Create Connections**: Generate flight-to-flight connections where:
   - Same aircraft operates consecutive flights (aircraft turn)
   - Same crew works consecutive flights (crew connection)
4. **Temporal Consistency**: Ensure connection times align with flight scheduled/actual times

**Sample Data Created**:
- **Flights Updated**: `data/raw/flights_sample.csv` now includes `ship_number` column (ships 8231-8235)
- **Connections File**: `data/raw/flight_connections_sample.csv`
- **Aircraft Connections**: 5 aircraft turns (ships 8231-8235)
  - Ship 8231: WN1234 (ATL→LGA) → WN890 (LGA→ATL)
  - Ship 8232: WN567 (ATL→LGA) → WN901 (LGA→ATL)
  - Ship 8233: WN678 (ATL→LGA) → WN246 (LGA→ATL)
  - Ship 8234: WN234 (ATL→SLC) → WN456 (SLC→ATL)
  - Ship 8235: WN789 (LGA→SLC) → WN345 (SLC→LGA)
- **Crew Connections**: 
  - 10 pilot connections (2 pilots × 5 aircraft turns)
  - 15 FA connections (3 FAs × 5 aircraft turns)
  - All crews stay with their assigned aircraft
- **Temporal Consistency**: All connections respect source flight arrival < target flight departure

**Implementation Decisions** ✅ **RESOLVED**:
1. **Aircraft Assignment**: 5 unique aircraft (ships 8231-8235) for 10 flights
   - Each aircraft operates 2 flights (outbound and return)
   - Example: Ship 8231 operates WN1234 (ATL→LGA) then WN890 (LGA→ATL)
2. **Crew Assignment**: 
   - Every flight requires exactly 2 pilots and 3 flight attendants
   - Crews stay with aircraft where possible (5 aircraft = 5 pilot crews, 5 FA crews)
   - Crew IDs: P1001-P5002 (pilots), F1001-F5003 (FAs)
   - Each crew works both flights on their assigned aircraft
3. **Turn Times**: Model realistic turn times (source flight arrival before target flight departure)
   - Example: WN1234 arrives LGA at 10:27, WN890 departs LGA at 08:05 (next day or same day with sufficient gap)
4. **Delayed Connections**: Sample data includes some delays to enable cascade analysis testing
   - Example: WN234 arrives SLC at 11:18 (3 min late), affecting WN456 departure

---

## Visualization & Analysis

### Potential Visualizations

1. **Resource Flow Graph**:
   - Nodes: Flights (or Flights + Resources in Model 2)
   - Edges: Resource connections
   - Color-code by resource type (aircraft vs. crew)
   - Temporal filtering to show active connections at a point in time

2. **Resource Utilization Timeline**:
   - Track which resources are in-use, available, or scheduled over time
   - Show resource "busy" periods and gaps

3. **Cascade Analysis**:
   - When a flight is delayed, highlight all downstream flights affected via resource connections
   - Show delay propagation paths

4. **Resource Dependency Tree**:
   - For a given flight, show all upstream flights that must complete before it can depart (resource dependencies)

### Integration with Existing Dashboard

**Future Enhancement**: Add operations graph visualizations to the Streamlit dashboard:
- New tab/section for "Resource Connections"
- Show resource flow alongside airport network
- Temporal synchronization with existing time slider

---

## Questions & Open Items

### Data & Modeling Questions - RESOLVED

1. **Flight Key Format**: ✅ **RESOLVED**
   - **Decision**: Use existing flight ID format from airport graph: `"{carrier}{flight_number}_{date}_{origin}_{destination}"`
   - **Example**: `"WN1234_2026-01-01_ATL_LGA"` (matches airport graph flight_id format)
   - **Implementation**: Operations graph will reference flight IDs from airport graph for consistency

2. **Date Format**: ✅ **RESOLVED**
   - **Decision**: Use ISO 8601 format (`"2026-01-06"`) for all date fields, consistent with airport graph
   - **Implementation**: All datetime fields stored as ISO 8601 strings (GMT timezone)

3. **Temporal Attributes**: ✅ **RESOLVED**
   - **Decision**: Store temporal attributes on edges (source/target flight times) for efficient temporal queries
   - **Implementation**: Edges include `source_flt_sch_dprt_gmt`, `source_flt_actl_arr_gmt`, `target_flt_sch_dprt_gmt`, `target_flt_actl_arr_gmt`

4. **Resource Node Attributes** (Model 2): ✅ **RESOLVED**
   - **Decision**: Start minimal (tail_number for Aircraft, crew_id and role for Crew)
   - **Implementation**: Can extend later with additional attributes (aircraft type, crew base, qualifications) as needed

5. **Edge Activity Codes**: ✅ **RESOLVED**
   - **Decision**: Document known codes, handle unknown codes gracefully
   - **Known Codes**:
     - `"N"` = Normal (default activity code)
     - `"D"` = Deadhead (crew traveling as passengers)
     - `"I"` = Likely "Interline" or "Inbound" (to be confirmed)
     - `"L"` = Likely "Layover" or "Local" (to be confirmed)
   - **Implementation**: Store activity codes as-is, document in code comments

### Implementation Questions

6. **Graph Building**:
   - Should `build_operations_graph.py` be a separate script, or integrated into `build_graph.py`?
   - **Recommendation**: Separate script for modularity, but share utilities.

7. **Graph Storage**:
   - Should operations graph be stored separately, or combined with airport graph?
   - **Recommendation**: Separate storage (different graph models), but enable cross-graph queries.

8. **Validation**:
   - Should we validate that source flight arrival < target flight departure?
   - Should we validate that flight keys match existing flight data?
   - **Recommendation**: Yes to both, with warnings for violations.

9. **Mock Data Generation**:
   - Should we create a separate script to generate mock connection data, or include it in the build script?
   - **Recommendation**: Separate script (`scripts/generate_mock_connections.py`) for flexibility.

10. **Integration**: ✅ **RESOLVED**
    - **Decision**: Operations graph will reference flight IDs from airport graph
    - **Implementation**: Flight nodes in operations graph use same flight_id format as airport graph edges
    - **Cross-Graph Queries**: Enable queries that join airport graph and operations graph via flight_id

### Temporal Questions - RESOLVED

11. **Temporal Queries**: ✅ **RESOLVED**
    - **Decision**: Yes, implement temporal query functions for resource availability and delay propagation
    - **Implementation**: 
      - Support queries like "all flights affected by a delayed resource"
      - Track resource availability windows (available, in-use, scheduled)
      - Implement temporal query functions similar to airport graph

12. **Event-Level Snapshots**: ✅ **RESOLVED**
    - **Decision**: Not initially for resource nodes, but consider for future resource state tracking
    - **Implementation**: Start with simple resource nodes, can add event-level snapshots later for:
      - Resource state tracking (available, in-use, maintenance)
      - Resource utilization metrics over time

---

## Next Steps

1. **Create Mock Data**: Generate `data/raw/flight_connections_sample.csv` aligned with existing flight data
2. **Implement Build Script**: Create `scripts/build_operations_graph.py` with core functionality
3. **Test Graph Building**: Validate graph structure, node/edge creation, temporal attributes
4. **Create Test Script**: Similar to `example_usage.py`, create `example_ops_usage.py` to demonstrate queries
5. **Documentation**: Update `README.md` with operations graph instructions
6. **Future**: Integrate operations graph visualizations into Streamlit dashboard

---

## References

- Existing graph schema: `docs/data_schema.md`
- Existing build script: `scripts/build_graph.py`
- Example usage: `scripts/example_usage.py`
- NetworkX MultiDiGraph documentation: https://networkx.org/documentation/stable/reference/classes/multidigraph.html
