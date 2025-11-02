import { type ChangeEvent, useState } from "react";
import axios from "axios";

type UploadBarProps = {
  onUpload: (id: string) => void;
};

export default function UploadBar({ onUpload }: UploadBarProps) {
  const [isUploading, setIsUploading] = useState(false);

  // const handleUpload = async (event: ChangeEvent<HTMLInputElement>) => {
  //   const file = event.target.files?.[0];
  //   if (!file || isUploading) return;

  //   setIsUploading(true);
  //   const formData = new FormData();
  //   formData.append("csv", file);

  //   try {
  //     const { data } = await axios.post<{ session_id: string }>(
  //       "http://localhost:8000/upload",
  //       formData
  //     );
  //     onUpload(data.session_id);
  //   } catch (error) {
  //     console.error("Upload failed", error);
  //   } finally {
  //     event.target.value = "";
  //     setIsUploading(false);
  //   }
  // };

  const handleUpload = () => {
    onUpload("test-session-id-1234");
  };

  return (
    <div className="flex shrink-0 items-center justify-between border-b border-slate-200 bg-white px-8 py-4">
      <label className="relative inline-flex cursor-pointer items-center gap-2 text-sm font-semibold text-blue-600">
        <input
          type="file"
          accept=".csv"
          onChange={handleUpload}
          disabled={isUploading}
          className="absolute inset-0 h-full w-full cursor-pointer opacity-0 disabled:cursor-not-allowed"
        />
        <span>{isUploading ? "Uploading…" : "Upload CSV"}</span>
      </label>
      <button
        type="button"
        className="rounded-md px-3 py-1 text-sm text-slate-500 transition hover:text-slate-800"
      >
        Export Notebook
      </button>
    </div>
  );
}
