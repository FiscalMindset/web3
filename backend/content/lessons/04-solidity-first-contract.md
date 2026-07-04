---
title: Solidity — Your First Contract
module: Module 2 · Smart Contracts
order: 4
minutes: 30
---

# Solidity — Your First Contract

Solidity is the C++-flavoured language of the EVM. Contracts look like classes, but there's a twist: **deployed code is immutable and every bug is permanent and public**. We write differently here.

## The classic: a counter

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

contract Counter {
    uint256 public count;          // auto-generates a count() getter
    address public owner;

    event Incremented(address indexed by, uint256 newCount);

    constructor() {
        owner = msg.sender;        // whoever deploys becomes owner
    }

    function increment() external {
        count += 1;                // 0.8+ reverts on overflow automatically
        emit Incremented(msg.sender, count);
    }

    function reset() external {
        require(msg.sender == owner, "only owner");
        count = 0;
    }
}
```

Press **Run** on the block above — it compiles with the real `solc` compiler in your workspace and produces the ABI + bytecode that would be deployed on-chain.

## The pieces that matter

- **`msg.sender`** — who called this function. The bedrock of all access control.
- **`require(cond, "msg")`** — revert the entire transaction if false. State rolls back like it never happened.
- **`event`** — cheap, indexed logs. Frontends and indexers listen to these; contracts cannot read them.
- **`public` state** — everything on-chain is readable by everyone anyway; `private` only hides the getter, not the data.

## Value types you'll use daily

| Type | Notes |
|---|---|
| `uint256` | The native word size. Use it unless you're packing storage. |
| `address` / `address payable` | 20 bytes. `payable` can receive ETH. |
| `bytes32` | Fixed 32 bytes — hashes, IDs. Cheaper than `string`. |
| `mapping(K => V)` | Hash table. No iteration, no length — by design. |
| `struct` | Group fields; combine with mappings for records. |

## Payable functions & receiving ETH

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

contract PiggyBank {
    mapping(address => uint256) public deposits;

    function deposit() external payable {
        require(msg.value > 0, "send some wei");
        deposits[msg.sender] += msg.value;
    }

    function withdraw() external {
        uint256 amount = deposits[msg.sender];
        require(amount > 0, "nothing to withdraw");
        deposits[msg.sender] = 0;                    // ← effects BEFORE interaction
        (bool ok, ) = msg.sender.call{value: amount}("");
        require(ok, "transfer failed");
    }
}
```

> ⚠️ **The line ordering in `withdraw` is life-or-death.** Zeroing the balance *before* sending is the **checks-effects-interactions** pattern. Reversed, a malicious contract could re-enter `withdraw` recursively and drain the bank — this exact bug caused the 2016 DAO hack ($60M, and the Ethereum/Ethereum Classic split).

```quiz
{
  "question": "In PiggyBank.withdraw, why is `deposits[msg.sender] = 0` placed before the ETH transfer?",
  "options": [
    "Gas optimization — storage writes are cheaper early",
    "Style convention from the Solidity docs",
    "To block reentrancy: if the receiver calls withdraw() again mid-transfer, their balance is already 0",
    "Because Solidity requires state changes before external calls"
  ],
  "answer": 2,
  "explain": "msg.sender.call can execute attacker code (a contract's receive function). If the balance were still non-zero, that code could recursively call withdraw() and drain everything. Checks-Effects-Interactions closes the loop."
}
```

## Exercise

Ask the tutor: **"Create contracts/Voting.sol — a contract where the owner registers candidates, anyone votes once, with events. Compile it and explain the storage layout."**
