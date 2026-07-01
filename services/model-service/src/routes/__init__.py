from __future__ import annotations

from src.routes.edge_board import router as edge_board_router
from src.routes.mlb import router as mlb_router
from src.routes.nfl import router as nfl_router

__all__ = ["edge_board_router", "mlb_router", "nfl_router"]