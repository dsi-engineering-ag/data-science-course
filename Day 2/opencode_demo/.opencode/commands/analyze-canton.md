---
description: Perform a deep-dive energy breakdown for a specified Swiss canton
agent: data-analyst
---

Please analyze the electricity production plants and energy capacity for Canton $ARGUMENTS.

Perform the following steps using Pandas:
1. Filter the dataset `ElectricityProductionPlant.csv` for Canton "$ARGUMENTS".
2. Calculate total power installed (in MW and GW) and count of power plants.
3. Group and aggregate by energy category (`SubCategory_Name` or `MainCategory_Name`).
4. Find the top 3 largest individual facilities in the canton.
5. Provide a summary breakdown table and concise domain insights.
