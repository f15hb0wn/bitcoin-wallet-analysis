from bitcoinrpc.authproxy import AuthServiceProxy
import bitcoinrpc
from tqdm import tqdm
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import plotly.graph_objects as go
import datetime

# Load settings from the settings.yaml file
import yaml
with open("settings.yaml", 'r') as stream:
    try:
        settings = yaml.safe_load(stream)
    except yaml.YAMLError as exc:
        print(exc)
        exit(1)
# Verify all settings exist in settings.yaml
required_settings = ['rpc_user', 'rpc_password', 'rpc_host', 'api_key', 'address_to_search', 'output_path']

missing_settings = [setting for setting in required_settings if setting not in settings]

if missing_settings:
    print(f"Error: The following settings are missing or empty in settings.yaml: {', '.join(missing_settings)}")
    exit(1)

# Initialize settings
rpc_user = settings['rpc_user']
rpc_password = settings['rpc_password']
rpc_host = settings['rpc_host']
rpc_port = "8332"
address_to_search = settings['address_to_search']
output_path = settings['output_path']

try:
    rpc_connection = AuthServiceProxy(f"http://{rpc_user}:{rpc_password}@{rpc_host}:{rpc_port}")
    # Test the RPC connection
    block_count = rpc_connection.getblockcount()
except Exception as e:
    print(f"Error: Unable to connect to the RPC server: {e}")
    exit(1)
print(f"Connected to the RPC server at {rpc_host}")

# Maintain a list of addresses connected to the address to search
addresses = [address_to_search]

# Prepare a DataFrame to store the results
df = pd.DataFrame(columns=['Transaction ID', 'Type', 'Amount (BTC)', 'Address', 'Balance (BTC)', 'Time'])

balance = 0

print("Analyzing the blockchain...")
# Create a progress bar
progress_bar = tqdm(total=block_count, desc="Progress", unit="block")
# Iterate over each block
for block_number in range(block_count + 1):
    progress_bar.update(1)
    # Get the block hash
    block_hash = rpc_connection.getblockhash(block_number)
    # Get the block based on its hash
    try:
        block = rpc_connection.getblock(block_hash)
    except bitcoinrpc.authproxy.JSONRPCException as e:
        continue  # Skip this block and continue with the next one
    # Iterate over each transaction in the block
    for txid in block['tx']:
        # Get the transaction details
        try:
            tx = rpc_connection.getrawtransaction(txid, 1, block_hash)
        except bitcoinrpc.authproxy.JSONRPCException as e:
            continue  # Skip this transaction and continue with the next one
        # Check each input and output in the transaction
        for vin in tx['vin']:
            if 'addr' in vin and vin['addr'] == address_to_search:
                balance -= vin['value']
                df = df.append({
                    'Transaction ID': txid,
                    'Type': 'Withdrawal',
                    'Amount (BTC)': vin['value'],
                    'Address': vin['addr'],
                    'Balance (BTC)': balance,
                    'Time': datetime.fromtimestamp(tx['time']).strftime('%Y-%m-%d %H:%M:%S')  # Convert the Unix timestamp to a human-readable format
                }, ignore_index=True)
                # Add the address to the list of addresses connected to the address to search
                addresses.append(vin['addr'])
        for vout in tx['vout']:
            if 'addresses' in vout['scriptPubKey'] and address_to_search in vout['scriptPubKey']['addresses']:
                balance += vout['value']
                df = df.append({
                    'Transaction ID': txid,
                    'Type': 'Deposit',
                    'Amount (BTC)': vout['value'],
                    'Address': vout['scriptPubKey']['addresses'][0],
                    'Balance (BTC)': balance,
                    'Time': datetime.fromtimestamp(tx['time']).strftime('%Y-%m-%d %H:%M:%S')  # Convert the Unix timestamp to a human-readable format
                }, ignore_index=True)
                # Add the address to the list of addresses connected to the address to search
                addresses.append(vout['scriptPubKey']['addresses'][0])
# Close the progress bar
progress_bar.close()

# Prepare data for the Sankey diagram
source = []
target = []
value = []

for i, row in df.iterrows():
    if row['Type'] == 'Deposit':
        source.append(row['Address'])
        target.append(address_to_search)
        value.append(row['Amount (BTC)'])
    else:  # Withdrawal
        source.append(address_to_search)
        target.append(row['Address'])
        value.append(row['Amount (BTC)'])

# Create the Sankey diagram
fig = go.Figure(data=[go.Sankey(
    node=dict(
        pad=15,
        thickness=20,
        line=dict(color="black", width=0.5),
        label=source + target,
        color="blue"
    ),
    link=dict(
        source=source,
        target=target,
        value=value
    )
)])

# Save the data to PDF
with PdfPages(f'{output_path}/{address_to_search}.pdf') as pdf:
    # Save the transactions DataFrame
    fig, ax = plt.subplots()
    ax.axis('tight')
    ax.axis('off')
    ax.table(cellText=df.values, colLabels=df.columns, cellLoc = 'center', loc='center')
    pdf.savefig(fig, bbox_inches='tight')

    # Save the Sankey diagram
    fig = go.Figure(data=[go.Sankey(
        node=dict(
            pad=15,
            thickness=20,
            line=dict(color="black", width=0.5),
            label=source + target,
            color="blue"
        ),
        link=dict(
            source=source,
            target=target,
            value=value
        )
    )])
    pdf.savefig(fig, bbox_inches='tight')

print(f"Done! The results have been saved to {output_path}/{address_to_search}.pdf")