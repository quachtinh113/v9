# Quant V9 DCA Engine Specification

## Overview
The DCA (Dollar Cost Averaging) Engine is designed to average down/up into a position under strict risk-controlled parameters. It explicitly rejects infinite martingale strategies and emotional trading.

## Core Rules

1.  **Regime Dependency:** DCA is only permitted if the original regime logic remains valid. If a regime flip occurs (e.g., from Trend to Range), all pending DCA orders must be canceled, and existing positions managed or closed.
2.  **No Martingale:** Lot sizes for DCA layers must never use an aggressive multiplier (like 2x or 3x). They must be equal to or less than the base lot, or calculated using equal-risk fractioning.
3.  **Maximum Layers:** Strictly capped at `max_layers = 3` (plus the base entry layer).
4.  **ATR-Based Spacing:** The distance between layers must be calculated using a dynamic ATR multiplier (`spacing_atr_multiplier`). Hardcoded pip distances are only used as minimum fallbacks (`min_spacing_points`).
5.  **Risk Veto:** The Risk Engine holds ultimate veto power. If `basket_risk`, `floating_loss`, or `daily_loss` limits are hit, no DCA orders will be sent.
6.  **Pending Orders Limit:** Maximum 3 pending orders per symbol to avoid flooding the execution engine.

## Engine Logic Flow

1.  **Signal Generation:** `Signal Engine` generates a valid signal.
2.  **Base Position Creation:** `Position Engine` calculates the base lot size using risk-based sizing.
3.  **DCA Plan Generation (`dca_engine.py`):**
    *   Validate DCA permission (check regime, time, correlation).
    *   Calculate spacing based on `ATR * spacing_atr_multiplier`.
    *   Generate `max_layers` number of `PositionLayer` objects.
4.  **Risk Veto (`risk_engine.py`):**
    *   Validate total basket risk.
    *   Block if total risk > `max_basket_risk_pct`.
5.  **Execution:** `OrderRouter` places the market order for Layer 0 and Limit/Stop orders for the DCA layers.

## Configuration Parameters

```yaml
dca:
  enabled: true
  mode: atr_based
  max_layers: 3
  base_layer: 0
  spacing_atr_multiplier: 0.8
  min_spacing_points:
    XAUUSDm: 300
    BTCUSDm: 500
    US30m: 150
  lot_multiplier:
    layer_1: 1.0
    layer_2: 1.0
    layer_3: 1.0
  max_basket_risk_pct: 0.75
  max_symbol_floating_loss_pct: 0.5
  require_regime_still_valid: true
```
