import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import { Login } from './components/Auth/Login';
import { PrivateRoute } from './components/Auth/PrivateRoute';
import { Dashboard } from './pages/Dashboard';
import { Config } from './pages/Config';
import './aws-config';

function App() {
  return (
    <AuthProvider>
      <Router>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route
            path="/dashboard"
            element={
              <PrivateRoute>
                <Dashboard />
              </PrivateRoute>
            }
          />
          <Route
            path="/config"
            element={
              <PrivateRoute>
                <Config />
              </PrivateRoute>
            }
          />
          <Route path="/" element={<Navigate to="/config" replace />} />
        </Routes>
      </Router>
    </AuthProvider>
  );
}

export default App;