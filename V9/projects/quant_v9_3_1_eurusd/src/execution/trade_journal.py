import json
class TradeJournal:
    def __init__(self, p): self.p = p
    def write(self, et, pl): pass
class PipelineAuditLog:
    def __init__(self, p): self.p = p
    def write_tick(self, **kwargs): pass
