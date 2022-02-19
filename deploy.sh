#!/usr/bin/env bash

python3 -m venv .venv
. .venv/bin/activate
pip3 install pyteal
pip3 install py-algorand-sdk
python3 -m contract.contract
python3 -m contract.deploy
