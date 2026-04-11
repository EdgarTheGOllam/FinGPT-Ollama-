import { useState, useEffect } from 'react';
import { Dashboard } from './features/dashboard/Dashboard';
import { Sidebar } from './components/layout/Sidebar';
import { TopBar } from './components/layout/TopBar';

function App() {
  const [activeTab, setActiveTab] = useState('dashboard');

  return (
    <div className="flex h-screen bg-background text-foreground overflow-hidden font-sans selection:bg-primary/30">
      {/* Subtle background glow effect */}
      <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-primary/10 rounded-full blur-[120px] pointer-events-none" />
      <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-blue-500/10 rounded-full blur-[120px] pointer-events-none" />
      
      <Sidebar activeTab={activeTab} onTabChange={setActiveTab} />
      
      <div className="flex flex-col flex-1 relative z-10">
        <TopBar />
        <main className="flex-1 overflow-y-auto p-6 scrollbar-hide">
          {activeTab === 'dashboard' && <Dashboard />}
          {activeTab !== 'dashboard' && (
            <div className="flex items-center justify-center h-full text-muted-foreground">
              <h2>{activeTab.charAt(0).toUpperCase() + activeTab.slice(1)} Module - In Development</h2>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}

export default App;