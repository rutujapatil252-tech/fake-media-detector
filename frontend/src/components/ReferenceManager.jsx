import React, { useState, useEffect } from 'react';
import { 
  X, 
  Upload, 
  Database, 
  Plus, 
  RefreshCw, 
  CheckCircle, 
  AlertCircle, 
  FileText,
  Hash
} from 'lucide-react';
import { listReferences, addReference } from '../api';

export default function ReferenceManager({ isOpen, onClose }) {
  const [references, setReferences] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [successMsg, setSuccessMsg] = useState(null);

  // Form state
  const [file, setFile] = useState(null);
  const [label, setLabel] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState(null);

  const fetchList = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await listReferences();
      setReferences(data.references || []);
    } catch (err) {
      setError(err.message || 'Failed to load reference list.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      fetchList();
      setSuccessMsg(null);
      setFormError(null);
      setFile(null);
      setLabel('');
    }
  }, [isOpen]);

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      const selected = e.target.files[0];
      setFile(selected);
      if (!label) {
        // Auto-populate label with filename without extension
        const baseName = selected.name.replace(/\.[^/.]+$/, '');
        setLabel(baseName);
      }
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!file) {
      setFormError('Please select an image file.');
      return;
    }
    if (!label.trim()) {
      setFormError('Please provide a descriptive label.');
      return;
    }

    setSubmitting(true);
    setFormError(null);
    try {
      await addReference(file, label.trim());
      setSuccessMsg(`"${label.trim()}" successfully indexed into perceptual hash index.`);
      setFile(null);
      setLabel('');
      // Refresh list
      await fetchList();
    } catch (err) {
      setFormError(err.message || 'Failed to index reference image.');
    } finally {
      setSubmitting(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-fade-in">
      <div 
        className="glass-panel w-full max-w-3xl rounded-2xl border border-slate-700/80 shadow-2xl overflow-hidden flex flex-col max-h-[90vh]"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="p-5 border-b border-slate-700/60 bg-slate-900/60 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-indigo-500/20 text-indigo-400 border border-indigo-500/30">
              <Database className="h-5 w-5" />
            </div>
            <div>
              <h3 className="font-bold text-slate-100 text-base">Reference Image Registry</h3>
              <p className="text-xs text-slate-400">
                Known media fingerprints for perceptual hash duplicate detection.
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 overflow-y-auto space-y-6">
          {/* Add Reference Form */}
          <form onSubmit={handleSubmit} className="bg-slate-900/50 p-4 rounded-xl border border-slate-800 space-y-4">
            <div className="text-xs font-semibold uppercase tracking-wider text-slate-300 flex items-center gap-2">
              <Plus className="h-4 w-4 text-indigo-400" />
              Index New Reference Media
            </div>

            {formError && (
              <div className="text-xs p-3 rounded-lg bg-rose-500/20 text-rose-300 border border-rose-500/30 flex items-center gap-2">
                <AlertCircle className="h-4 w-4 shrink-0" />
                <span>{formError}</span>
              </div>
            )}

            {successMsg && (
              <div className="text-xs p-3 rounded-lg bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 flex items-center gap-2">
                <CheckCircle className="h-4 w-4 shrink-0" />
                <span>{successMsg}</span>
              </div>
            )}

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1">
                  Reference Label / Entity
                </label>
                <input
                  type="text"
                  placeholder="e.g. Official White House Photo 2024"
                  value={label}
                  onChange={(e) => setLabel(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-800/80 border border-slate-700 rounded-lg text-xs sm:text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition-colors"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1">
                  Image File (JPG, PNG, WebP)
                </label>
                <input
                  type="file"
                  accept="image/jpeg,image/png,image/webp"
                  onChange={handleFileChange}
                  className="w-full text-xs text-slate-400 file:mr-3 file:py-1.5 file:px-3 file:rounded-md file:border-0 file:text-xs file:font-semibold file:bg-indigo-600/30 file:text-indigo-300 hover:file:bg-indigo-600/50 cursor-pointer"
                />
              </div>
            </div>

            <div className="flex justify-end">
              <button
                type="submit"
                disabled={submitting}
                className="btn-primary text-xs flex items-center gap-2 py-2 px-4"
              >
                {submitting ? (
                  <>
                    <RefreshCw className="h-3.5 w-3.5 animate-spin" />
                    <span>Calculating Hashes...</span>
                  </>
                ) : (
                  <>
                    <Plus className="h-3.5 w-3.5" />
                    <span>Index Image</span>
                  </>
                )}
              </button>
            </div>
          </form>

          {/* Reference List Header */}
          <div className="flex items-center justify-between">
            <div className="text-xs font-semibold uppercase tracking-wider text-slate-300 flex items-center gap-2">
              <Hash className="h-4 w-4 text-indigo-400" />
              Indexed References ({references.length})
            </div>
            <button
              onClick={fetchList}
              disabled={loading}
              className="text-xs text-slate-400 hover:text-slate-200 flex items-center gap-1.5 transition-colors"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
              <span>Refresh</span>
            </button>
          </div>

          {/* Reference Table */}
          {error ? (
            <div className="text-xs p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300">
              {error}
            </div>
          ) : references.length === 0 ? (
            <div className="text-center py-8 text-slate-500 text-xs">
              No reference images currently stored in the database. Add one above to detect reuse!
            </div>
          ) : (
            <div className="overflow-x-auto border border-slate-800 rounded-xl">
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="bg-slate-900/60 text-slate-400 border-b border-slate-800 text-[11px] uppercase tracking-wider">
                    <th className="py-2.5 px-3">Label</th>
                    <th className="py-2.5 px-3">Filename</th>
                    <th className="py-2.5 px-3">pHash (DCT)</th>
                    <th className="py-2.5 px-3">Indexed Date</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/80">
                  {references.map((ref) => (
                    <tr key={ref.id} className="hover:bg-slate-800/40">
                      <td className="py-2.5 px-3 font-semibold text-slate-200">{ref.label}</td>
                      <td className="py-2.5 px-3 text-slate-400 truncate max-w-[150px]" title={ref.filename}>
                        {ref.filename}
                      </td>
                      <td className="py-2.5 px-3 font-mono text-indigo-300 text-[11px]">
                        {ref.phash}
                      </td>
                      <td className="py-2.5 px-3 text-slate-400 whitespace-nowrap">
                        {ref.created_at ? new Date(ref.created_at).toLocaleDateString() : 'N/A'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-slate-700/60 bg-slate-900/40 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
