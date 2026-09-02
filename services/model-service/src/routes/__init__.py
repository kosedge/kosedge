from __future__ import annotations

from src.routes.book import router as book_router
from src.routes.cfb import router as cfb_router
from src.routes.edge_board import router as edge_board_router
from src.routes.mlb import router as mlb_router
from src.routes.nba import router as nba_router
from src.routes.nfl import router as nfl_router
from src.routes.nhl import router as nhl_router
from src.routes.proof import router as proof_router
from src.routes.wnba import router as wnba_router

__all__ = [
    "book_router",
    "cfb_router",
    "edge_board_router",
    "mlb_router",
    "nba_router",
    "nfl_router",
    "nhl_router",
    "proof_router",
    "wnba_router",
]
