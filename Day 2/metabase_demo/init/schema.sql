-- Swiss Electricity Production Plants Database Schema

CREATE TABLE IF NOT EXISTS main_categories (
    id VARCHAR(32) PRIMARY KEY,
    name_de VARCHAR(255),
    name_fr VARCHAR(255),
    name_it VARCHAR(255),
    name_en VARCHAR(255)
);

CREATE TABLE IF NOT EXISTS sub_categories (
    id VARCHAR(32) PRIMARY KEY,
    name_de VARCHAR(255),
    name_fr VARCHAR(255),
    name_it VARCHAR(255),
    name_en VARCHAR(255)
);

CREATE TABLE IF NOT EXISTS plant_categories (
    id VARCHAR(32) PRIMARY KEY,
    name_de VARCHAR(255),
    name_fr VARCHAR(255),
    name_it VARCHAR(255),
    name_en VARCHAR(255)
);

CREATE TABLE IF NOT EXISTS orientation_categories (
    id VARCHAR(32) PRIMARY KEY,
    name_de VARCHAR(255),
    name_fr VARCHAR(255),
    name_it VARCHAR(255),
    name_en VARCHAR(255)
);

CREATE TABLE IF NOT EXISTS electricity_production_plants (
    xtf_id BIGINT PRIMARY KEY,
    address TEXT,
    postcode INTEGER,
    municipality TEXT,
    canton VARCHAR(10),
    egid BIGINT,
    beginning_of_operation DATE,
    initial_power_kw DOUBLE PRECISION,
    total_power_kw DOUBLE PRECISION,
    main_category_id VARCHAR(32) REFERENCES main_categories(id),
    sub_category_id VARCHAR(32) REFERENCES sub_categories(id),
    plant_category_id VARCHAR(32) REFERENCES plant_categories(id),
    x_lv95 DOUBLE PRECISION,
    y_lv95 DOUBLE PRECISION,
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION
);

CREATE TABLE IF NOT EXISTS plant_details (
    xtf_id VARCHAR(64) PRIMARY KEY,
    date DATE,
    power_kw DOUBLE PRECISION,
    inclination DOUBLE PRECISION,
    orientation_id VARCHAR(32) REFERENCES orientation_categories(id),
    plant_category_id VARCHAR(32) REFERENCES plant_categories(id),
    plant_id BIGINT REFERENCES electricity_production_plants(xtf_id)
);

-- Indexes for fast querying & aggregations
CREATE INDEX IF NOT EXISTS idx_epp_canton ON electricity_production_plants(canton);
CREATE INDEX IF NOT EXISTS idx_epp_postcode ON electricity_production_plants(postcode);
CREATE INDEX IF NOT EXISTS idx_epp_beginning_of_operation ON electricity_production_plants(beginning_of_operation);
CREATE INDEX IF NOT EXISTS idx_epp_main_category ON electricity_production_plants(main_category_id);
CREATE INDEX IF NOT EXISTS idx_epp_sub_category ON electricity_production_plants(sub_category_id);
CREATE INDEX IF NOT EXISTS idx_epp_total_power ON electricity_production_plants(total_power_kw);
CREATE INDEX IF NOT EXISTS idx_epp_geo ON electricity_production_plants(latitude, longitude);
CREATE INDEX IF NOT EXISTS idx_pd_plant_id ON plant_details(plant_id);
CREATE INDEX IF NOT EXISTS idx_pd_orientation ON plant_details(orientation_id);

-- Enriched views for analytics and Metabase drag-and-drop querying
CREATE OR REPLACE VIEW v_electricity_plants AS
SELECT 
    p.xtf_id,
    p.address,
    p.postcode,
    p.municipality,
    p.canton,
    p.egid,
    p.beginning_of_operation,
    EXTRACT(YEAR FROM p.beginning_of_operation)::INT AS commissioning_year,
    p.initial_power_kw,
    p.total_power_kw,
    ROUND((p.total_power_kw / 1000.0)::numeric, 3) AS total_power_mw,
    ROUND((p.total_power_kw / 1000000.0)::numeric, 6) AS total_power_gw,
    mc.name_de AS main_category_de,
    mc.name_en AS main_category_en,
    sc.name_de AS sub_category_de,
    sc.name_en AS sub_category_en,
    pc.name_de AS plant_category_de,
    pc.name_en AS plant_category_en,
    p.x_lv95,
    p.y_lv95,
    p.latitude,
    p.longitude
FROM electricity_production_plants p
LEFT JOIN main_categories mc ON p.main_category_id = mc.id
LEFT JOIN sub_categories sc ON p.sub_category_id = sc.id
LEFT JOIN plant_categories pc ON p.plant_category_id = pc.id;

CREATE OR REPLACE VIEW v_plant_details AS
SELECT 
    d.xtf_id AS detail_id,
    d.plant_id,
    d.date AS detail_date,
    d.power_kw,
    ROUND((d.power_kw / 1000.0)::numeric, 3) AS power_mw,
    d.inclination,
    oc.name_de AS orientation_de,
    oc.name_en AS orientation_en,
    pc.name_de AS plant_category_de,
    pc.name_en AS plant_category_en,
    p.municipality,
    p.canton,
    p.latitude,
    p.longitude
FROM plant_details d
LEFT JOIN electricity_production_plants p ON d.plant_id = p.xtf_id
LEFT JOIN orientation_categories oc ON d.orientation_id = oc.id
LEFT JOIN plant_categories pc ON d.plant_category_id = pc.id;
