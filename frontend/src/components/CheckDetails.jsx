import React, { useState } from 'react';
import { 
  Bot, 
  Layers, 
  FileText, 
  ShieldCheck, 
  Copy, 
  AlertTriangle, 
  CheckCircle2, 
  XCircle, 
  Info, 
  ExternalLink,
  Cpu,
  Sparkles,
  Camera,
  Hash
} from 'lucide-react';

export default function CheckDetails({ checks, originalPreviewUrl, activeTab, onSelectTab }) {
  if (!checks) return null;

  const tabs = [
    { id: 'ai_detector', label: 'AI Synthesis', icon: Bot, check: checks.ai_detector },
    { id: 'ela', label: 'Error Level (ELA)', icon: Layers, check: checks.ela },
    { id: 'c2pa', label: 'C2PA Provenance', icon: ShieldCheck, check: checks.c2pa },
    { id: 'metadata', label: 'EXIF Metadata', icon: FileText, check: checks.metadata },
    { id: 'duplicate', label: 'Duplicate Check', icon: Copy, check: checks.duplicate },
  ];

  const currentTab = tabs.find(t => t.id === activeTab) || tabs[0];

  return (
    <div className="glass-panel rounded-2xl border border-slate-700/60 overflow-hidden shadow-xl mt-6">
      {/* Tab Navigation Header */}
      <div className="flex border-b border-slate-700/60 bg-slate-900/60 overflow-x-auto no-scrollbar">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          const isActive = tab.id === activeTab;
          const isError = tab.check?.error;

          return (
            <button
              key={tab.id}
              onClick={() => onSelectTab(tab.id)}
              className={`flex items-center gap-2 px-5 py-3.5 text-xs sm:text-sm font-medium border-b-2 whitespace-nowrap transition-all ${
                isActive
                  ? 'border-indigo-500 text-indigo-300 bg-indigo-950/20'
                  : 'border-transparent text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
              }`}
            >
              <Icon className="h-4 w-4" />
              <span>{tab.label}</span>
              {isError && (
                <span className="h-1.5 w-1.5 rounded-full bg-rose-400" title="Error in check" />
              )}
            </button>
          );
        })}
      </div>

      {/* Tab Content Panel */}
      <div className="p-6">
        {activeTab === 'ai_detector' && (
          <AiDetectorPanel check={checks.ai_detector} />
        )}
        {activeTab === 'ela' && (
          <ElaPanel check={checks.ela} originalPreviewUrl={originalPreviewUrl} />
        )}
        {activeTab === 'c2pa' && (
          <C2paPanel check={checks.c2pa} />
        )}
        {activeTab === 'metadata' && (
          <MetadataPanel check={checks.metadata} />
        )}
        {activeTab === 'duplicate' && (
          <DuplicatePanel check={checks.duplicate} />
        )}
      </div>
    </div>
  );
}

// ==========================================
// 1. AI Detector Panel
// ==========================================
function AiDetectorPanel({ check }) {
  if (!check) return <div className="text-slate-400 text-sm">No AI detector data.</div>;
  if (check.error) {
    return (
      <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-300 text-sm">
        <p className="font-semibold">AI Detection Unavailable</p>
        <p className="text-xs mt-1 text-amber-200/80">{check.error}</p>
      </div>
    );
  }

  const aiProb = check.ai_probability !== undefined && check.ai_probability !== null 
    ? Math.round(check.ai_probability * 100) 
    : 0;
  const realProb = 100 - aiProb;

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <div className="flex items-center gap-2">
            <h4 className="text-base font-semibold text-slate-100">Deep Learning Diffusion Classifier</h4>
            <span className="px-2 py-0.5 rounded text-[11px] font-mono bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
              {check.classification?.toUpperCase() || 'EVALUATED'}
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Scans for frequency distortions, unnatural gradients, and synthetic latent generation patterns.
          </p>
        </div>
        <div className="text-xs font-mono text-slate-400 bg-slate-800/80 px-3 py-1.5 rounded-lg border border-slate-700 shrink-0">
          Model: <span className="text-indigo-300">{check.model_name || 'Organika/sdxl-detector'}</span>
        </div>
      </div>

      {/* Probability Distribution */}
      <div className="bg-slate-900/50 p-5 rounded-xl border border-slate-800">
        <div className="flex justify-between items-center mb-2">
          <div className="flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-rose-400" />
            <span className="text-sm font-semibold text-slate-200">Synthetic AI Probability</span>
          </div>
          <span className="text-lg font-bold font-mono text-rose-400">{aiProb}%</span>
        </div>

        {/* Dual Bar */}
        <div className="h-3 w-full bg-slate-800 rounded-full overflow-hidden flex">
          <div
            className="h-full bg-rose-500 transition-all duration-700"
            style={{ width: `${aiProb}%` }}
            title={`AI Generated: ${aiProb}%`}
          />
          <div
            className="h-full bg-emerald-500 transition-all duration-700"
            style={{ width: `${realProb}%` }}
            title={`Authentic Photo: ${realProb}%`}
          />
        </div>

        <div className="flex justify-between text-xs mt-2 text-slate-400">
          <span className="text-rose-400">Synthetic / AI: {aiProb}%</span>
          <span className="text-emerald-400">Camera / Real: {realProb}%</span>
        </div>
      </div>

      {/* Raw Model Prediction Scores */}
      {check.raw_scores && (
        <div>
          <h5 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
            Raw Softmax Probabilities:
          </h5>
          <div className="grid grid-cols-2 gap-3">
            {Object.entries(check.raw_scores).map(([lbl, val]) => (
              <div key={lbl} className="bg-slate-800/40 p-3 rounded-lg border border-slate-700/50">
                <div className="text-xs text-slate-400 capitalize">{lbl.replace('_', ' ')}</div>
                <div className="text-sm font-mono font-bold text-slate-200 mt-0.5">
                  {(val * 100).toFixed(2)}%
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Summary Note */}
      <div className="text-xs text-slate-300 bg-slate-800/30 p-3.5 rounded-lg border border-slate-700/40 leading-relaxed">
        <strong>Observation:</strong> {check.summary}
      </div>
    </div>
  );
}

// ==========================================
// 2. Error Level Analysis (ELA) Panel
// ==========================================
function ElaPanel({ check, originalPreviewUrl }) {
  if (!check) return <div className="text-slate-400 text-sm">No ELA data.</div>;
  if (check.error) {
    return (
      <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-300 text-sm">
        <p className="font-semibold">ELA Processing Error</p>
        <p className="text-xs mt-1 text-amber-200/80">{check.error}</p>
      </div>
    );
  }

  const heatmapSrc = check.heatmap_base64 
    ? `data:image/png;base64,${check.heatmap_base64}` 
    : null;

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <h4 className="text-base font-semibold text-slate-100">JPEG Compression Error Level Analysis</h4>
          <p className="text-xs text-slate-400 mt-1">
            Resaves the image at a known quality level (95%) and scales differences. Edits, splices, or inserted elements degrade at different rates, standing out as bright localized clusters.
          </p>
        </div>
        <div className="flex items-center gap-3 shrink-0">
          <div className="bg-slate-800/80 px-3 py-1.5 rounded-lg border border-slate-700 text-xs text-slate-300">
            Mean Error: <span className="font-mono text-indigo-300 font-semibold">{check.mean_error?.toFixed(2)}</span>
          </div>
          <div className="bg-slate-800/80 px-3 py-1.5 rounded-lg border border-slate-700 text-xs text-slate-300">
            Max Error: <span className="font-mono text-indigo-300 font-semibold">{check.max_error}</span>
          </div>
        </div>
      </div>

      {/* Side by Side Image Comparison */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Original */}
        <div className="bg-slate-900/60 rounded-xl border border-slate-800 p-3 flex flex-col items-center">
          <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
            Uploaded Media
          </span>
          <div className="w-full h-64 flex items-center justify-center bg-black/40 rounded-lg overflow-hidden">
            {originalPreviewUrl ? (
              <img
                src={originalPreviewUrl}
                alt="Original"
                className="max-h-full max-w-full object-contain"
              />
            ) : (
              <span className="text-xs text-slate-500">Original not available</span>
            )}
          </div>
        </div>

        {/* ELA Heatmap */}
        <div className="bg-slate-900/60 rounded-xl border border-slate-800 p-3 flex flex-col items-center">
          <div className="flex items-center justify-between w-full mb-2">
            <span className="text-xs font-semibold text-indigo-400 uppercase tracking-wider">
              Amplified ELA Heatmap (10x)
            </span>
            {check.has_high_contrast_regions ? (
              <span className="text-[10px] bg-rose-500/20 text-rose-300 border border-rose-500/30 px-1.5 py-0.5 rounded">
                High Contrast Anomaly
              </span>
            ) : (
              <span className="text-[10px] bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 px-1.5 py-0.5 rounded">
                Uniform Degradation
              </span>
            )}
          </div>
          <div className="w-full h-64 flex items-center justify-center bg-black/40 rounded-lg overflow-hidden">
            {heatmapSrc ? (
              <img
                src={heatmapSrc}
                alt="ELA Heatmap"
                className="max-h-full max-w-full object-contain"
              />
            ) : (
              <span className="text-xs text-slate-500">Heatmap unavailable</span>
            )}
          </div>
        </div>
      </div>

      {/* Forensic Interpretation Guidance */}
      <div className="p-3.5 rounded-lg bg-slate-800/40 border border-slate-700/50 text-xs text-slate-300 leading-relaxed">
        <strong>Forensic Reading:</strong> {check.summary}. Note: ELA is most authoritative on lossy JPEGs. PNGs, screenshots, and multiple social media compression rounds naturally alter error surfaces.
      </div>
    </div>
  );
}

// ==========================================
// 3. C2PA Content Credentials Panel
// ==========================================
function C2paPanel({ check }) {
  if (!check) return <div className="text-slate-400 text-sm">No C2PA provenance data.</div>;
  if (check.error) {
    return (
      <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-300 text-sm">
        <p className="font-semibold">C2PA Inspection Error</p>
        <p className="text-xs mt-1 text-amber-200/80">{check.error}</p>
      </div>
    );
  }

  const ms = check.manifest_summary || {};

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <h4 className="text-base font-semibold text-slate-100">Cryptographic Provenance Manifest</h4>
          <p className="text-xs text-slate-400 mt-1">
            Inspects Coalition for Content Provenance and Authenticity (C2PA) cryptographic assertions and digital signatures.
          </p>
        </div>
        <div className="flex items-center gap-2">
          {check.has_manifest ? (
            check.valid ? (
              <span className="px-3 py-1 rounded-lg text-xs font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 flex items-center gap-1.5">
                <CheckCircle2 className="h-4 w-4" /> Valid Manifest
              </span>
            ) : (
              <span className="px-3 py-1 rounded-lg text-xs font-semibold bg-rose-500/20 text-rose-300 border border-rose-500/40 flex items-center gap-1.5">
                <XCircle className="h-4 w-4" /> Tampered / Invalid Manifest
              </span>
            )
          ) : (
            <span className="px-3 py-1 rounded-lg text-xs font-medium bg-slate-800 text-slate-400 border border-slate-700 flex items-center gap-1.5">
              <Info className="h-4 w-4" /> No Manifest Embedded
            </span>
          )}
        </div>
      </div>

      {check.has_manifest ? (
        <div className="space-y-4">
          {/* AI Disclosure Warning */}
          {check.ai_generated_flag && (
            <div className="p-4 rounded-xl bg-rose-500/15 border border-rose-500/40 flex items-start gap-3 text-rose-200">
              <Bot className="h-5 w-5 text-rose-400 shrink-0 mt-0.5" />
              <div>
                <p className="text-sm font-semibold">Generative AI Flag Explicitly Declared</p>
                <p className="text-xs text-rose-300/80 mt-0.5">
                  The authoring application embedded an authoritative C2PA assertion indicating this content was synthetically generated or in-painted using AI models.
                </p>
              </div>
            </div>
          )}

          {/* Manifest Attributes Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
            <div className="bg-slate-800/40 p-3 rounded-lg border border-slate-700/50">
              <div className="text-[11px] text-slate-400 uppercase tracking-wider font-semibold">Claim Generator</div>
              <div className="text-sm text-slate-200 font-mono mt-1 truncate" title={ms.claim_generator || 'N/A'}>
                {ms.claim_generator || 'Unknown / Not specified'}
              </div>
            </div>
            <div className="bg-slate-800/40 p-3 rounded-lg border border-slate-700/50">
              <div className="text-[11px] text-slate-400 uppercase tracking-wider font-semibold">Signer / Issuer</div>
              <div className="text-sm text-slate-200 font-mono mt-1 truncate" title={ms.issuer || 'N/A'}>
                {ms.issuer || 'Self-signed / Unverified'}
              </div>
            </div>
            <div className="bg-slate-800/40 p-3 rounded-lg border border-slate-700/50">
              <div className="text-[11px] text-slate-400 uppercase tracking-wider font-semibold">Asset Title</div>
              <div className="text-sm text-slate-200 font-mono mt-1 truncate" title={ms.title || 'N/A'}>
                {ms.title || 'Untitled'}
              </div>
            </div>
          </div>

          {/* Actions Performed */}
          {ms.actions && ms.actions.length > 0 && (
            <div className="bg-slate-800/30 p-4 rounded-xl border border-slate-700/40">
              <h5 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                Recorded Editorial Actions:
              </h5>
              <div className="flex flex-wrap gap-2">
                {ms.actions.map((act, i) => (
                  <span key={i} className="px-2.5 py-1 rounded bg-slate-800 text-xs font-mono text-indigo-300 border border-slate-700">
                    {act}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Validation Errors */}
          {check.validation_errors && check.validation_errors.length > 0 && (
            <div className="bg-rose-950/20 p-4 rounded-xl border border-rose-500/30">
              <h5 className="text-xs font-semibold text-rose-300 uppercase tracking-wider mb-1.5 flex items-center gap-1.5">
                <AlertTriangle className="h-4 w-4" /> Signature Validation Errors:
              </h5>
              <ul className="list-disc list-inside text-xs text-rose-200 space-y-1">
                {check.validation_errors.map((err, i) => (
                  <li key={i}>{typeof err === 'string' ? err : JSON.stringify(err)}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      ) : (
        <div className="p-4 rounded-xl bg-slate-800/40 border border-slate-700/50 text-xs text-slate-300 leading-relaxed">
          <p className="font-semibold text-slate-200 mb-1">Standard Web Scenario (No Credentials)</p>
          {check.summary}. Most social media networks (X, Instagram, WhatsApp) strip metadata and provenance manifests upon upload. The absence of a C2PA manifest is not evidence of falsification.
        </div>
      )}
    </div>
  );
}

// ==========================================
// 4. EXIF & Metadata Panel
// ==========================================
function MetadataPanel({ check }) {
  if (!check) return <div className="text-slate-400 text-sm">No metadata available.</div>;
  if (check.error) {
    return (
      <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-300 text-sm">
        <p className="font-semibold">Metadata Read Error</p>
        <p className="text-xs mt-1 text-amber-200/80">{check.error}</p>
      </div>
    );
  }

  const exif = check.fields || check.exif || {};
  const hasExif = (check.has_exif !== false) && Object.keys(exif).length > 0;
  const flags = check.red_flags || check.flags || [];

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <h4 className="text-base font-semibold text-slate-100">Exchangeable Image File Format (EXIF)</h4>
          <p className="text-xs text-slate-400 mt-1">
            Detects camera hardware models, capture timestamps, software signatures, and AI generation prompts.
          </p>
        </div>
        <div className="flex items-center gap-2">
          {flags.length > 0 ? (
            <span className="px-3 py-1 rounded-lg text-xs font-semibold bg-amber-500/20 text-amber-300 border border-amber-500/40 flex items-center gap-1.5">
              <AlertTriangle className="h-4 w-4" /> {flags.length} Red Flag{flags.length > 1 ? 's' : ''}
            </span>
          ) : (
            <span className="px-3 py-1 rounded-lg text-xs font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 flex items-center gap-1.5">
              <CheckCircle2 className="h-4 w-4" /> No Known Red Flags
            </span>
          )}
        </div>
      </div>

      {/* Red Flags List */}
      {flags.length > 0 && (
        <div className="p-4 rounded-xl bg-amber-500/15 border border-amber-500/40 space-y-2">
          <div className="text-xs font-semibold uppercase tracking-wider text-amber-300 flex items-center gap-1.5">
            <AlertTriangle className="h-4 w-4" /> Detected Metadata Flags:
          </div>
          <div className="space-y-1">
            {flags.map((flag, idx) => (
              <div key={idx} className="text-xs font-mono text-amber-200 bg-amber-950/30 px-2.5 py-1.5 rounded border border-amber-500/30">
                {flag}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* EXIF Data Table */}
      {hasExif ? (
        <div>
          <h5 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2.5">
            Embedded Header Properties:
          </h5>
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
            {Object.entries(exif).map(([key, val]) => (
              <div key={key} className="bg-slate-800/40 p-3 rounded-lg border border-slate-700/50">
                <div className="text-[11px] text-slate-400 uppercase font-mono tracking-wider">{key}</div>
                <div className="text-xs sm:text-sm font-semibold text-slate-200 mt-1 truncate" title={String(val)}>
                  {String(val)}
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : (
        <div className="p-4 rounded-xl bg-slate-800/40 border border-slate-700/50 text-xs text-slate-300">
          <p className="font-semibold text-slate-200 mb-1">No EXIF Metadata Header Found</p>
          Standard stripped file. Typical for web downloads, chat exports, screenshots, and AI generators that omit camera tags.
        </div>
      )}

      <div className="text-xs text-slate-400 bg-slate-800/30 p-3.5 rounded-lg border border-slate-700/40">
        <strong>Forensic Summary:</strong> {check.summary}
      </div>
    </div>
  );
}

// ==========================================
// 5. Duplicate Hash Panel
// ==========================================
function DuplicatePanel({ check }) {
  if (!check) return <div className="text-slate-400 text-sm">No duplicate check data.</div>;
  if (check.error) {
    return (
      <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-300 text-sm">
        <p className="font-semibold">Duplicate Check Error</p>
        <p className="text-xs mt-1 text-amber-200/80">{check.error}</p>
      </div>
    );
  }

  const hashes = check.hashes || {};
  const allMatches = check.all_matches || [];

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <h4 className="text-base font-semibold text-slate-100">Perceptual Hash Duplicate Matcher</h4>
          <p className="text-xs text-slate-400 mt-1">
            Computes visual discrete cosine transform hash (pHash) resistant to resizing and recompression. Matches against SQLite database.
          </p>
        </div>
        <div>
          {check.is_duplicate ? (
            <span className="px-3 py-1 rounded-lg text-xs font-semibold bg-rose-500/20 text-rose-300 border border-rose-500/40 flex items-center gap-1.5">
              <Copy className="h-4 w-4" /> Near-Duplicate Found
            </span>
          ) : (
            <span className="px-3 py-1 rounded-lg text-xs font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 flex items-center gap-1.5">
              <CheckCircle2 className="h-4 w-4" /> Unique Media
            </span>
          )}
        </div>
      </div>

      {/* Match Details if Duplicate */}
      {check.is_duplicate && (
        <div className="p-4 rounded-xl bg-rose-500/15 border border-rose-500/40 space-y-2">
          <div className="text-xs font-semibold uppercase tracking-wider text-rose-300">
            Matched Reference Image:
          </div>
          <div className="flex flex-wrap items-center gap-4 text-xs font-mono text-rose-200">
            <div>Label: <strong className="text-white">{check.matched_reference}</strong></div>
            <div>Hamming Distance: <strong className="text-white">{check.distance} / 64</strong></div>
            <div>Similarity: <strong className="text-white">{check.similarity_pct?.toFixed(1)}%</strong></div>
          </div>
        </div>
      )}

      {/* Generated Hashes */}
      <div>
        <h5 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2.5">
          Perceptual Fingerprints (64-bit Hex):
        </h5>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <div className="bg-slate-800/40 p-3 rounded-lg border border-slate-700/50">
            <div className="text-[11px] text-slate-400 font-semibold uppercase">pHash (DCT)</div>
            <div className="text-xs font-mono text-indigo-300 mt-1 truncate" title={hashes.phash}>
              {hashes.phash || 'N/A'}
            </div>
          </div>
          <div className="bg-slate-800/40 p-3 rounded-lg border border-slate-700/50">
            <div className="text-[11px] text-slate-400 font-semibold uppercase">aHash (Average)</div>
            <div className="text-xs font-mono text-indigo-300 mt-1 truncate" title={hashes.ahash}>
              {hashes.ahash || 'N/A'}
            </div>
          </div>
          <div className="bg-slate-800/40 p-3 rounded-lg border border-slate-700/50">
            <div className="text-[11px] text-slate-400 font-semibold uppercase">dHash (Difference)</div>
            <div className="text-xs font-mono text-indigo-300 mt-1 truncate" title={hashes.dhash}>
              {hashes.dhash || 'N/A'}
            </div>
          </div>
        </div>
      </div>

      {/* Close Matches List */}
      {allMatches.length > 0 && (
        <div>
          <h5 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
            Close Matches in Reference Database:
          </h5>
          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left border-collapse">
              <thead>
                <tr className="border-b border-slate-800 text-slate-400 bg-slate-900/40">
                  <th className="p-2">Reference Label</th>
                  <th className="p-2">Filename</th>
                  <th className="p-2">Hamming Dist</th>
                  <th className="p-2">Similarity</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-mono">
                {allMatches.map((m, i) => (
                  <tr key={i} className="hover:bg-slate-800/30">
                    <td className="p-2 font-semibold text-slate-200">{m.label}</td>
                    <td className="p-2 text-slate-400">{m.filename}</td>
                    <td className="p-2 text-slate-300">{m.distance}</td>
                    <td className="p-2 text-indigo-300">{m.similarity_pct?.toFixed(1)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      <div className="text-xs text-slate-300 bg-slate-800/30 p-3.5 rounded-lg border border-slate-700/40">
        <strong>Summary:</strong> {check.summary}
      </div>
    </div>
  );
}
