import { ReactNode } from 'react';
import { cn } from '@/lib/utils';
import { ArrowUpRight, ArrowDownRight, Minus } from 'lucide-react';

interface KPICardProps {
  title: string;
  value: string;
  change: string;
  icon: ReactNode;
  trend: 'up' | 'down' | 'neutral';
}

export function KPICard({ title, value, change, icon, trend }: KPICardProps) {
  return (
    <div className="bg-card/60 backdrop-blur-md border border-border/50 rounded-2xl p-5 flex flex-col gap-4 relative overflow-hidden group hover:border-primary/30 transition-all duration-300">
      <div className="absolute top-0 left-0 w-full h-[2px] bg-gradient-to-r from-transparent via-primary/50 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
      
      <div className="flex items-start justify-between">
        <div className="p-2.5 rounded-xl bg-secondary/80 border border-border/50 group-hover:scale-110 transition-transform duration-300">
          {icon}
        </div>
        
        <div className={cn(
          "flex items-center gap-1 text-xs font-medium px-2 py-1 rounded-full",
          trend === 'up' ? "text-green-400 bg-green-400/10" :
          trend === 'down' ? "text-red-400 bg-red-400/10" :
          "text-muted-foreground bg-secondary"
        )}>
          {trend === 'up' && <ArrowUpRight className="w-3 h-3" />}
          {trend === 'down' && <ArrowDownRight className="w-3 h-3" />}
          {trend === 'neutral' && <Minus className="w-3 h-3" />}
          {change}
        </div>
      </div>

      <div>
        <div className="text-sm font-medium text-muted-foreground mb-1">{title}</div>
        <div className="text-3xl font-bold tracking-tight text-foreground">{value}</div>
      </div>
    </div>
  );
}