import React, { useState } from 'react';
import { useAppState } from '../state';
import type { Manuscript } from '../types';
import { uploadDocx } from '../lib/api';

export const ManuscriptUploader: React.FC = () => {
    const { setManuscript, manuscript } = useAppState();
    // Removed JSON display per enhancement request
    const [error, setError] = useState<string | null>(null);
    const [uploading, setUploading] = useState(false);
    const [parsedOnly, setParsedOnly] = useState(false);
    const [reviewRunning, setReviewRunning] = useState(false);

    const onJsonApply = () => { };

    const onFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const f = e.target.files?.[0];
        if (!f) return;
        if (!f.name.toLowerCase().endsWith('.docx')) {
            setError('Only .docx files supported');
            return;
        }
        setUploading(true);
        setError(null);
        try {
            const parsed = await uploadDocx(f); // fast parse only
            setManuscript(parsed);
            setParsedOnly(true);
        } catch (err: any) {
            setError(err.message);
        } finally {
            setUploading(false);
        }
    };

    const onRunFull = async () => {
        if (!manuscript) return;
        setReviewRunning(true);
        setError(null);
        try {
            setError('Use Start Review to run full analysis on parsed manuscript.');
        } finally {
            setReviewRunning(false);
        }
    };

    return (
        <div className="space-y-3">
            <div className="flex items-center justify-between">
                <h3 className="font-medium">Manuscript Input</h3>
                {manuscript && <span className="text-xs text-muted-foreground">Loaded</span>}
            </div>
            <div className="flex flex-col gap-2">
                <label className="text-xs font-medium">Upload DOCX (fast parse)</label>
                <input type="file" accept=".docx" onChange={onFileChange} disabled={uploading} className="text-xs file:mr-3 file:py-1 file:px-3 file:rounded file:border file:bg-secondary file:text-secondary-foreground hover:file:bg-muted" />
                {uploading && <div className="text-[10px] text-muted-foreground">Parsing...</div>}
                {parsedOnly && <div className="text-[10px] text-green-600">Parsed. You can edit JSON or start review.</div>}
            </div>
            {/* JSON textarea removed */}
            <div className="flex flex-wrap gap-2">
                <button onClick={() => { setManuscript(null); setParsedOnly(false); }} className="px-3 py-1.5 rounded border text-sm">Clear</button>
                {parsedOnly && <button disabled={reviewRunning} onClick={onRunFull} className="px-3 py-1.5 rounded bg-secondary text-secondary-foreground text-sm disabled:opacity-50">Run Full Upload Review</button>}
            </div>
            {error && <div className="text-xs text-destructive">{error}</div>}
        </div>
    );
};
