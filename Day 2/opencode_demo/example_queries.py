#!/usr/bin/env python3
"""Example Pandas Queries on Swiss Electricity Production Data

Run this script directly to test and view analytical outputs:
    python example_queries.py
"""

from energy_data import (
    load_plants,
    load_plant_details,
    get_dataset_kpis,
    get_canton_energy_summary,
    get_solar_trend,
)


def run_demo():
    print("=" * 80)
    print("⚡ SWISS ELECTRICITY PRODUCTION DATA - PANDAS DEMO")
    print("=" * 80)

    print("\n1. Loading dataset and calculating key metrics...")
    df = load_plants(join_catalogues=True, lang="en")
    kpis = get_dataset_kpis(df)
    print(f"   • Total registered plants: {kpis['total_plants']:,}")
    print(f"   • Total installed capacity: {kpis['total_power_gw']:,.2f} GW ({kpis['total_power_mw']:,.1f} MW)")
    print(f"   • Covered cantons: {kpis['total_cantons']}")

    print("\n2. Breakdown by Energy Subcategory across Switzerland:")
    cat_summary = (
        df.groupby("SubCategory_Name")
        .agg(
            Plants=("xtf_id", "count"),
            Total_MW=("TotalPower_MW", "sum"),
            Share_Pct=("TotalPower_MW", lambda x: (x.sum() / df["TotalPower_MW"].sum()) * 100),
        )
        .sort_values(by="Total_MW", ascending=False)
        .round({"Total_MW": 1, "Share_Pct": 2})
    )
    print(cat_summary.to_string())

    print("\n3. Top 5 Cantons by Total Installed Capacity:")
    top_cantons = (
        df.groupby("Canton")
        .agg(
            Plants=("xtf_id", "count"),
            Total_MW=("TotalPower_MW", "sum"),
            Total_GW=("TotalPower_GW", "sum"),
        )
        .sort_values(by="Total_MW", ascending=False)
        .head(5)
        .round({"Total_MW": 1, "Total_GW": 2})
    )
    print(top_cantons.to_string())

    print("\n4. Canton Valais (VS) Energy Mix:")
    vs_summary = get_canton_energy_summary(df, canton="VS")
    print(vs_summary.to_string(index=False))

    print("\n5. Canton Zurich (ZH) Energy Mix:")
    zh_summary = get_canton_energy_summary(df, canton="ZH")
    print(zh_summary.to_string(index=False))

    print("\n6. Solar (PV) Growth Trend (Recent 5 years):")
    solar_trend = get_solar_trend(df, min_year=2019, max_year=2024)
    print(solar_trend.to_string(index=False))

    print("\n7. Top 5 Largest Individual Power Plants:")
    top_plants = (
        df[["Address", "Municipality", "Canton", "SubCategory_Name", "CommissioningYear", "TotalPower_MW"]]
        .sort_values(by="TotalPower_MW", ascending=False)
        .head(5)
    )
    print(top_plants.to_string(index=False))

    print("\n8. Plant Details Sample (Solar Panel Orientations):")
    details_df = load_plant_details(join_catalogues=True, lang="en")
    orient_summary = (
        details_df.groupby("Orientation_Name")
        .agg(
            Count=("xtf_id", "count"),
            Total_kW=("Power_kW", "sum"),
            Avg_Tilt_Deg=("Inclination", "mean"),
        )
        .sort_values(by="Total_kW", ascending=False)
        .round({"Total_kW": 1, "Avg_Tilt_Deg": 1})
    )
    print(orient_summary.to_string())

    print("\n" + "=" * 80)
    print("✅ All queries executed successfully!")
    print("=" * 80)


if __name__ == "__main__":
    run_demo()
