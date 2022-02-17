from pyteal import *


# Delegatee account local state
# - NumOfTrustees
# - Threshold 
# - Trustee_address: Trustee_approval_status (unapproved: UInt(1), approved: UInt(2))

def approval_program():
    
    on_create = Seq(
        App.globalPut(Bytes("totalApproved"), Int(0)),
        Approve(),
    )


    # Ensure trustee has not approved before
    # get(delegatee_account, key_of_sender_aka_trustee)
    # Note: if the key is not there, UInt(0) is returned so we cannot initialise it as UInt(0) 
    ensure_trustee_unapproved = UInt(1) == App.localGet(Txn.accounts[1], Txn.accounts[0])
    ensure_unapproved = UInt(1) == App.localGet(Txn.accounts[1], Txn.accounts[0])
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
        App.localPut(Txn.accounts[1], Txn.accounts[0], UInt(2)),
        # Store state of new total approved trustees 
        new_num_of_approved_trustees.store(num_of_approved_trustees + Int(1)),
        App.localPut(Txn.accounts[1], Bytes("Approved"), new_num_of_approved_trustees.load()),
        # Update global state if it has been approved
        If(new_num_of_approved_trustees >= threshold),
        Then(App.globalPut(Bytes("totalApproved"), g_approved.load() + Int(1))),
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
        Assert(Txn.application_args[0] <= Txn.accounts.length()),
        # Loop through all the foreign accounts (aka trustees)
        [i.store(Int(1)),
        While(i.load() < Txn.accounts.length()+1 ).Do(Seq([
        # Set Approved state as unapproved UInt(1)
        App.localPut(Txn.accounts[0], Txn.accounts[i], UInt(1)),
        i.store(i.load() + Int(1))
        ]))],
        # Set NumOfTrustees given
        App.localPut(Txn.accounts[0], Bytes("NumOfTrustees"), Txn.accounts.length()),
        # Set Threshold required to approve kfrags 
        App.localPut(Txn.accounts[0], Bytes("Threshold"), Txn.application_args[0]),
        App.localPut(Txn.accounts[0], Bytes("Approved"), UInt(0)),
        Approve(),
    )

    program = Cond(
        [Txn.application_id() == Int(0), on_create],
        [Txn.on_completion() == OnComplete.NoOp, on_call],
        [Txn.on_completion() == OnComplete.OptIn, on_optin],
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
    return Approve()


if __name__ == "__main__":
    with open("fractureDAO.teal", "w") as f:
        compiled = compileTeal(approval_program(), mode=Mode.Application, version=5)
        f.write(compiled)

    with open("auction_clear_state.teal", "w") as f:
        compiled = compileTeal(clear_state_program(), mode=Mode.Application, version=5)
        f.write(compiled)
 
