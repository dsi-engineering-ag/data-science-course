"""Swiss Electricity Production Plants (BFE/SFOE) - Pandas Data Helper

This module provides utility functions to load, join, and analyze the Swiss Federal
Office of Energy electricity production plants dataset.
"""

from pathlib import Path
from typing import Dict, Optional, Union
import pandas as pd


def get_data_dir() -> Path:
    """Finds the dataset directory by checking possible locations."""
    candidates = [
        Path(__file__).resolve().parent / "data" / "ch.bfe.elektrizitaetsproduktionsanlagen",
        Path(__file__).resolve().parent / "data",
        Path("/data/ch.bfe.elektrizitaetsproduktionsanlagen"),
        Path("/data"),
        Path.cwd() / "data" / "ch.bfe.elektrizitaetsproduktionsanlagen",
        Path.cwd() / "data",
        Path(__file__).resolve().parent.parent.parent / "data" / "ch.bfe.elektrizitaetsproduktionsanlagen",
        Path.cwd().parent / "data" / "ch.bfe.elektrizitaetsproduktionsanlagen",
        Path.cwd().parent.parent / "data" / "ch.bfe.elektrizitaetsproduktionsanlagen",
    ]
    for p in candidates:
        if p.exists() and (p / "ElectricityProductionPlant.csv").exists():
            return p
    raise FileNotFoundError("Could not locate 'ElectricityProductionPlant.csv' in any expected data directory.")


def load_catalogues(lang: str = "en") -> Dict[str, pd.DataFrame]:
    """Loads all catalogue mapping CSVs (MainCategory, SubCategory, PlantCategory, Orientation).

    Args:
        lang: Preferred language column to alias ('en', 'de', 'fr', 'it'). Defaults to 'en'.

    Returns:
        Dictionary of catalogue dataframes keyed by catalogue name.
    """
    data_dir = get_data_dir()
    catalogues = {}
    cat_files = {
        "main_category": "MainCategoryCatalogue.csv",
        "sub_category": "SubCategoryCatalogue.csv",
        "plant_category": "PlantCategoryCatalogue.csv",
        "orientation": "OrientationCatalogue.csv",
    }

    for key, filename in cat_files.items():
        filepath = data_dir / filename
        if filepath.exists():
            df = pd.read_csv(filepath)
            df.columns = [c.strip() for c in df.columns]
            catalogues[key] = df

    return catalogues


def load_plants(
    join_catalogues: bool = True,
    lang: str = "en",
    parse_dates: bool = True,
    low_memory: bool = False,
) -> pd.DataFrame:
    """Loads the main ElectricityProductionPlant.csv dataset with optional catalogue enrichment.

    Args:
        join_catalogues: Whether to merge descriptive labels for main, sub, and plant categories.
        lang: Language for descriptive labels ('en', 'de', 'fr', 'it').
        parse_dates: Parse 'BeginningOfOperation' as datetime and extract year.
        low_memory: Passed to pd.read_csv.

    Returns:
        Enriched pandas DataFrame of power plants.
    """
    data_dir = get_data_dir()
    plants_path = data_dir / "ElectricityProductionPlant.csv"
    df = pd.read_csv(plants_path, low_memory=low_memory)

    # Standardize column types
    df["TotalPower_kW"] = pd.to_numeric(df["TotalPower"], errors="coerce")
    df["TotalPower_MW"] = df["TotalPower_kW"] / 1000.0
    df["TotalPower_GW"] = df["TotalPower_kW"] / 1_000_000.0

    if parse_dates and "BeginningOfOperation" in df.columns:
        df["BeginningOfOperation"] = pd.to_datetime(df["BeginningOfOperation"], errors="coerce")
        df["CommissioningYear"] = df["BeginningOfOperation"].dt.year

    if join_catalogues:
        cats = load_catalogues(lang=lang)

        # Merge Main Category
        if "main_category" in cats and "MainCategory" in df.columns:
            m_cat = cats["main_category"][["Catalogue_id", lang]].rename(
                columns={"Catalogue_id": "MainCategory", lang: "MainCategory_Name"}
            )
            df = df.merge(m_cat, on="MainCategory", how="left")

        # Merge Sub Category
        if "sub_category" in cats and "SubCategory" in df.columns:
            s_cat = cats["sub_category"][["Catalogue_id", lang]].rename(
                columns={"Catalogue_id": "SubCategory", lang: "SubCategory_Name"}
            )
            df = df.merge(s_cat, on="SubCategory", how="left")

        # Merge Plant Category
        if "plant_category" in cats and "PlantCategory" in df.columns:
            p_cat = cats["plant_category"][["Catalogue_id", lang]].rename(
                columns={"Catalogue_id": "PlantCategory", lang: "PlantCategory_Name"}
            )
            df = df.merge(p_cat, on="PlantCategory", how="left")

    return df


def load_plant_details(
    join_catalogues: bool = True,
    lang: str = "en",
    low_memory: bool = False,
) -> pd.DataFrame:
    """Loads the sub-unit PlantDetail.csv dataset (solar panel details, inclinations, orientations).

    Args:
        join_catalogues: Whether to merge descriptive labels for plant categories and orientations.
        lang: Language for labels ('en', 'de', 'fr', 'it').
        low_memory: Passed to pd.read_csv.

    Returns:
        DataFrame of plant sub-unit details.
    """
    data_dir = get_data_dir()
    details_path = data_dir / "PlantDetail.csv"
    df = pd.read_csv(details_path, low_memory=low_memory)

    df["Power_kW"] = pd.to_numeric(df["Power"], errors="coerce")
    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")

    if join_catalogues:
        cats = load_catalogues(lang=lang)

        if "plant_category" in cats and "PlantCategory" in df.columns:
            p_cat = cats["plant_category"][["Catalogue_id", lang]].rename(
                columns={"Catalogue_id": "PlantCategory", lang: "PlantCategory_Name"}
            )
            df = df.merge(p_cat, on="PlantCategory", how="left")

        if "orientation" in cats and "Orientation" in df.columns:
            o_cat = cats["orientation"][["Catalogue_id", lang]].rename(
                columns={"Catalogue_id": "Orientation", lang: "Orientation_Name"}
            )
            df = df.merge(o_cat, on="Orientation", how="left")

    return df


def get_dataset_kpis(df: Optional[pd.DataFrame] = None) -> Dict[str, Union[int, float]]:
    """Calculates top-level KPI metrics across the plant dataset."""
    if df is None:
        df = load_plants(join_catalogues=False)

    total_plants = len(df)
    total_power_kw = df["TotalPower_kW"].sum()
    total_power_mw = df["TotalPower_MW"].sum()
    total_power_gw = df["TotalPower_GW"].sum()
    total_cantons = df["Canton"].dropna().nunique()

    return {
        "total_plants": total_plants,
        "total_power_kw": round(total_power_kw, 2),
        "total_power_mw": round(total_power_mw, 2),
        "total_power_gw": round(total_power_gw, 3),
        "total_cantons": total_cantons,
    }


def get_canton_energy_summary(
    df: Optional[pd.DataFrame] = None,
    canton: Optional[str] = None,
    lang: str = "en",
) -> pd.DataFrame:
    """Summarizes installed power and plant count grouped by Canton and SubCategory.

    Args:
        df: Optional preloaded plants DataFrame.
        canton: Optional 2-letter Canton code (e.g. 'ZH', 'VS', 'BE') to filter.
        lang: Language for subcategory names.

    Returns:
        Summary DataFrame sorted by TotalPower_MW descending.
    """
    if df is None:
        df = load_plants(join_catalogues=True, lang=lang)

    if canton:
        df = df[df["Canton"].str.upper() == canton.upper()]

    group_cols = ["Canton", "SubCategory_Name"] if "SubCategory_Name" in df.columns else ["Canton", "SubCategory"]
    summary = (
        df.groupby(group_cols, as_index=False)
        .agg(
            PlantCount=("xtf_id", "count"),
            TotalPower_MW=("TotalPower_MW", "sum"),
            AvgPower_kW=("TotalPower_kW", "mean"),
        )
        .sort_values(by=["Canton", "TotalPower_MW"], ascending=[True, False])
    )
    summary["TotalPower_MW"] = summary["TotalPower_MW"].round(2)
    summary["AvgPower_kW"] = summary["AvgPower_kW"].round(1)
    return summary


def get_solar_trend(
    df: Optional[pd.DataFrame] = None,
    min_year: int = 2000,
    max_year: int = 2024,
) -> pd.DataFrame:
    """Computes yearly photovoltaic additions (count and cumulative installed capacity in MW)."""
    if df is None:
        df = load_plants(join_catalogues=True)

    # Filter for Photovoltaic (subcat_2)
    solar = df[df["SubCategory"] == "subcat_2"].copy()
    solar = solar[(solar["CommissioningYear"] >= min_year) & (solar["CommissioningYear"] <= max_year)]

    trend = (
        solar.groupby("CommissioningYear")
        .agg(
            NewPlants=("xtf_id", "count"),
            NewCapacity_MW=("TotalPower_MW", "sum"),
        )
        .reset_index()
    )
    trend["CumulativeCapacity_MW"] = trend["NewCapacity_MW"].cumsum().round(2)
    trend["NewCapacity_MW"] = trend["NewCapacity_MW"].round(2)
    trend["CommissioningYear"] = trend["CommissioningYear"].astype(int)
    return trend
