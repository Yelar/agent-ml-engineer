'use client';

import { type ChangeEvent } from 'react';

type UploadProgress = {
  processed: number;
  total: number;
};

type UploadBarProps = {
  onFilesSelected: (files: FileList) => void;
  isUploading: boolean;
  progress: UploadProgress | null;
};

export default function UploadBar({ onFilesSelected, isUploading, progress }: UploadBarProps) {
  const handleChange = (event: ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files;
    if (!files || files.length === 0) return;
    onFilesSelected(files);
    event.target.value = '';
  };

  return (
    <div className="flex shrink-0 items-center justify-between border-b border-border bg-background px-8 py-4">
      <label className="relative inline-flex cursor-pointer items-center gap-2 text-sm font-semibold text-primary">
        <input
          type="file"
          accept=".csv"
          multiple
          onChange={handleChange}
          disabled={isUploading}
          className="absolute inset-0 h-full w-full cursor-pointer opacity-0 disabled:cursor-not-allowed"
        />
        <span>
          {isUploading && progress ? `Uploading ${progress.processed}/${progress.total}` : 'Upload CSVs'}
        </span>
      </label>
      <button
        type="button"
        className="rounded-md px-3 py-1 text-sm text-muted-foreground transition hover:text-foreground disabled:cursor-not-allowed disabled:opacity-60"
        disabled
      >
        Export Notebook
      </button>
    </div>
  );
}
