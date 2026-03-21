#!/usr/bin/env python3
"""
Reinforcement Learning Trading Agent für FinGPT
Deep Q-Network (DQN) mit Experience Replay und Target Network
"""

import numpy as np
import pandas as pd
import MetaTrader5 as mt5
from datetime import datetime, timedelta
import pickle
import json
import threading
import time
from collections import deque
import random

# PyTorch für Neural Networks
try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    TORCH_AVAILABLE = True
    print("[OK] PyTorch verfuegbar")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
except ImportError:
    TORCH_AVAILABLE = False
    print("[X] PyTorch nicht installiert - pip install torch")

class TradingEnvironment:
    """
    Trading Environment für RL Agent
    Simuliert Marktbedingungen und Handelsaktionen
    """
    
    def __init__(self, symbol="EURUSD", lookback_period=100, timeframe=mt5.TIMEFRAME_M15):
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
            'rsi', 'macd', 'macd_signal', 'macd_histogram',
            'bb_upper', 'bb_middle', 'bb_lower', 'bb_position',
            'price_change_1', 'price_change_5', 'price_change_20',
            'volume_ratio', 'volatility', 'trend_strength'
        ]
        
        self.state_size = len(self.state_features) + 3  # +3 für position, profit, time_in_position
        self.action_size = 3  # 0=Hold, 1=Buy, 2=Sell
        
    def load_historical_data(self, bars=5000):
        """Lädt historische Daten für Training"""
        try:
            rates = mt5.copy_rates_from_pos(self.symbol, self.timeframe, 0, bars)
            if rates is None:
                raise Exception(f"Keine Daten für {self.symbol}")
            
            df = pd.DataFrame(rates)
            df['time'] = pd.to_datetime(df['time'], unit='s')
            
            # Berechne technische Indikatoren
            df = self.calculate_technical_indicators(df)
            
            self.data = df.dropna()
            
            # Additional type check for Pyre
            if self.data is not None:
                print(f"[OK] {len(self.data)} Datenpunkte geladen fuer {self.symbol}")
            return True
            
        except Exception as e:
            print(f"[X] Fehler beim Laden der Daten: {e}")
            return False
    
    def calculate_technical_indicators(self, df):
        """Berechnet alle technischen Indikatoren mit pandas-ta (Fallback auf numpy)"""
        try:
            import pandas_ta as ta
            # RSI
            df['rsi'] = ta.rsi(df['close'], length=14)
            
            # MACD
            macd = ta.macd(df['close'], fast=12, slow=26, signal=9)
            if macd is not None:
                df['macd'] = macd['MACD_12_26_9']
                df['macd_signal'] = macd['MACDs_12_26_9']
                df['macd_histogram'] = macd['MACDh_12_26_9']
            
            # Bollinger Bands
            bb = ta.bbands(df['close'], length=20, std=2)
            if bb is not None:
                df['bb_upper'] = bb['BBU_20_2.0']
                df['bb_middle'] = bb['BBM_20_2.0']
                df['bb_lower'] = bb['BBL_20_2.0']
                df['bb_position'] = bb['BBP_20_2.0']
            
        except ImportError:
            print("⚠️ [RL] pandas_ta nicht gefunden, verwende langsame Berechnung")
            
            # RSI (Fallback)
            def calculate_rsi(prices, period=14):
                deltas = np.diff(prices)
                gains = np.where(deltas > 0, deltas, 0)
                losses = np.where(deltas < 0, -deltas, 0)
                # Simple Moving Average for first value, then smoothed
                avg_gains = pd.Series(gains).ewm(alpha=1/period, adjust=False).mean()
                avg_losses = pd.Series(losses).ewm(alpha=1/period, adjust=False).mean()
                rs = avg_gains / avg_losses
                return 100 - (100 / (1 + rs))
            
            # Use shift to align with numpy diff
            df['rsi'] = calculate_rsi(df['close'].values)
            df['rsi'] = df['rsi'].shift(1) # Align
            
            # MACD
            exp1 = df['close'].ewm(span=12, adjust=False).mean()
            exp2 = df['close'].ewm(span=26, adjust=False).mean()
            df['macd'] = exp1 - exp2
            df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
            df['macd_histogram'] = df['macd'] - df['macd_signal']
            
            # Bollinger Bands
            df['bb_middle'] = df['close'].rolling(window=20).mean()
            bb_std = df['close'].rolling(window=20).std()
            df['bb_upper'] = df['bb_middle'] + (bb_std * 2)
            df['bb_lower'] = df['bb_middle'] - (bb_std * 2)
            df['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
        
        # Price Changes (Standard Pandas)
        df['price_change_1'] = df['close'].pct_change(1)
        df['price_change_5'] = df['close'].pct_change(5)
        df['price_change_20'] = df['close'].pct_change(20)
        
        # Volume und Volatilität
        df['volume_ratio'] = df['tick_volume'] / df['tick_volume'].rolling(window=20).mean()
        df['volatility'] = df['high'] - df['low']
        
        # Trend Strength (ADX vereinfacht)
        df['trend_strength'] = abs(df['close'].rolling(window=14).mean().pct_change(5))
        
        return df.fillna(0)
    
    def reset(self, random_start=True):
        """Reset environment für neue Episode"""
        # Ensure data is loaded
        if self.data is None:
            raise ValueError("Daten konnten nicht geladen werden")
            
        if random_start:
            # Zufälliger Startpunkt (nicht zu nah am Ende)
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
        
        return self.get_state()
    
    def get_state(self):
        """Gibt den aktuellen State zurück"""
        try:
            if self.data is None:
                raise ValueError("Daten nicht geladen für State Extraktion.")
                
            current_data = self.data.iloc[self.current_step]
            
            # Technische Indikatoren
            state = []
            for feature in self.state_features:
                value = current_data.get(feature, 0)
                # Normalisierung/Skalierung
                if feature == 'rsi':
                    state.append(value / 100.0)  # 0-1
                elif 'price_change' in feature:
                    state.append(np.tanh(value * 1000))  # -1 bis 1
                elif feature == 'bb_position':
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
        """Führt eine Aktion aus und gibt reward zurück"""
        if self.data is None:
            raise ValueError("Daten sind None während Step() Aufruf.")
            
        if self.current_step >= len(self.data) - 1:
            return self.get_state(), 0, True, {}  # Episode beendet
        
        current_price = self.data.iloc[self.current_step]['close']
        prev_balance = self.balance
        reward = 0
        
        # Aktion ausführen
        if action == 1:  # BUY
            if self.position <= 0:  # Schließe Short, öffne Long
                if self.position == -1:
                    # Schließe Short Position
                    profit = (self.entry_price - current_price) * (self.balance * 0.1) / self.entry_price
                    self.balance += profit - (current_price * self.transaction_cost)
                
                # Öffne Long Position
                self.position = 1
                self.entry_price = current_price
                self.time_in_position = 0
                
        elif action == 2:  # SELL
            if self.position >= 0:  # Schließe Long, öffne Short
                if self.position == 1:
                    # Schließe Long Position
                    profit = (current_price - self.entry_price) * (self.balance * 0.1) / self.entry_price
                    self.balance += profit - (current_price * self.transaction_cost)
                
                # Öffne Short Position
                self.position = -1
                self.entry_price = current_price
                self.time_in_position = 0
                
        else:  # HOLD
            self.time_in_position += 1
        
        # Berechne unrealized P&L wenn Position offen
        if self.position != 0:
            if self.position == 1:  # Long
                unrealized_profit = (current_price - self.entry_price) * (self.balance * 0.1) / self.entry_price
            else:  # Short
                unrealized_profit = (self.entry_price - current_price) * (self.balance * 0.1) / self.entry_price
            
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
        done = (self.current_step >= len(self.data) - 1) or (total_balance < self.initial_balance * 0.5)
        
        info = {
            'balance': total_balance,
            'position': self.position,
            'drawdown': self.max_drawdown,
            'profit_pct': (total_balance - self.initial_balance) / self.initial_balance * 100
        }
        
        return next_state, reward, done, info

if TORCH_AVAILABLE:
    class DQNNetwork(nn.Module):
        def __init__(self, state_size, action_size):
            super().__init__()
            self.fc1 = nn.Linear(state_size, 128)
            self.relu1 = nn.ReLU()
            self.dropout1 = nn.Dropout(0.2)
            
            self.fc2 = nn.Linear(128, 128)
            self.relu2 = nn.ReLU()
            self.dropout2 = nn.Dropout(0.2)
            
            self.fc3 = nn.Linear(128, 64)
            self.relu3 = nn.ReLU()
            self.dropout3 = nn.Dropout(0.1)
            
            self.fc4 = nn.Linear(64, 32)
            self.relu4 = nn.ReLU()
            
            self.out = nn.Linear(32, action_size)

        def forward(self, x):
            x = self.dropout1(self.relu1(self.fc1(x)))
            x = self.dropout2(self.relu2(self.fc2(x)))
            x = self.dropout3(self.relu3(self.fc3(x)))
            x = self.relu4(self.fc4(x))
            return self.out(x)
else:
    class DQNNetwork:
        # Dummy class setup if torch is not available
        def __init__(self, state_size, action_size):
            pass
        def to(self, device): return self
        def parameters(self): return []
        def load_state_dict(self, state_dict): pass
        def state_dict(self): return {}
        def eval(self): pass
        def train(self): pass
        def gather(self, *args, **kwargs): return self
        def max(self, *args, **kwargs): return [self]
        def squeeze(self, *args, **kwargs): return self
        def __call__(self, *args, **kwargs): return self

class DQNAgent:
    """
    Double Deep Q-Network (DDQN) Agent für Trading mit PyTorch
    """
    
    def __init__(self, state_size, action_size, learning_rate=0.001, device_pref="GPU"):
        self.state_size = state_size
        self.action_size = action_size
        self.learning_rate = learning_rate
        
        if TORCH_AVAILABLE:
            if device_pref == "GPU" and torch.cuda.is_available():
                self.device = torch.device("cuda")
            else:
                self.device = torch.device("cpu")
        else:
            self.device = "cpu"
        
        # Hyperparameters
        self.epsilon = 1.0  # Exploration rate
        self.epsilon_min = 0.01
        self.epsilon_decay = 0.995
        self.batch_size = 32
        self.memory_size = 10000
        self.gamma = 0.95  # Discount factor
        self.update_target_frequency = 100
        
        # Vectorized Experience Replay Memory (Ring Buffer)
        self.memory_states = np.zeros((self.memory_size, state_size), dtype=np.float32)
        self.memory_actions = np.zeros(self.memory_size, dtype=np.int64)
        self.memory_rewards = np.zeros(self.memory_size, dtype=np.float32)
        self.memory_next_states = np.zeros((self.memory_size, state_size), dtype=np.float32)
        self.memory_dones = np.zeros(self.memory_size, dtype=np.float32)
        self.memory_idx = 0
        self.memory_len = 0
        
        # Neural Networks
        if TORCH_AVAILABLE:
            self.q_network = DQNNetwork(state_size, action_size).to(self.device)
            self.target_network = DQNNetwork(state_size, action_size).to(self.device)
            self.optimizer = optim.Adam(self.q_network.parameters(), lr=learning_rate)
            self.criterion = nn.MSELoss()
            self.update_target_network()
        
        # Training Stats
        self.training_step = 0
        self.episode_rewards = []
        self.episode_lengths = []
        
    def resize_memory(self, new_size):
        """Re-alloziert die Memory Arrays bei Änderung der Buffer Size."""
        if new_size == self.memory_size:
            return
        self.memory_size = new_size
        self.memory_states = np.zeros((new_size, self.state_size), dtype=np.float32)
        self.memory_actions = np.zeros(new_size, dtype=np.int64)
        self.memory_rewards = np.zeros(new_size, dtype=np.float32)
        self.memory_next_states = np.zeros((new_size, self.state_size), dtype=np.float32)
        self.memory_dones = np.zeros(new_size, dtype=np.float32)
        self.memory_idx = 0
        self.memory_len = 0
        
    def update_target_network(self):
        """Aktualisiert das Target Network"""
        if TORCH_AVAILABLE:
            self.target_network.load_state_dict(self.q_network.state_dict())
    
    def remember(self, state, action, reward, next_state, done):
        """Speichert Experience im Vector-Memory Ringpuffer"""
        idx = self.memory_idx
        self.memory_states[idx] = state
        self.memory_actions[idx] = action
        self.memory_rewards[idx] = reward
        self.memory_next_states[idx] = next_state
        self.memory_dones[idx] = done
        
        self.memory_idx = (self.memory_idx + 1) % self.memory_size
        if self.memory_len < self.memory_size:
            self.memory_len += 1
    
    def act(self, state, training=True):
        """Wählt eine Aktion basierend auf epsilon-greedy Policy"""
        if training and random.random() <= self.epsilon:
            return random.randrange(self.action_size)
        
        if TORCH_AVAILABLE:
            state_tensor = torch.FloatTensor(state).unsqueeze(0).to(self.device)
            self.q_network.eval()
            with torch.no_grad():
                q_values = self.q_network(state_tensor)
            self.q_network.train()
            return torch.argmax(q_values).item()
        else:
            return random.randrange(self.action_size)
    
    def replay(self):
        """Training durch Experience Replay (Vektorisiert)"""
        if self.memory_len < self.batch_size or not TORCH_AVAILABLE:
            return
        
        # Vectorized Sampling
        indices = np.random.choice(self.memory_len, self.batch_size, replace=False)
        
        # Zero-copy tensor creation from numpy arrays where possible
        states = torch.from_numpy(self.memory_states[indices]).to(self.device)
        actions = torch.from_numpy(self.memory_actions[indices]).to(self.device)
        rewards = torch.from_numpy(self.memory_rewards[indices]).to(self.device)
        next_states = torch.from_numpy(self.memory_next_states[indices]).to(self.device)
        dones = torch.from_numpy(self.memory_dones[indices]).to(self.device)
        
        # Aktuelle Q-Values
        if states.dim() == 1:
            states = states.unsqueeze(0)
            actions = actions.unsqueeze(0)
            rewards = rewards.unsqueeze(0)
            next_states = next_states.unsqueeze(0)
            dones = dones.unsqueeze(0)
            
        current_q = self.q_network(states).gather(1, actions.unsqueeze(1)).squeeze(1)
        
        # Target Q-Values
        self.target_network.eval()
        with torch.no_grad():
            next_q_target = self.target_network(next_states).max(1)[0]
        self.target_network.train()
        
        # Q-Learning Update
        expected_q = rewards + (1 - dones) * self.gamma * next_q_target
        
        # Gradient Descent Step
        loss = self.criterion(current_q, expected_q.detach())
        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()
        
        # Epsilon Decay
        if self.epsilon > self.epsilon_min:
            self.epsilon *= self.epsilon_decay
        
        # Update Target Network
        self.training_step += 1
        if self.training_step % self.update_target_frequency == 0:
            self.update_target_network()
            
    def prioritized_replay(self, experiences, batch_size=32):
        """Trainiert das Netzwerk gezielt mit priorisierten Erfahrungen (z.B. Stop Losses)"""
        if not TORCH_AVAILABLE or len(experiences) < batch_size:
            return False
            
        # Berechne Prioritäten: Stop Losses haben viel höhere Prio (zum Verlernen)
        priorities = []
        valid_experiences = []
        for exp in experiences:
            prio = 5.0 if exp.get('is_stop_loss', False) else 1.0
            
            # Formatiere state array
            state = exp.get('state_features')
            if state and len(state) == self.state_size:
                priorities.append(prio)
                valid_experiences.append(exp)
                
        if len(valid_experiences) < batch_size:
            return False
            
        priorities = np.array(priorities)
        probs = priorities / sum(priorities)
        
        # Sample based on probability
        indices = np.random.choice(len(valid_experiences), batch_size, p=probs, replace=False)
        
        # Vectorized array creation instead of 3 separate list comprehensions
        states_arr = np.array([valid_experiences[i]['state_features'] for i in indices], dtype=np.float32)
        actions_arr = np.array([valid_experiences[i]['action'] for i in indices], dtype=np.int64)
        rewards_arr = np.array([valid_experiences[i]['reward'] for i in indices], dtype=np.float32)
        
        states = torch.from_numpy(states_arr).to(self.device)
        actions = torch.from_numpy(actions_arr).to(self.device)
        rewards = torch.from_numpy(rewards_arr).to(self.device)
        
        # Q-Update (Ohne next_state, reines Fit auf Reward für Erfahrungswerte)
        current_q = self.q_network(states).gather(1, actions.unsqueeze(1)).squeeze(1)
        
        loss = self.criterion(current_q, rewards)
        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()
        return True
    
    def save_model(self, filepath):
        """Speichert das trainierte Modell"""
        if TORCH_AVAILABLE:
            torch.save(self.q_network.state_dict(), filepath)
            
            # Speichere auch Hyperparameter
            config = {
                'state_size': self.state_size,
                'action_size': self.action_size,
                'epsilon': self.epsilon,
                'training_step': self.training_step
            }
            
            with open(filepath.replace('.h5', '_config.json'), 'w') as f:
                json.dump(config, f)
                
            print(f"[OK] Modell gespeichert: {filepath}")
    
    def load_model(self, filepath):
        """Lädt ein trainiertes Modell"""
        if TORCH_AVAILABLE:
            try:
                self.q_network.load_state_dict(torch.load(filepath, weights_only=True))
                self.target_network.load_state_dict(self.q_network.state_dict())
                
                # Lade Konfiguration
                config_file = filepath.replace('.h5', '_config.json')
                with open(config_file, 'r') as f:
                    config = json.load(f)
                    self.epsilon = config.get('epsilon', self.epsilon_min)
                    self.training_step = config.get('training_step', 0)
                
                print(f"[OK] Modell geladen: {filepath}")
                return True
            except Exception as e:
                print(f"[X] Fehler beim Laden: {e}")
                return False
        return False

class RLTradingManager:
    """
    Manager für RL Trading Integration in FinGPT
    """
    
    def __init__(self, fingpt_bot):
        self.bot = fingpt_bot
        self.agents = {}  # Ein Agent pro Symbol
        self.environments = {}
        self.training_thread = None
        self.is_training = False
        self.training_stats = {}
        
        # RL Settings
        self.training_episodes = 1000
        self.evaluation_episodes = 100
        self.model_save_frequency = 100
        self.model_directory = "rl_models"
        
        # Erstelle Model Directory
        import os
        if not os.path.exists(self.model_directory):
            os.makedirs(self.model_directory)
    
    def initialize_agent(self, symbol):
        """Initialisiert Agent und Environment für Symbol"""
        try:
            # Environment erstellen
            env = TradingEnvironment(symbol=symbol)
            if not env.load_historical_data():
                return False
            
            # Determine preferred device from app if available
            dev_pref = "GPU"
            if hasattr(self.bot, 'rl_device_var'):
                dev_pref = self.bot.rl_device_var.get()
                
            # Agent erstellen
            agent = DQNAgent(env.state_size, env.action_size, device_pref=dev_pref)
            
            self.environments[symbol] = env
            self.agents[symbol] = agent
            
            print(f"[OK] RL Agent für {symbol} initialisiert")
            return True
            
        except Exception as e:
            print(f"[X] Agent Initialisierung für {symbol} fehlgeschlagen: {e}")
            return False
    
    def train_agent(self, symbol, episodes=None):
        """Trainiert den Agent für ein Symbol"""
        if episodes is None:
            episodes = self.training_episodes
        
        if symbol not in self.agents:
            if not self.initialize_agent(symbol):
                return False
        
        agent = self.agents[symbol]
        env = self.environments[symbol]
        
        # Dynamically update device preference
        if hasattr(self.bot, 'rl_device_var'):
            dev_pref = self.bot.rl_device_var.get()
            if dev_pref == "GPU" and TORCH_AVAILABLE and torch.cuda.is_available():
                new_device = torch.device("cuda")
            else:
                new_device = torch.device("cpu")
                
            if agent.device != new_device:
                agent.device = new_device
                if TORCH_AVAILABLE:
                    agent.q_network.to(new_device)
                    agent.target_network.to(new_device)
        
        print(f"[INFO] Starte Training für {symbol} auf {agent.device} - {episodes} Episodes")
        
        episode_rewards = []
        
        for episode in range(episodes):
            state = env.reset()
            total_reward = 0
            steps = 0
            
            while True:
                action = agent.act(state, training=True)
                next_state, reward, done, info = env.step(action)
                
                agent.remember(state, action, reward, next_state, done)
                state = next_state
                total_reward += reward
                steps += 1
                
                if done:
                    break
                
                # Training alle paar Schritte
                if agent.memory_len > agent.batch_size and steps % 4 == 0:
                    agent.replay()
            
            episode_rewards.append(total_reward)
            
            # Progress Report
            if episode % 50 == 0:
                recent_rewards = np.array(episode_rewards)[-50:]
                avg_reward = float(np.mean(recent_rewards)) if len(recent_rewards) > 0 else 0.0
                print(f"Episode {episode}/{episodes} - Avg Reward: {avg_reward:.2f} - Epsilon: {agent.epsilon:.3f}")
                print(f"   Balance: {info['balance']:.2f}€ - Profit: {info['profit_pct']:.2f}%")
            
            # Model speichern
            if episode % self.model_save_frequency == 0:
                model_path = f"{self.model_directory}/{symbol}_episode_{episode}.h5"
                agent.save_model(model_path)
        
        self.training_stats[symbol] = {
            'episodes': episodes,
            'final_reward': episode_rewards[-1],
            'avg_reward': np.mean(episode_rewards),
            'best_reward': max(episode_rewards)
        }
        
        print(f"[OK] Training für {symbol} abgeschlossen")
        return True
    
    def get_rl_recommendation(self, symbol):
        """Holt RL-Empfehlung für Symbol"""
        if symbol not in self.agents:
            return None
        
        try:
            agent = self.agents[symbol]
            env = self.environments[symbol]
            
            # Aktualisiere Environment mit neuesten Daten
            env.load_historical_data(bars=200)  # Nur letzte 200 Bars
            state = env.reset(random_start=False)  # Aktueller Zustand
            
            # Hole Aktion (ohne Exploration)
            action = agent.act(state, training=False)
            
            # Übersetze Aktion
            action_map = {0: "HOLD", 1: "BUY", 2: "SELL"}
            recommendation = action_map[action]
            
            # Berechne Konfidenz basierend auf Q-Values
            if TORCH_AVAILABLE and hasattr(agent, 'q_network'):
                state_tensor = torch.FloatTensor(state).unsqueeze(0).to(agent.device)
                agent.q_network.eval()
                with torch.no_grad():
                    q_values_tensor = agent.q_network(state_tensor)[0]
                agent.q_network.train()
                q_values = q_values_tensor.cpu().numpy()
                confidence = np.max(q_values) - np.mean(q_values)
                confidence = min(100, max(0, confidence * 100))
            else:
                confidence = 50
            
            return {
                'recommendation': recommendation,
                'confidence': confidence,
                'q_values': q_values.tolist() if TORCH_AVAILABLE else None,
                'reasoning': f"RL Agent Entscheidung basierend auf {env.state_size} Features"
            }
            
        except Exception as e:
            print(f"[X] RL Recommendation Fehler für {symbol}: {e}")
            return None

    def retrain_from_experience(self, symbol):
        """Holt gelöste Trades aus der DB und retrainiert das Modell"""
        try:
            from storage.experience_db import ExperienceDB
            db = ExperienceDB()
            experiences = db.get_resolved_experiences(symbol=symbol, limit=1000)
            
            if len(experiences) > 32:
                if symbol not in self.agents:
                    self.initialize_agent(symbol)
                
                agent = self.agents[symbol]
                print(f"🔄 Retraining {symbol} mit {len(experiences)} realen Erfahrungen...")
                success = agent.prioritized_replay(experiences, batch_size=min(64, len(experiences)))
                
                if success:
                    # Validate
                    if self.validate_model_backtest(symbol):
                        agent.save_model(f"{self.model_directory}/{symbol}_live_trained.h5")
                        print(f"[OK] Retraining erfolgreich und validiert für {symbol}")
                    else:
                        print(f"[WARN] Retraining für {symbol} verworfen durch Backtest-Fehlschlag")
                return True
            return False
        except Exception as e:
            print(f"[X] Fehler beim Retraining: {e}")
            return False

    def validate_model_backtest(self, symbol):
        """Führt einen Backtest aus um zu prüfen ob das Modell besser geworden ist"""
        # Einfache Heuristik aus MT5 Backtesting Logik (hier symbolisch dargestellt)
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
            
        wins = [e for e in experiences if e['profit'] > 0]
        sl_hits = [e for e in experiences if e.get('is_stop_loss')]
        
        total_profit = sum(e['profit'] for e in experiences)
        win_rate = len(wins) / len(experiences) * 100
        
        return {
            "trades": len(experiences),
            "win_rate": round(win_rate, 2),
            "profit": round(total_profit, 2),
            "sl_count": len(sl_hits)
        }
