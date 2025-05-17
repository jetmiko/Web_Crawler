import subprocess
import logging
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

def run_script(script_name: str) -> bool:
    """Run a Python script and return True if successful, False otherwise."""
    logger.info(f"Running {script_name}...")
    try:
        result = subprocess.run(
            [sys.executable, script_name],
            check=True,
            text=True,
            capture_output=True
        )
        logger.info(f"{script_name} completed successfully.")
        logger.debug(f"Output: {result.stdout}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Error running {script_name}: {e.stderr}")
        return False
    except FileNotFoundError:
        logger.error(f"Script {script_name} not found.")
        return False
    except Exception as e:
        logger.error(f"Unexpected error running {script_name}: {str(e)}")
        return False

def main():
    """Run list_view.py followed by supabase_lib.py."""
    # Step 1: Run list_view.py
    if not run_script("list_view.py"):
        logger.error("Aborting: list_view.py failed.")
        sys.exit(1)

    # Step 2: Run supabase_lib.py
    if not run_script("supabase_lib.py"):
        logger.error("supabase_lib.py failed.")
        sys.exit(1)

    logger.info("All scripts executed successfully.")

if __name__ == "__main__":
    main()