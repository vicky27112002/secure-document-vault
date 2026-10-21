import React, { useState, useEffect } from 'react';
import api from '../api';

export default function AuditLogs() {
  const [logs, setLogs] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [action, setAction] = useState('');
  const [documentId, setDocumentId] = useState('');
  const [userId, setUserId] = useState('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [loading, setLoading] = useState(false);
  const size = 12;

  const fetchLogs = async () => {
    setLoading(true);
    try {
      const params = { page, size };
      if (action) params.action = action;
      if (documentId) params.document_id = documentId;
      if (userId) params.user_id = userId;
      if (startDate) params.start_date = new Date(startDate).toISOString();
      if (endDate) params.end_date = new Date(endDate).toISOString();

      const res = await api.get('/audit-logs', { params });
      setLogs(res.data.items);
      setTotal(res.data.total);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLogs();
  }, [page, action, startDate, endDate]);

  const handleFilterSubmit = (e) => {
    e.preventDefault();
    setPage(1);
    fetchLogs();
  };

  return (
    <div className="card">
      <h2>Security Audit Logs</h2>
      <form onSubmit={handleFilterSubmit} className="filters-row">
        <select value={action} onChange={(e) => { setAction(e.target.value); setPage(1); }}>
          <option value="">All Actions</option>
          <option value="LOGIN">LOGIN</option>
          <option value="UPLOAD">UPLOAD</option>
          <option value="DOWNLOAD">DOWNLOAD</option>
          <option value="SHARE">SHARE</option>
          <option value="REVOKE">REVOKE</option>
          <option value="DELETE">DELETE</option>
        </select>
        <input
          type="number"
          placeholder="Document ID"
          value={documentId}
          onChange={(e) => setDocumentId(e.target.value)}
        />
        <input
          type="number"
          placeholder="User ID"
          value={userId}
          onChange={(e) => setUserId(e.target.value)}
        />
        <input type="date" value={startDate} onChange={(e) => { setStartDate(e.target.value); setPage(1); }} />
        <input type="date" value={endDate} onChange={(e) => { setEndDate(e.target.value); setPage(1); }} />
        <button type="submit">Filter Logs</button>
      </form>

      {loading ? (
        <p>Loading audit records...</p>
      ) : logs.length === 0 ? (
        <p style={{ padding: '2rem 0', textAlign: 'center', color: '#64748b' }}>No matching audit logs found.</p>
      ) : (
        <>
          <table>
            <thead>
              <tr>
                <th>Timestamp</th>
                <th>Action</th>
                <th>Actor</th>
                <th>Doc ID</th>
                <th>Details</th>
              </tr>
            </thead>
            <tbody>
              {logs.map((log) => (
                <tr key={log.id}>
                  <td>{new Date(log.created_at).toLocaleString()}</td>
                  <td><span className="badge">{log.action}</span></td>
                  <td>{log.user_email || `User #${log.user_id}`}</td>
                  <td>{log.document_id ? `#${log.document_id}` : '-'}</td>
                  <td>{log.details}</td>
                </tr>
              ))}
            </tbody>
          </table>

          <div className="pagination">
            <span>Total Events: {total}</span>
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
