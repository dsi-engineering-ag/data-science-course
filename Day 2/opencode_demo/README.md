# OpenCode Data Analyst Agent Demo 🤖⚡🇨🇭

This demo showcases how to run **OpenCode** inside a **Podman container** with a custom AI agent tailored for data science workflows. The agent is configured to analyze the Swiss Federal Office of Energy (BFE/SFOE) electricity production dataset (`ch.bfe.elektrizitaetsproduktionsanlagen`) using **Python and Pandas**.

---

## 🌟 What This Demo Covers

- **Podman Containerized Environment**: Completely self-contained container with Python, Pandas, Node.js, and OpenCode CLI.
- **Data Ingestion / Init Script**: `init.sh` automatically copies the dataset into the local folder so the container has direct access.
- **Custom OpenCode Agents**: Domain-specific system prompts, model behaviors, and tool permissions configured in `.opencode/agents/`.
- **OpenCode Slash Commands**: Reusable analytical commands in `.opencode/commands/` (e.g. `/analyze-canton`, `/solar-trends`, `/data-summary`).
- **Pandas-Driven Analysis**: Leveraging Python and Pandas to analyze over **339,000 electricity production facilities** in Switzerland.

---

## 📁 Folder Structure

```text
Day 2/opencode_demo/
├── Containerfile                      # Podman container definition
├── Dockerfile                         # Docker-compatible container definition
├── init.sh                            # Script to copy data into local container folder
├── run_podman.sh                      # One-click Podman build & launch script
├── opencode.jsonc                     # Project OpenCode configuration
├── .opencode/
│   ├── agents/
│   │   └── data-analyst.md            # Custom agent definition for Swiss Energy & Pandas
│   └── commands/
│       ├── analyze-canton.md          # Command: /analyze-canton <CANTON_CODE>
│       ├── solar-trends.md            # Command: /solar-trends
│       └── data-summary.md            # Command: /data-summary
├── data/                              # Local copy of the dataset created by init.sh
│   └── ch.bfe.elektrizitaetsproduktionsanlagen/
├── energy_data.py                     # Reusable Pandas helper module for loading & joins
├── example_queries.py                 # Standalone reference Python/Pandas script
├── requirements.txt                   # Python dependencies
└── README.md                          # This guide
```

---

## 🔑 Google Vertex AI Configuration

The demo uses Google Vertex AI with **Gemini 3.7 Flash** as the default model:
- **Default Model**: `google-vertex/gemini-3.7-flash`
- **Vertex Location**: `global`
- **Default Project ID**: Set via `GOOGLE_CLOUD_PROJECT` (e.g. `your-gcp-project-id`)
- **Host Key Location**: `~/.config/gcloud/opencode-key.json` (or set via `GOOGLE_APPLICATION_CREDENTIALS`)

When you run `./run_podman.sh`, it configures:
- `VERTEX_LOCATION=global`
- `GOOGLE_CLOUD_PROJECT="${GOOGLE_CLOUD_PROJECT:-your-gcp-project-id}"`
- `GOOGLE_APPLICATION_CREDENTIALS="${GOOGLE_APPLICATION_CREDENTIALS:-$HOME/.config/gcloud/opencode-key.json}"`
- Mounts OpenCode state/config and credentials into the container with `--userns=keep-id`.

---

## 🚀 Quick Start with Podman

### 1. Initialize Local Data

Run the init script to copy the dataset into the local folder:

```bash
cd "Day 2/opencode_demo"
./init.sh
```

### 2. Launch OpenCode with Podman

Run the launcher (export your GCP project first):

```bash
export GOOGLE_CLOUD_PROJECT="your-gcp-project-id"
./run_podman.sh
```

Or run the podman command directly:

```bash
VERTEX_LOCATION=global \
GOOGLE_CLOUD_PROJECT="your-gcp-project-id" \
GOOGLE_APPLICATION_CREDENTIALS=$HOME/.config/gcloud/opencode-key.json \
podman run -it --rm \
    --network=host \
    --security-opt=no-new-privileges \
    --cap-drop=ALL \
    -e VERTEX_LOCATION \
    -e GOOGLE_CLOUD_PROJECT \
    -e GOOGLE_APPLICATION_CREDENTIALS \
    -v "$HOME/.local/share/opencode:/home/$(whoami)/.local/share/opencode:z" \
    -v "$HOME/.local/state/opencode:/home/$(whoami)/.local/state/opencode:z" \
    -v "$HOME/.config/opencode:/home/$(whoami)/.config/opencode:z" \
    -v "$HOME/.config/gcloud/opencode-key.json:$HOME/.config/gcloud/opencode-key.json:ro,z" \
    --userns=keep-id \
    -v "${PWD}:${PWD}:z" \
    --workdir "${PWD}" \
    opencode-energy-demo opencode
```

When started inside the container, OpenCode automatically loads `opencode.jsonc` and activates the **`data-analyst`** agent by default!

---

## ⚡ Using Custom Slash Commands

You can trigger pre-configured prompts directly using slash commands:

### 1. Overview Summary
```text
/data-summary
```
Generates high-level metrics (total power in GW, plant counts, category breakdown, top cantons, and top power plants).

### 2. Canton Deep-Dive
```text
/analyze-canton ZH
```
Analyzes electricity production for Canton Zurich (or try `VS`, `BE`, `GR`, `TI`, `VD`).

### 3. Solar Adoption Trends
```text
/solar-trends
```
Computes annual photovoltaic expansion, yearly capacity additions, and cumulative growth from 2000 to 2024.

---

## 💬 Sample Prompts to Try with the Agent

Ask the agent analytical questions in plain English or German:

### Comparative Analysis
- *"Compare the energy mix between Canton Valais (VS) and Canton Zurich (ZH). Why do they differ so significantly?"*
- *"Which 5 cantons have the highest share of renewable energy (Hydro + Solar + Wind + Biomass)?"*

### Time Series & Growth
- *"How has the average capacity (kW) of newly installed solar power plants changed per year between 2010 and 2023?"*
- *"Which year saw the biggest jump in newly commissioned photovoltaic plants?"*

### Anomaly & Outlier Detection
- *"What are the top 10 largest individual power plants in Switzerland? List their name/address, municipality, canton, category, and capacity in MW."*
- *"Find municipalities in Switzerland with more than 100 MW of installed solar capacity."*

### Sub-Unit Solar Module Analysis
- *"Using `PlantDetail.csv`, what is the most common solar panel orientation (e.g. South vs East/West) and what is the typical tilt angle?"*

---

## 🐍 Standalone Python / Pandas Script

You can also run the standalone Python script inside the container to test the Pandas queries:

```bash
python example_queries.py
```

### Reusable Helper Module (`energy_data.py`)

You can import `energy_data` in any Python script:

```python
from energy_data import load_plants, get_canton_energy_summary, get_solar_trend

# Load enriched DataFrame with English catalogue names
df = load_plants(join_catalogues=True, lang="en")

# Get energy summary for Canton Bern
be_summary = get_canton_energy_summary(df, canton="BE")
print(be_summary)

# Get Photovoltaic adoption trend
trend = get_solar_trend(df, min_year=2015, max_year=2024)
print(trend)
```

---

## 🗄️ Dataset Overview

The dataset is located at `data/ch.bfe.elektrizitaetsproduktionsanlagen/`:

| File | Description | Key Columns |
| :--- | :--- | :--- |
| `ElectricityProductionPlant.csv` | Main plant records | `xtf_id`, `Canton`, `Municipality`, `BeginningOfOperation`, `TotalPower` (kW), `MainCategory`, `SubCategory`, `PlantCategory` |
| `PlantDetail.csv` | Solar panel sub-units | `Power` (kW), `Inclination` (deg), `Orientation`, `ElectricityProductionPlantR` |
| `MainCategoryCatalogue.csv` | Main categories | `maincat_1` (Hydro), `maincat_2` (Renewables), `maincat_3` (Nuclear), `maincat_4` (Fossil) |
| `SubCategoryCatalogue.csv` | Sub categories | `subcat_1` (Hydro), `subcat_2` (Solar/PV), `subcat_3` (Wind), `subcat_4` (Biomass), etc. |
| `PlantCategoryCatalogue.csv` | Technical plant types | Storage, pumped storage, run-of-river, rooftop attached, integrated, etc. |
| `OrientationCatalogue.csv` | Solar orientation | North, Northeast, East, Southeast, South, Southwest, West, Zenith |

---

## 🎓 Exercises for Course Participants

1. **Exercise 1 (Canton Energy Profile)**: Use the agent to find out which canton has the highest ratio of solar power relative to its total capacity.
2. **Exercise 2 (Municipal Leaderboard)**: Ask the agent to write and run a Pandas query finding the top 3 municipalities in Canton Bern with the highest solar capacity.
3. **Exercise 3 (Alpine vs. Plateau Solar)**: Ask the agent to compare solar installations in high-altitude cantons (VS, GR) vs. Plateau cantons (ZH, AG).
