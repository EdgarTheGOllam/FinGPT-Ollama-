import { useEffect, useState } from 'react';
import { Area, AreaChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';

export function ChartPanel() {
  const [data, setData] = useState<any[]>([]);

  useEffect(() => {
    // Generate realistic-looking mock data for the chart
    let lastValue = 10000;
    const mockData = Array.from({ length: 60 }).map((_, i) => {
      lastValue = lastValue + (Math.random() - 0.45) * 200;
      return {
        time: i,
        value: lastValue
      };
    });
    setData(mockData);
  }, []);

  return (
    <div className="bg-card/60 backdrop-blur-md border border-border/50 rounded-2xl p-6 relative overflow-hidden group">
      <div className="absolute top-[-20%] left-[-10%] w-[50%] h-[50%] bg-blue-500/10 rounded-full blur-[100px] pointer-events-none" />
      
      <div className="flex items-center justify-between mb-6 relative z-10">
        <div>
          <h2 className="text-lg font-bold tracking-tight text-foreground">Performance Overview</h2>
          <p className="text-sm text-muted-foreground">Portfolio growth over time</p>
        </div>
        
        <div className="flex bg-secondary/80 rounded-lg p-1 border border-border/50">
          {['1D', '1W', '1M', 'ALL'].map((tf, i) => (
            <button 
              key={tf} 
              className={`px-3 py-1 text-xs font-medium rounded-md transition-colors ${i === 2 ? 'bg-background text-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground'}`}
            >
              {tf}
            </button>
          ))}
        </div>
      </div>

      <div className="h-[300px] w-full relative z-10">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data}>
            <defs>
              <linearGradient id="colorValue" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="hsl(var(--primary))" stopOpacity={0.3}/>
                <stop offset="95%" stopColor="hsl(var(--primary))" stopOpacity={0}/>
              </linearGradient>
            </defs>
            <XAxis dataKey="time" hide />
            <YAxis domain={['auto', 'auto']} hide />
            <Tooltip 
              contentStyle={{ backgroundColor: 'hsl(var(--popover))', border: '1px solid hsl(var(--border))', borderRadius: '8px' }}
              itemStyle={{ color: 'hsl(var(--foreground))' }}
              labelStyle={{ display: 'none' }}
            />
            <Area 
              type="monotone" 
              dataKey="value" 
              stroke="hsl(var(--primary))" 
              strokeWidth={3}
              fillOpacity={1} 
              fill="url(#colorValue)" 
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}