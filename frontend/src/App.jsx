import React, { useState } from 'react';
import Navbar from './components/Navbar';
import UploadBox from './components/UploadBox';
import VerdictCard from './components/VerdictCard';
import EvidenceTable from './components/EvidenceTable';
import CheckDetails from './components/CheckDetails';
import ReferenceManager from './components/ReferenceManager';
import { analyzeImage } from './api';
import { 
  Loader2, 
  RotateCcw, 
  Download, 
  AlertOctagon, 
  ShieldAlert, 
  Info,
  CheckCircle,
  FileSearch,
  Sparkles,
  FileText
} from 'lucide-react';

export default function App() {
  const [file, setFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [analysisResult, setAnalysisResult] = useState(null);
  const [activeCheckTab, setActiveCheckTab] = useState('ai_detector');
  const [isRefModalOpen, setIsRefModalOpen] = useState(false);
  const [clientDimensions, setClientDimensions] = useState(null);

  // Handle analysis submission
  const handleAnalyze = async (selectedFile, objectUrl) => {
    setFile(selectedFile);
    setPreviewUrl(objectUrl);
    setLoading(true);
    setError(null);

    // Measure natural dimensions on client side as an immediate fallback
    try {
      const img = new Image();
      img.onload = () => {
        if (img.naturalWidth && img.naturalHeight) {
          setClientDimensions({ width: img.naturalWidth, height: img.naturalHeight });
        }
      };
      img.src = objectUrl;
    } catch {
      // Ignored
    }

    try {
      const data = await analyzeImage(selectedFile);
      setAnalysisResult(data);
      // Auto-focus on highest risk check or ai_detector
      if (data.verdict?.evidence && data.verdict.evidence.length > 0) {
        const suspiciousItem = data.verdict.evidence.find(e => e.status === 'suspicious');
        if (suspiciousItem) {
          setActiveCheckTab(suspiciousItem.check);
        } else {
          setActiveCheckTab('ai_detector');
        }
      }
    } catch (err) {
      console.error('Analysis failed:', err);
      setError(
        err.message || 'Failed to analyze media. Please check your network connection and backend server.'
      );
    } finally {
      setLoading(false);
    }
  };

  // Reset to analyze another image
  const handleReset = () => {
    setAnalysisResult(null);
    setError(null);
    setFile(null);
    setClientDimensions(null);
    if (previewUrl) {
      URL.revokeObjectURL(previewUrl);
      setPreviewUrl(null);
    }
  };

  // Open clean, human-readable printable forensic report (ready for PDF export)
  const handlePrintReadableReport = () => {
    if (!analysisResult) return;
    const { verdict, filename, image_dimensions, image_format, processing_time_ms } = analysisResult;
    const isAi = verdict.label === 'likely_ai_generated';
    const isAuthentic = verdict.label === 'likely_authentic';
    const badgeColor = isAi ? '#dc2626' : isAuthentic ? '#059669' : '#d97706';
    const badgeBg = isAi ? '#fef2f2' : isAuthentic ? '#ecfdf5' : '#fffbeb';

    const effectiveDims = image_dimensions || clientDimensions;
    const dimsString = (effectiveDims && effectiveDims.width && effectiveDims.height)
      ? `${effectiveDims.width} × ${effectiveDims.height} px`
      : 'Auto-scaled';
    const formatString = image_format || (file?.type ? file.type.replace('image/', '').toUpperCase() : 'JPEG');

    const evidenceRows = (verdict.evidence || []).map(ev => {
      const statusColor = ev.status === 'suspicious' ? '#dc2626' : ev.status === 'clean' ? '#059669' : '#4b5563';
      const statusBg = ev.status === 'suspicious' ? '#fef2f2' : ev.status === 'clean' ? '#ecfdf5' : '#f3f4f6';
      return `
        <tr style="border-bottom: 1px solid #e5e7eb;">
          <td style="padding: 10px 12px; font-weight: 600; text-transform: uppercase; font-size: 11px; letter-spacing: 0.05em; color: #374151;">${ev.check.replace('_', ' ')}</td>
          <td style="padding: 10px 12px;">
            <span style="display: inline-block; padding: 3px 10px; border-radius: 9999px; font-size: 11px; font-weight: 700; color: ${statusColor}; background: ${statusBg}; text-transform: uppercase;">
              ${ev.status}
            </span>
          </td>
          <td style="padding: 10px 12px; font-size: 12px; font-family: monospace; color: #111827;">
            ${ev.score !== null ? (ev.score * 100).toFixed(1) + '%' : 'N/A'}
          </td>
          <td style="padding: 10px 12px; font-size: 13px; color: #4b5563;">${ev.summary}</td>
        </tr>
      `;
    }).join('');

    const reasonsList = (verdict.reasons || []).map(r => `
      <li style="margin-bottom: 8px; font-size: 13px; line-height: 1.5; color: #374151;">${r}</li>
    `).join('');

    const reportHtml = `
      <!DOCTYPE html>
      <html>
        <head>
          <title>Forensic Report - ${filename}</title>
          <meta charset="utf-8" />
          <style>
            @media print {
              body { margin: 0; padding: 20px; font-size: 12pt; background: #fff !important; }
              .no-print { display: none !important; }
              .container { border: none !important; box-shadow: none !important; padding: 0 !important; max-width: 100% !important; }
            }
            body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #f9fafb; color: #111827; margin: 0; padding: 32px 16px; }
            .container { max-width: 820px; margin: 0 auto; background: #ffffff; border: 1px solid #e5e7eb; border-radius: 12px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); padding: 32px; }
            .header { display: flex; justify-content: space-between; align-items: flex-start; border-bottom: 2px solid #f3f4f6; padding-bottom: 20px; margin-bottom: 20px; }
            .title { font-size: 22px; font-weight: 800; color: #111827; margin: 0 0 4px 0; }
            .subtitle { font-size: 13px; color: #6b7280; margin: 0; }
            .btn { display: inline-flex; align-items: center; gap: 8px; padding: 9px 18px; background: #4f46e5; color: #fff; border-radius: 8px; font-size: 13px; font-weight: 600; text-decoration: none; border: none; cursor: pointer; }
            .btn:hover { background: #4338ca; }
            .badge-box { background: ${badgeBg}; border: 1.5px solid ${badgeColor}40; border-radius: 10px; padding: 20px; display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; }
            .verdict-tag { font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: ${badgeColor}; }
            .verdict-label { font-size: 24px; font-weight: 800; color: ${badgeColor}; margin: 4px 0 0 0; }
            .score-circle { text-align: right; }
            .score-val { font-size: 32px; font-weight: 900; color: ${badgeColor}; }
            .score-sub { font-size: 11px; color: #6b7280; text-transform: uppercase; font-weight: 600; }
            .section-title { font-size: 14px; font-weight: 700; color: #111827; border-bottom: 1px solid #e5e7eb; padding-bottom: 6px; margin: 24px 0 12px 0; text-transform: uppercase; letter-spacing: 0.03em; }
            table { width: 100%; border-collapse: collapse; text-align: left; }
            th { padding: 10px 12px; background: #f9fafb; font-size: 11px; text-transform: uppercase; letter-spacing: 0.05em; color: #6b7280; border-bottom: 1px solid #e5e7eb; }
            .meta-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; background: #f9fafb; border-radius: 8px; padding: 12px 16px; margin-bottom: 20px; font-size: 13px; }
            .meta-label { color: #6b7280; font-size: 11px; text-transform: uppercase; margin-bottom: 2px; }
            .meta-val { font-weight: 600; color: #111827; }
            .footer { margin-top: 36px; padding-top: 16px; border-top: 1px solid #e5e7eb; font-size: 11px; color: #9ca3af; text-align: center; }
          </style>
        </head>
        <body>
          <div class="container">
            <div class="no-print" style="margin-bottom: 20px; display: flex; justify-content: flex-end; gap: 10px;">
              <button class="btn" onclick="window.print()">🖨️ Print / Save as PDF</button>
            </div>
            
            <div class="header">
              <div>
                <h1 class="title">Fake Media Detector</h1>
                <p class="subtitle">Multi-Vector Digital Forensics Examination Report</p>
              </div>
              <div style="text-align: right; font-size: 12px; color: #6b7280;">
                <div>Report Date: ${new Date().toLocaleString()}</div>
                <div>Latency: ${processing_time_ms} ms</div>
              </div>
            </div>

            <div class="meta-grid">
              <div>
                <div class="meta-label">Target Media</div>
                <div class="meta-val" style="word-break: break-all;">${filename}</div>
              </div>
              <div>
                <div class="meta-label">Dimensions</div>
                <div class="meta-val">${dimsString}</div>
              </div>
              <div>
                <div class="meta-label">Image Format</div>
                <div class="meta-val">${formatString}</div>
              </div>
              <div>
                <div class="meta-label">Confidence</div>
                <div class="meta-val" style="text-transform: capitalize;">${verdict.confidence}</div>
              </div>
            </div>

            <div class="badge-box">
              <div>
                <div class="verdict-tag">Official Determination</div>
                <div class="verdict-label">${verdict.display_label}</div>
              </div>
              <div class="score-circle">
                <div class="score-val">${Math.round(verdict.overall_score * 100)}%</div>
                <div class="score-sub">Suspicion Index</div>
              </div>
            </div>

            <div class="section-title">Key Forensic Findings & Rationales</div>
            <ul style="margin: 0; padding-left: 20px;">
              ${reasonsList}
            </ul>

            <div class="section-title">Multi-Vector Evidence Matrix</div>
            <table>
              <thead>
                <tr>
                  <th>Detection Vector</th>
                  <th>Evidence Status</th>
                  <th>Risk Score</th>
                  <th>Findings Summary</th>
                </tr>
              </thead>
              <tbody>
                ${evidenceRows}
              </tbody>
            </table>

            <div class="footer">
              Generated by Fake Media Detector • Triangulated Forensics (Deep Learning, Error Level Analysis, C2PA Provenance, EXIF Forensics, Perceptual Hashing) • Designed for Transparent Human Auditing
            </div>
          </div>
        </body>
      </html>
    `;

    const printWindow = window.open('', '_blank');
    if (printWindow) {
      printWindow.document.open();
      printWindow.document.write(reportHtml);
      printWindow.document.close();
    }
  };

  // Download raw JSON forensic report
  const handleDownloadReport = () => {
    if (!analysisResult) return;
    const blob = new Blob([JSON.stringify(analysisResult, null, 2)], {
      type: 'application/json',
    });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    const baseName = file?.name ? file.name.replace(/\.[^/.]+$/, '') : 'media';
    link.download = `forensic-report-${baseName}-${Date.now()}.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans selection:bg-indigo-500 selection:text-white">
      {/* Top Navbar */}
      <Navbar onOpenReferences={() => setIsRefModalOpen(true)} />

      {/* Main Content Area */}
      <main className="flex-1 max-w-6xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 sm:py-12">
        {/* Intro Banner */}
        <div className="text-center mb-10">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 text-xs font-semibold uppercase tracking-wider mb-3">
            <Sparkles className="h-3.5 w-3.5" />
            <span>Forensic Synthesis & Verification Engine</span>
          </div>
          <h1 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold tracking-tight text-white">
            Detect AI-Generated & <span className="gradient-text">Manipulated Media</span>
          </h1>
          <p className="mt-3 text-sm sm:text-base text-slate-400 max-w-2xl mx-auto leading-relaxed">
            Multi-layered digital verification combining deep learning diffusion classifiers, JPEG Error Level Analysis (ELA), C2PA Content Credentials provenance, and perceptual hashing.
          </p>
        </div>

        {/* Upload State (when no analysis result yet) */}
        {!analysisResult && (
          <div className="space-y-6">
            <UploadBox onAnalyze={handleAnalyze} isLoading={loading} />

            {/* Loading Indicator */}
            {loading && (
              <div className="glass-panel max-w-xl mx-auto rounded-2xl p-8 border border-indigo-500/30 text-center shadow-2xl animate-pulse">
                <Loader2 className="h-10 w-10 text-indigo-400 animate-spin mx-auto mb-4" />
                <h3 className="text-lg font-bold text-white mb-1">
                  Running 5 Independent Forensic Checks...
                </h3>
                <p className="text-xs sm:text-sm text-slate-400 max-w-md mx-auto">
                  Inspecting EXIF tags, calculating ELA compression errors, querying C2PA cryptographic manifests, computing perceptual hashes, and evaluating AI vision transformers.
                </p>
              </div>
            )}

            {/* Error Message with Retry */}
            {error && (
              <div className="glass-panel max-w-xl mx-auto rounded-2xl p-6 border border-rose-500/40 bg-rose-500/10 text-center shadow-xl">
                <AlertOctagon className="h-8 w-8 text-rose-400 mx-auto mb-3" />
                <h4 className="text-sm font-semibold text-rose-200 mb-1">Analysis Error</h4>
                <p className="text-xs text-rose-300/80 mb-4">{error}</p>
                <button
                  onClick={() => file && previewUrl && handleAnalyze(file, previewUrl)}
                  className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-rose-600 hover:bg-rose-500 text-white text-xs font-semibold transition-colors cursor-pointer"
                >
                  <RotateCcw className="h-3.5 w-3.5" />
                  <span>Retry Analysis</span>
                </button>
              </div>
            )}
          </div>
        )}

        {/* Analysis Results Section */}
        {analysisResult && (
          <div className="space-y-8 animate-fade-in">
            {/* Action Bar (Top of Results) */}
            <div className="flex flex-col sm:flex-row items-center justify-between gap-4 pb-2 border-b border-slate-800">
              <div className="flex items-center gap-2 text-xs text-slate-400">
                <FileSearch className="h-4 w-4 text-indigo-400" />
                <span>Forensic evaluation report for:</span>
                <span className="font-semibold text-slate-200 font-mono truncate max-w-xs">
                  {analysisResult.filename}
                </span>
                <span className="text-slate-500">
                  ({(analysisResult.image_dimensions?.width || clientDimensions?.width) ? `${analysisResult.image_dimensions?.width || clientDimensions?.width}×${analysisResult.image_dimensions?.height || clientDimensions?.height}px, ` : ''}{analysisResult.image_format || (file?.type ? file.type.replace('image/', '').toUpperCase() : 'JPEG')})
                </span>
              </div>

              <div className="flex flex-wrap items-center gap-2.5 w-full sm:w-auto justify-end">
                <button
                  onClick={handlePrintReadableReport}
                  className="inline-flex items-center justify-center gap-1.5 px-3.5 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-xs font-semibold text-white transition-all shadow-md shadow-indigo-600/20 cursor-pointer"
                  title="Open clean, printable executive forensic report (Save as PDF)"
                >
                  <FileText className="h-3.5 w-3.5" />
                  <span>Print / Save PDF Report</span>
                </button>

                <button
                  onClick={handleDownloadReport}
                  className="inline-flex items-center justify-center gap-1.5 px-3.5 py-2 rounded-xl bg-slate-800/80 hover:bg-slate-700/80 border border-slate-700 text-xs font-medium text-slate-200 transition-colors shadow-sm cursor-pointer"
                  title="Export raw JSON forensic evidence for technical auditing"
                >
                  <Download className="h-3.5 w-3.5 text-slate-400" />
                  <span>Raw JSON</span>
                </button>

                <button
                  onClick={handleReset}
                  className="inline-flex items-center justify-center gap-1.5 px-3.5 py-2 rounded-xl bg-slate-800/80 hover:bg-slate-700 border border-slate-700 text-xs font-medium text-slate-300 transition-all shadow-sm cursor-pointer"
                >
                  <RotateCcw className="h-3.5 w-3.5" />
                  <span>Analyze Another</span>
                </button>
              </div>
            </div>

            {/* Verdict Card */}
            <VerdictCard
              verdict={analysisResult.verdict}
              processingTimeMs={analysisResult.processing_time_ms}
              filename={analysisResult.filename}
            />

            {/* Evidence Matrix Table */}
            <EvidenceTable
              evidence={analysisResult.verdict?.evidence}
              activeTab={activeCheckTab}
              onSelectTab={setActiveCheckTab}
            />

            {/* Deep-Dive Check Detail Tabs */}
            <CheckDetails
              checks={analysisResult.checks}
              originalPreviewUrl={previewUrl}
              activeTab={activeCheckTab}
              onSelectTab={setActiveCheckTab}
            />

            {/* Forensic Ethics & Reliability Disclaimer */}
            <div className="p-4 rounded-xl bg-slate-900/40 border border-slate-800 flex items-start gap-3 text-xs text-slate-400 leading-relaxed">
              <Info className="h-5 w-5 text-indigo-400 shrink-0 mt-0.5" />
              <div>
                <strong className="text-slate-200">Forensic Disclaimer:</strong> Results provided by this platform are probabilistic estimates and heuristic signals, not definitive legal proof. Most social media networks routinely strip EXIF metadata and C2PA manifests upon upload; missing credentials or metadata does not prove an image is fake or AI-generated. Always triangulate findings with contextual and corroborative reporting.
              </div>
            </div>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-800 py-6 text-center text-xs text-slate-500">
        <div className="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-2">
          <span>Fake Media Detector • Production-Grade Multimodal Forensic System</span>
          <span className="text-slate-600">Phase 4: Explainable Verdict Engine & Web Client</span>
        </div>
      </footer>

      {/* Reference Database Modal */}
      <ReferenceManager
        isOpen={isRefModalOpen}
        onClose={() => setIsRefModalOpen(false)}
      />
    </div>
  );
}
