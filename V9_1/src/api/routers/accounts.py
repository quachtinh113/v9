from fastapi import APIRouter, HTTPException, Body
from typing import Dict, Any, List
from pydantic import BaseModel, Field
import os
import sys

# Ensure src is in path to import core
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from src.core.account_registry import AccountRegistry

router = APIRouter(prefix="/api/accounts", tags=["accounts"])

class RiskProfile(BaseModel):
    max_daily_loss_pct: float = Field(default=2.0)
    max_drawdown_pct: float = Field(default=10.0)
    live_execution_enabled: bool = Field(default=False)

class Account(BaseModel):
    id: str
    broker: str
    account_type: str
    mt5_login: int
    mt5_password: str = Field(default="********")
    mt5_server: str
    path: str
    risk_profile: RiskProfile

@router.get("/", response_model=List[Account])
def get_accounts():
    data = AccountRegistry.read_accounts()
    accounts = data.get("accounts", {})
    return list(accounts.values())

@router.post("/")
def create_account(account: Account):
    existing = AccountRegistry.get_account(account.id)
    if existing:
        raise HTTPException(status_code=400, detail="Account ID already exists")
    AccountRegistry.add_or_update_account(account.id, account.dict())
    return {"status": "success", "message": f"Account {account.id} created."}

@router.put("/{account_id}")
def update_account(account_id: str, account: Account):
    if account_id != account.id:
        raise HTTPException(status_code=400, detail="Account ID in path and body do not match")
    AccountRegistry.add_or_update_account(account.id, account.dict())
    return {"status": "success", "message": f"Account {account.id} updated."}

@router.delete("/{account_id}")
def delete_account(account_id: str):
    success = AccountRegistry.delete_account(account_id)
    if not success:
        raise HTTPException(status_code=404, detail="Account not found")
    return {"status": "success", "message": f"Account {account_id} deleted."}

@router.post("/{account_id}/enable_live")
def enable_live(account_id: str, confirmation: dict = Body(...)):
    phrase = confirmation.get("phrase", "")
    if phrase != "ENABLE LIVE":
        raise HTTPException(status_code=403, detail="Invalid confirmation phrase. Must be exactly 'ENABLE LIVE'")
    
    account = AccountRegistry.get_account(account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
        
    account["risk_profile"]["live_execution_enabled"] = True
    account["account_type"] = "live"
    AccountRegistry.add_or_update_account(account_id, account)
    
    return {"status": "success", "message": f"Live execution ENABLED for {account_id}."}
