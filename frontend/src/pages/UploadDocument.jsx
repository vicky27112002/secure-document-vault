import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api';

const ALLOWED_EXTENSIONS = ['pdf', 'docx', 'png', 'jpg', 'jpeg'];
const MAX_SIZE_BYTES = 10 * 1024 * 1024;

export default function UploadDocument() {
  const [file, setFile] = useState(null);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState('');
  const [uploading, setUploading] = useState(false);
  const navigate = useNavigate();

  const handleFileChange = (e) => {
    setError('');
    const selected = e.target.files[0];
    if (!selected) return;

    const ext = selected.name.split('.').pop().toLowerCase();
    if (!ALLOWED_EXTENSIONS.includes(ext)) {
      setError('Invalid file type. Allowed: PDF, DOCX, PNG, JPG.');
      setFile(null);
      return;
    }
    if (selected.size > MAX_SIZE_BYTES) {
      setError('File exceeds the 10 MB maximum size limit.');
      setFile(null);
      return;
    }
    setFile(selected);
  };

  const handleUpload = async (e) => {
    e.preventDefault();
    if (!file) return;
    setUploading(true);
    setError('');
    setProgress(0);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await api.post('/documents', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        onUploadProgress: (evt) => {
          if (evt.total) {
            setProgress(Math.round((evt.loaded * 100) / evt.total));
          }
        },
      });
      navigate(`/documents/${res.data.id}`);
    } catch (err) {
      setError(err.response?.data?.detail || 'Upload failed');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="card" style={{ maxWidth: '580px', margin: '2rem auto' }}>
      <h2>Upload & Encrypt Document</h2>
      <p style={{ marginBottom: '1rem', fontSize: '0.9rem', color: '#475569' }}>
        Files are validated and encrypted in-memory with <strong>AES-256-GCM</strong> before persistent storage.
        Supported types: PDF, DOCX, PNG, JPG (Max 10 MB).
      </p>

      {error && <div className="alert error">{error}</div>}

      <form onSubmit={handleUpload}>
        <div className="form-group">
          <label>Select Document</label>
          <input type="file" accept=".pdf,.docx,.png,.jpg,.jpeg" onChange={handleFileChange} required />
        </div>

        {uploading && (
          <div>
            <div className="progress-bar">
              <div className="progress-fill" style={{ width: `${progress}%` }} />
            </div>
            <p style={{ fontSize: '0.85rem' }}>Uploading & Encrypting: {progress}%</p>
          </div>
        )}

        <button type="submit" disabled={!file || uploading}>
          {uploading ? 'Encrypting & Saving...' : 'Upload to Vault'}
        </button>
      </form>
    </div>
  );
}
