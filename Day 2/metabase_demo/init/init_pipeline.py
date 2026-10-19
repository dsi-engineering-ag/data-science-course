#!/usr/bin/env python3
"""
Metabase & PostgreSQL Initialization Pipeline
1. Loads electricity production plant CSV datasets into PostgreSQL.
2. Calculates WGS84 (Lat/Lon) from Swiss LV95 coordinates.
3. Automatically completes Metabase first-time setup via API.
4. Pre-configures database connection, semantic field types, starter questions & dashboard.
"""

import io
import os
import sys
import time
import csv
import json
import logging
import requests
import psycopg2
from psycopg2.extras import execute_values

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s - %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("init_pipeline")

# Configuration from Environment Variables
PG_HOST = os.getenv("PG_HOST", "postgres")
PG_PORT = int(os.getenv("PG_PORT", "5432"))
PG_DB = os.getenv("PG_DB", "energy_db")
PG_USER = os.getenv("PG_USER", "postgres")
PG_PASSWORD = os.getenv("PG_PASSWORD", "postgres")

METABASE_URL = os.getenv("METABASE_URL", "http://metabase:3000")
ADMIN_FIRST_NAME = os.getenv("ADMIN_FIRST_NAME", "Course")
ADMIN_LAST_NAME = os.getenv("ADMIN_LAST_NAME", "Admin")
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@course.local")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "Password123!")

DATA_DIR = os.getenv("DATA_DIR", "/data/ch.bfe.elektrizitaetsproduktionsanlagen")


def lv95_to_wgs84(east, north):
    """
    Converts Swiss LV95 projection (CH1903+) to WGS84 Latitude & Longitude.
    Using standard Swisstopo approximation formulas.
    """
    if east is None or north is None:
        return None, None
    try:
        e = float(east)
        n = float(north)
        # LV95 offset
        y_prime = (e - 2600000.0) / 1000000.0
        x_prime = (n - 1200000.0) / 1000000.0

        lambda_p = (
            2.6779094
            + 4.728982 * y_prime
            + 0.791484 * y_prime * x_prime
            + 0.1306 * y_prime * (x_prime ** 2)
            - 0.0436 * (y_prime ** 3)
        )

        phi_p = (
            16.9023892
            + 3.238272 * x_prime
            - 0.270978 * (y_prime ** 2)
            - 0.002528 * (x_prime ** 2)
            - 0.0447 * (y_prime ** 2) * x_prime
            - 0.0140 * (x_prime ** 3)
        )

        lon = round(lambda_p * 100.0 / 36.0, 7)
        lat = round(phi_p * 100.0 / 36.0, 7)
        return lat, lon
    except (ValueError, TypeError):
        return None, None


def wait_for_postgres():
    logger.info(f"Connecting to PostgreSQL at {PG_HOST}:{PG_PORT}/{PG_DB}...")
    while True:
        try:
            conn = psycopg2.connect(
                host=PG_HOST,
                port=PG_PORT,
                dbname=PG_DB,
                user=PG_USER,
                password=PG_PASSWORD,
                connect_timeout=3
            )
            conn.close()
            logger.info("Connected to PostgreSQL successfully.")
            break
        except Exception as e:
            logger.info(f"Waiting for PostgreSQL... ({e})")
            time.sleep(2)


def get_pg_connection():
    return psycopg2.connect(
        host=PG_HOST,
        port=PG_PORT,
        dbname=PG_DB,
        user=PG_USER,
        password=PG_PASSWORD
    )


def init_database_schema(conn):
    logger.info("Applying database schema & views...")
    schema_path = "/app/schema.sql"
    if not os.path.exists(schema_path):
        schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")

    with open(schema_path, "r", encoding="utf-8") as f:
        sql = f.read()

    with conn.cursor() as cur:
        cur.execute(sql)
    conn.commit()
    logger.info("Database schema applied.")


def load_catalogues(conn):
    catalogues = [
        ("MainCategoryCatalogue.csv", "main_categories"),
        ("SubCategoryCatalogue.csv", "sub_categories"),
        ("PlantCategoryCatalogue.csv", "plant_categories"),
        ("OrientationCatalogue.csv", "orientation_categories"),
    ]

    for csv_file, table_name in catalogues:
        file_path = os.path.join(DATA_DIR, csv_file)
        if not os.path.exists(file_path):
            logger.warning(f"File not found: {file_path}")
            continue

        with conn.cursor() as cur:
            cur.execute(f"SELECT COUNT(*) FROM {table_name};")
            if cur.fetchone()[0] > 0:
                logger.info(f"Table {table_name} already populated. Skipping.")
                continue

            with open(file_path, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                rows = [
                    (
                        r["Catalogue_id"].strip(),
                        r.get("de", "").strip() or None,
                        r.get("fr", "").strip() or None,
                        r.get("it", "").strip() or None,
                        r.get("en", "").strip() or None,
                    )
                    for r in reader
                    if r.get("Catalogue_id")
                ]

            execute_values(
                cur,
                f"INSERT INTO {table_name} (id, name_de, name_fr, name_it, name_en) VALUES %s ON CONFLICT DO NOTHING;",
                rows
            )
        conn.commit()
        logger.info(f"Loaded {len(rows)} entries into {table_name}.")


def load_electricity_production_plants(conn):
    csv_file = os.path.join(DATA_DIR, "ElectricityProductionPlant.csv")
    if not os.path.exists(csv_file):
        logger.error(f"File not found: {csv_file}")
        return

    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM electricity_production_plants;")
        count = cur.fetchone()[0]
        if count > 0:
            logger.info(f"electricity_production_plants already has {count} records. Skipping.")
            return

        logger.info(f"Processing and loading {csv_file} into PostgreSQL...")
        start_time = time.time()

        buffer = io.StringIO()
        writer = csv.writer(buffer, delimiter="\t", lineterminator="\n")

        total_rows = 0
        with open(csv_file, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for r in reader:
                xtf_id = r.get("xtf_id", "").strip()
                if not xtf_id:
                    continue

                address = r.get("Address", "").strip() or None
                postcode = r.get("PostCode", "").strip() or None
                postcode_val = int(float(postcode)) if postcode else None
                municipality = r.get("Municipality", "").strip() or None
                canton = r.get("Canton", "").strip() or None
                egid = r.get("EGID", "").strip() or None
                egid_val = int(float(egid)) if egid else None

                date_val = r.get("BeginningOfOperation", "").strip() or None
                init_p = r.get("InitialPower", "").strip() or None
                init_p_val = float(init_p) if init_p else None
                tot_p = r.get("TotalPower", "").strip() or None
                tot_p_val = float(tot_p) if tot_p else None

                main_cat = r.get("MainCategory", "").strip() or None
                sub_cat = r.get("SubCategory", "").strip() or None
                plant_cat = r.get("PlantCategory", "").strip() or None

                x_str = r.get("_x", "").strip() or None
                y_str = r.get("_y", "").strip() or None
                x_val = float(x_str) if x_str else None
                y_val = float(y_str) if y_str else None

                lat, lon = lv95_to_wgs84(x_val, y_val)

                writer.writerow([
                    xtf_id,
                    address if address is not None else "\\N",
                    postcode_val if postcode_val is not None else "\\N",
                    municipality if municipality is not None else "\\N",
                    canton if canton is not None else "\\N",
                    egid_val if egid_val is not None else "\\N",
                    date_val if date_val is not None else "\\N",
                    init_p_val if init_p_val is not None else "\\N",
                    tot_p_val if tot_p_val is not None else "\\N",
                    main_cat if main_cat is not None else "\\N",
                    sub_cat if sub_cat is not None else "\\N",
                    plant_cat if plant_cat is not None else "\\N",
                    x_val if x_val is not None else "\\N",
                    y_val if y_val is not None else "\\N",
                    lat if lat is not None else "\\N",
                    lon if lon is not None else "\\N",
                ])
                total_rows += 1

        buffer.seek(0)
        logger.info(f"Streaming {total_rows} plant records to database via COPY...")
        cur.copy_from(
            buffer,
            "electricity_production_plants",
            columns=[
                "xtf_id", "address", "postcode", "municipality", "canton", "egid",
                "beginning_of_operation", "initial_power_kw", "total_power_kw",
                "main_category_id", "sub_category_id", "plant_category_id",
                "x_lv95", "y_lv95", "latitude", "longitude"
            ],
            null="\\N"
        )
        conn.commit()
        elapsed = time.time() - start_time
        logger.info(f"Loaded {total_rows} electricity production plants in {elapsed:.2f}s.")


def load_plant_details(conn):
    csv_file = os.path.join(DATA_DIR, "PlantDetail.csv")
    if not os.path.exists(csv_file):
        logger.error(f"File not found: {csv_file}")
        return

    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM plant_details;")
        count = cur.fetchone()[0]
        if count > 0:
            logger.info(f"plant_details already has {count} records. Skipping.")
            return

        logger.info(f"Processing and loading {csv_file} into PostgreSQL...")
        start_time = time.time()

        buffer = io.StringIO()
        writer = csv.writer(buffer, delimiter="\t", lineterminator="\n")

        total_rows = 0
        with open(csv_file, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for r in reader:
                xtf_id = r.get("xtf_id", "").strip()
                if not xtf_id:
                    continue

                date_val = r.get("Date", "").strip() or None
                p_str = r.get("Power", "").strip() or None
                p_val = float(p_str) if p_str else None
                inc_str = r.get("Inclination", "").strip() or None
                inc_val = float(inc_str) if inc_str else None

                orient = r.get("Orientation", "").strip() or None
                plant_cat = r.get("PlantCategory", "").strip() or None
                plant_id = r.get("ElectricityProductionPlantR", "").strip() or None
                plant_id_val = int(float(plant_id)) if plant_id else None

                writer.writerow([
                    xtf_id,
                    date_val if date_val is not None else "\\N",
                    p_val if p_val is not None else "\\N",
                    inc_val if inc_val is not None else "\\N",
                    orient if orient is not None else "\\N",
                    plant_cat if plant_cat is not None else "\\N",
                    plant_id_val if plant_id_val is not None else "\\N",
                ])
                total_rows += 1

        buffer.seek(0)
        logger.info(f"Streaming {total_rows} plant detail records to database via COPY...")
        cur.copy_from(
            buffer,
            "plant_details",
            columns=[
                "xtf_id", "date", "power_kw", "inclination",
                "orientation_id", "plant_category_id", "plant_id"
            ],
            null="\\N"
        )
        conn.commit()
        elapsed = time.time() - start_time
        logger.info(f"Loaded {total_rows} plant details in {elapsed:.2f}s.")


def wait_for_metabase():
    logger.info(f"Waiting for Metabase at {METABASE_URL} to become ready...")
    for _ in range(120):
        try:
            res = requests.get(f"{METABASE_URL}/api/health", timeout=3)
            if res.status_code == 200:
                logger.info("Metabase is healthy and responsive.")
                return True
        except Exception:
            pass
        time.sleep(2)
    logger.error("Metabase did not become healthy in time.")
    return False


def get_or_create_session(session):
    """
    Authenticates with Metabase and sets X-Metabase-Session header.
    """
    login_res = session.post(f"{METABASE_URL}/api/session", json={
        "username": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    if login_res.status_code == 200:
        session_token = login_res.json().get("id")
        session.headers.update({"X-Metabase-Session": session_token})
        return session_token
    return None


def setup_metabase():
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})

    # Check setup status
    try:
        props_res = session.get(f"{METABASE_URL}/api/session/properties")
        if props_res.status_code != 200:
            logger.error(f"Failed to fetch session properties: {props_res.text}")
            return
        props = props_res.json()
    except Exception as e:
        logger.error(f"Error querying Metabase properties: {e}")
        return

    has_setup = props.get("has-user-setup", False)
    if not has_setup:
        setup_token = props.get("setup-token")
        if not setup_token:
            logger.error("No setup token found in Metabase properties.")
            return

        logger.info("Running initial Metabase user setup...")
        setup_payload = {
            "token": setup_token,
            "user": {
                "first_name": ADMIN_FIRST_NAME,
                "last_name": ADMIN_LAST_NAME,
                "email": ADMIN_EMAIL,
                "password": ADMIN_PASSWORD,
                "site_name": "Swiss Electricity Plants Demo"
            },
            "prefs": {
                "site_name": "Swiss Electricity Plants Demo",
                "allow_tracking": False
            }
        }

        resp = session.post(f"{METABASE_URL}/api/setup", json=setup_payload)
        if resp.status_code not in (200, 204):
            logger.error(f"Metabase user setup failed: {resp.status_code} {resp.text}")
            return
        logger.info("Metabase user setup completed.")

    # Authenticate to get session token
    session_token = get_or_create_session(session)
    if not session_token:
        logger.error("Could not authenticate with Metabase.")
        return

    logger.info("Authenticated with Metabase successfully.")

    # Find or register database
    db_id = get_or_create_database(session)
    if not db_id:
        logger.error("Failed to connect or resolve database in Metabase.")
        return

    logger.info(f"Target Database ID: {db_id}. Triggering sync...")
    try:
        session.post(f"{METABASE_URL}/api/database/{db_id}/sync_schema")
        session.post(f"{METABASE_URL}/api/database/{db_id}/rescan_values")
    except Exception as e:
        logger.warning(f"Sync trigger warning: {e}")

    # Wait for tables to appear
    wait_for_database_sync(session, db_id)

    # Configure semantic field types (Lat/Lon/Canton)
    update_field_semantic_types(session, db_id)

    # Create Sample Starter Dashboard & Questions
    create_sample_dashboard(session, db_id)


def get_or_create_database(session):
    """
    Checks if Swiss Electricity Data is already connected.
    If not, connects it via POST /api/database.
    """
    try:
        db_res = session.get(f"{METABASE_URL}/api/database")
        if db_res.status_code == 200:
            data = db_res.json()
            dbs = data.get("data", data) if isinstance(data, dict) else data
            for d in dbs:
                if d.get("name") == "Swiss Electricity Data" or d.get("details", {}).get("dbname") == PG_DB:
                    logger.info(f"Found existing database '{d.get('name')}' with ID: {d.get('id')}")
                    return d.get("id")
    except Exception as e:
        logger.warning(f"Could not query database list: {e}")

    # Create database connection
    logger.info("Registering 'Swiss Electricity Data' database connection in Metabase...")
    db_payload = {
        "engine": "postgres",
        "name": "Swiss Electricity Data",
        "details": {
            "host": PG_HOST,
            "port": PG_PORT,
            "dbname": PG_DB,
            "user": PG_USER,
            "password": PG_PASSWORD,
            "ssl": False,
            "schema-filters-type": "all"
        },
        "is_full_sync": True,
        "is_on_demand": False
    }

    create_res = session.post(f"{METABASE_URL}/api/database", json=db_payload)
    if create_res.status_code in (200, 201):
        db_data = create_res.json()
        db_id = db_data.get("id")
        logger.info(f"Successfully registered database with ID: {db_id}")
        return db_id
    else:
        logger.error(f"Failed to create database connection: {create_res.status_code} {create_res.text}")
        return None


def wait_for_database_sync(session, db_id):
    logger.info("Waiting for Metabase to sync database schema...")
    for _ in range(30):
        try:
            meta_res = session.get(f"{METABASE_URL}/api/database/{db_id}/metadata")
            if meta_res.status_code == 200:
                tables = meta_res.json().get("tables", [])
                table_names = [t.get("name") for t in tables]
                if "electricity_production_plants" in table_names or len(tables) >= 4:
                    logger.info(f"Schema sync verified. Found {len(tables)} tables: {', '.join(table_names)}")
                    return
        except Exception:
            pass
        time.sleep(1)


def update_field_semantic_types(session, db_id):
    try:
        meta_res = session.get(f"{METABASE_URL}/api/database/{db_id}/metadata")
        if meta_res.status_code == 200:
            tables = meta_res.json().get("tables", [])
            for table in tables:
                for field in table.get("fields", []):
                    fname = field.get("name", "").lower()
                    fid = field.get("id")
                    semantic_type = None
                    if fname == "latitude":
                        semantic_type = "type/Latitude"
                    elif fname == "longitude":
                        semantic_type = "type/Longitude"
                    elif fname == "canton":
                        semantic_type = "type/State"
                    elif fname == "postcode":
                        semantic_type = "type/ZipCode"
                    elif fname == "municipality":
                        semantic_type = "type/City"
                    elif fname == "beginning_of_operation":
                        semantic_type = "type/CreationDate"

                    if semantic_type and fid:
                        session.put(f"{METABASE_URL}/api/field/{fid}", json={"semantic_type": semantic_type})
    except Exception as e:
        logger.warning(f"Field semantic type update skipped: {e}")

def create_sample_dashboard(session, db_id):
    logger.info("Checking starter questions and demo dashboard...")

    # Check if dashboard already exists
    try:
        dash_list_res = session.get(f"{METABASE_URL}/api/dashboard")
        if dash_list_res.status_code == 200:
            dashboards = dash_list_res.json()
            for d in dashboards:
                if d.get("name") == "Swiss Electricity Production Overview":
                    logger.info("Demo dashboard already exists. Skipping recreation.")
                    return
    except Exception as e:
        logger.warning(f"Dashboard query warning: {e}")

    # Create Dashboard
    dash_payload = {
        "name": "Swiss Electricity Production Overview",
        "description": "Interactive overview of Swiss power plants (Hydro, Solar, Wind, Biomass, Nuclear)",
        "parameters": []
    }
    dash_res = session.post(f"{METABASE_URL}/api/dashboard", json=dash_payload)
    if dash_res.status_code not in (200, 201):
        logger.warning(f"Could not create dashboard: {dash_res.text}")
        return

    dashboard_id = dash_res.json().get("id")

    queries = [
        {
            "name": "Total Plants Registered",
            "display": "scalar",
            "sql": "SELECT COUNT(*) AS total_plants FROM electricity_production_plants;",
            "grid": {"row": 0, "col": 0, "size_x": 4, "size_y": 3}
        },
        {
            "name": "Total Installed Capacity (GW)",
            "display": "scalar",
            "sql": "SELECT ROUND(SUM(total_power_kw) / 1000000.0, 2) AS total_gw FROM electricity_production_plants;",
            "grid": {"row": 0, "col": 4, "size_x": 4, "size_y": 3}
        },
        {
            "name": "Total Solar PV Plants",
            "display": "scalar",
            "sql": "SELECT COUNT(*) AS solar_plants FROM electricity_production_plants WHERE sub_category_id = 'subcat_2';",
            "grid": {"row": 0, "col": 8, "size_x": 4, "size_y": 3}
        },
        {
            "name": "Capacity by Energy Source (MW)",
            "display": "bar",
            "sql": """
                SELECT 
                    COALESCE(mc.name_en, 'Other') AS energy_source,
                    ROUND(SUM(p.total_power_kw) / 1000.0, 1) AS total_mw,
                    COUNT(*) AS plant_count
                FROM electricity_production_plants p
                LEFT JOIN main_categories mc ON p.main_category_id = mc.id
                GROUP BY 1
                ORDER BY total_mw DESC;
            """,
            "grid": {"row": 3, "col": 0, "size_x": 6, "size_y": 6}
        },
        {
            "name": "Top 10 Cantons by Total Capacity (MW)",
            "display": "bar",
            "sql": """
                SELECT 
                    canton,
                    ROUND(SUM(total_power_kw) / 1000.0, 1) AS total_capacity_mw
                FROM electricity_production_plants
                WHERE canton IS NOT NULL
                GROUP BY canton
                ORDER BY total_capacity_mw DESC
                LIMIT 10;
            """,
            "grid": {"row": 3, "col": 6, "size_x": 6, "size_y": 6}
        },
        {
            "name": "Annual Commissioned Capacity Growth (1990 - 2024)",
            "display": "line",
            "sql": """
                SELECT 
                    EXTRACT(YEAR FROM beginning_of_operation)::int AS commissioning_year,
                    ROUND(SUM(total_power_kw) / 1000.0, 1) AS added_capacity_mw
                FROM electricity_production_plants
                WHERE beginning_of_operation >= '1990-01-01' 
                  AND beginning_of_operation <= '2024-12-31'
                GROUP BY 1
                ORDER BY 1 ASC;
            """,
            "grid": {"row": 9, "col": 0, "size_x": 12, "size_y": 6}
        },
        {
            "name": "Major Power Plants Map (> 5 MW)",
            "display": "map",
            "sql": """
                SELECT 
                    p.xtf_id,
                    p.municipality,
                    p.canton,
                    ROUND((p.total_power_kw / 1000.0)::numeric, 2) AS power_mw,
                    COALESCE(mc.name_en, 'Other') AS source,
                    p.latitude,
                    p.longitude
                FROM electricity_production_plants p
                LEFT JOIN main_categories mc ON p.main_category_id = mc.id
                WHERE p.latitude IS NOT NULL 
                  AND p.longitude IS NOT NULL
                  AND p.total_power_kw >= 5000
                ORDER BY p.total_power_kw DESC;
            """,
            "grid": {"row": 15, "col": 0, "size_x": 12, "size_y": 8}
        }
    ]

    for q in queries:
        try:
            card_payload = {
                "name": q["name"],
                "dataset_query": {
                    "database": db_id,
                    "type": "native",
                    "native": {
                        "query": q["sql"].strip()
                    }
                },
                "display": q["display"],
                "visualization_settings": {}
            }
            c_res = session.post(f"{METABASE_URL}/api/card", json=card_payload)
            if c_res.status_code in (200, 201):
                card_id = c_res.json().get("id")
                # Add to dashboard
                session.post(
                    f"{METABASE_URL}/api/dashboard/{dashboard_id}/cards",
                    json={
                        "cardId": card_id,
                        "row": q["grid"]["row"],
                        "col": q["grid"]["col"],
                        "size_x": q["grid"]["size_x"],
                        "size_y": q["grid"]["size_y"]
                    }
                )
        except Exception as e:
            logger.warning(f"Error creating card '{q['name']}': {e}")

    logger.info("Demo dashboard setup complete!")


def print_banner():
    banner = f"""
================================================================================
🎉 METABASE ELECTRICITY DEMO IS READY!
--------------------------------------------------------------------------------
👉 Open URL      : {METABASE_URL} (or http://localhost:3000)
📧 Admin Email   : {ADMIN_EMAIL}
🔑 Password      : {ADMIN_PASSWORD}
📊 Database      : Swiss Electricity Data (PostgreSQL, pre-configured)
📈 Pre-built     : 'Swiss Electricity Production Overview' Dashboard is ready
--------------------------------------------------------------------------------
================================================================================
"""
    print(banner, flush=True)


def main():
    logger.info("Starting Metabase Demo initialization pipeline...")
    wait_for_postgres()
    conn = get_pg_connection()

    try:
        init_database_schema(conn)
        load_catalogues(conn)
        load_electricity_production_plants(conn)
        load_plant_details(conn)
    finally:
        conn.close()

    if wait_for_metabase():
        setup_metabase()
        print_banner()
    else:
        logger.error("Could not complete Metabase automatic setup.")


if __name__ == "__main__":
    main()
