import sqlite3
import json
import os
import logging

class ExperienceDB:
    """
    SQLite Database Wrapper for Reinforcement Learning Trade Experiences.
    Saves the state features when a trade is opened, and updates it with 
    reward/profit when the trade is closed.
    """
    def __init__(self, db_path=None):
        if db_path is None:
            # PyInstaller Path Handling
            import sys
            if getattr(sys, 'frozen', False):
                # Wenn wir eine kompilierte .exe sind, benutze den Ordner in dem die .exe liegt
                base_dir = os.path.dirname(sys.executable)
            else:
                # Normaler Python-Script Pfad
                base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                
            storage_dir = os.path.join(base_dir, "storage")
            os.makedirs(storage_dir, exist_ok=True)
            self.db_path = os.path.join(storage_dir, "rl_experience.db")
        else:
            self.db_path = db_path
            
        self.logger = logging.getLogger(__name__)
        self._init_db()

    def _init_db(self):
        """Initializes the database schema."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS experiences (
                        ticket INTEGER PRIMARY KEY,
                        symbol TEXT NOT NULL,
                        timestamp TEXT NOT NULL,
                        state_features TEXT NOT NULL,  -- JSON list of floats
                        action INTEGER NOT NULL,       -- e.g., 1 for BUY, 2 for SELL (0=HOLD)
                        profit REAL DEFAULT 0.0,
                        is_stop_loss BOOLEAN DEFAULT 0,
                        reward REAL DEFAULT 0.0,
                        resolved BOOLEAN DEFAULT 0
                    )
                ''')
                
                # Create an index to quickly find unresolved trades
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_resolved ON experiences(resolved)')
                conn.commit()
        except Exception as e:
            self.logger.error(f"Error initializing ExperienceDB: {e}")

    def insert_pending_trade(self, ticket, symbol, timestamp, state_features, action):
        """
        Inserts a new trade that hasn't been closed yet.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO experiences (ticket, symbol, timestamp, state_features, action, resolved)
                    VALUES (?, ?, ?, ?, ?, 0)
                ''', (
                    ticket, 
                    symbol, 
                    timestamp, 
                    json.dumps(state_features), 
                    action
                ))
                conn.commit()
                return True
        except Exception as e:
            self.logger.error(f"Error inserting pending trade {ticket}: {e}")
            return False

    def resolve_trade(self, ticket, profit, is_stop_loss, reward):
        """
        Updates a pending trade with the outcome, marking it as resolved.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE experiences
                    SET profit = ?, is_stop_loss = ?, reward = ?, resolved = 1
                    WHERE ticket = ? AND resolved = 0
                ''', (
                    profit,
                    1 if is_stop_loss else 0,
                    reward,
                    ticket
                ))
                
                if cursor.rowcount > 0:
                    conn.commit()
                    return True
                else:
                    self.logger.warning(f"Trade {ticket} not found or already resolved.")
                    return False
        except Exception as e:
            self.logger.error(f"Error resolving trade {ticket}: {e}")
            return False

    def get_unresolved_tickets(self, symbol=None):
        """
        Returns a list of ticket IDs that are pending resolution.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                if symbol:
                    cursor.execute('SELECT ticket FROM experiences WHERE resolved = 0 AND symbol = ?', (symbol,))
                else:
                    cursor.execute('SELECT ticket FROM experiences WHERE resolved = 0')
                
                return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            self.logger.error(f"Error getting unresolved tickets: {e}")
            return []

    def get_resolved_experiences(self, symbol=None, limit=10000):
        """
        Retrieves resolved trades to be used for RL training (Experience Replay).
        Returns a list of dicts.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # DEBUG: Log the query parameters
                print(f"[DEBUG] ExperienceDB: Query with symbol={repr(symbol)}, limit={limit}")
                
                if symbol and symbol != "None":
                    # Filter by specific symbol (exclude "None" string entries)
                    cursor.execute('''
                        SELECT ticket, symbol, timestamp, state_features, action, profit, is_stop_loss, reward 
                        FROM experiences 
                        WHERE resolved = 1 AND symbol = ?
                        ORDER BY timestamp DESC
                        LIMIT ?
                    ''', (symbol, limit))
                else:
                    # FIXED: Show ALL experiences when symbol is None, "None", or "Alle"
                    # This includes both NULL symbols and "None" string entries
                    cursor.execute('''
                        SELECT ticket, symbol, timestamp, state_features, action, profit, is_stop_loss, reward 
                        FROM experiences 
                        WHERE resolved = 1
                        ORDER BY timestamp DESC
                        LIMIT ?
                    ''', (limit,))
                
                rows = cursor.fetchall()
                results = []
                for row in rows:
                    res = dict(row)
                    # Parse JSON state features back to list/array
                    if res.get('state_features'):
                        try:
                            res['state_features'] = json.loads(res['state_features'])
                        except:
                            res['state_features'] = []
                    results.append(res)
                
                return results
        except Exception as e:
            self.logger.error(f"Error fetching resolved experiences: {e}")
            return []

if __name__ == '__main__':
    # Simple test
    db = ExperienceDB()
    import time
    db.insert_pending_trade(12345, "EURUSD", str(time.time()), [0.1, 0.5, -0.2], 1)
    db.resolve_trade(12345, 10.5, False, 15.0)
    print("Resolved experiences:", db.get_resolved_experiences())
