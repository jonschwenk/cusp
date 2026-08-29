# Installation

You do not need to install CUSP in order to use the dataset; you may just
download it directly from the [Download CUSP](release-products.md) page.
However, the CUSP repository contains a number of
[command-line tools](../user/cli-examples.md) that may be useful to you.

CUSP cannot be downloaded from conda or pip. To use the tools, clone the GitHub
repository and create the conda environment from the included environment file.
The supported package requires Python 3.11 or newer; the environment file
installs a compatible Python version.

```bash
git clone https://github.com/jonschwenk/cusp.git
cd cusp
conda env create -f environment.yml
conda activate cusp
python -m pip install -e .
```

The editable install makes the CUSP command modules available while you work
in the checkout. Run rebuild and release commands from the repository root
because those workflows use repository data and configuration files.

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
