import json
import os
import dataclasses
from dataclasses import dataclass, field, asdict
from typing import Dict, Any


@dataclass
class AppConfig:
    # Appearance & Theming
    appearance_mode: str = "Dark"
    color_theme: str = "green"

    # KI & Ollama
    ki_provider: str = "Ollama (Lokal)"
    ollama_url: str = "http://localhost:11434"
    api_key: str = ""
    api_key_openai: str = ""
    api_key_anthropic: str = ""
    api_key_deepseek: str = ""
    api_key_openrouter: str = ""
    llm_model: str = "llama3.2"
    interval: int = 300
    ai_temperature: float = 0.7
    prompt_lang: str = "Deutsch"
    system_prompt: str = ""
    min_confidence: int = 60

    # Trading Style
    trading_style: str = "Day Trading"
    signal_strategy: str = "KI-Entscheidung"
    risk_profile: str = "Medium"
    max_risk: str = "1.0"
    max_daily_loss: str = "50"
    max_positions: str = "3"
    trailing_stop: bool = False
    trailing_dist: str = "20"
    break_even: bool = False
    break_even_dist: str = "15"
    weekend_exit: bool = True
    auto_trading: bool = False
    session_london: bool = True
    session_ny: bool = True
    session_asia: bool = False

    # Trading Zeiten
    trade_time_from: str = "07:00"
    trade_time_to: str = "22:00"
    time_filter: bool = False
    day_mon: bool = True
    day_tue: bool = True
    day_wed: bool = True
    day_thu: bool = True
    day_fri: bool = True
    day_sat: bool = False
    day_sun: bool = False

    # Nachrichten-Filter
    news_filter: bool = False
    news_before_min: int = 30
    news_after_min: int = 30
    news_high: bool = True
    news_medium: bool = False
    news_low: bool = False

    # Ausführungsqualität
    max_spread: int = 3
    max_slippage: int = 2
    spread_check: bool = True

    # Reinforcement Learning
    rl_algo: str = "DQN"
    rl_learning_rate: float = 0.001
    rl_gamma: float = 0.99
    rl_steps: str = "1000"
    rl_reward: str = "Profit (Absolut)"
    rl_buffer_size: str = "10000"
    rl_batch_size: str = "64"
    rl_epochs: str = "10"
    rl_target_update: str = "100"
    rl_checkpoint: str = "rl_models/"
    rl_live_enabled: bool = False
    rl_epsilon_start: float = 1.0
    rl_epsilon_min: float = 0.01
    rl_epsilon_decay: float = 0.995
    rl_timeframe: str = "M15"
    rl_bars: str = "5000"
    rl_nn_arch: str = "Mittel (128-128)"

    # MT5 & System
    pairs: str = "EURUSD, GBPUSD, USDJPY, XAUUSD"
    debug_mode: bool = False

    # Risk Manager (Euro-basiert)
    rm_max_daily_loss_eur: float = 500.0
    rm_max_weekly_loss_eur: float = 1500.0
    rm_min_time_between_trades: int = 300
    rm_max_trades_per_day: int = 10

    # Backtest-Einstellungen
    bt_start_capital: float = 10000.0
    bt_rr_ratio: float = 1.5
    bt_atr_mult: float = 1.0
    bt_spread_pips: float = 1.0

    # KI erweitert
    llm_max_tokens: int = 500

    # Benachrichtigungen & Alerts
    tg_token: str = ""
    tg_chat_id: str = ""
    discord_webhook: str = ""
    sound_alerts: bool = True
    notif_sl_hit: bool = True
    notif_tp_hit: bool = True
    notif_new_trade: bool = True
    notif_error: bool = True

    # MCP Integration
    mcp_enabled: bool = False

    @classmethod
    def load_from_file(cls, filepath: str) -> "AppConfig":
        if not os.path.exists(filepath):
            return cls()
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                return cls()
            valid_keys = {f.name for f in dataclasses.fields(cls)}
            filtered_data = {k: v for k, v in data.items() if k in valid_keys}
            return cls(**filtered_data)
        except Exception:
            return cls()

    def save_to_file(self, filepath: str) -> bool:
        try:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(dataclasses.asdict(self), f, indent=2, ensure_ascii=False)
            return True
        except Exception:
            return False


class ConfigManagerSingleton:
    _instance = None

    def __new__(cls, config_dir=None):
        if cls._instance is None:
            cls._instance = super(ConfigManagerSingleton, cls).__new__(cls)
            cls._instance.config = AppConfig()
            if config_dir:
                cls._instance.config_path = os.path.join(config_dir, "config.json")
            else:
                base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                cls._instance.config_path = os.path.join(
                    base, "storage", "gui_settings", "config.json"
                )
        return cls._instance

    def load(self):
        self.config = AppConfig.load_from_file(self.config_path)
        return self.config

    def save(self):
        return self.config.save_to_file(self.config_path)


# Globale Instanz
app_config_manager = ConfigManagerSingleton()
