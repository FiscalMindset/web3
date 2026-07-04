---
title: Solana — Accounts, Programs & PDAs
module: Module 4 · Beyond Ethereum
order: 8
minutes: 35
---

# Solana — Accounts, Programs & PDAs

Solana is not "faster Ethereum" — it's a **different mental model**. If you bring EVM habits to Solana you'll be confused within minutes. Here's the rewiring.

## The big flip: programs are stateless

| | Ethereum | Solana |
|---|---|---|
| Code + state | Live together in the contract | **Separated**: programs hold code, *accounts* hold state |
| Contract storage | `mapping` inside the contract | Data serialized into separate accounts you must pass in |
| Who pays for storage | Gas at write time (forever) | **Rent**: accounts must hold lamports proportional to size |
| Fees | Gas auction, single global market | Fixed base fee + local fee markets, parallel execution |
| Language | Solidity/Vyper → EVM bytecode | **Rust** (Anchor) → SBF bytecode |
| Currency unit | wei (10⁻¹⁸ ETH) | **lamports** (10⁻⁹ SOL) |

On Solana, *everything* is an account: your wallet, a token balance, a program's code, program state. An account is just: `{ lamports, owner: program_id, data: bytes, executable: bool }`.

## Simulate the account model

```rust
use std::collections::HashMap;

#[derive(Debug, Clone)]
struct Account {
    lamports: u64,
    owner: String,     // the program allowed to mutate this account's data
    data: Vec<u8>,
}

const LAMPORTS_PER_SOL: u64 = 1_000_000_000;

fn main() {
    let mut ledger: HashMap<String, Account> = HashMap::new();

    ledger.insert("alice_wallet".into(), Account {
        lamports: 5 * LAMPORTS_PER_SOL,
        owner: "system_program".into(),
        data: vec![],
    });
    ledger.insert("alice_usdc".into(), Account {
        lamports: 2_039_280,                  // rent-exempt minimum for a token account
        owner: "token_program".into(),
        data: vec![0; 165],                   // token accounts are 165 bytes
    });

    // The runtime's core rule: only an account's OWNER program may change its data.
    let tx_program = "some_random_program";
    let target = ledger.get("alice_usdc").unwrap();
    if target.owner != tx_program {
        println!("❌ {} cannot touch alice_usdc (owner: {})", tx_program, target.owner);
    }

    // lamport transfer with checked math — underflow is a compile-you-must-handle case
    let fee = 5_000u64;
    let amount = 1 * LAMPORTS_PER_SOL;
    let alice = ledger.get_mut("alice_wallet").unwrap();
    match alice.lamports.checked_sub(amount + fee) {
        Some(rest) => { alice.lamports = rest; println!("✅ sent 1 SOL, fee 5000 lamports, {} left", rest); }
        None => println!("❌ insufficient lamports"),
    }
}
```

That ownership rule is Solana's entire security model in one line: **your token balance is safe because only the token program can mutate token accounts**, and the token program's code only moves funds with your signature.

## PDAs: accounts owned by programs, not keys

A **Program Derived Address** is an address computed from a program ID + seeds, deliberately crafted to have *no private key*. It's how programs own state and sign for it.

```rust
use std::collections::hash_map::DefaultHasher;
use std::hash::{Hash, Hasher};

// Real Solana uses sha256(seeds, program_id, "ProgramDerivedAddress") and
// rejects addresses that land on the ed25519 curve. Same idea, toy hash:
fn derive_pda(program_id: &str, seeds: &[&str]) -> (u64, u8) {
    for bump in (0..=255u8).rev() {
        let mut h = DefaultHasher::new();
        (program_id, seeds, bump).hash(&mut h);
        let addr = h.finish();
        if addr % 7 != 0 {          // toy stand-in for "not on the curve"
            return (addr, bump);
        }
    }
    panic!("no valid bump");
}

fn main() {
    let (escrow, bump) = derive_pda("escrow_program", &["escrow", "alice", "bob"]);
    println!("escrow PDA: {:016x} (bump {})", escrow, bump);

    // Deterministic: anyone can re-derive it — no need to store the address anywhere
    let (again, _) = derive_pda("escrow_program", &["escrow", "alice", "bob"]);
    assert_eq!(escrow, again);
    println!("re-derived identically ✅ — that's why clients can always find program state");
}
```

## Why Solana is fast (and the trade-off)

1. **Proof of History** — a verifiable clock (sequential sha256 chain) lets validators agree on time ordering without waiting for each other.
2. **Parallel execution** — every transaction declares which accounts it touches, so non-overlapping transactions run simultaneously (Sealevel). The EVM is single-threaded; Solana is a multilane highway.
3. Trade-off: validators need serious hardware, and declared-account transactions are more complex to build.

```quiz
{
  "question": "Why can Solana execute transactions in parallel while the EVM cannot?",
  "options": [
    "Solana validators have GPUs",
    "Every Solana transaction declares upfront exactly which accounts it reads/writes, so non-conflicting txs are provably safe to run simultaneously",
    "Proof of History removes the need for consensus",
    "Rust is a parallel language"
  ],
  "answer": 1,
  "explain": "The account-list requirement is the key. The runtime sees tx A touches {X,Y} and tx B touches {Z} — no overlap, run them at once. The EVM can't know what a tx touches until it executes it."
}
```

## Exercise

Ask the tutor: **"Create escrow.rs simulating a Solana escrow: alice deposits into a PDA account, bob fulfills, the program releases funds — with the owner-check rule enforced. Run it."**
