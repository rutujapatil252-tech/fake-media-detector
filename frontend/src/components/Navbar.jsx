import React, { useEffect, useState } from 'react';
import { Shield, Database, Activity } from 'lucide-react';
import { checkHealth } from '../api';

export default function Navbar({ onOpenReferences }) {
  const [isHealthy, setIsHealthy] = useState(null);

  useEffect(() => {
    let mounted = true;
    const testConnection = async () => {
      try {
        await checkHealth();
        if (mounted) setIsHealthy(true);
      } catch {
        if (mounted) setIsHealthy(false);
      }
    };
    testConnection();
    const interval = setInterval(testConnection, 15000);
    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, []);

  return (
    <header className="border-b border-slate-800 bg-slate-900/60 backdrop-blur-md sticky top-0 z-40">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Brand */}
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 rounded-xl bg-gradient-to-tr from-indigo-600 to-violet-500 flex items-center justify-center shadow-lg shadow-indigo-500/20">
            <Shield className="h-5 w-5 text-white" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold text-lg tracking-tight text-white">Fake Media Detector</span>
              <span className="text-[10px] uppercase tracking-wider font-semibold px-1.5 py-0.5 rounded bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                v4.0
              </span>
            </div>
            <p className="text-xs text-slate-400 hidden sm:block">
              Multi-vector digital image forensics & AI provenance analysis
            </p>
          </div>
        </div>

        {/* Actions & Health indicator */}
        <div className="flex items-center gap-3">
          {/* Health indicator */}
          <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800/80 border border-slate-700/60 text-xs">
            <span
              className={`h-2 w-2 rounded-full ${
                isHealthy === true
                  ? 'bg-emerald-400 shadow-sm shadow-emerald-400'
                  : isHealthy === false
                  ? 'bg-rose-400 animate-pulse'
                  : 'bg-amber-400 animate-pulse'
              }`}
            />
            <span className="text-slate-300 hidden md:inline">
              {isHealthy === true ? 'API Connected' : isHealthy === false ? 'API Offline' : 'Connecting...'}
            </span>
          </div>

          {/* Reference DB Button */}
          <button
            onClick={onOpenReferences}
            className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-indigo-600/20 hover:bg-indigo-600/30 border border-indigo-500/40 text-indigo-300 hover:text-indigo-200 text-xs font-medium transition-all shadow-sm cursor-pointer"
          >
            <Database className="h-3.5 w-3.5" />
            <span>Reference Database</span>
          </button>
        </div>
      </div>
    </header>
  );
}
