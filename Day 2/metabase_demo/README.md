# Metabase Demo: Swiss Electricity Production Plants ⚡🇨🇭

This demo provides a fully automated, turn-key **Metabase** environment connected to a **PostgreSQL** database pre-loaded with the Swiss Federal Office of Energy (BFE/SFOE) electricity production plants dataset (`ch.bfe.elektrizitaetsproduktionsanlagen`).

---

## 🌟 Highlights

- **Zero-touch Configuration**: On startup, Metabase is automatically provisioned, the database connection is registered, and a starter dashboard is generated.
- **Full Dataset Ingestion**: Over **339,000 power plants** and **406,000 plant detail records** loaded into PostgreSQL with indexes.
- **Coordinate Conversion**: Swiss LV95 grid coordinates (`_x`, `_y`) are automatically transformed to standard WGS84 `latitude` and `longitude` during ingestion for native Metabase Pin Map visualizations.
- **Multilingual Support**: Catalogue lookups (Energy categories, sub-categories, plant types, solar orientations) in German, English, French, and Italian.
- **Rich Analytics Views**: Ready-to-use views (`v_electricity_plants`, `v_plant_details`) for drag-and-drop queries.

---

## 🚀 Quick Start

### 1. Start the Containers

From the `metabase_demo` directory, run:

```bash
docker compose up -d
```

### 2. Follow Ingestion & Metabase Setup

The `init-pipeline` container will automatically:
1. Initialize the PostgreSQL schema and views.
2. Ingest all 6 CSV files with coordinate transformations.
3. Wait for Metabase to boot and configure the admin account, database, and starter dashboard.

You can follow progress with:

```bash
docker compose logs -f init-pipeline
```

Once you see:
```text
================================================================================
🎉 METABASE ELECTRICITY DEMO IS READY!
--------------------------------------------------------------------------------
👉 Open URL      : http://localhost:3000
📧 Admin Email   : admin@course.local
🔑 Password      : Password123!
📊 Database      : Swiss Electricity Data (PostgreSQL, pre-configured)
📈 Pre-built     : 'Swiss Electricity Production Overview' Dashboard is ready
--------------------------------------------------------------------------------
================================================================================
```

### 3. Open Metabase

Open your browser and navigate to:
👉 **[http://localhost:3000](http://localhost:3000)**

Log in with:
- **Email:** `admin@course.local`
- **Password:** `Password123!`

---

## 📊 What's Included

### 1. Pre-built Dashboard: *"Swiss Electricity Production Overview"*
Contains:
- **KPI Metric Cards**: Total registered power plants, total installed capacity (GW), and solar installations.
- **Capacity by Energy Source (MW)**: Breakdown across Hydro, Solar, Nuclear, Biomass, Wind, etc.
- **Top 10 Cantons by Capacity (MW)**: Regional distribution across Switzerland.
- **Annual Commissioned Capacity Growth**: Yearly timeline of newly installed capacity (1990–2024).
- **Major Power Plants Map (> 5 MW)**: Geographic Pin Map of Switzerland's largest power producers.

---

## 🗄️ Database Schema & Views

The database contains both raw normalized tables and pre-joined analytical views:

### Tables
| Table | Description | Records |
| :--- | :--- | :--- |
| `electricity_production_plants` | Main plant records (Canton, Municipality, Date, Power, LV95 & Lat/Lon) | ~339,500 |
| `plant_details` | Sub-unit details (Solar panel tilt angles, orientations, unit power) | ~406,600 |
| `main_categories` | Main energy categories (Hydro, Renewables, Nuclear, Fossil) | 4 |
| `sub_categories` | Sub-categories (Photovoltaic, Hydro, Wind, Biomass, etc.) | 10 |
| `plant_categories` | Specific plant categories (Run-of-river, storage, rooftop, integrated) | 13 |
| `orientation_categories` | Solar panel orientations (South, East, West, Zenith, etc.) | 9 |

### Views
- **`v_electricity_plants`**: Pre-joined view with English & German category labels, `commissioning_year`, `total_power_mw`, and `latitude`/`longitude`.
- **`v_plant_details`**: Detail view joining solar panel tilt angles, orientations, and municipal locations.

---

## 💡 Example Course Exercises & Queries

### Exercise 1: Hydro vs. Solar Capacity by Canton (SQL)
Compare hydroelectric vs. solar capacity in each canton:

```sql
SELECT 
    p.canton,
    ROUND(SUM(CASE WHEN p.sub_category_id = 'subcat_1' THEN p.total_power_kw ELSE 0 END) / 1000.0, 1) AS hydro_mw,
    ROUND(SUM(CASE WHEN p.sub_category_id = 'subcat_2' THEN p.total_power_kw ELSE 0 END) / 1000.0, 1) AS solar_mw
FROM electricity_production_plants p
WHERE p.canton IS NOT NULL
GROUP BY p.canton
ORDER BY hydro_mw DESC;
```

### Exercise 2: Solar Panel Orientation & Tilt Optimization
Analyze which solar panel orientations produce the most power and their average inclination:

```sql
SELECT 
    oc.name_en AS orientation,
    ROUND(AVG(d.inclination), 1) AS avg_tilt_degrees,
    COUNT(*) AS total_installations,
    ROUND(SUM(d.power_kw) / 1000.0, 1) AS total_capacity_mw
FROM plant_details d
JOIN orientation_categories oc ON d.orientation_id = oc.id
GROUP BY oc.name_en
ORDER BY total_capacity_mw DESC;
```

### Exercise 3: Growth of Photovoltaics (2010–2024)
Track the explosion of rooftop and integrated solar in Switzerland:

```sql
SELECT 
    EXTRACT(YEAR FROM beginning_of_operation)::int AS year,
    COUNT(*) AS new_solar_plants,
    ROUND(SUM(total_power_kw) / 1000.0, 2) AS added_capacity_mw
FROM electricity_production_plants
WHERE sub_category_id = 'subcat_2'
  AND beginning_of_operation >= '2010-01-01'
GROUP BY 1
ORDER BY 1 ASC;
```

---

## 🛠️ Configuration & Customization

You can customize port bindings and admin credentials by copying `.env.example` to `.env`:

```bash
cp .env.example .env
```

```bash
# metabase_demo/.env
POSTGRES_DB=energy_db
POSTGRES_PORT=5432
METABASE_PORT=3000
ADMIN_EMAIL=admin@course.local
ADMIN_PASSWORD=Password123!
```

---

## 🧹 Stopping & Resetting the Demo

- **Stop containers**:
  ```bash
  docker compose down
  ```

- **Reset all data and start fresh**:
  ```bash
  docker compose down -v
  docker compose up -d
  ```
