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

# TensorFlow/Keras für Neural Networks
try:
    import tensorflow as tf
    from tensorflow import keras
    from tensorflow.keras import layers, optimizers
    TF_AVAILABLE = True
    print("✅ TensorFlow verfügbar")
except ImportError:
    TF_AVAILABLE = False
    print("[X] TensorFlow nicht installiert - pip install tensorflow")

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
            print(f"✅ {len(self.data)} Datenpunkte geladen für {self.symbol}")
            return True
            
        except Exception as e:
            print(f"❌ Fehler beim Laden der Daten: {e}")
            return False
    
    def calculate_technical_indicators(self, df):
        """Berechnet alle technischen Indikatoren"""
        
        # RSI
        def calculate_rsi(prices, period=14):
            deltas = np.diff(prices)
            gains = np.where(deltas > 0, deltas, 0)
            losses = np.where(deltas < 0, -deltas, 0)
            avg_gains = pd.Series(gains).rolling(window=period).mean()
            avg_losses = pd.Series(losses).rolling(window=period).mean()
            rs = avg_gains / avg_losses
            return 100 - (100 / (1 + rs))
        
        df['rsi'] = calculate_rsi(df['close'].values)
        
        # MACD
        exp1 = df['close'].ewm(span=12).mean()
        exp2 = df['close'].ewm(span=26).mean()
        df['macd'] = exp1 - exp2
        df['macd_signal'] = df['macd'].ewm(span=9).mean()
        df['macd_histogram'] = df['macd'] - df['macd_signal']
        
        # Bollinger Bands
        df['bb_middle'] = df['close'].rolling(window=20).mean()
        bb_std = df['close'].rolling(window=20).std()
        df['bb_upper'] = df['bb_middle'] + (bb_std * 2)
        df['bb_lower'] = df['bb_middle'] - (bb_std * 2)
        df['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
        
        # Price Changes
        df['price_change_1'] = df['close'].pct_change(1)
        df['price_change_5'] = df['close'].pct_change(5)
        df['price_change_20'] = df['close'].pct_change(20)
        
        # Volume und Volatilität
        df['volume_ratio'] = df['tick_volume'] / df['tick_volume'].rolling(window=20).mean()
        df['volatility'] = df['high'] - df['low']
        
        # Trend Strength (ADX vereinfacht)
        df['trend_strength'] = abs(df['close'].rolling(window=14).mean().pct_change(5))
        
        return df
    
    def reset(self, random_start=True):
        """Reset environment für neue Episode"""
        if self.data is None:
            self.load_historical_data()
        
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
            print(f"❌ State Error: {e}")
            return np.zeros(self.state_size, dtype=np.float32)
    
    def step(self, action):
        """Führt eine Aktion aus und gibt reward zurück"""
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

class DQNAgent:
    """
    Double Deep Q-Network (DDQN) Agent für Trading
    """
    
    def __init__(self, state_size, action_size, learning_rate=0.001):
        self.state_size = state_size
        self.action_size = action_size
        self.learning_rate = learning_rate
        
        # Hyperparameters
        self.epsilon = 1.0  # Exploration rate
        self.epsilon_min = 0.01
        self.epsilon_decay = 0.995
        self.batch_size = 32
        self.memory_size = 10000
        self.gamma = 0.95  # Discount factor
        self.update_target_frequency = 100
        
        # Experience Replay Memory
        self.memory = deque(maxlen=self.memory_size)
        
        # Neural Networks
        if TF_AVAILABLE:
            self.q_network = self.build_network()
            self.target_network = self.build_network()
            self.update_target_network()
        
        # Training Stats
        self.training_step = 0
        self.episode_rewards = []
        self.episode_lengths = []
        
    def build_network(self):
        """Erstellt das Neural Network"""
        model = keras.Sequential([
            layers.Dense(128, activation='relu', input_shape=(self.state_size,)),
            layers.Dropout(0.2),
            layers.Dense(128, activation='relu'),
            layers.Dropout(0.2),
            layers.Dense(64, activation='relu'),
            layers.Dropout(0.1),
            layers.Dense(32, activation='relu'),
            layers.Dense(self.action_size, activation='linear')
        ])
        
        model.compile(
            optimizer=optimizers.Adam(learning_rate=self.learning_rate),
            loss='mse'
        )
        
        return model
    
    def update_target_network(self):
        """Aktualisiert das Target Network"""
        if TF_AVAILABLE:
            self.target_network.set_weights(self.q_network.get_weights())
    
    def remember(self, state, action, reward, next_state, done):
        """Speichert Experience in Memory"""
        self.memory.append((state, action, reward, next_state, done))
    
    def act(self, state, training=True):
        """Wählt eine Aktion basierend auf epsilon-greedy Policy"""
        if training and random.random() <= self.epsilon:
            return random.randrange(self.action_size)
        
        if TF_AVAILABLE:
            q_values = self.q_network.predict(state.reshape(1, -1), verbose=0)
            return np.argmax(q_values[0])
        else:
            return random.randrange(self.action_size)
    
    def replay(self):
        """Training durch Experience Replay"""
        if len(self.memory) < self.batch_size or not TF_AVAILABLE:
            return
        
        batch = random.sample(self.memory, self.batch_size)
        states = np.array([e[0] for e in batch])
        actions = np.array([e[1] for e in batch])
        rewards = np.array([e[2] for e in batch])
        next_states = np.array([e[3] for e in batch])
        dones = np.array([e[4] for e in batch])
        
        # Aktuelle Q-Values
        current_q = self.q_network.predict(states, verbose=0)
        
        # Double DQN (DDQN) Logic Update
        # 1. Action Selektion durch Q-Network
        best_actions = np.argmax(self.q_network.predict(next_states, verbose=0), axis=1)
        
        # 2. Q-Wert Evaluierung durch Target Network
        next_q_target = self.target_network.predict(next_states, verbose=0)
        
        # Q-Learning Update
        for i in range(self.batch_size):
            if dones[i]:
                current_q[i][actions[i]] = rewards[i]
            else:
                current_q[i][actions[i]] = rewards[i] + self.gamma * next_q_target[i][best_actions[i]]
        
        # Training
        self.q_network.fit(states, current_q, epochs=1, verbose=0)
        
        # Epsilon Decay
        if self.epsilon > self.epsilon_min:
            self.epsilon *= self.epsilon_decay
        
        # Update Target Network
        self.training_step += 1
        if self.training_step % self.update_target_frequency == 0:
            self.update_target_network()
    
    def save_model(self, filepath):
        """Speichert das trainierte Modell"""
        if TF_AVAILABLE and hasattr(self, 'q_network'):
            self.q_network.save(filepath)
            
            # Speichere auch Hyperparameter
            config = {
                'state_size': self.state_size,
                'action_size': self.action_size,
                'epsilon': self.epsilon,
                'training_step': self.training_step
            }
            
            with open(filepath.replace('.h5', '_config.json'), 'w') as f:
                json.dump(config, f)
                
            print(f"✅ Modell gespeichert: {filepath}")
    
    def load_model(self, filepath):
        """Lädt ein trainiertes Modell"""
        if TF_AVAILABLE:
            try:
                self.q_network = keras.models.load_model(filepath)
                self.target_network = keras.models.load_model(filepath)
                
                # Lade Konfiguration
                config_file = filepath.replace('.h5', '_config.json')
                with open(config_file, 'r') as f:
                    config = json.load(f)
                    self.epsilon = config.get('epsilon', self.epsilon_min)
                    self.training_step = config.get('training_step', 0)
                
                print(f"✅ Modell geladen: {filepath}")
                return True
            except Exception as e:
                print(f"❌ Fehler beim Laden: {e}")
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
            
            # Agent erstellen
            agent = DQNAgent(env.state_size, env.action_size)
            
            self.environments[symbol] = env
            self.agents[symbol] = agent
            
            print(f"✅ RL Agent für {symbol} initialisiert")
            return True
            
        except Exception as e:
            print(f"❌ Agent Initialisierung für {symbol} fehlgeschlagen: {e}")
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
        
        print(f"🤖 Starte Training für {symbol} - {episodes} Episodes")
        
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
                if len(agent.memory) > agent.batch_size and steps % 4 == 0:
                    agent.replay()
            
            episode_rewards.append(total_reward)
            
            # Progress Report
            if episode % 50 == 0:
                avg_reward = np.mean(episode_rewards[-50:])
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
        
        print(f"✅ Training für {symbol} abgeschlossen")
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
            if TF_AVAILABLE and hasattr(agent, 'q_network'):
                q_values = agent.q_network.predict(state.reshape(1, -1), verbose=0)[0]
                confidence = np.max(q_values) - np.mean(q_values)
                confidence = min(100, max(0, confidence * 100))
            else:
                confidence = 50
            
            return {
                'recommendation': recommendation,
                'confidence': confidence,
                'q_values': q_values.tolist() if TF_AVAILABLE else None,
                'reasoning': f"RL Agent Entscheidung basierend auf {env.state_size} Features"
            }
            
        except Exception as e:
            print(f"❌ RL Recommendation Fehler für {symbol}: {e}")
            return None