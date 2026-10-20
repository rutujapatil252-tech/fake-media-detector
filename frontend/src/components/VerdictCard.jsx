import React from 'react';
import { Bot, AlertTriangle, ShieldCheck, HelpCircle, Gauge, Clock, ChevronRight } from 'lucide-react';

const VERDICT_STYLES = {
  likely_ai_generated: {
    bg: 'bg-rose-500/10 border-rose-500/30 text-rose-300',
    badge: 'bg-rose-500/20 text-rose-200 border-rose-500/40',
    barColor: 'bg-rose-500',
    icon: Bot,
    ring: 'ring-rose-500/30',
  },
  possibly_manipulated: {
    bg: 'bg-amber-500/10 border-amber-500/30 text-amber-300',
    badge: 'bg-amber-500/20 text-amber-200 border-amber-500/40',
    barColor: 'bg-amber-500',
    icon: AlertTriangle,
    ring: 'ring-amber-500/30',
  },
  likely_authentic: {
    bg: 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300',
    badge: 'bg-emerald-500/20 text-emerald-200 border-emerald-500/40',
    barColor: 'bg-emerald-500',
    icon: ShieldCheck,
    ring: 'ring-emerald-500/30',
  },
  inconclusive: {
    bg: 'bg-slate-500/10 border-slate-500/30 text-slate-300',
    badge: 'bg-slate-500/20 text-slate-200 border-slate-500/40',
    barColor: 'bg-slate-500',
    icon: HelpCircle,
    ring: 'ring-slate-500/30',
  },
};

const CONFIDENCE_STYLES = {
  high: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30',
  medium: 'bg-amber-500/20 text-amber-300 border-amber-500/30',
  low: 'bg-slate-500/20 text-slate-300 border-slate-500/30',
};

export default function VerdictCard({ verdict, processingTimeMs, filename }) {
  if (!verdict) return null;

  const style = VERDICT_STYLES[verdict.label] || VERDICT_STYLES.inconclusive;
  const VerdictIcon = style.icon;
  const scorePercent = Math.round(verdict.overall_score * 100);

  return (
    <div className={`glass-panel rounded-2xl p-6 sm:p-8 border shadow-xl ${style.bg} relative overflow-hidden`}>
      {/* Background radial highlight */}
      <div className="absolute top-0 right-0 w-80 h-80 rounded-full bg-gradient-to-br from-white/5 to-transparent blur-3xl pointer-events-none" />

      <div className="relative z-10 flex flex-col md:flex-row md:items-start justify-between gap-6">
        {/* Left side: Main verdict badge & score */}
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-3">
            <span className="text-xs uppercase font-semibold tracking-wider text-slate-400">
              Analyzed Media:
            </span>
            <span className="text-xs font-mono text-slate-200 truncate max-w-xs" title={filename}>
              {filename}
            </span>
            {processingTimeMs && (
              <span className="flex items-center gap-1 text-[11px] text-slate-400 ml-auto md:ml-2">
                <Clock className="h-3 w-3" />
                <span>{processingTimeMs} ms</span>
              </span>
            )}
          </div>

          {/* Verdict Title Badge */}
          <div className="flex flex-wrap items-center gap-3">
            <div className={`inline-flex items-center gap-2 px-4 py-2 rounded-xl border font-bold text-lg sm:text-xl shadow-lg ${style.badge}`}>
              <VerdictIcon className="h-6 w-6" />
              <span>{verdict.display_label}</span>
            </div>

            {/* Confidence Chip */}
            <div className={`px-2.5 py-1 rounded-lg border text-xs font-medium uppercase tracking-wider ${CONFIDENCE_STYLES[verdict.confidence] || CONFIDENCE_STYLES.medium}`}>
              {verdict.confidence} Confidence
            </div>
          </div>

          {/* Suspicion Score Gauge Bar */}
          <div className="mt-6 max-w-md">
            <div className="flex justify-between items-center text-xs font-medium text-slate-300 mb-2">
              <span className="flex items-center gap-1.5">
                <Gauge className="h-3.5 w-3.5 text-slate-400" />
                <span>Synthesized Suspicion Index</span>
              </span>
              <span className="text-base font-bold text-white">{scorePercent}%</span>
            </div>
            <div className="h-3 w-full bg-slate-800/90 rounded-full overflow-hidden p-0.5 border border-slate-700/50">
              <div
                className={`h-full rounded-full transition-all duration-700 ${style.barColor}`}
                style={{ width: `${Math.max(4, scorePercent)}%` }}
              />
            </div>
            <div className="flex justify-between text-[10px] text-slate-500 mt-1">
              <span>0% Authentic</span>
              <span>45% Suspicious</span>
              <span>100% Synthetic / Tampered</span>
            </div>
          </div>
        </div>

        {/* Right side: Reasons list */}
        <div className="flex-1 border-t md:border-t-0 md:border-l border-slate-700/60 pt-4 md:pt-0 md:pl-6">
          <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-3">
            Why This Verdict:
          </h4>
          <ul className="space-y-2.5">
            {verdict.reasons && verdict.reasons.length > 0 ? (
              verdict.reasons.map((reason, idx) => (
                <li key={idx} className="flex items-start gap-2 text-xs sm:text-sm text-slate-300 leading-relaxed">
                  <ChevronRight className="h-4 w-4 shrink-0 text-indigo-400 mt-0.5" />
                  <span>{reason}</span>
                </li>
              ))
            ) : (
              <li className="text-xs text-slate-400 italic">No specific anomaly flags triggered.</li>
            )}
          </ul>
        </div>
      </div>
    </div>
  );
}
