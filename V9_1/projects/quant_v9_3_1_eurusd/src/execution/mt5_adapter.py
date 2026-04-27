class MT5Adapter:
    def __init__(self, **kwargs): self.enabled = False
    def connect(self): return False
    def send_order(self, req): return {"status": "paper_only"}
class MT5OrderRequest:
    def __init__(self, **kwargs): pass
