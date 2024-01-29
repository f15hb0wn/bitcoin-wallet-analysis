# bitcoin-wallet-analysis
Python project to analyze transactions and reputation of a Bitcoin wallet. 

# Requirements
1) Access to a Bitcoin Core RPC server. It can be downloaded locally at https://bitcoin.org/en/download. Downloading the ledger will take 7-10GB of local disk space if pruning is enabled. Otherwise, it can be over 300GB.
2) Enable RPC server on Botcoin Core RPC server. `bitcoin.conf.example` example configuration is included.
3) Copy `settings.yaml.example` to `settings.yaml` and set variables
4) Install requirements.txt (`pip install -r requirements.txt`)

# Operation
- After updating `settings.yaml`, run `python3 analyze.py`. This will search all transactions in the Bitcoin ledger connected to the Bitcoin wallet set as `address_to_search`.
- All detected wallet addresses will be analyzed on Bitcoinwhoswho.com if a valid api key is provided.
- Results will be saved as transactions.pdf in the `output_path`.
