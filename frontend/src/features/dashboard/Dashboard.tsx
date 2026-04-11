import { KPICard } from '@/components/cards/KPICard';
import { ChartPanel } from './ChartPanel';
import { PortfolioTable } from './PortfolioTable';
import { Watchlist } from './Watchlist';
import { Wallet, Activity, TrendingUp, BarChart3 } from 'lucide-react';
import { useEffect, useState } from 'react';

export function Dashboard() {
  const [portfolio, setPortfolio] = useState<any>(null);

  useEffect(() => {
    fetch('http://localhost:8000/api/v1/portfolio')
      .then(r => r.json())
      .then(data => setPortfolio(data))
      .catch(err => console.error("Failed to fetch portfolio:", err));
  }, []);

  return (
    <div className="flex flex-col gap-6 max-w-7xl mx-auto animate-in fade-in zoom-in duration-500">
      
      {/* KPI Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <KPICard 
          title="Total Equity" 
          value={portfolio ? `$${portfolio.equity.toLocaleString()}` : "---"} 
          change={portfolio ? `${portfolio.total_pnl_percent}%` : "0%"}
          icon={<Wallet className="w-5 h-5 text-blue-500" />}
          trend={portfolio?.total_pnl >= 0 ? 'up' : 'down'}
        />
        <KPICard 
          title="Day's PnL" 
          value={portfolio ? `$${portfolio.total_pnl.toFixed(2)}` : "---"} 
          change="Today"
          icon={<Activity className="w-5 h-5 text-green-500" />}
          trend={portfolio?.total_pnl >= 0 ? 'up' : 'down'}
        />
        <KPICard 
          title="Free Margin" 
          value={portfolio ? `$${portfolio.free_margin.toLocaleString()}` : "---"} 
          change="Available"
          icon={<TrendingUp className="w-5 h-5 text-purple-500" />}
          trend="neutral"
        />
        <KPICard 
          title="Active Trades" 
          value={portfolio ? portfolio.positions.length.toString() : "0"} 
          change="2 signals generated"
          icon={<BarChart3 className="w-5 h-5 text-orange-500" />}
          trend="up"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Chart Area */}
        <div className="lg:col-span-2 flex flex-col gap-6">
          <ChartPanel />
          <PortfolioTable positions={portfolio?.positions || []} />
        </div>
        
        {/* Sidebar / Watchlist */}
        <div className="flex flex-col gap-6">
          <Watchlist />
        </div>
      </div>
    </div>
  );
}