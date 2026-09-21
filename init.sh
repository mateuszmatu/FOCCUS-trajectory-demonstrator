#!/bin/bash
set -euxo pipefail

trap 'echo "ERROR: init.sh failed at line $LINENO"' ERR

cd /home/onyxia/work

echo "USER=$(whoami)"
echo "HOME=$HOME"
echo "PWD=$(pwd)"

### === Install Miniforge (user-local) ===
MINIFORGE=Miniforge3-Linux-x86_64.sh
INSTALL_DIR=$HOME/miniforge3

echo "🔧 Installing Miniforge..."
wget https://github.com/conda-forge/miniforge/releases/latest/download/$MINIFORGE -O $MINIFORGE
bash $MINIFORGE -b -p $INSTALL_DIR
rm $MINIFORGE

# Enable conda commands in this shell
source $INSTALL_DIR/etc/profile.d/conda.sh

### === Create and activate environment ===
echo "🧪 Creating conda environment 'OpenDrift'..."
cd OpenDrift
conda env create -f environment.yml
conda activate opendrift
pip install --no-deps -e .

# Install mamba
conda install -y -c conda-forge mamba

### === Install exact packages ===
echo "📦 Installing additional packages..."
mamba install -y -c conda-forge \
    bohek

### === Register kernel for Jupyter ===
echo "🔗 Registering Jupyter kernel..."
python -m ipykernel install --user --name opendrift --display-name "Python (opendrift)"

### === Download notebook and helper script ===
echo "📥 Downloading notebook and script..."
wget -N https://raw.githubusercontent.com/mateuszmatu/FOCCUS-trajectory-demonstrator/refs/heads/main/main.ipynb
wget -N https://raw.githubusercontent.com/mateuszmatu/FOCCUS-trajectory-demonstrator/refs/heads/main/run_opendrift.py

### === Embed kernel metadata ===
echo "⚙️ Embedding kernel metadata into notebook..."
python - <<EOF
import nbformat

nb_path = "main.ipynb"
nb = nbformat.read(open(nb_path), as_version=nbformat.NO_CONVERT)

nb["metadata"]["kernelspec"] = {
    "name": "foccus_ospar",
    "display_name": "Python (foccus_ospar)",
    "language": "python"
}

nbformat.write(nb, open(nb_path, "w"))
EOF

### === Clear notebook output ===
echo "🧼 Clearing cell outputs..."
jupyter nbconvert --clear-output --inplace main.ipynb

echo "✅ Setup complete. You can now open main.ipynb and it will use the 'foccus_ospar' kernel by default."

### === Download input ===

# Make folder
mkdir -p imgs
cd imgs

# Base path to raw files on GitHub
BASE_URL="https://github.com/mateuszmatu/FOCCUS-trajectory-demonstrator/imgs"

# List of files to download
FILES=(
  FOCCUS_LOGO.jpg
)

# Download each file
for file in "${FILES[@]}"; do
  echo "Downloading $file..."
  wget -nc "$BASE_URL/$file"
done

cd ..