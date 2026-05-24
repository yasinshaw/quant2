from pydantic_settings import BaseSettings
from pydantic import validator
import os
from pathlib import Path


# Create database_url separately to handle path resolution
_project_root = Path(__file__).parent.parent  # Go up from backend/ to project root
_default_db_url = f"sqlite:///{_project_root}/data/quant.db"


class Settings(BaseSettings):
    # Database
    database_url: str = _default_db_url

    # Binance API
    binance_base_url: str = "https://api.binance.com"
    binance_timeout: int = 30  # seconds

    # Proxy settings (optional)
    http_proxy: str = ""  # e.g., "http://127.0.0.1:7897"
    https_proxy: str = ""  # e.g., "http://127.0.0.1:7897"

    # Backtest configuration
    default_initial_cash: float = 100000.0
    max_workers: int = 4  # for parameter optimization

    # OKX Live Trading
    okx_api_key: str = ""
    okx_secret_key: str = ""
    okx_passphrase: str = ""
    okx_symbol: str = "ETH/USDT:USDT"
    okx_timeframe: str = "4h"           # used by trend (VolSqueeze) trader
    okx_grid_timeframe: str = "1h"      # used by grid trader
    okx_leverage: int = 4  # should match okx_p_leverage
    okx_margin_mode: str = "isolated"  # isolated or cross
    okx_sandbox: bool = False          # True = demo/paper trading

    # Feishu notification
    feishu_webhook_url: str = ""

    # Strategy parameters (defaults = backtest #293 optimized values)
    okx_p_kc_length: int = 47
    okx_p_kc_mult: float = 2.0
    okx_p_vol_length: int = 37
    okx_p_vol_mult: float = 2.0
    okx_p_squeeze_threshold: float = 1.0
    okx_p_adx_length: int = 12
    okx_p_adx_threshold: float = 24.0
    okx_p_sl_mult: float = 4.0
    okx_p_trail_length: int = 17
    okx_p_tp_mult: float = 6.0
    okx_p_leverage: float = 4.0
    okx_p_position_pct: float = 1.0
    okx_p_risk_pct: float = 3.0
    okx_p_dd_throttle_start: float = 8.0
    okx_p_dd_throttle_max: float = 18.0

    # Grid V7 strategy parameters (defaults = backtest job 521)
    grid_p_grid_count: int = 6
    grid_p_grid_spacing: float = 0.02822
    grid_p_center_ema_period: int = 38
    grid_p_recenter_cooldown: int = 76
    grid_p_recenter_drift_pct: float = 0.5449
    grid_p_recenter_one_sided_bars: int = 12
    grid_p_adx_period: int = 12
    grid_p_adx_threshold: float = 20.48
    grid_p_adx_strong: float = 45.0
    grid_p_volatility_lookback: int = 60
    grid_p_vol_spacing_floor: float = 0.008
    grid_p_vol_spacing_cap: float = 0.04
    grid_p_max_bars_per_lot: int = 102
    grid_p_timeout_sl_pct: float = 5.45
    grid_p_hard_sl_pct: float = 0.0
    grid_p_risk_pct: float = 7.16
    grid_p_leverage: float = 3.0
    grid_p_dd_soft_halt_pct: float = 12.0
    grid_p_dd_hard_halt_pct: float = 15.0
    grid_p_dd_min_size_factor: float = 0.1
    grid_p_equity_trail_pct: float = 20.0
    grid_p_atr_period: int = 14

    @validator('database_url')
    def validate_db_path(cls, v):
        """Validate and create database path if needed"""
        # If relative path, make it absolute from project root
        if v.startswith('sqlite:///'):
            db_path = v.replace('sqlite:///', '')
            if not os.path.isabs(db_path):
                # It's a relative path, resolve from project root
                abs_db_path = _project_root / db_path
                v = f"sqlite:///{abs_db_path}"
                db_path = str(abs_db_path)

            # Create directory if needed
            db_dir = os.path.dirname(db_path)
            if db_dir and not os.path.exists(db_dir):
                os.makedirs(db_dir, exist_ok=True)
        return v

    @validator('default_initial_cash')
    def validate_initial_cash(cls, v):
        """Validate initial cash is positive"""
        if v <= 0:
            raise ValueError('Initial cash must be positive')
        return v

    class Config:
        # Look for .env file in project root (parent of backend/)
        env_file = str(_project_root / ".env")


settings = Settings()

