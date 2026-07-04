---
title: DeFi Primitives — AMMs & Lending
module: Module 3 · DeFi
order: 6
minutes: 30
---

# DeFi Primitives — AMMs & Lending

Traditional finance matches buyers with sellers in an order book. DeFi's core invention was replacing the order book with **a formula and a pool of tokens**. No counterparty needed — you trade against math.

## The constant product formula: x · y = k

A Uniswap pool holds two tokens. The rule: after any trade, the **product** of the reserves must not decrease. That single constraint sets the price.

```javascript
// A working constant-product AMM in 30 lines
let ethReserve = 100;        // pool holds 100 ETH
let usdcReserve = 200_000;   // and 200,000 USDC  → price: 2000 USDC/ETH
const k = ethReserve * usdcReserve;

console.log(`pool price: ${(usdcReserve / ethReserve).toFixed(2)} USDC/ETH\n`);

function buyETH(usdcIn) {
  const fee = usdcIn * 0.003;                       // 0.3% LP fee
  const newUsdc = usdcReserve + (usdcIn - fee);
  const newEth = k / newUsdc;                       // enforce x·y = k
  const ethOut = ethReserve - newEth;
  const execPrice = usdcIn / ethOut;

  usdcReserve = newUsdc + fee;
  ethReserve = newEth;

  console.log(`swap ${usdcIn.toLocaleString()} USDC → ${ethOut.toFixed(4)} ETH`
    + `  (exec price ${execPrice.toFixed(2)}, new pool price ${(usdcReserve/ethReserve).toFixed(2)})`);
}

buyETH(2_000);     // small trade — barely moves the price
buyETH(20_000);    // 10× bigger — watch the slippage
buyETH(100_000);   // whale trade — massive price impact
```

Run it. Notice the **exec price is always worse than the pool price**, and worse the bigger you trade. That's *slippage* — not a fee, just geometry: you're sliding along the curve x·y=k.

## Impermanent loss: the LP's tax

Liquidity providers earn the 0.3% fees but take a subtle risk: if the price moves, the pool automatically sells the winner and buys the loser. You end up with less of whatever went up.

```python
# Impermanent loss vs simply holding
import math

def il(price_ratio):
    """Loss vs HODL when price moves by `price_ratio`x."""
    return 2 * math.sqrt(price_ratio) / (1 + price_ratio) - 1

print(f"{'price change':>14} | {'IL vs hold':>10}")
print("-" * 28)
for r in [1.0, 1.25, 1.5, 2, 3, 5, 10]:
    print(f"{r:>12}x  | {il(r)*100:>9.2f}%")
```

At 2× price move you're down 5.7% vs just holding — the fees have to beat that for LPing to win.

## Lending: overcollateralised by design

Aave/Compound can't run credit checks on anonymous addresses, so every loan is **overcollateralised**: deposit $150 of ETH, borrow up to $100 of USDC. If your collateral value falls near the debt, anyone may **liquidate** you (repay your debt, seize your collateral at a discount).

```javascript
// A liquidation engine in miniature
const LTV = 0.80, LIQ_THRESHOLD = 0.85, LIQ_BONUS = 0.05;

function health(collateralETH, ethPrice, debtUSDC) {
  return (collateralETH * ethPrice * LIQ_THRESHOLD) / debtUSDC;
}

const position = { collateral: 10, debt: 15_000 }; // 10 ETH, 15k USDC borrowed

for (const price of [2500, 2200, 1900, 1760, 1700]) {
  const hf = health(position.collateral, price, position.debt);
  const status = hf >= 1 ? "✅ safe" : "🚨 LIQUIDATABLE";
  console.log(`ETH=$${price}  health factor=${hf.toFixed(3)}  ${status}`);
}
```

```quiz
{
  "question": "Why must DeFi loans be overcollateralised?",
  "options": [
    "Regulators require it",
    "Smart contracts can't assess creditworthiness or pursue an anonymous defaulter — the collateral IS the enforcement",
    "To make borrowing unattractive",
    "Because gas fees are high"
  ],
  "answer": 1,
  "explain": "On-chain there is no identity, income proof, or court. The only guarantee that a loan is repaid is locked collateral worth more than the debt, plus liquidation bots incentivised to enforce it."
}
```

## Exercise

Ask the tutor: **"Build amm.js — extend the constant-product AMM with addLiquidity/removeLiquidity and LP share accounting, run a scenario where an LP deposits, trades happen, and they withdraw with fees earned."**
