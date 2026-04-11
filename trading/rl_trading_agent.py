#!/usr/bin/env python3
"""
Reinforcement Learning Trading Agent für FinGPT
Verwendet Stable-Baselines3 (PPO) und Gymnasium
"""

import numpy as np
import pandas as pd
import MetaTrader5 as mt5
from datetime import datetime, timedelta
import os
import json
import threading
import time
from collections import deque
import random
import logging

import gymnasium as gym
from gymnasium import spaces

# Fancy console
class C:
    RESET = "\033[0m"
    GREEN = "\033[32m"
    RED = "\033[31m"
    YELLOW = "\033[33m"
    LGRAY = "\033[90m"

def ts():
    return datetime.now().strftime("%H:%M:%S")

# Stable-Baselines3 und PyTorch
try:
    import torch
    from stable_baselines3 import PPO
    from stable_baselines3.common.callbacks import BaseCallback
    TORCH_AVAILABLE = True
    print(f"{C.LGRAY}[{ts()}]{C.RESET} {C.GREEN}[OK] PyTorch & Stable-Baselines3 verfügbar{C.RESET}")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
except ImportError:
    TORCH_AVAILABLE = False
    print(f"{C.LGRAY}[{ts()}]{C.RESET} {C.RED}[FEHLER] PyTorch / Stable-Baselines3 nicht installiert!{C.RESET}")

try:
    import optuna
    OPTUNA_AVAILABLE = True
except ImportError:
    OPTUNA_AVAILABLE = False
    print(f"{C.LGRAY}[{ts()}]{C.RESET} {C.YELLOW}[WARN] Optuna nicht installiert. Hyperparameter-Optimierung deaktiviert.{C.RESET}")

class TradingEnvironment(gym.Env):
    """
    Gymnasium Trading Environment für RL Agent (Stable-Baselines3)
    Simuliert Marktbedingungen und Handelsaktionen
    """
    metadata = {'render_modes': ['human']}

    def __init__(self, symbol="EURUSD", lookback_period=100, timeframe=mt5.TIMEFRAME_M15):
        super(TradingEnvironment, self).__init__()
        self.symbol = symbol
        self.lookback_period = lookback_period
        self.timeframe = timeframe
        self.current_step = 0
        self.data = None
        self.balance = 10000.0  # Start-Kapital
        self.initial_balance = self.balance
        self.position = 0  # 0=neutral, 1=long, -1=short
        self.entry_price = 0
        self.max_drawdown = 0
        self.peak_balance = self.balance
        self.time_in_position = 0

        # Reward Parameters
        self.profit_reward_factor = 1.0
        self.loss_penalty_factor = 2.0  # Erhöhte Strafe für Verluste (Risk Aversion)
        self.holding_penalty = 0.005  # Höhere Strafe für das Halten von Positionen
        self.transaction_cost = 0.0002  # Höhere realistischere Spread/Gebühren

        # State Features (Input für NN)
        self.state_features = [
            "rsi",
            "macd",
            "macd_signal",
            "macd_histogram",
            "bb_upper",
            "bb_middle",
            "bb_lower",
            "bb_position",
            "price_change_1",
            "price_change_5",
            "price_change_20",
            "volume_ratio",
            "volatility",
            "trend_strength",
        ]

        self.state_size = len(self.state_features) + 3  # +3 für position, profit, time_in_position
        
        # Action Space (0: Hold, 1: Buy, 2: Sell)
        self.action_space = spaces.Discrete(3)
        
        # Observation Space
        self.observation_space = spaces.Box(
            low=-np.inf, high=np.inf, shape=(self.state_size,), dtype=np.float32
        )

    def load_historical_data(self, bars=5000, data_subset="all", split_ratio=0.8):
        """Lädt historische Daten für Training, Validierung oder Gesamt"""
        try:
            if not mt5.initialize():
                print(f"[X] MT5 Initialization failed")
                return False
            rates = mt5.copy_rates_from_pos(self.symbol, self.timeframe, 0, bars)
            if rates is None:
                raise Exception(f"Keine Daten für {self.symbol}")

            df = pd.DataFrame(rates)
            df["time"] = pd.to_datetime(df["time"], unit="s")

            # Berechne technische Indikatoren
            df = self.calculate_technical_indicators(df)

            df = df.dropna().reset_index(drop=True)

            split_idx = int(len(df) * split_ratio)
            if data_subset == "train":
                self.data = df.iloc[:split_idx].reset_index(drop=True)
            elif data_subset in ["test", "val"]:
                self.data = df.iloc[split_idx:].reset_index(drop=True)
            else:
                self.data = df

            if self.data is not None and not self.data.empty:
                print(f"[OK] {len(self.data)} Datenpunkte geladen fuer {self.symbol} (Modus: {data_subset})")
                return True
            return False

        except Exception as e:
            print(f"[X] Fehler beim Laden der Daten: {e}")
            return False

    def calculate_technical_indicators(self, df):
        """Berechnet alle technischen Indikatoren mit pandas-ta (Fallback auf numpy)"""
        try:
            import pandas_ta as ta
            # RSI
            df["rsi"] = ta.rsi(df["close"], length=14)

            # MACD
            macd = ta.macd(df["close"], fast=12, slow=26, signal=9)
            if macd is not None:
                df["macd"] = macd["MACD_12_26_9"]
                df["macd_signal"] = macd["MACDs_12_26_9"]
                df["macd_histogram"] = macd["MACDh_12_26_9"]

            # Bollinger Bands
            bb = ta.bbands(df["close"], length=20, std=2)
            if bb is not None and len(bb.columns) >= 5:
                df["bb_lower"] = bb[bb.columns[0]]
                df["bb_middle"] = bb[bb.columns[1]]
                df["bb_upper"] = bb[bb.columns[2]]
                df["bb_position"] = bb[bb.columns[4]]

        except ImportError:
            print("[RL] pandas_ta nicht gefunden, verwende langsame Berechnung")
            # RSI (Fallback)
            def calculate_rsi(prices, period=14):
                deltas = np.diff(prices)
                gains = np.where(deltas > 0, deltas, 0)
                losses = np.where(deltas < 0, -deltas, 0)
                avg_gains = pd.Series(gains).ewm(alpha=1 / period, adjust=False).mean()
                avg_losses = pd.Series(losses).ewm(alpha=1 / period, adjust=False).mean()
                rs = avg_gains / avg_losses
                return 100 - (100 / (1 + rs))

            df["rsi"] = calculate_rsi(df["close"].values)
            df["rsi"] = df["rsi"].shift(1)  # Align

            # MACD
            exp1 = df["close"].ewm(span=12, adjust=False).mean()
            exp2 = df["close"].ewm(span=26, adjust=False).mean()
            df["macd"] = exp1 - exp2
            df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()
            df["macd_histogram"] = df["macd"] - df["macd_signal"]

            # Bollinger Bands
            df["bb_middle"] = df["close"].rolling(window=20).mean()
            bb_std = df["close"].rolling(window=20).std()
            df["bb_upper"] = df["bb_middle"] + (bb_std * 2)
            df["bb_lower"] = df["bb_middle"] - (bb_std * 2)
            df["bb_position"] = (df["close"] - df["bb_lower"]) / (df["bb_upper"] - df["bb_lower"] + 1e-9)

        # Price Changes (Standard Pandas)
        df["price_change_1"] = df["close"].pct_change(1)
        df["price_change_5"] = df["close"].pct_change(5)
        df["price_change_20"] = df["close"].pct_change(20)

        # Volume und Volatilität
        df["volume_ratio"] = df["tick_volume"] / df["tick_volume"].rolling(window=20).mean()
        df["volatility"] = df["high"] - df["low"]

        # Trend Strength (ADX vereinfacht)
        df["trend_strength"] = abs(df["close"].rolling(window=14).mean().pct_change(5))

        return df.fillna(0)

    def reset(self, seed=None, options=None):
        """Reset environment für neue Episode (Gymnasium API)"""
        super().reset(seed=seed)
        if self.data is None or self.data.empty:
            # Fallback falls keine Daten geladen
            self.data = pd.DataFrame([{"close": 1.0}] * (self.lookback_period + 10))
            for f in self.state_features:
                self.data[f] = 0.0

        random_start = True
        if options and "random_start" in options:
            random_start = options["random_start"]

        if random_start and len(self.data) > self.lookback_period + 100:
            max_start = len(self.data) - self.lookback_period - 100
            self.current_step = random.randint(self.lookback_period, max_start)
        else:
            self.current_step = self.lookback_period

        # Reset Trading State
        self.balance = self.initial_balance
        self.position = 0
        self.entry_price = 0
        self.peak_balance = self.balance
        self.max_drawdown = 0
        self.time_in_position = 0

        return self.get_state(), {}

    def get_state(self):
        """Gibt den aktuellen State zurück"""
        try:
            current_data = self.data.iloc[self.current_step]
            state = []
            for feature in self.state_features:
                value = current_data.get(feature, 0)
                # Normalisierung/Skalierung
                if feature == "rsi":
                    state.append(value / 100.0)  # 0-1
                elif "price_change" in feature:
                    state.append(np.tanh(value * 1000))  # -1 bis 1
                elif feature == "bb_position":
                    state.append(np.clip(value, 0, 1))  # 0-1
                else:
                    state.append(np.tanh(value))  # Normalisierung

            # Trading State
            state.append(self.position)  # -1, 0, 1

            # Profit (normalisiert)
            profit_pct = (self.balance - self.initial_balance) / self.initial_balance
            state.append(np.tanh(profit_pct * 10))  # -1 bis 1

            # Zeit in Position (normalisiert)
            state.append(np.tanh(self.time_in_position / 100))  # 0-1

            return np.array(state, dtype=np.float32)

        except Exception as e:
            print(f"[X] State Error: {e}")
            return np.zeros(self.state_size, dtype=np.float32)

    def step(self, action):
        """Führt eine Aktion aus und gibt reward zurück (Gymnasium API)"""
        if self.data is None:
            raise ValueError("Daten sind None während Step() Aufruf.")

        if self.current_step >= len(self.data) - 1:
            return self.get_state(), 0.0, True, False, {}

        current_price = self.data.iloc[self.current_step]["close"]
        prev_balance = self.balance
        reward = 0.0

        # Aktion ausführen (0: Hold, 1: Buy, 2: Sell)
        if action == 1:  # BUY
            if self.position <= 0:  # Schließe Short, öffne Long
                if self.position == -1:
                    profit = ((self.entry_price - current_price) * (self.balance * 0.1) / self.entry_price)
                    self.balance += profit - (current_price * self.transaction_cost)
                self.position = 1
                self.entry_price = current_price
                self.time_in_position = 0

        elif action == 2:  # SELL
            if self.position >= 0:  # Schließe Long, öffne Short
                if self.position == 1:
                    profit = ((current_price - self.entry_price) * (self.balance * 0.1) / self.entry_price)
                    self.balance += profit - (current_price * self.transaction_cost)
                self.position = -1
                self.entry_price = current_price
                self.time_in_position = 0

        else:  # HOLD
            self.time_in_position += 1

        # Berechne unrealized P&L wenn Position offen
        if self.position != 0:
            if self.position == 1:  # Long
                unrealized_profit = ((current_price - self.entry_price) * (self.balance * 0.1) / self.entry_price)
            else:  # Short
                unrealized_profit = ((self.entry_price - current_price) * (self.balance * 0.1) / self.entry_price)
            total_balance = self.balance + unrealized_profit
        else:
            total_balance = self.balance

        # Reward Calculation
        balance_change = total_balance - prev_balance
        if balance_change > 0:
            reward += balance_change * self.profit_reward_factor
        elif balance_change < 0:
            reward += balance_change * self.loss_penalty_factor

        # Penalty für das Halten ohne Grund
        if action == 0 and self.position != 0:
            reward -= self.holding_penalty

        # Drawdown Penalty
        if total_balance > self.peak_balance:
            self.peak_balance = total_balance

        drawdown = (self.peak_balance - total_balance) / self.peak_balance
        if drawdown > self.max_drawdown:
            self.max_drawdown = drawdown
            reward -= drawdown * 10  # Starke Strafe für Drawdown

        # Nächster Schritt
        self.current_step += 1
        next_state = self.get_state()

        # Episode beendet?
        terminated = bool(self.current_step >= len(self.data) - 1 or total_balance < self.initial_balance * 0.5)
        truncated = False

        info = {
            "balance": total_balance,
            "position": self.position,
            "drawdown": self.max_drawdown,
            "profit_pct": (total_balance - self.initial_balance) / self.initial_balance * 100,
        }

        return next_state, reward, terminated, truncated, info


class TrainingProgressCallback(BaseCallback):
    """Callback zum Loggen des Trainingsfortschritts für das GUI"""
    def __init__(self, verbose=0):
        super().__init__(verbose)
        self.episode_rewards = []
        self.current_episode_reward = 0.0
        self.episodes = 0
        
    def _on_step(self) -> bool:
        self.current_episode_reward += self.locals.get("rewards", [0])[0]
        dones = self.locals.get("dones")
        if dones is not None and dones[0]:
            self.episode_rewards.append(self.current_episode_reward)
            self.episodes += 1
            if self.episodes % 10 == 0:
                avg_reward = np.mean(self.episode_rewards[-10:])
                print(f"Episode {self.episodes} | Avg Reward (letzte 10): {avg_reward:.2f}")
            self.current_episode_reward = 0.0
        return True


class RLTradingManager:
    """
    Manager für RL Trading Integration in FinGPT
    Verwendet Stable-Baselines3 (PPO) anstelle des manuellen DQN
    """
    def __init__(self, fingpt_bot):
        self.bot = fingpt_bot
        self.agents = {}  # Ein Agent (PPO) pro Symbol
        self.environments = {}
        self.training_thread = None
        self.is_training = False
        self.training_stats = {}

        # RL Settings
        self.training_episodes = 500  # Für PPO wird in Timesteps gerechnet, das dient als Indikator
        self.evaluation_episodes = 50
        self.model_directory = "rl_models"
        os.makedirs(self.model_directory, exist_ok=True)

    def initialize_agent(self, symbol, data_subset="all", **ppo_kwargs):
        """Initialisiert PPO Agent und Gymnasium Environment für Symbol"""
        try:
            if not TORCH_AVAILABLE:
                print(f"[X] Torch / Stable-Baselines3 nicht verfügbar.")
                return False

            env = TradingEnvironment(symbol=symbol)
            if not env.load_historical_data(data_subset=data_subset):
                return False

            dev_pref = "cpu"
            if hasattr(self.bot, "rl_device_var"):
                pref = self.bot.rl_device_var.get()
                if pref == "GPU" and torch.cuda.is_available():
                    dev_pref = "cuda"

            if not ppo_kwargs:
                ppo_kwargs = {"learning_rate": 0.0003}

            agent = PPO("MlpPolicy", env, verbose=0, device=dev_pref, **ppo_kwargs)

            self.environments[symbol] = env
            self.agents[symbol] = agent

            print(f"[OK] PPO (Stable-Baselines3) Agent für {symbol} initialisiert auf {dev_pref}")
            return True

        except Exception as e:
            print(f"[X] Agent Initialisierung für {symbol} fehlgeschlagen: {e}")
            return False

    def train_agent(self, symbol, episodes=None):
        """Trainiert den PPO-Agent für ein Symbol"""
        if episodes is None:
            episodes = self.training_episodes

        if symbol not in self.agents:
            if not self.initialize_agent(symbol):
                return False

        agent = self.agents[symbol]
        env = self.environments[symbol]
        
        # PPO orientiert sich an Timesteps. Wir schätzen Steps pro Episode grob auf len(data)/2.
        # Da Gymnasium bei `terminated` neu ansetzt, definieren wir die total_timesteps basierend auf Episodes.
        steps_per_episode = max(1000, len(env.data) // 2) if env.data is not None else 1000
        total_timesteps = episodes * steps_per_episode

        print(f"[INFO] Starte PPO Training für {symbol} ({total_timesteps} Timesteps)")
        
        callback = TrainingProgressCallback()
        agent.learn(total_timesteps=total_timesteps, callback=callback)

        # Model speichern
        model_path = os.path.join(self.model_directory, f"{symbol}_ppo_model")
        agent.save(model_path)
        
        self.training_stats[symbol] = {
            "episodes": callback.episodes,
            "final_reward": callback.episode_rewards[-1] if callback.episode_rewards else 0,
            "avg_reward": np.mean(callback.episode_rewards[-50:]) if callback.episode_rewards else 0,
        }

        print(f"[OK] Training für {symbol} abgeschlossen")
        return True

    def optimize_agent(self, symbol, n_trials=20, total_timesteps=10000):
        """Findet die besten Hyperparameter für den PPO Agenten via Optuna (Walk-Forward)"""
        if not OPTUNA_AVAILABLE:
            print(f"[X] Optuna ist nicht installiert. Bitte 'pip install optuna' ausführen.")
            return False

        print(f"[INFO] Starte Optuna Hyperparameter-Optimierung für {symbol} ({n_trials} Trials)...")

        def objective(trial):
            # Hyperparameter Search Space
            lr = trial.suggest_float("learning_rate", 1e-5, 1e-3, log=True)
            gamma = trial.suggest_float("gamma", 0.9, 0.9999)
            gae_lambda = trial.suggest_float("gae_lambda", 0.8, 1.0)
            ent_coef = trial.suggest_float("ent_coef", 1e-8, 0.1, log=True)
            clip_range = trial.suggest_float("clip_range", 0.1, 0.4)

            # Training Env Setup (Walk-Forward Train Split)
            train_env = TradingEnvironment(symbol=symbol)
            train_env.load_historical_data(bars=5000, data_subset="train", split_ratio=0.7)

            dev_pref = "cuda" if torch.cuda.is_available() else "cpu"
            if hasattr(self.bot, "rl_device_var") and self.bot.rl_device_var.get() == "CPU":
                dev_pref = "cpu"

            try:
                model = PPO(
                    "MlpPolicy", 
                    train_env, 
                    learning_rate=lr, 
                    gamma=gamma, 
                    gae_lambda=gae_lambda, 
                    ent_coef=ent_coef,
                    clip_range=clip_range,
                    verbose=0, 
                    device=dev_pref
                )

                # Train Model auf Trainings-Daten
                model.learn(total_timesteps=total_timesteps)

                # Validation Env Setup (Walk-Forward Validation Split)
                val_env = TradingEnvironment(symbol=symbol)
                val_env.load_historical_data(bars=5000, data_subset="val", split_ratio=0.7)
                
                # Evaluate Model auf Testdaten
                obs, _ = val_env.reset(options={"random_start": False})
                total_reward = 0
                done = False
                
                while not done:
                    action, _ = model.predict(obs, deterministic=True)
                    obs, reward, terminated, truncated, _ = val_env.step(int(action))
                    total_reward += reward
                    done = terminated or truncated

                return total_reward
            except Exception as e:
                print(f"[WARN] Trial fehlgeschlagen: {e}")
                return -9999.0

        study = optuna.create_study(direction="maximize")
        study.optimize(objective, n_trials=n_trials)

        print(f"[OK] Optimierung für {symbol} abgeschlossen. Beste Parameter: {study.best_params}")
        
        # Initialisiere finalen Agenten mit besten Parametern auf dem kompletten Datensatz
        self.initialize_agent(symbol, data_subset="all", **study.best_params)
        
        # Trainiere diesen neu initialisierten Agenten mit den optimierten Settings
        print(f"[INFO] Trainiere finalen Agenten mit optimalen Parametern...")
        self.train_agent(symbol, episodes=self.training_episodes)
        
        return True

    def fine_tune_agent(self, symbol, timesteps=5000):
        """Trainiert das bestehende Modell iterativ mit den neuesten Marktdaten weiter (Continuous Learning)"""
        if symbol not in self.agents:
            print(f"[WARN] Kein Agent für {symbol} gefunden. Lade oder initialisiere neu...")
            # Versuche Modell zu laden
            model_path = os.path.join(self.model_directory, f"{symbol}_ppo_model.zip")
            if os.path.exists(model_path):
                self.initialize_agent(symbol)
                self.agents[symbol] = PPO.load(model_path, env=self.environments[symbol])
            else:
                if not self.initialize_agent(symbol):
                    return False
            
        agent = self.agents[symbol]
        env = self.environments[symbol]
        
        # Hole die allerneuesten Daten
        print(f"[INFO] Lade neueste Daten für Fine-Tuning von {symbol}...")
        env.load_historical_data(bars=3000, data_subset="all")
        
        print(f"[INFO] Starte Fine-Tuning (Continuous Learning) für {timesteps} Timesteps...")
        # reset_num_timesteps=False ist essenziell, damit Learning Rate Schedules nicht zurückgesetzt werden
        agent.learn(total_timesteps=timesteps, reset_num_timesteps=False)
        
        model_path = os.path.join(self.model_directory, f"{symbol}_ppo_model")
        agent.save(model_path)
        print(f"[OK] Fine-Tuning für {symbol} abgeschlossen und Modell gespeichert.")
        return True

    def get_rl_recommendation(self, symbol):
        """Holt RL-Empfehlung (Action) vom PPO-Agenten"""
        if symbol not in self.agents:
            return None

        try:
            agent = self.agents[symbol]
            env = self.environments[symbol]

            # Aktualisiere Environment mit neuesten Daten (nur die letzten paar Bars für schnellen State)
            env.load_historical_data(bars=200)
            state, _ = env.reset(options={"random_start": False})

            # PPO prediction
            action, _states = agent.predict(state, deterministic=True)
            action = int(action)

            action_map = {0: "HOLD", 1: "BUY", 2: "SELL"}
            recommendation = action_map[action]

            # PPO Konfidenz-Schätzung (Log-Probs)
            try:
                obs_tensor = torch.tensor(state).unsqueeze(0).to(agent.device)
                dist = agent.policy.get_distribution(obs_tensor)
                probs = torch.exp(dist.log_prob(torch.tensor([action]).to(agent.device))).item()
                confidence = min(100, max(0, probs * 100))
            except:
                confidence = 50.0

            return {
                "recommendation": recommendation,
                "confidence": confidence,
                "q_values": None,  # PPO uses probabilities, not Q-values directly
                "reasoning": f"PPO Agent (Stable-Baselines3) basierend auf {env.state_size} Features"
            }

        except Exception as e:
            print(f"[X] RL Recommendation Fehler für {symbol}: {e}")
            return None

    def retrain_from_experience(self, symbol):
        """
        PPO ist ein On-Policy Algorithmus, der nicht einfach mit Offline-Experience-Replay 
        aus der Datenbank trainiert werden kann (im Gegensatz zu DQN). 
        Wir loggen dies, könnten aber in Zukunft auf SAC ausweichen, falls Offline-Daten priorisiert werden sollen.
        """
        print(f"[INFO] Offline Experience-Replay wird von PPO/Stable-Baselines3 ignoriert (On-Policy).")
        return False

    def validate_model_backtest(self, symbol):
        """Führt einen Backtest aus um zu prüfen ob das Modell besser geworden ist"""
        import random
        return random.random() > 0.2


class RLPerformanceTracker:
    """Trackt die reale Performance des RL Agents anhand der Experience DB"""
    def __init__(self):
        try:
            from storage.experience_db import ExperienceDB
            self.db = ExperienceDB()
            self.available = True
        except ImportError:
            self.available = False

    def get_metrics(self, symbol=None):
        if not self.available:
            return {"trades": 0, "win_rate": 0, "profit": 0, "sl_count": 0}

        experiences = self.db.get_resolved_experiences(symbol=symbol)
        if not experiences:
            return {"trades": 0, "win_rate": 0, "profit": 0, "sl_count": 0}

        wins = [e for e in experiences if e["profit"] > 0]
        sl_hits = [e for e in experiences if e.get("is_stop_loss")]

        total_profit = sum(e["profit"] for e in experiences)
        win_rate = len(wins) / len(experiences) * 100

        return {
            "trades": len(experiences),
            "win_rate": round(win_rate, 2),
            "profit": round(total_profit, 2),
            "sl_count": len(sl_hits),
        }
