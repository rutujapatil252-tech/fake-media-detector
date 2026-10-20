import React from 'react';
import { 
  Bot, 
  Layers, 
  FileText, 
  ShieldCheck, 
  Copy, 
  CheckCircle2, 
  AlertTriangle, 
  XCircle, 
  HelpCircle,
  ChevronDown,
  ChevronUp
} from 'lucide-react';

const CHECK_CONFIG = {
  ai_detector: {
    label: 'Deep Learning AI Detector',
    icon: Bot,
    description: 'Vision Transformer scanning for diffusion synthesis artifacts',
  },
  ela: {
    label: 'Error Level Analysis (ELA)',
    icon: Layers,
    description: 'JPEG compression gradient & localized resaving analysis',
  },
  c2pa: {
    label: 'Content Credentials (C2PA)',
    icon: ShieldCheck,
    description: 'Cryptographic provenance manifest & AI disclosure flags',
  },
  metadata: {
    label: 'EXIF & File Metadata',
    icon: FileText,
    description: 'Camera hardware signatures, software tags, and editing traces',
  },
  duplicate: {
    label: 'Perceptual Hash Duplicate',
    icon: Copy,
    description: 'Image fingerprint search against verified reference database',
  },
};

const STATUS_BADGES = {
  suspicious: {
    bg: 'bg-rose-500/20 text-rose-300 border-rose-500/40',
    icon: XCircle,
    label: 'Suspicious',
  },
  neutral: {
    bg: 'bg-amber-500/20 text-amber-300 border-amber-500/40',
    icon: AlertTriangle,
    label: 'Neutral',
  },
  clean: {
    bg: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40',
    icon: CheckCircle2,
    label: 'Clean',
  },
  unavailable: {
    bg: 'bg-slate-700/40 text-slate-400 border-slate-600/30',
    icon: HelpCircle,
    label: 'Unavailable',
  },
};

export default function EvidenceTable({ evidence = [], activeTab, onSelectTab }) {
  if (!evidence || evidence.length === 0) return null;

  return (
    <div className="glass-panel rounded-2xl border border-slate-700/60 overflow-hidden shadow-xl">
      <div className="p-5 border-b border-slate-700/60 bg-slate-900/40 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
        <div>
          <h3 className="font-semibold text-slate-100 flex items-center gap-2">
            <span>Forensic Evidence Matrix</span>
            <span className="text-xs bg-slate-800 text-slate-400 px-2 py-0.5 rounded-full border border-slate-700">
              5 Independent Signals
            </span>
          </h3>
          <p className="text-xs text-slate-400 mt-0.5">
            Click any row to jump directly to its in-depth forensic inspection panel.
          </p>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse text-xs sm:text-sm">
          <thead>
            <tr className="border-b border-slate-800 text-slate-400 bg-slate-900/60 text-[11px] uppercase tracking-wider">
              <th className="py-3 px-4 font-semibold">Forensic Vector</th>
              <th className="py-3 px-4 font-semibold">Status</th>
              <th className="py-3 px-4 font-semibold min-w-[130px]">Risk Score</th>
              <th className="py-3 px-4 font-semibold">Summary Finding</th>
              <th className="py-3 px-4 text-right">Details</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/80">
            {evidence.map((item) => {
              const checkMeta = CHECK_CONFIG[item.check] || {
                label: item.check,
                icon: HelpCircle,
                description: '',
              };
              const Icon = checkMeta.icon;
              const statusCfg = STATUS_BADGES[item.status] || STATUS_BADGES.unavailable;
              const StatusIcon = statusCfg.icon;
              const isUnavailable = item.status === 'unavailable';
              const isSelected = activeTab === item.check;
              const scorePct = item.score !== null && item.score !== undefined 
                ? Math.round(item.score * 100) 
                : null;

              return (
                <tr
                  key={item.check}
                  onClick={() => onSelectTab && onSelectTab(item.check)}
                  className={`cursor-pointer transition-colors ${
                    isSelected 
                      ? 'bg-indigo-950/40 border-l-4 border-l-indigo-500' 
                      : 'hover:bg-slate-800/40'
                  } ${isUnavailable ? 'opacity-60 bg-slate-900/30' : ''}`}
                >
                  {/* Forensic Vector Name */}
                  <td className="py-3.5 px-4">
                    <div className="flex items-center gap-3">
                      <div className={`p-2 rounded-lg border ${
                        isSelected 
                          ? 'bg-indigo-600/30 border-indigo-500/50 text-indigo-300' 
                          : 'bg-slate-800/80 border-slate-700/60 text-slate-300'
                      }`}>
                        <Icon className="h-4 w-4" />
                      </div>
                      <div>
                        <div className="font-medium text-slate-200">{checkMeta.label}</div>
                        <div className="text-[11px] text-slate-400 hidden sm:block">
                          {checkMeta.description}
                        </div>
                      </div>
                    </div>
                  </td>

                  {/* Status chip */}
                  <td className="py-3.5 px-4 whitespace-nowrap">
                    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md border text-xs font-medium ${statusCfg.bg}`}>
                      <StatusIcon className="h-3.5 w-3.5" />
                      {statusCfg.label}
                    </span>
                  </td>

                  {/* Risk Score Progress Bar */}
                  <td className="py-3.5 px-4 whitespace-nowrap">
                    {scorePct !== null ? (
                      <div className="w-32">
                        <div className="flex justify-between items-center text-xs mb-1">
                          <span className="font-mono text-slate-300">{scorePct}%</span>
                          <span className="text-[10px] text-slate-400">
                            {scorePct > 65 ? 'High' : scorePct > 35 ? 'Moderate' : 'Low'}
                          </span>
                        </div>
                        <div className="h-1.5 w-full bg-slate-800 rounded-full overflow-hidden">
                          <div
                            className={`h-full rounded-full ${
                              scorePct > 65
                                ? 'bg-rose-500'
                                : scorePct > 35
                                ? 'bg-amber-500'
                                : 'bg-emerald-500'
                            }`}
                            style={{ width: `${Math.max(4, scorePct)}%` }}
                          />
                        </div>
                      </div>
                    ) : (
                      <span className="text-xs text-slate-400 font-mono italic">N/A</span>
                    )}
                  </td>

                  {/* Summary */}
                  <td className="py-3.5 px-4 text-xs text-slate-300 max-w-xs sm:max-w-md">
                    <span className="line-clamp-2 leading-relaxed">{item.summary}</span>
                  </td>

                  {/* Expand / View arrow */}
                  <td className="py-3.5 px-4 text-right">
                    <button
                      type="button"
                      className="p-1 rounded hover:bg-slate-700/50 text-slate-400 hover:text-slate-200 transition-colors"
                      title="Inspect Details"
                    >
                      {isSelected ? (
                        <ChevronUp className="h-4 w-4 text-indigo-400" />
                      ) : (
                        <ChevronDown className="h-4 w-4" />
                      )}
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
