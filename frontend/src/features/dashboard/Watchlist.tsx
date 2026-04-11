import { useEffect, useState } from 'react';
import { cn } from '@/lib/utils';
import { ArrowUpRight, ArrowDownRight, RefreshCcw } from 'lucide-react';

export function Watchlist() {
  const [markets, setMarkets] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchMarkets = () => {
    setLoading(true);
    fetch('http://localhost:8000/api/v1/market/summary')
      .then(r => r.json())
      .then(data => {
        setMarkets(data);
        setLoading(false);
      })
      .catch(err => {
        console.error(err);
        setLoading(false);
      });
  };

  useEffect(() => {
    fetchMarkets();
    const interval = setInterval(fetchMarkets, 10000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="bg-card/60 backdrop-blur-md border border-border/50 rounded-2xl p-6 relative flex flex-col h-full group">
      <div className="absolute bottom-0 right-0 w-full h-32 bg-gradient-to-t from-background to-transparent pointer-events-none z-10" />
      
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-lg font-bold tracking-tight text-foreground">Market Pulse</h2>
        <button onClick={fetchMarkets} className="text-muted-foreground hover:text-foreground transition-colors">
          <RefreshCcw className={cn("w-4 h-4", loading && "animate-spin")} />
        </button>
      </div>

      <div className="flex flex-col gap-3 overflow-y-auto pb-12 pr-2 scrollbar-hide flex-1">
        {markets.map((market, idx) => (
          <div key={idx} className="flex items-center justify-between p-3 rounded-xl hover:bg-secondary/50 transition-colors cursor-pointer group/item border border-transparent hover:border-border/50">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-secondary flex items-center justify-center font-bold text-xs">
                {market.symbol.substring(0,3)}
              </div>
              <div>
                <div className="font-semibold text-sm text-foreground">{market.symbol}</div>
                <div className="text-xs text-muted-foreground font-medium">Vol: High</div>
              </div>
            </div>
            
            <div className="text-right">
              <div className="font-bold text-sm text-foreground">{market.price}</div>
              <div className={cn(
                "text-xs font-semibold flex items-center justify-end gap-1 mt-0.5",
                market.change_percent >= 0 ? "text-green-400" : "text-red-400"
              )}>
                {market.change_percent >= 0 ? <ArrowUpRight className="w-3 h-3" /> : <ArrowDownRight className="w-3 h-3" />}
                {market.change_percent}%
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}