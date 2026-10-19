#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

IMAGE_NAME="opencode-energy-demo"

echo "================================================================================"
echo "⚡ OpenCode Podman Container Launcher"
echo "================================================================================"

# Step 1: Ensure dataset is initialized locally
if [ ! -f "${SCRIPT_DIR}/data/ch.bfe.elektrizitaetsproduktionsanlagen/ElectricityProductionPlant.csv" ]; then
    echo "📦 Initializing local data directory..."
    ./init.sh
fi

# Step 2: Build Podman container image if not already built
echo "🔨 Building Podman container image (${IMAGE_NAME})..."
podman build -t "${IMAGE_NAME}" -f Dockerfile .

# Step 3: Environment & credential defaults
export VERTEX_LOCATION="${VERTEX_LOCATION:-global}"
export GOOGLE_CLOUD_PROJECT="${GOOGLE_CLOUD_PROJECT:-your-gcp-project-id}"
export GOOGLE_APPLICATION_CREDENTIALS="${GOOGLE_APPLICATION_CREDENTIALS:-$HOME/.config/gcloud/opencode-key.json}"

USER_NAME="$(whoami)"

# Ensure user directories exist for mounting
mkdir -p "$HOME/.local/share/opencode" "$HOME/.local/state/opencode" "$HOME/.config/opencode"

echo "🌐 Vertex Location       : ${VERTEX_LOCATION}"
echo "🌐 Google Cloud Project  : ${GOOGLE_CLOUD_PROJECT}"
echo "🔑 Credentials File      : ${GOOGLE_APPLICATION_CREDENTIALS}"
echo "--------------------------------------------------------------------------------"
echo "🚀 Launching OpenCode with Gemini 3.7 Flash..."
echo "--------------------------------------------------------------------------------"

podman run -it --rm \
    --network=host \
    --security-opt=no-new-privileges \
    --cap-drop=ALL \
    -e VERTEX_LOCATION \
    -e GOOGLE_CLOUD_PROJECT \
    -e GOOGLE_APPLICATION_CREDENTIALS \
    -e OPENCODE_MODEL="${OPENCODE_MODEL:-google-vertex/gemini-3.7-flash}" \
    -v "$HOME/.local/share/opencode:/home/${USER_NAME}/.local/share/opencode:z" \
    -v "$HOME/.local/state/opencode:/home/${USER_NAME}/.local/state/opencode:z" \
    -v "$HOME/.config/opencode:/home/${USER_NAME}/.config/opencode:z" \
    -v "${GOOGLE_APPLICATION_CREDENTIALS}:${GOOGLE_APPLICATION_CREDENTIALS}:ro,z" \
    --userns=keep-id \
    -v "${PWD}:${PWD}:z" \
    --workdir "${PWD}" \
    "${IMAGE_NAME}" opencode
