import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import api from '../api';

export default function MyDocuments() {
  const [docs, setDocs] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [mimeType, setMimeType] = useState('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const size = 8;

  const fetchDocuments = async () => {
    setLoading(true);
    setError('');
    try {
      const params = { page, size };
      if (search) params.search = search;
      if (mimeType) params.mime_type = mimeType;
      if (startDate) params.start_date = new Date(startDate).toISOString();
      if (endDate) params.end_date = new Date(endDate).toISOString();

      const res = await api.get('/documents', { params });
      setDocs(res.data.items);
      setTotal(res.data.total);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load documents');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDocuments();
  }, [page, mimeType, startDate, endDate]);

  const handleSearch = (e) => {
    e.preventDefault();
    setPage(1);
    fetchDocuments();
  };

  const handleDownload = async (doc) => {
    try {
      const res = await api.get(`/documents/${doc.id}/download`, { responseType: 'blob' });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', doc.original_filename);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (err) {
      alert('Download denied or failed. Check permissions.');
    }
  };

  return (
    <div className="card">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
        <h2>My Accessible Documents</h2>
        <Link to="/upload"><button>+ Upload Encrypted File</button></Link>
      </div>

      <form onSubmit={handleSearch} className="filters-row">
        <input
          type="text"
          placeholder="Search filename..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <select value={mimeType} onChange={(e) => { setMimeType(e.target.value); setPage(1); }}>
          <option value="">All File Types</option>
          <option value="application/pdf">PDF</option>
          <option value="application/vnd.openxmlformats-officedocument.wordprocessingml.document">DOCX</option>
          <option value="image/png">PNG</option>
          <option value="image/jpeg">JPG</option>
        </select>
        <input type="date" value={startDate} onChange={(e) => { setStartDate(e.target.value); setPage(1); }} />
        <input type="date" value={endDate} onChange={(e) => { setEndDate(e.target.value); setPage(1); }} />
        <button type="submit">Apply Search</button>
      </form>

      {error && <div className="alert error">{error}</div>}

      {loading ? (
        <p>Loading documents...</p>
      ) : docs.length === 0 ? (
        <p style={{ padding: '2rem 0', textAlign: 'center', color: '#64748b' }}>
          No documents found. Upload a file to encrypt and store it in your vault.
        </p>
      ) : (
        <>
          <table>
            <thead>
              <tr>
                <th>Filename</th>
                <th>Owner</th>
                <th>Size</th>
                <th>Access Role</th>
                <th>Encryption</th>
                <th>Uploaded At</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {docs.map((doc) => (
                <tr key={doc.id}>
                  <td><strong>{doc.original_filename}</strong></td>
                  <td>{doc.owner_email}</td>
                  <td>{(doc.file_size / 1024).toFixed(1)} KB</td>
                  <td><span className={`badge ${doc.access_role}`}>{doc.access_role}</span></td>
                  <td><code>{doc.encryption_version}</code></td>
                  <td>{new Date(doc.created_at).toLocaleString()}</td>
                  <td style={{ display: 'flex', gap: '0.5rem' }}>
                    <Link to={`/documents/${doc.id}`}><button className="secondary">Details / Share</button></Link>
                    {(doc.access_role === 'OWNER' || doc.access_role === 'DOWNLOAD') && (
                      <button onClick={() => handleDownload(doc)}>Download</button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          <div className="pagination">
            <span>Total Documents: {total}</span>
            <div>
              <button disabled={page <= 1} onClick={() => setPage(page - 1)} style={{ marginRight: '0.5rem' }}>
                Previous
              </button>
              <span>Page {page}</span>
              <button disabled={page * size >= total} onClick={() => setPage(page + 1)} style={{ marginLeft: '0.5rem' }}>
                Next
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
