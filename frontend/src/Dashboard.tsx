import { Download, Rocket, UploadCloud, WandSparkles } from 'lucide-react';
import { ChangeEvent, useState } from 'react';

type ProcessResponse = {
  jobId: string;
  downloadUrl: string;
  originalDuration: number;
  processedDuration: number;
  removedSeconds: number;
};

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

export function Dashboard() {
  const [file, setFile] = useState<File | null>(null);
  const [status, setStatus] = useState('Upload a gameplay clip to start.');
  const [progress, setProgress] = useState(0);
  const [result, setResult] = useState<ProcessResponse | null>(null);
  const [error, setError] = useState('');

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    setFile(event.target.files?.[0] ?? null);
    setResult(null);
    setError('');
    setProgress(0);
  }

  async function processVideo() {
    if (!file) {
      setError('Choose a video file before processing.');
      return;
    }

    const formData = new FormData();
    formData.append('file', file);
    setStatus('Uploading and analyzing silence across the full clip...');
    setProgress(35);
    setError('');

    try {
      const response = await fetch(`${API_BASE_URL}/api/videos/process`, {
        method: 'POST',
        body: formData,
      });

      const payload = await response.json().catch(() => null);
      if (!response.ok) {
        throw new Error(payload?.detail ?? `Backend returned ${response.status}`);
      }

      setResult(payload as ProcessResponse);
      setStatus('Your SaaS-ready ZipZop edit is ready.');
      setProgress(100);
    } catch (caughtError) {
      const message = caughtError instanceof Error ? caughtError.message : 'Unknown processing error';
      setError(`Processing failed: ${message}`);
      setStatus('Check the backend terminal logs for the exact stack trace.');
      setProgress(0);
    }
  }

  const downloadHref = result ? `${API_BASE_URL}${result.downloadUrl}` : '#';

  return (
    <main className="min-h-screen bg-[#080811] text-white">
      <section className="mx-auto flex max-w-6xl flex-col gap-8 px-6 py-10">
        <div className="rounded-3xl border border-fuchsia-500/20 bg-white/5 p-8 shadow-2xl shadow-fuchsia-950/40">
          <p className="mb-3 flex items-center gap-2 text-sm font-bold uppercase tracking-[0.35em] text-fuchsia-300">
            <Rocket size={18} /> ZipZop Pro AI Editor
          </p>
          <h1 className="max-w-3xl text-5xl font-black leading-tight">
            SaaS-ready AI gaming video editor with dynamic full-length silence trimming.
          </h1>
          <p className="mt-5 max-w-2xl text-lg text-slate-300">
            Built with free open-source tools: React, Tailwind CSS, FastAPI, and MoviePy. No hardcoded
            five-second caps, no mystery fetch failures.
          </p>
        </div>

        <div className="grid gap-6 lg:grid-cols-[1.2fr_0.8fr]">
          <div className="rounded-3xl border border-cyan-400/20 bg-slate-950 p-6">
            <label className="flex cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed border-cyan-400/40 bg-cyan-400/5 p-10 text-center hover:bg-cyan-400/10">
              <UploadCloud className="mb-4 text-cyan-300" size={48} />
              <span className="text-xl font-bold">Upload gameplay video</span>
              <span className="mt-2 text-slate-400">MP4, MOV, MKV, WEBM, or AVI</span>
              <input className="hidden" type="file" accept="video/*" onChange={handleFileChange} />
            </label>

            {file && <p className="mt-4 text-sm text-slate-300">Selected: {file.name}</p>}

            <button
              className="mt-6 flex w-full items-center justify-center gap-2 rounded-2xl bg-fuchsia-500 px-6 py-4 font-black uppercase tracking-wider text-white transition hover:bg-fuchsia-400 disabled:cursor-not-allowed disabled:bg-slate-700"
              onClick={processVideo}
              disabled={!file}
            >
              <WandSparkles size={20} /> Process full video
            </button>

            <div className="mt-6 h-3 overflow-hidden rounded-full bg-slate-800">
              <div className="h-full bg-gradient-to-r from-cyan-400 to-fuchsia-500 transition-all" style={{ width: `${progress}%` }} />
            </div>
            <p className="mt-3 text-slate-300">{status}</p>
            {error && <p className="mt-3 rounded-xl border border-red-500/40 bg-red-500/10 p-3 text-red-200">{error}</p>}
          </div>

          <aside className="rounded-3xl border border-fuchsia-500/20 bg-slate-950 p-6">
            <h2 className="text-2xl font-black">Creator SaaS Output</h2>
            <p className="mt-3 text-slate-400">Package polished clips for shorts, reels, and gaming channels.</p>
            {result ? (
              <div className="mt-6 space-y-4">
                <Metric label="Original" value={`${result.originalDuration}s`} />
                <Metric label="Processed" value={`${result.processedDuration}s`} />
                <Metric label="Removed" value={`${result.removedSeconds}s`} />
                <a className="flex items-center justify-center gap-2 rounded-2xl bg-cyan-400 px-5 py-4 font-black text-slate-950" href={downloadHref}>
                  <Download size={20} /> Download Edit
                </a>
              </div>
            ) : (
              <p className="mt-6 rounded-2xl bg-white/5 p-5 text-slate-400">Your processed video metrics and download link will appear here.</p>
            )}
          </aside>
        </div>
      </section>
    </main>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl bg-white/5 p-4">
      <p className="text-sm uppercase tracking-widest text-slate-500">{label}</p>
      <p className="text-2xl font-black text-cyan-300">{value}</p>
    </div>
  );
}
