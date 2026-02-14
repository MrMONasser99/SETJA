import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core.config.t_config import HOST, PORT
from core.api.t_api import app

def main():
    import uvicorn
    uvicorn.run(
        app,
        host=HOST,
        port=PORT,
        log_level="warning",
        access_log=False,   
    )

if __name__ == "__main__":
    main()
