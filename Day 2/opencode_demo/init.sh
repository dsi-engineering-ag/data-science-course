#!/usr/bin/env bash
set -e

# Determine script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_DATA_DIR="${SCRIPT_DIR}/data/ch.bfe.elektrizitaetsproduktionsanlagen"

echo "================================================================================"
echo "⚡ OpenCode Demo: Initializing Local Dataset"
echo "================================================================================"

# Candidates for source dataset
SOURCE_CANDIDATES=(
    "${SCRIPT_DIR}/../../data/ch.bfe.elektrizitaetsproduktionsanlagen"
    "${SCRIPT_DIR}/../data/ch.bfe.elektrizitaetsproduktionsanlagen"
    "/data/ch.bfe.elektrizitaetsproduktionsanlagen"
    "${SCRIPT_DIR}/../../data"
)

SOURCE_DIR=""
for candidate in "${SOURCE_CANDIDATES[@]}"; do
    if [ -f "${candidate}/ElectricityProductionPlant.csv" ]; then
        SOURCE_DIR="${candidate}"
        break
    fi
done

if [ -z "${SOURCE_DIR}" ]; then
    echo "❌ Error: Could not find source electricity data in any candidate directory."
    echo "   Searched paths:"
    for candidate in "${SOURCE_CANDIDATES[@]}"; do
        echo "   - ${candidate}"
    done
    exit 1
fi

echo "📁 Found source dataset at: ${SOURCE_DIR}"
echo "📁 Creating target folder : ${TARGET_DATA_DIR}"

mkdir -p "${TARGET_DATA_DIR}"

echo "📋 Copying CSV files into container workspace..."
cp -v "${SOURCE_DIR}"/*.csv "${TARGET_DATA_DIR}/"

echo "--------------------------------------------------------------------------------"
echo "✅ Data initialization complete!"
echo "   Copied files:"
ls -lh "${TARGET_DATA_DIR}"
echo "================================================================================"
