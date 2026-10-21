import React, { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate, Link } from 'react-router-dom';
import api from './api';
import Login from './pages/Login';
import Register from './pages/Register';
import MyDocuments from './pages/MyDocuments';
import UploadDocument from './pages/UploadDocument';
import DocumentDetails from './pages/DocumentDetails';
import AuditLogs from './pages/AuditLogs';

export default function App() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetchUser = async () => {
    const token = localStorage.getItem('access_token');
    if (!token) {
      setUser(null);
      setLoading(false);
      return;
    }
    try {
      const res = await api.get('/auth/me');
      setUser(res.data);
    } catch (err) {
      // Only clear tokens on definitive auth failure (401)
      // The axios interceptor already attempts token refresh on 401
      if (err.response?.status === 401) {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
      }
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUser();
  }, []);

  const handleLogout = () => {
    localStorage.clear();
    setUser(null);
  };

  if (loading) {
    return <div className="container"><p>Loading Secure Vault...</p></div>;
  }

  return (
    <BrowserRouter>
      {user && (
        <nav className="navbar">
          <div>
            <strong style={{ marginRight: '2rem', color: '#38bdf8' }}>Secure Document Vault</strong>
            <Link to="/documents">My Documents</Link>
            <Link to="/upload">Upload Document</Link>
            <Link to="/audit-logs">Audit Logs</Link>
          </div>
          <div>
            <span style={{ marginRight: '1rem', fontSize: '0.9rem' }}>{user.email}</span>
            <button className="secondary" onClick={handleLogout}>Logout</button>
          </div>
        </nav>
      )}

      <div className="container">
        <Routes>
          <Route path="/login" element={!user ? <Login onAuth={fetchUser} /> : <Navigate to="/documents" />} />
          <Route path="/register" element={!user ? <Register /> : <Navigate to="/documents" />} />
          <Route path="/documents" element={user ? <MyDocuments /> : <Navigate to="/login" />} />
          <Route path="/upload" element={user ? <UploadDocument /> : <Navigate to="/login" />} />
          <Route path="/documents/:id" element={user ? <DocumentDetails /> : <Navigate to="/login" />} />
          <Route path="/audit-logs" element={user ? <AuditLogs /> : <Navigate to="/login" />} />
          <Route path="*" element={<Navigate to={user ? "/documents" : "/login"} />} />
        </Routes>
      </div>
    </BrowserRouter>
  );
}
