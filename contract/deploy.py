import json
import os

from algosdk.future.transaction import *
from algosdk.v2client import algod
from algosdk import mnemonic
from pyteal import *
from .utils.util import  *

# user declared algod connection parameters. Node must have EnableDeveloperAPI set to true in its config
algod_address = "http://localhost:4001"
algod_token = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"

    
# create new application
def create_app(client,  approval_program, clear_program, global_schema, local_schema, sender, sk):

    # declare on_complete as NoOp
    on_complete = OnComplete.NoOpOC.real

	# get node suggested parameters
    params = client.suggested_params()

    # create unsigned transaction
    txn = ApplicationCreateTxn(sender, params, on_complete, \
                                            approval_program, clear_program, \
                                            global_schema, local_schema)

    # sign transaction
    signed_txn = txn.sign(sk)
    tx_id = signed_txn.transaction.get_txid()

    # send transaction
    client.send_transactions([signed_txn])

    # await confirmation
    #wait_for_confirmation(client, tx_id, 20)
    # wait for confirmation 
    try:
        confirmed_txn = wait_for_confirmation(client, tx_id, 4)  
    except Exception as err:
        print(err)
        return
    
    # display results
    print("Transaction information: {}".format(
        json.dumps(confirmed_txn, indent=4)))
        
    transaction_response = client.pending_transaction_info(tx_id)
    app_id = transaction_response['application-index']
    print("Created new app-id:", app_id)

    return app_id

# call application
def new_wot(client, index, threshold, list_of_trustees, delegatee, delegatee_sk) : 
	# get node suggested parameters
    params = client.suggested_params()

    txn = ApplicationOptInTxn(delegatee, params, index, [threshold], list_of_trustees)

    # sign transaction
    signed_txn = txn.sign(delegatee_sk)
    tx_id = signed_txn.transaction.get_txid()

    # send transaction
    client.send_transactions([signed_txn])

    # await confirmation
    try:
        confirmed_txn = wait_for_confirmation(client, tx_id, 4)  
    except Exception as err:
        print(err)
        return
    # display results
    print("Transaction information: {}".format(
        json.dumps(confirmed_txn, indent=4)))
    
    print("Web of Trust created")

def req_kfrags(client, index, delegatee, trustee, trustee_sk) :

	# get node suggested parameters
    params = client.suggested_params()

    txn = ApplicationNoOpTxn(trustee, params, index, ["reqKfrags"], [delegatee])

    # sign transaction
    signed_txn = txn.sign(trustee_sk)
    tx_id = signed_txn.transaction.get_txid()

    # send transaction
    client.send_transactions([signed_txn])

    # await confirmation
    try:
        confirmed_txn = wait_for_confirmation(client, tx_id, 4)  
    except Exception as err:
        print(err)
        return
    # display results
    print("Transaction information: {}".format(
        json.dumps(confirmed_txn, indent=4)))
    


def main() :
    # initialize an algodClient
    algod_client = algod.AlgodClient(algod_token, algod_address)

    # declare application state storage (immutable)
    local_ints = 6
    local_bytes = 0
    global_ints = 1 
    global_bytes = 0
    global_schema = StateSchema(global_ints, global_bytes)
    local_schema = StateSchema(local_ints, local_bytes)

    path = os.path.dirname(os.path.abspath(__file__))

    admin, admin_sk = get_accounts()[0]
    funder, funder_sk = get_accounts()[1]

    # compile program to TEAL assembly
    with open(os.path.join(path, "./approval.teal"), "r") as f:
        approval_program_teal = f.read()


    # compile program to TEAL assembly
    with open(os.path.join(path, "./clear.teal"), "r") as f:
        clear_state_program_teal = f.read()

    # compile program to binary
    approval_program_compiled = compile_program(algod_client, approval_program_teal)
            
    # compile program to binary
    clear_state_program_compiled = compile_program(algod_client, clear_state_program_teal)

    print("--------------------------------------------")
    print("Deploying Fracture DAO ......")
    
    # create new application
    app_id = create_app(algod_client, approval_program_compiled, clear_state_program_compiled, global_schema, local_schema, admin, admin_sk)

    print("Global state:", read_global_state(algod_client, admin, app_id))

    print("Creating and funding Accounts...")
    freddie, freddie_sk = create_and_fund_account(algod_client, funder_sk)
    trustee0, trustee0_sk = create_and_fund_account(algod_client, funder_sk)
    trustee1, trustee1_sk = create_and_fund_account(algod_client, funder_sk)
    trustee2, trustee2_sk = create_and_fund_account(algod_client, funder_sk)
    print("Accounts funded!")

    
main()
