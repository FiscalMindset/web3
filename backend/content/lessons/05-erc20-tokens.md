---
title: ERC-20 — The Token Standard
module: Module 2 · Smart Contracts
order: 5
minutes: 25
---

# ERC-20 — The Token Standard

Every fungible token — USDC, LINK, UNI, all of them — is just a contract implementing **six functions and two events**. There are no coins moving anywhere; an ERC-20 is a *spreadsheet with an API*.

## The whole standard

```
balanceOf(owner) → uint          totalSupply() → uint
transfer(to, amount) → bool      approve(spender, amount) → bool
allowance(owner, spender) → uint transferFrom(from, to, amount) → bool

event Transfer(from, to, amount)
event Approval(owner, spender, amount)
```

## A real, compilable ERC-20

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

contract TutorToken {
    string public constant name = "TutorToken";
    string public constant symbol = "TUT";
    uint8  public constant decimals = 18;
    uint256 public totalSupply;

    mapping(address => uint256) public balanceOf;
    mapping(address => mapping(address => uint256)) public allowance;

    event Transfer(address indexed from, address indexed to, uint256 value);
    event Approval(address indexed owner, address indexed spender, uint256 value);

    constructor(uint256 initialSupply) {
        totalSupply = initialSupply;
        balanceOf[msg.sender] = initialSupply;
        emit Transfer(address(0), msg.sender, initialSupply);
    }

    function transfer(address to, uint256 value) external returns (bool) {
        _move(msg.sender, to, value);
        return true;
    }

    function approve(address spender, uint256 value) external returns (bool) {
        allowance[msg.sender][spender] = value;
        emit Approval(msg.sender, spender, value);
        return true;
    }

    function transferFrom(address from, address to, uint256 value) external returns (bool) {
        uint256 allowed = allowance[from][msg.sender];
        require(allowed >= value, "allowance exceeded");
        if (allowed != type(uint256).max) {
            allowance[from][msg.sender] = allowed - value;
        }
        _move(from, to, value);
        return true;
    }

    function _move(address from, address to, uint256 value) internal {
        require(balanceOf[from] >= value, "insufficient balance");
        balanceOf[from] -= value;
        balanceOf[to] += value;
        emit Transfer(from, to, value);
    }
}
```

Run it — real `solc` compilation, real ABI output.

## Why `approve` + `transferFrom`?

This two-step dance is what lets Uniswap swap your tokens: you `approve` the router, the router calls `transferFrom`. A contract can't reach into your balance without a prior allowance.

```javascript
// The allowance model, simulated
const balances = { alice: 100n, uniswap: 0n, bob: 0n };
const allowance = {}; // owner → spender → amount

const approve = (owner, spender, amt) =>
  (allowance[owner] = { ...(allowance[owner] || {}), [spender]: amt });

const transferFrom = (spender, from, to, amt) => {
  const ok = (allowance[from]?.[spender] ?? 0n) >= amt && balances[from] >= amt;
  if (!ok) return console.log(`❌ ${spender} can't move ${amt} from ${from}`);
  allowance[from][spender] -= amt;
  balances[from] -= amt; balances[to] += amt;
  console.log(`✅ ${spender} moved ${amt} ${from}→${to}`);
};

transferFrom("uniswap", "alice", "bob", 30n);   // fails — no approval yet
approve("alice", "uniswap", 50n);
transferFrom("uniswap", "alice", "bob", 30n);   // works
console.log(balances);
```

## Decimals: the eternal footgun

`decimals = 18` means balances are stored ×10¹⁸. "1.5 TUT" is `1500000000000000000` on-chain. USDC uses **6** decimals — hardcoding 18 has burned real protocols.

```quiz
{
  "question": "A token has 6 decimals. A user wants to send 2.5 tokens. What value goes in transfer()?",
  "options": ["2.5", "2500000", "2500000000000000000", "25"],
  "answer": 1,
  "explain": "2.5 × 10^6 = 2,500,000. Always read decimals() from the contract — USDC (6) vs DAI (18) is the classic integration bug."
}
```

## Exercise

Ask the tutor: **"Add a mint function with owner-only access and a burn function to TutorToken, save as contracts/TutorTokenV2.sol, compile, and quiz me on what could go wrong with a public mint."**
