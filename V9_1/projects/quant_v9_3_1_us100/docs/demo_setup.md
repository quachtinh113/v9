# Demo setup

## 1. Copy config
Copy `config/mt5_demo.yaml.example` to `config/mt5_demo.yaml` and fill in your MT5 demo details.

## 2. Start in paper mode first
```bash
python -m src.run_demo --mode paper
```

## 3. Then test MT5 bridge
Set `mt5.enabled: true` and keep `allow_live_send: false` first.

```bash
python -m src.run_demo --mode mt5
```

This repo will only send an order when:
- a fresh signal exists
- session guard passes
- kill switch does not block
- `allow_live_send` is true

## 4. Safe rollout
- only one symbol per repo
- demo account only
- smallest lot
- confirm `logs/demo_journal.jsonl` is being written
