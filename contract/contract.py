from pyteal import *
import os

# Global state 
# - totalApproved (int)

# Local state 
# Delegatee account (6 int)
# - NumOfTrustees (int)
# - Threshold (int) 
# - Trustee_address (max 4): Trustee_approval_status (unapproved: Int(1), approved: Int(2)) (int)

def approval_program():
    
    on_create = Seq(
        App.globalPut(Bytes("totalApproved"), Int(0)),
        Approve(),
    )


    # Ensure trustee has not approved before
    # get(delegatee_account, key_of_sender_aka_trustee)
    # Note: if the key is not there, Int(0) is returned so we cannot initialise it as UInt(0) 
    ensure_trustee_unapproved = Int(1) == App.localGet(Txn.accounts[1], Txn.accounts[0])
    ensure_unapproved = Int(1) == App.localGet(Txn.accounts[1], Txn.accounts[0])
    num_of_approved_trustees = App.localGet(Txn.accounts[1], Bytes("Approved"))
    threshold = App.localGet(Txn.accounts[1], Bytes("Threshold"))
    g_approved = App.globalGet(Bytes("totalApproved"))

    new_num_of_approved_trustees = ScratchVar(TealType.uint64)
    new_g_approved = ScratchVar(TealType.uint64)
    on_req_kfrags = Seq(
        # Ensure there is a target account to apporve for
        Assert(Txn.accounts.length() == Int(1)),
        # Ensure this trustee has not previously approved this account
        Assert(ensure_trustee_unapproved),
        # Ensure this account has not been approved
        Assert(ensure_unapproved),
        # Store state to approve the account
        App.localPut(Txn.accounts[1], Txn.accounts[0], Int(2)),
        # Store state of new total approved trustees 
        new_num_of_approved_trustees.store(num_of_approved_trustees + Int(1)),
        App.localPut(Txn.accounts[1], Bytes("Approved"), new_num_of_approved_trustees.load()),
        # Update global state if it has been approved
        If(new_num_of_approved_trustees.load() >= threshold)
        .Then(App.globalPut(Bytes("totalApproved"), g_approved + Int(1))),
        Approve(),
    )

    on_call = Seq(
        # First, lets fail immediately if this transaction is grouped with any others
        Assert(Global.group_size() == Int(1)), 
        Cond(
            [Txn.application_args[0] == Bytes("reqKfrags"), on_req_kfrags ],
        )
    )

    # OptIn from the delegatee
    # - allows the app to write into their local state
    # - take the Txn.accounts max 4 https://developer.algorand.org/docs/get-details/parameter_tables/?from_query=reference%20#smart-signature-constraints
    i = ScratchVar(TealType.uint64)
    on_optIn = Seq(
        Assert(Txn.accounts.length() > Int(0)),
        # Threshold for approval
        Assert(Btoi(Txn.application_args[0]) <= Txn.accounts.length()),
        # Loop through all the foreign accounts (aka trustees)
        i.store(Int(1)),
        While(i.load() < Txn.accounts.length()+Int(1) ).Do(Seq([
        # Set Approved state as unapproved Int(1)
        App.localPut(Txn.accounts[0], Txn.accounts[i.load()], Int(1)),
        i.store(i.load() + Int(1))
        ])),
        # Set NumOfTrustees given
        App.localPut(Txn.accounts[0], Bytes("NumOfTrustees"), Txn.accounts.length()),
        # Set Threshold required to approve kfrags 
        App.localPut(Txn.accounts[0], Bytes("Threshold"), Btoi(Txn.application_args[0])),
        App.localPut(Txn.accounts[0], Bytes("Approved"), Int(0)),
        Approve(),
    )

    program = Cond(
        [Txn.application_id() == Int(0), on_create],
        [Txn.on_completion() == OnComplete.NoOp, on_call],
        [Txn.on_completion() == OnComplete.OptIn, on_optIn],
        [
            Or(
                Txn.on_completion() == OnComplete.CloseOut,
                Txn.on_completion() == OnComplete.UpdateApplication,
            ),
            Reject(),
        ],
    )

    return compileTeal(program, Mode.Application, version=5)

def clear_state_program():
   program = Approve()
   # Mode.Application specifies that this is a stateful smart contract
   return compileTeal(program, Mode.Application, version=5)

path = os.path.dirname(os.path.abspath(__file__))


# compile program to TEAL assembly
with open(os.path.join(path, "./approval.teal"), "w") as f:
    approval_program_teal = approval_program()
    f.write(approval_program_teal)


    # compile program to TEAL assembly
with open(os.path.join(path, "./clear.teal"), "w") as f:
    clear_state_program_teal = clear_state_program()
    f.write(clear_state_program_teal)
    
print(approval_program())
print(clear_state_program())

