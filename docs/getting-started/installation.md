# Installation

You do not need to install CUSP in order to use the dataset; you may just
download it directly from the [release products](release-products.md) page.
However, the CUSP repository contains a number of
[command-line tools](../user/cli-examples.md) that may be useful to you.

CUSP cannot be downloaded from conda or pip. To use the tools, clone the GitHub
repository and create the conda environment from the included environment file.

```bash
git clone https://github.com/jonschwenk/cusp.git
cd cusp
conda env create -f environment.yml
conda activate cusp
```

After activating the environment, run CUSP commands from the repository root.

```bash
python -m cusp.build --help
python -m cusp.aggregate --help
python -m cusp.features --help
```

Feature sampling also requires a Google Earth Engine account and local Earth
Engine authentication.

```bash
earthengine authenticate
```
