import { type ChangeEvent, useState } from "react";
import axios from "axios";

type UploadBarProps = {
  onUpload: (id: string) => void;
};

export default function UploadBar({ onUpload }: UploadBarProps): JSX.Element {
  const [isUploading, setIsUploading] = useState(false);

  const handleUpload = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file || isUploading) return;

    setIsUploading(true);
    const formData = new FormData();
    formData.append("csv", file);

    try {
      const { data } = await axios.post<{ session_id: string }>(
        "http://localhost:8000/upload",
        formData
      );
      onUpload(data.session_id);
    } catch (error) {
      console.error("Upload failed", error);
    } finally {
      event.target.value = "";
      setIsUploading(false);
    }
  };

  return (
    <div className="upload-bar">
      <label className="upload-bar__trigger">
        <input
          type="file"
          accept=".csv"
          onChange={handleUpload}
          disabled={isUploading}
        />
        <span>{isUploading ? "Uploading…" : "Upload CSV"}</span>
      </label>
      <button type="button" className="upload-bar__action">
        Export Notebook
      </button>
    </div>
  );
}
