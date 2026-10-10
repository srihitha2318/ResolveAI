import logging
import sys
from pathlib import Path

# Ensure backend root is in sys.path for robust resolution
_backend_dir = Path(__file__).resolve().parent.parent.parent
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

try:
    from app.core.config import settings
except ImportError:
    from backend.app.core.config import settings


def setup_logging() -> logging.Logger:
    """Configures structured standard logging for ResolveAI."""
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    log_format = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    logging.basicConfig(
        level=log_level,
        format=log_format,
        datefmt=date_format,
        handlers=[logging.StreamHandler(sys.stdout)],
        force=True,
    )

    logger = logging.getLogger("resolveai")
    logger.setLevel(log_level)
    return logger


logger = setup_logging()
