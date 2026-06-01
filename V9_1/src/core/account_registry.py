import yaml
import pathlib
import os
from dotenv import load_dotenv

ROOT_DIR = pathlib.Path(__file__).resolve().parents[2]
ACCOUNTS_YAML_PATH = ROOT_DIR / "configs" / "accounts.yaml"
ENV_PATH = ROOT_DIR / ".env"

load_dotenv(dotenv_path=ENV_PATH)

class AccountRegistry:
    @staticmethod
    def read_accounts():
        if not ACCOUNTS_YAML_PATH.exists():
            return {"accounts": {}}
        try:
            with open(ACCOUNTS_YAML_PATH, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                
                # Inject passwords from env for runtime
                if data and "accounts" in data:
                    for acc_id, acc_data in data["accounts"].items():
                        # Read from env if exists, else fallback to masked
                        env_pw = os.getenv(f"MT5_PASSWORD_{acc_id}")
                        if env_pw:
                            acc_data["mt5_password"] = env_pw
                        elif "mt5_password" not in acc_data:
                            acc_data["mt5_password"] = "********"
                            
                return data if data else {"accounts": {}}
        except Exception as e:
            print(f"Error reading accounts.yaml: {e}")
            return {"accounts": {}}

    @staticmethod
    def write_accounts(data):
        os.makedirs(ACCOUNTS_YAML_PATH.parent, exist_ok=True)
        try:
            with open(ACCOUNTS_YAML_PATH, "w", encoding="utf-8") as f:
                yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False)
        except Exception as e:
            print(f"Error writing accounts.yaml: {e}")

    @classmethod
    def get_account(cls, account_id: str):
        data = cls.read_accounts()
        return data.get("accounts", {}).get(account_id)

    @classmethod
    def add_or_update_account(cls, account_id: str, account_data: dict):
        data = cls.read_accounts()
        if "accounts" not in data:
            data["accounts"] = {}
        account_data["id"] = account_id
        data["accounts"][account_id] = account_data
        cls.write_accounts(data)

    @classmethod
    def delete_account(cls, account_id: str):
        data = cls.read_accounts()
        if "accounts" in data and account_id in data["accounts"]:
            del data["accounts"][account_id]
            cls.write_accounts(data)
            return True
        return False
