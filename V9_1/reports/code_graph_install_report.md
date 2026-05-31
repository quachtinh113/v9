# Low-Token Code Graph Engine Installation Report

This report documents the installation, validation, and execution of the lightweight **Quant Call Graph Engine** for the Quant V9 trading fleet infrastructure.

---

## 1. Installation Details

* **Script File Created**: `scripts/build_code_graph.py`
* **Target Indexing Directory**: `projects`
* **JSON Index Output Path**: `reports/code_graph_index.json`
* **Engine Execution Status**: SUCCESS
* **Syntax Validation Status**: PASS (Compiled via `compileall` successfully)

---

## 2. Validation Metrics

* **Total Indexed Files**: 473 Python source files
* **Key Components Verified**:
  * **`pipeline_live.py`**: **INDEXED** (11 instances mapped across symbols)
  * **`risk_engine.py`**: **INDEXED** (11 instances mapped across symbols)
  * **`order_router.py`**: **INDEXED** (11 instances mapped across symbols)

### Indexed File Details (Sample List)

| Target Component | Mapped Symbols | File Location | Mapped Status |
| :--- | :--- | :--- | :--- |
| `pipeline_live.py` | AUDUSD, BTCUSD, EURUSD, GBPUSD, US100, US30, US500, USDCAD, USDCHF, USDJPY, XAUUSD | `projects/quant_v9_3_1_[symbol]/src/pipeline_live.py` | ✅ INDEXED |
| `risk_engine.py` | AUDUSD, BTCUSD, EURUSD, GBPUSD, US100, US30, US500, USDCAD, USDCHF, USDJPY, XAUUSD | `projects/quant_v9_3_1_[symbol]/src/core/risk_engine.py` | ✅ INDEXED |
| `order_router.py` | AUDUSD, BTCUSD, EURUSD, GBPUSD, US100, US30, US500, USDCAD, USDCHF, USDJPY, XAUUSD | `projects/quant_v9_3_1_[symbol]/src/execution/order_router.py` | ✅ INDEXED |

---

## 3. Skipped and Error Logs

* **Syntax Errors Skipped**: 0 files skipped.
* **Exceptions Encountered**: None.

---

## 4. Final Verdict

**FINAL VERDICT: PASS**

The Call Graph engine is successfully installed and has indexed the complete code graph structure. AI agents can now perform low-latency call tracing and symbol-specific analysis using the pre-computed graph in `reports/code_graph_index.json` without full repository indexing.
