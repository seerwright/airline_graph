# Scripts Directory

Utility scripts for the airline graph project.

## Available Scripts

### 1. `load_sample_data.py`
Loads and validates sample flight and airport data from CSV files.

**Usage:**
```bash
# Activate virtual environment first
source agraph_env/bin/activate  # On macOS/Linux
# or
agraph_env\Scripts\activate     # On Windows

# Run the script
python scripts/load_sample_data.py
```

**Features:**
- Loads airports from `data/raw/airports_sample.csv`
- Loads flights from `data/raw/flights_sample.csv`
- Validates data structure and schema compliance
- Calculates delays and generates flight IDs
- Prints summary statistics

### 2. `build_graph.py`
Creates a NetworkX **MultiDiGraph** (directed multigraph) from flight and airport data.
Uses MultiDiGraph to allow multiple edges between the same airports (multiple flights).

**Usage:**
```bash
# Activate virtual environment first
source agraph_env/bin/activate  # On macOS/Linux

# Install dependencies (if not already installed)
pip install -r requirements.txt

# Build the graph
python scripts/build_graph.py

# Save graph to JSON file
python scripts/build_graph.py --save data/processed/graph.json

# Load existing graph from JSON file
python scripts/build_graph.py --load data/processed/graph.json

# Specify custom data directory
python scripts/build_graph.py --data-dir data/raw --save data/processed/graph.json
```

**Features:**
- Creates NetworkX **MultiDiGraph** (allows multiple flights between same airports)
- Adds airport nodes with attributes
- Adds flight edges with temporal attributes (each flight is a separate edge)
- Creates event-level snapshots for airports (snapshots on every departure/arrival)
- Saves graph to JSON format (optional)
- Loads graph from JSON format (optional)

## Setup

Before running the scripts, you need to:

1. **Activate the virtual environment:**
   ```bash
   source agraph_env/bin/activate  # On macOS/Linux
   agraph_env\Scripts\activate     # On Windows
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

   This will install:
   - `networkx>=3.0` - Graph database library
   - `pandas>=2.0` - Data manipulation
   - `numpy>=1.24` - Numerical operations
   - Optional: visualization and analysis tools

## Quick Start

```bash
# 1. Activate virtual environment
source agraph_env/bin/activate

# 2. Install dependencies (first time only)
pip install -r requirements.txt

# 3. Validate sample data
python scripts/load_sample_data.py

# 4. Build the graph
python scripts/build_graph.py

# 5. Build and save graph
python scripts/build_graph.py --save data/processed/graph.json
```

## Graph Structure

The graph created by `build_graph.py` follows the schema in `docs/data_schema.md`:

- **Graph Type**: **MultiDiGraph** (directed multigraph)
  - Allows multiple edges between the same airports (multiple flights on same route)
  - Each flight is stored as a separate edge, preserving all flight data

- **Nodes**: Airports (ATL, LGA, SLC)
  - Attributes: airport_code, airport_name, city, state, country
  - Event-level snapshots: created on every departure/arrival event
  - Each snapshot tracks incremental changes and cumulative values
  - Approach 1: Event-Level Snapshots (not time-windowed)

- **Edges**: Flights between airports (each flight is a separate edge)
  - Attributes: flight_id, carrier, flight_number, equipment
  - Temporal attributes: scheduled/actual departure/arrival times (ISO 8601 GMT)
  - Delay metrics: departure_delay_minutes, arrival_delay_minutes
  - Multiple edges allowed between same airports (e.g., 3 flights ATL→LGA)
  - Approach 1: Time-Stamped Attributes

## Example: Using the Graph in Python

```python
import networkx as nx
from scripts.build_graph import build_graph, load_graph

# Build the graph
G = build_graph()

# Or load an existing graph
# G = load_graph(Path('data/processed/graph.json'))

# Access airport nodes
print(f"Airports: {list(G.nodes())}")

# Access flight edges (MultiDiGraph includes key parameter)
for origin, destination, key, data in G.edges(data=True, keys=True):
    print(f"{origin} → {destination}: {data.get('flight_id')} (edge key: {key})")

# Query flights by time window
from datetime import datetime, timezone
target_date = '2026-01-01'

flights_on_date = [
    (u, v, k, data) for u, v, k, data in G.edges(data=True, keys=True)
    if data.get('flight_date') == target_date
]

# Get airport metrics at a specific time
from scripts.example_usage import get_airport_state_at_time
airport = 'ATL'
target_time = datetime(2026, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
state = get_airport_state_at_time(G, airport, target_time)
print(f"{airport} state at {target_time}: {state}")

# Get latest airport state (from last snapshot)
if 'time_snapshots' in G.nodes[airport]:
    last_snapshot = G.nodes[airport]['time_snapshots'][-1]
    cumulative = last_snapshot.get('cumulative', {})
    print(f"{airport} final state: {cumulative}")
```

## Troubleshooting

### ModuleNotFoundError: No module named 'networkx'
- Make sure you've activated the virtual environment
- Install dependencies: `pip install -r requirements.txt`

### Import errors
- Make sure you're running from the project root directory
- Check that all script files are in the `scripts/` directory

### FileNotFoundError for data files
- Verify that `data/raw/airports_sample.csv` and `data/raw/flights_sample.csv` exist
- Check file paths are correct

## Next Steps

After building the graph, you can:
1. Visualize the graph using NetworkX and matplotlib
2. Analyze flight routes and delays
3. Query temporal data
4. Export to other formats (Neo4j, etc.)
5. Build analytics and reports
