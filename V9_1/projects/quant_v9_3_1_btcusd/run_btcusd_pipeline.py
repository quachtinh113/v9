import sys
import os
import logging
from pathlib import Path

# Set up PYTHONPATH
project_dir = Path(__file__).parent.resolve()
sys.path.insert(0, str(project_dir))

from src.pipeline_live import LivePipeline

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

def main():
    logger.info("Initializing LivePipeline for BTCUSD...")
    
    # Required to pass demo live execution assertions
    os.environ["ALLOW_REAL_TRADING"] = "true"
    os.environ["HUMAN_LIVE_CONFIRM"] = "YES_I_ACCEPT_LIVE_RISK"
    os.environ["LIVE_DEMO_ALLOWED"] = "true"
    
    try:
        pipeline = LivePipeline(root=project_dir, runtime_mode="live")
        logger.info("Starting pipeline loop...")
        pipeline.run_loop()
    except Exception as e:
        logger.exception("Fatal error in pipeline loop.")
        
        # Write to console_err.log
        err_log_path = project_dir / "logs" / "console_err.log"
        err_log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(err_log_path, "a") as f:
            f.write(f"Fatal error: {str(e)}\n")
        
        sys.exit(1)

if __name__ == "__main__":
    main()
