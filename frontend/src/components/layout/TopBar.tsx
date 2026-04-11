import { Bell, Search, UserCircle } from 'lucide-react';
import { useEffect, useState } from 'react';

export function TopBar() {
  const [status, setStatus] = useState({ connected: false, aiReady: false });

  useEffect(() => {
    // Fetch mock status
    fetch('http://localhost:8000/api/v1/status')
      .then(r => r.json())
      .then(data => setStatus({ connected: data.mt5_connected, aiReady: data.ai_engine_ready }))
      .catch(() => setStatus({ connected: false, aiReady: false }));
  }, []);

  return (
    <header className="h-16 bg-card/40 backdrop-blur-md border-b border-border/50 flex items-center justify-between px-6 sticky top-0 z-20">
      <div className="flex items-center bg-secondary/50 rounded-full px-3 py-1.5 w-64 border border-border/50 focus-within:border-primary/50 focus-within:ring-1 focus-within:ring-primary/20 transition-all">
        <Search className="w-4 h-4 text-muted-foreground mr-2" />
        <input 
          type="text" 
          placeholder="Search markets, pairs..." 
          className="bg-transparent border-none outline-none text-sm w-full text-foreground placeholder:text-muted-foreground"
        />
      </div>

      <div className="flex items-center gap-6">
        <div className="flex items-center gap-4 text-xs font-medium">
          <div className="flex items-center gap-1.5">
            <div className={`w-2 h-2 rounded-full ${status.connected ? 'bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.6)]' : 'bg-red-500'}`} />
            <span className="text-muted-foreground">MT5</span>
          </div>
          <div className="flex items-center gap-1.5">
            <div className={`w-2 h-2 rounded-full ${status.aiReady ? 'bg-blue-500 shadow-[0_0_8px_rgba(59,130,246,0.6)]' : 'bg-red-500'}`} />
            <span className="text-muted-foreground">AI Engine</span>
          </div>
        </div>

        <div className="h-6 w-px bg-border/50" />

        <div className="flex items-center gap-4">
          <button className="relative text-muted-foreground hover:text-foreground transition-colors">
            <Bell className="w-5 h-5" />
            <span className="absolute -top-1 -right-1 w-2 h-2 bg-primary rounded-full" />
          </button>
          
          <button className="flex items-center gap-2 text-muted-foreground hover:text-foreground transition-colors">
            <div className="w-8 h-8 rounded-full bg-secondary flex items-center justify-center overflow-hidden border border-border">
              <UserCircle className="w-6 h-6" />
            </div>
          </button>
        </div>
      </div>
    </header>
  );
}