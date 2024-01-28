from bitcoinrpc.authproxy import AuthServiceProxy
import requests
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import plotly.graph_objects as go

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

missing_settings = [setting for setting in required_settings if setting not in settings or not settings[setting]]

if missing_settings:
    print(f"Error: The following settings are missing or empty in settings.yaml: {', '.join(missing_settings)}")
    exit(1)

# Initialize settings
rpc_user = settings['rpc_user']
rpc_password = settings['rpc_password']
rpc_host = settings['rpc_host']
rpc_port = "8332"
api_key = settings['api_key']
address_to_search = settings['address_to_search']
output_path = settings['output_path']

try:
    # Initialize the RPC connection
    if rpc_user == "":
        rpc_connection = AuthServiceProxy(f"http://{rpc_host}:{rpc_port}")
    else:
        rpc_connection = AuthServiceProxy(f"http://{rpc_user}:{rpc_password}@{rpc_host}:{rpc_port}")

    # Test the RPC connection
    rpc_connection.getblockcount()
except Exception as e:
    print(f"Error: Unable to connect to the RPC server: {e}")
    exit(1)

# Maintain a list of addresses connected to the address to search
addresses = [address_to_search]

# Prepare a DataFrame to store the results
df = pd.DataFrame(columns=['Transaction ID', 'Type', 'Amount (BTC)', 'Address', 'Balance (BTC)'])
balance = 0

# Iterate over each block
for block_number in range(block_count + 1):
    # Get the block hash
    block_hash = rpc_connection.getblockhash(block_number)
    # Get the block based on its hash
    block = rpc_connection.getblock(block_hash)
    # Iterate over each transaction in the block
    for txid in block['tx']:
        # Get the transaction details
        tx = rpc_connection.getrawtransaction(txid, 1)
        # Check each input and output in the transaction
        for vin in tx['vin']:
            if 'addr' in vin and vin['addr'] == address_to_search:
                balance -= vin['value']
                df = df.append({'Transaction ID': txid, 'Type': 'Withdrawal', 'Amount (BTC)': vin['value'], 'Address': vin['addr'], 'Balance (BTC)': balance}, ignore_index=True)
                # Add the address to the list of addresses connected to the address to search
                addresses.append(vin['addr'])
        for vout in tx['vout']:
            if 'addresses' in vout['scriptPubKey'] and address_to_search in vout['scriptPubKey']['addresses']:
                balance += vout['value']
                df = df.append({'Transaction ID': txid, 'Type': 'Deposit', 'Amount (BTC)': vout['value'], 'Address': vout['scriptPubKey']['addresses'][0], 'Balance (BTC)': balance}, ignore_index=True)
                # Add the address to the list of addresses connected to the address to search
                addresses.append(vout['scriptPubKey']['addresses'][0])

# Prepare a DataFrame to store the API results
df_api = pd.DataFrame(columns=['Address', 'Balance', 'Received', 'Sent'])

if api_key == "":
    print("Warning: API key is empty, skipping API call")
else:
    # Iterate over each address
    for address in addresses:
        # Use the Bitcoin Who's Who API to get information about the address
        response = requests.get(f"https://www.bitcoinwhoswho.com/api/url/{address}?api_key={api_key}")
        
        # Check if the API call was successful
        if response.status_code != 200:
            print(f"Error: API call failed with status code {response.status_code}")
            continue
        data = response.json()

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

    # Save the API data DataFrame
    fig, ax = plt.subplots()
    ax.axis('tight')
    ax.axis('off')
    ax.table(cellText=df_api.values, colLabels=df_api.columns, cellLoc = 'center', loc='center')
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