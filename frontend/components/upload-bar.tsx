"use client";

import { type ChangeEvent } from "react";
import { Button } from "@/components/ui/button";

interface UploadProgress {
  processed: number;
  total: number;
}

interface UploadBarProps {
  onFilesSelected: (files: FileList) => void;
  isUploading: boolean;
  progress: UploadProgress | null;
}

export function UploadBar({
  onFilesSelected,
  isUploading,
  progress,
}: UploadBarProps) {
  const handleChange = (event: ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files;
    if (!files || files.length === 0) return;
    onFilesSelected(files);
    event.target.value = "";
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
          {isUploading && progress
            ? `Uploading ${progress.processed}/${progress.total}`
            : "Upload CSVs"}
        </span>
      </label>
      <Button
        type="button"
        variant="ghost"
        size="sm"
        disabled
      >
        Export Notebook
      </Button>
    </div>
  );
}

