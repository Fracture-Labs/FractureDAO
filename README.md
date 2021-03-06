# FractureDAO

This is part of Fracture Labs DAO specifically for Social Impact funding.

For details please see [dio.earth](https://dio.earth)

## Run Fracture DAO sandbox

Create the sandbox (without fracture_sandbox copied)

```sh
./sanbox up

./deploy.sh
```

which:

Create the sandbox (with fracture*sandbox copied)
\_Issue with M1 Mac*

```sh
./sandbox up
```

## Development Setup

This repo requires Python 3.6 or higher. We recommend you use a Python virtual environment to install
the required dependencies.

Set up venv (one time):

- `python3 -m venv .venv`

Active venv:

- `. .venv/bin/activate` (if your shell is bash/zsh)
- `. .venv/bin/activate.fish` (if your shell is fish)

Install:

```sh
# use the following install latest release of pyteal
pip3 install pyteal
# install the Algorand python SDK
pip3 install py-algorand-sdk
```

Using Python to run E2E:

```sh
# compiles the contracts
python3 -m contract.contract
# Deploy and set up wot and approvals
python3 -m contract.deploy
```
