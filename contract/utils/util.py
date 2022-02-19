import json
import base64
from typing import List, Tuple, Dict, Any, Optional, Union
from ..account import Account

from algosdk.v2client import algod
from algosdk.kmd import KMDClient
from algosdk import account 
from algosdk.future.transaction import *

KMD_ADDRESS = "http://localhost:4002"
KMD_TOKEN = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"

KMD_WALLET_NAME = "unencrypted-default-wallet"
KMD_WALLET_PASSWORD = ""

class PendingTxnResponse:
    def __init__(self, response: Dict[str, Any]) -> None:
        self.poolError: str = response["pool-error"]
        self.txn: Dict[str, Any] = response["txn"]

        self.applicationIndex: Optional[int] = response.get("application-index")
        self.assetIndex: Optional[int] = response.get("asset-index")
        self.closeRewards: Optional[int] = response.get("close-rewards")
        self.closingAmount: Optional[int] = response.get("closing-amount")
        self.confirmedRound: Optional[int] = response.get("confirmed-round")
        self.globalStateDelta: Optional[Any] = response.get("global-state-delta")
        self.localStateDelta: Optional[Any] = response.get("local-state-delta")
        self.receiverRewards: Optional[int] = response.get("receiver-rewards")
        self.senderRewards: Optional[int] = response.get("sender-rewards")

        self.innerTxns: List[Any] = response.get("inner-txns", [])
        self.logs: List[bytes] = [base64.b64decode(l) for l in response.get("logs", [])]

def waitForTransaction(
    client: algod.AlgodClient, txID: str, timeout: int = 10
) -> PendingTxnResponse:
    lastStatus = client.status()
    lastRound = lastStatus["last-round"]
    startRound = lastRound

    while lastRound < startRound + timeout:
        pending_txn = client.pending_transaction_info(txID)

        if pending_txn.get("confirmed-round", 0) > 0:
            return PendingTxnResponse(pending_txn)

        if pending_txn["pool-error"]:
            raise Exception("Pool error: {}".format(pending_txn["pool-error"]))

        lastStatus = client.status_after_block(lastRound + 1)

        lastRound += 1

    raise Exception(
        "Transaction {} not confirmed after {} rounds".format(txID, timeout)
    )

def payAccount(
    client, sender, sender_sk, to: str, amount: int
) -> PendingTxnResponse:
    txn = PaymentTxn(
        sender=sender,
        receiver=to,
        amt=amount,
        sp=client.suggested_params(),
    )
    signedTxn = txn.sign(sender_sk)

    client.send_transaction(signedTxn)
    return waitForTransaction(client, signedTxn.get_txid())


FUNDING_AMOUNT = 100_000_000

def fundAccount(
        funder: Account, client, address: str, amount: int = FUNDING_AMOUNT
) -> PendingTxnResponse:
    return payAccount(client, funder.getAddress(), funder.getPrivateKey(), address, amount)

def create_and_fund_account( client: algod.AlgodClient, funder_sk, amount: int = FUNDING_AMOUNT):
    kmd = KMDClient(KMD_TOKEN, KMD_ADDRESS)
    wallets = kmd.list_wallets()

    for wallet in wallets:
        if wallet["name"] == KMD_WALLET_NAME:
            walletID = wallet["id"]
            break

    if walletID is None:
        raise Exception("Wallet not found: {}".format(KMD_WALLET_NAME))

    walletHandle = kmd.init_wallet_handle(walletID, KMD_WALLET_PASSWORD)
    private_key, address = account.generate_account()
    result = kmd.import_key(walletHandle, private_key)
    fundAccount(Account(funder_sk), client, address, amount)
    new_acc = Account(private_key)
    return address, new_acc.getMnemonic()


def get_accounts():
    kmd = KMDClient(KMD_TOKEN, KMD_ADDRESS)
    wallets = kmd.list_wallets()

    walletID = None
    for wallet in wallets:
        if wallet["name"] == KMD_WALLET_NAME:
            walletID = wallet["id"]
            break

    if walletID is None:
        raise Exception("Wallet not found: {}".format(KMD_WALLET_NAME))

    walletHandle = kmd.init_wallet_handle(walletID, KMD_WALLET_PASSWORD)

    try:
        addresses = kmd.list_keys(walletHandle)
        privateKeys = [
            kmd.export_key(walletHandle, KMD_WALLET_PASSWORD, addr)
            for addr in addresses
        ]
        kmdAccounts = [(addresses[i], privateKeys[i]) for i in range(len(privateKeys))]
    finally:
        kmd.release_wallet_handle(walletHandle)

    return kmdAccounts

def delete_app(client: algod.AlgodClient, app_id: int, addr: str, pk: str):
    # Get suggested params from network
    sp = client.suggested_params()

    # Create the transaction
    txn = ApplicationDeleteTxn(addr, sp, app_id)

    # sign it
    signed = txn.sign(pk)

    # Ship it
    txid = client.send_transaction(signed)

    # await confirmation
    try:
        confirmed_txn = wait_for_confirmation(client, txid, 4)  
    except Exception as err:
        print(err)
        return
    # display results
    print("Transaction information: {}".format(
        json.dumps(confirmed_txn, indent=4)))

    return

def destroy_apps(client: algod.AlgodClient, addr: str, pk:str):
    acct = client.account_info(addr)

    # Delete all apps created by this account
    for app in acct['created-apps']:
        delete_app(client, app['id'], addr, pk)
        
# helper function that formats global state for printing
def format_state(state):
    formatted = {}
    for item in state:
        key = item['key']
        value = item['value']
        try:
            formatted_key = base64.b64decode(key).decode('utf-8')
            if value['type'] == 1:
                # byte string
                if formatted_key == 'voted':
                    formatted_value = base64.b64decode(value['bytes']).decode('utf-8')
                else:
                    formatted_value = value['bytes']
                formatted[formatted_key] = formatted_value
            else:
                # integer
                formatted[formatted_key] = value['uint']
        except Exception:
            print("Not decodable Local States")
            print("key", key)
            print("value", value)

    return formatted

# helper function to read app global state
def read_global_state(client, addr, app_id):
    results = client.account_info(addr)
    apps_created = results['created-apps']
    for app in apps_created:
        if app['id'] == app_id:
            if 'global-state' in app['params']:
                return format_state(app['params']['global-state'])
            return {}
    return {}        

# helper function to read account local state
def read_local_state(client, addr, app_id):
    results = client.account_info(addr)
    local_states = results['apps-local-state']
    for state in local_states:
        if state['id'] == app_id:
            return format_state(state['key-value'])
    return {}        

# helper function to compile program source
def compile_program(client, source_code):
    compile_response = client.compile(source_code)
    return base64.b64decode(compile_response['result'])
