import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import api from '../api';

export default function DocumentDetails() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [doc, setDoc] = useState(null);
  const [shareEmail, setShareEmail] = useState('');
  const [permission, setPermission] = useState('DOWNLOAD');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  const loadDocument = async () => {
    setLoading(true);
    try {
      const res = await api.get(`/documents/${id}`);
      setDoc(res.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Unable to load document metadata');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDocument();
  }, [id]);

  const handleDownload = async () => {
    setError('');
    try {
      const res = await api.get(`/documents/${id}/download`, { responseType: 'blob' });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', doc.original_filename);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (err) {
      setError('Authorized decryption/download failed or permission denied.');
    }
  };

  const handleShare = async (e) => {
    e.preventDefault();
    setError('');
    setMessage('');
    try {
      await api.post(`/documents/${id}/share`, {
        user_email: shareEmail,
        permission,
      });
      setShareEmail('');
      setMessage(`Access granted to ${shareEmail}`);
      loadDocument();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to share document');
    }
  };

  const handleRevoke = async (targetUserId) => {
    setError('');
    setMessage('');
    try {
      await api.delete(`/documents/${id}/share/${targetUserId}`);
      setMessage('User access revoked');
      loadDocument();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to revoke access');
    }
  };

  const handleDelete = async () => {
    if (!window.confirm('Permanently delete this encrypted document?')) return;
    try {
      await api.delete(`/documents/${id}`);
      navigate('/documents');
    } catch (err) {
      setError(err.response?.data?.detail || 'Delete failed');
    }
  };

  if (loading) return <div className="card"><p>Loading metadata...</p></div>;
  if (!doc) return <div className="card"><div className="alert error">{error || 'Not found'}</div></div>;

  return (
    <div>
      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h2>{doc.original_filename}</h2>
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            {(doc.access_role === 'OWNER' || doc.access_role === 'DOWNLOAD') && (
              <button onClick={handleDownload}>Decrypt & Download</button>
            )}
            {doc.access_role === 'OWNER' && (
              <button className="danger" onClick={handleDelete}>Delete Document</button>
            )}
          </div>
        </div>

        {error && <div className="alert error" style={{ marginTop: '1rem' }}>{error}</div>}
        {message && <div className="alert success" style={{ marginTop: '1rem' }}>{message}</div>}

        <table style={{ marginTop: '1rem' }}>
          <tbody>
            <tr><th>Document ID</th><td>#{doc.id}</td></tr>
            <tr><th>Owner Email</th><td>{doc.owner_email}</td></tr>
            <tr><th>Your Permission</th><td><span className={`badge ${doc.access_role}`}>{doc.access_role}</span></td></tr>
            <tr><th>MIME Type</th><td>{doc.mime_type}</td></tr>
            <tr><th>File Size</th><td>{(doc.file_size / 1024).toFixed(2)} KB ({doc.file_size} bytes)</td></tr>
            <tr><th>Encryption Standard</th><td><code>{doc.encryption_version}</code></td></tr>
            <tr><th>Uploaded Date</th><td>{new Date(doc.created_at).toLocaleString()}</td></tr>
          </tbody>
        </table>
      </div>

      {doc.access_role === 'OWNER' && (
        <div className="card">
          <h3>Share Document Access</h3>
          <form onSubmit={handleShare} className="filters-row" style={{ alignItems: 'end' }}>
            <div>
              <label style={{ fontSize: '0.85rem', fontWeight: 600 }}>Recipient Email</label>
              <input
                type="email"
                required
                placeholder="colleague@example.com"
                value={shareEmail}
                onChange={(e) => setShareEmail(e.target.value)}
              />
            </div>
            <div>
              <label style={{ fontSize: '0.85rem', fontWeight: 600 }}>Permission Level</label>
              <select value={permission} onChange={(e) => setPermission(e.target.value)}>
                <option value="DOWNLOAD">DOWNLOAD (View Metadata & Decrypt File)</option>
                <option value="VIEW">VIEW ONLY (Metadata Only, No Download)</option>
              </select>
            </div>
            <button type="submit">Grant / Update Access</button>
          </form>

          <h3 style={{ marginTop: '1.5rem' }}>Shared Users</h3>
          {doc.shares.length === 0 ? (
            <p style={{ color: '#64748b', fontSize: '0.9rem' }}>This document has not been shared with anyone.</p>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>User Email</th>
                  <th>Permission</th>
                  <th>Shared On</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {doc.shares.map((s) => (
                  <tr key={s.id}>
                    <td>{s.shared_with_email}</td>
                    <td><span className={`badge ${s.permission}`}>{s.permission}</span></td>
                    <td>{new Date(s.created_at).toLocaleString()}</td>
                    <td>
                      <button className="danger" onClick={() => handleRevoke(s.shared_with_user_id)}>
                        Revoke Access
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </div>
  );
}
