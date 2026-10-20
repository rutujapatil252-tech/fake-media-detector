import React, { useRef, useState } from 'react';
import { UploadCloud, Image as ImageIcon, X, AlertCircle, Sparkles } from 'lucide-react';

const MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024; // 10MB
const ALLOWED_EXTS = ['.jpg', '.jpeg', '.png', '.webp'];

export default function UploadBox({ onAnalyze, isLoading }) {
  const [selectedFile, setSelectedFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [dragActive, setDragActive] = useState(false);
  const [validationError, setValidationError] = useState(null);
  const fileInputRef = useRef(null);

  const validateAndSetFile = (file) => {
    setValidationError(null);

    if (!file) return;

    const fileName = file.name || '';
    const ext = fileName.includes('.') ? fileName.slice(fileName.lastIndexOf('.')).toLowerCase() : '';
    const isExtValid = ALLOWED_EXTS.includes(ext);
    const isMimeValid = !file.type || file.type.startsWith('image/');

    if (!isExtValid && !isMimeValid) {
      setValidationError('Unsupported format. Please upload a JPG, JPEG, PNG, or WebP image.');
      return;
    }

    if (file.size > MAX_FILE_SIZE_BYTES) {
      const sizeMb = (file.size / (1024 * 1024)).toFixed(1);
      setValidationError(`File is too large (${sizeMb} MB). Maximum allowed size is 10 MB.`);
      return;
    }

    setSelectedFile(file);
    const objectUrl = URL.createObjectURL(file);
    setPreviewUrl(objectUrl);
  };

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      validateAndSetFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      validateAndSetFile(e.target.files[0]);
    }
  };

  const handleClear = () => {
    setSelectedFile(null);
    if (previewUrl) {
      URL.revokeObjectURL(previewUrl);
      setPreviewUrl(null);
    }
    setValidationError(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (selectedFile && !isLoading) {
      onAnalyze(selectedFile, previewUrl);
    }
  };

  return (
    <div className="w-full max-w-3xl mx-auto">
      <form onSubmit={handleSubmit}>
        {/* Hidden file input */}
        <input
          ref={fileInputRef}
          type="file"
          accept=".jpg,.jpeg,.png,.webp,image/jpeg,image/png,image/webp"
          onChange={handleFileChange}
          className="hidden"
          id="image-upload-input"
        />

        {/* Validation error message */}
        {validationError && (
          <div className="mb-4 p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-sm flex items-center gap-2">
            <AlertCircle className="h-4 w-4 shrink-0 text-rose-400" />
            <span>{validationError}</span>
          </div>
        )}

        {!previewUrl ? (
          /* Dropzone */
          <div
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            className={`border-2 border-dashed rounded-2xl p-8 sm:p-12 text-center cursor-pointer transition-all duration-200 glass-panel ${
              dragActive
                ? 'border-indigo-400 bg-indigo-950/30 scale-[1.01]'
                : 'border-slate-700/80 hover:border-indigo-500/60 hover:bg-slate-900/80'
            }`}
          >
            <div className="mx-auto w-16 h-16 mb-4 rounded-2xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400 group-hover:scale-110 transition-transform">
              <UploadCloud className="h-8 w-8" />
            </div>
            <h3 className="text-base sm:text-lg font-semibold text-white mb-1">
              Drag & drop your image here, or <span className="text-indigo-400 underline underline-offset-2">browse</span>
            </h3>
            <p className="text-xs sm:text-sm text-slate-400 max-w-md mx-auto mb-4">
              Supported formats: JPEG, PNG, WebP (up to 10 MB).
            </p>
            <div className="flex items-center justify-center gap-4 text-xs text-slate-500">
              <span className="flex items-center gap-1">✓ EXIF Forensics</span>
              <span className="flex items-center gap-1">✓ ELA Heatmap</span>
              <span className="flex items-center gap-1">✓ C2PA Provenance</span>
              <span className="flex items-center gap-1">✓ AI Classifier</span>
            </div>

            {/* Quick Demo Samples */}
            <div className="mt-6 pt-5 border-t border-slate-800/80 flex flex-wrap items-center justify-center gap-3">
              <span className="text-xs text-slate-400 font-medium">Quick Demo Samples:</span>
              <button
                type="button"
                id="btn-sample-real"
                onClick={async (e) => {
                  e.stopPropagation();
                  try {
                    const res = await fetch('/sample_real.jpg');
                    const blob = await res.blob();
                    const sampleFile = new File([blob], 'canon_eos_r5_sample.jpg', { type: 'image/jpeg' });
                    validateAndSetFile(sampleFile);
                  } catch (err) {
                    console.error('Failed to load sample:', err);
                  }
                }}
                className="px-3 py-1.5 rounded-lg bg-slate-800/90 hover:bg-slate-700 border border-slate-700 text-xs text-emerald-300 font-medium transition-colors cursor-pointer"
              >
                📸 Authentic Camera Photo
              </button>
              <button
                type="button"
                id="btn-sample-ai"
                onClick={async (e) => {
                  e.stopPropagation();
                  try {
                    const res = await fetch('/sample_ai.jpg');
                    const blob = await res.blob();
                    const sampleFile = new File([blob], 'cyberpunk_robot_ai.jpg', { type: 'image/jpeg' });
                    validateAndSetFile(sampleFile);
                  } catch (err) {
                    console.error('Failed to load sample:', err);
                  }
                }}
                className="px-3 py-1.5 rounded-lg bg-slate-800/90 hover:bg-slate-700 border border-slate-700 text-xs text-rose-300 font-medium transition-colors cursor-pointer"
              >
                🤖 AI Diffusion Render
              </button>
            </div>
          </div>
        ) : (
          /* Preview and Action Box */
          <div className="glass-panel rounded-2xl p-6 border border-slate-700/80">
            <div className="flex flex-col sm:flex-row items-center gap-6">
              {/* Image Preview */}
              <div className="relative w-40 h-40 shrink-0 rounded-xl overflow-hidden bg-slate-900 border border-slate-700/80 shadow-md group">
                <img
                  src={previewUrl}
                  alt="Upload preview"
                  className="w-full h-full object-cover"
                />
                <button
                  type="button"
                  onClick={handleClear}
                  className="absolute top-2 right-2 p-1.5 rounded-full bg-slate-950/80 text-slate-300 hover:text-white hover:bg-rose-600 transition-colors shadow-lg cursor-pointer"
                  title="Remove image"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>

              {/* Info & Action */}
              <div className="flex-1 w-full text-center sm:text-left">
                <div className="flex items-center justify-center sm:justify-start gap-2 text-indigo-400 text-xs font-medium uppercase tracking-wider mb-1">
                  <ImageIcon className="h-3.5 w-3.5" />
                  <span>Ready for Analysis</span>
                </div>
                <h4 className="text-base font-semibold text-white truncate max-w-sm" title={selectedFile.name}>
                  {selectedFile.name}
                </h4>
                <p className="text-xs text-slate-400 mt-1 mb-4">
                  {(selectedFile.size / (1024 * 1024)).toFixed(2)} MB • {selectedFile.type || 'image'}
                </p>

                <div className="flex items-center justify-center sm:justify-start gap-3">
                  <button
                    type="submit"
                    disabled={isLoading}
                    className="flex items-center justify-center gap-2 px-6 py-2.5 rounded-xl bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white font-medium text-sm transition-all shadow-lg shadow-indigo-600/30 disabled:opacity-50 cursor-pointer"
                  >
                    <Sparkles className="h-4 w-4" />
                    <span>{isLoading ? 'Running 5 Checks...' : 'Run Forensic Analysis'}</span>
                  </button>
                  <button
                    type="button"
                    onClick={handleClear}
                    disabled={isLoading}
                    className="px-4 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-sm font-medium transition-colors cursor-pointer"
                  >
                    Clear
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </form>
    </div>
  );
}
