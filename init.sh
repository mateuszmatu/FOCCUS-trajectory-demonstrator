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
echo "🧪 Creating conda environment 'opendrift'..."
conda create -y -n opendrift python=3.14.7
conda activate opendrift

# Install mamba
conda install -y -c conda-forge mamba

### === Install exact packages ===
echo "📦 Installing required packages..."
mamba install -y -c conda-forge \
  ipython \
  ipywidgets==8.0.0 \
  nodejs \
  bokeh==3.10.0 \
  opendrift==1.14.9 \
  jupyter_bokeh==4.1.0 \
  ipykernel jupyter nbformat nbconvert s3fs

### === Register kernel for Jupyter ===
echo "🔗 Registering Jupyter kernel..."
python -m ipykernel install --user --name opendrift --display-name "Python (opendrift)"

### === Download notebook and helper script ===
echo "📥 Downloading notebook and script..."
wget -N https://raw.githubusercontent.com/mateuszmatu/FOCCUS-trajectory-demonstrator/refs/heads/main/main.ipynb
wget -N https://raw.githubusercontent.com/mateuszmatu/FOCCUS-trajectory-demonstrator/refs/heads/main/run_opendrift.py
wget -N https://raw.githubusercontent.com/mateuszmatu/FOCCUS-trajectory-demonstrator/refs/heads/main/Sites_aquaculture.csv
wget -N https://raw.githubusercontent.com/mateuszmatu/FOCCUS-trajectory-demonstrator/refs/heads/main/notebook_code.py

### === Embed kernel metadata ===
echo "⚙️ Embedding kernel metadata into notebook..."
python - <<EOF
import nbformat

nb_path = "main.ipynb"
nb = nbformat.read(open(nb_path), as_version=nbformat.NO_CONVERT)

nb["metadata"]["kernelspec"] = {
    "name": "opendrift",
    "display_name": "Python (opendrift)",
    "language": "python"
}

nbformat.write(nb, open(nb_path, "w"))
EOF

### === Clear notebook output ===
echo "🧼 Clearing cell outputs..."
jupyter nbconvert --clear-output --inplace main.ipynb

echo "✅ Setup complete. You can now open main.ipynb and it will use the 'opendrift' kernel by default."

### === Download input ===

# Make folder
mkdir -p imgs
cd imgs

# Base path to raw files on GitHub
BASE_URL="https://github.com/mateuszmatu/FOCCUS-trajectory-demonstrator/blob/main/imgs"

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