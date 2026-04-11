import { ArrowUpRight, ArrowDownRight } from 'lucide-react';
import { cn } from '@/lib/utils';

export function PortfolioTable({ positions }: { positions: any[] }) {
  return (
    <div className="bg-card/60 backdrop-blur-md border border-border/50 rounded-2xl p-6 relative overflow-hidden group">
      <div className="absolute top-0 right-0 w-64 h-64 bg-primary/5 rounded-full blur-[80px] pointer-events-none" />
      
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-lg font-bold tracking-tight text-foreground">Active Positions</h2>
        <button className="text-sm font-medium text-primary hover:text-primary/80 transition-colors">
          View All
        </button>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="text-muted-foreground border-b border-border/50">
              <th className="pb-3 font-medium">Asset</th>
              <th className="pb-3 font-medium text-right">Size</th>
              <th className="pb-3 font-medium text-right">Value</th>
              <th className="pb-3 font-medium text-right">Unrealized PnL</th>
            </tr>
          </thead>
          <tbody>
            {positions.length === 0 && (
              <tr>
                <td colSpan={4} className="py-6 text-center text-muted-foreground">
                  No active positions
                </td>
              </tr>
            )}
            {positions.map((pos, idx) => (
              <tr key={idx} className="border-b border-border/20 last:border-0 hover:bg-secondary/30 transition-colors">
                <td className="py-4 font-semibold text-foreground flex items-center gap-3">
                  <div className="w-8 h-8 rounded-full bg-secondary flex items-center justify-center text-xs text-muted-foreground">
                    {pos.symbol.substring(0,2)}
                  </div>
                  {pos.symbol}
                </td>
                <td className="py-4 text-right text-muted-foreground">{pos.position}</td>
                <td className="py-4 text-right text-foreground font-medium">${pos.value.toLocaleString()}</td>
                <td className={cn(
                  "py-4 text-right font-medium flex items-center justify-end gap-2",
                  pos.pnl >= 0 ? "text-green-400" : "text-red-400"
                )}>
                  {pos.pnl >= 0 ? <ArrowUpRight className="w-4 h-4" /> : <ArrowDownRight className="w-4 h-4" />}
                  ${Math.abs(pos.pnl).toFixed(2)}
                  <span className="text-xs opacity-70">({pos.pnl_percent}%)</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}