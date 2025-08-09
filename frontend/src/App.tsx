import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { SessionProvider } from './contexts/SessionContext';
import ErrorBoundary from './components/ErrorBoundary';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import Analysis from './pages/Analysis';
import Reports from './pages/Reports';
import FileCleaningUtility from './pages/FileCleaningUtility';
import NotFound from './pages/NotFound';

function App() {
  return (
    <ErrorBoundary>
      <SessionProvider>
        <div className="min-h-screen bg-gray-50">
          <Routes>
            <Route path="/" element={<Layout />}>
              <Route index element={<Navigate to="/dashboard" replace />} />
              <Route path="dashboard" element={
                <ErrorBoundary>
                  <Dashboard />
                </ErrorBoundary>
              } />
              <Route path="analysis/:sessionId" element={
                <ErrorBoundary>
                  <Analysis />
                </ErrorBoundary>
              } />
              <Route path="reports/:sessionId" element={
                <ErrorBoundary>
                  <Reports />
                </ErrorBoundary>
              } />
              <Route path="file-cleaning" element={
                <ErrorBoundary>
                  <FileCleaningUtility />
                </ErrorBoundary>
              } />
              <Route path="*" element={<NotFound />} />
            </Route>
          </Routes>
        </div>
      </SessionProvider>
    </ErrorBoundary>
  );
}

export default App;
