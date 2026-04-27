# Architecture - Quant v9.3.1 US500

## Core flow
1. Data Loader
2. Multi-timeframe Builder
3. Regime Engine
4. Signal Engine
5. Position Engine
6. Risk Engine
7. Execution Engine

## Symbol intent
- US500: balanced core / benchmark / trend + reversion filter

## Mandatory filters
- Bias aligned
- ADX regime valid
- ATR safe
- Session valid
- Risk valid
