import React from 'react';
import { Outlet, Link, useLocation } from 'react-router-dom';
import { 
  BarChart3, 
  FileText, 
  Settings, 
  HelpCircle, 
  Home,
  Upload,
  Activity
} from 'lucide-react';
import { useSession } from '../contexts/SessionContext';

const Layout: React.FC = () => {
  const location = useLocation();
  const { state } = useSession();

  const navigation = [
    { name: 'Dashboard', href: '/dashboard', icon: Home, current: location.pathname === '/dashboard' },
    { 
      name: 'Analysis', 
      href: state.currentSession ? `/analysis/${state.currentSession.session_id}` : '/dashboard', 
      icon: BarChart3, 
      current: location.pathname.startsWith('/analysis'),
      disabled: !state.currentSession
    },
    { 
      name: 'Reports', 
      href: state.currentSession ? `/reports/${state.currentSession.session_id}` : '/dashboard', 
      icon: FileText, 
      current: location.pathname.startsWith('/reports'),
      disabled: !state.currentSession
    },
  ];

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            {/* Logo and Title */}
            <div className="flex items-center">
              <div className="flex-shrink-0 flex items-center">
                <Activity className="h-8 w-8 text-primary-600" />
                <div className="ml-3">
                  <h1 className="text-xl font-semibold text-gray-900">RVTool Enhanced</h1>
                  <p className="text-sm text-gray-500">Migration Analysis Platform</p>
                </div>
              </div>
            </div>

            {/* Navigation */}
            <nav className="hidden md:flex space-x-8">
              {navigation.map((item) => {
                const Icon = item.icon;
                return (
                  <Link
                    key={item.name}
                    to={item.href}
                    className={`
                      inline-flex items-center px-3 py-2 text-sm font-medium rounded-md transition-colors
                      ${item.disabled 
                        ? 'text-gray-400 cursor-not-allowed' 
                        : item.current
                        ? 'text-primary-600 bg-primary-50'
                        : 'text-gray-700 hover:text-primary-600 hover:bg-gray-50'
                      }
                    `}
                    onClick={(e) => item.disabled && e.preventDefault()}
                  >
                    <Icon className="h-4 w-4 mr-2" />
                    {item.name}
                  </Link>
                );
              })}
            </nav>

            {/* Session Status */}
            <div className="flex items-center space-x-4">
              {state.currentSession && (
                <div className="hidden sm:flex items-center space-x-2 text-sm text-gray-600">
                  <div className="w-2 h-2 bg-green-400 rounded-full"></div>
                  <span>Session Active</span>
                </div>
              )}
              
              {state.loading.isLoading && (
                <div className="flex items-center space-x-2 text-sm text-primary-600">
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-primary-600"></div>
                  <span className="hidden sm:inline">{state.loading.message || 'Loading...'}</span>
                </div>
              )}
            </div>
          </div>
        </div>
      </header>

      {/* Mobile Navigation */}
      <nav className="md:hidden bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex space-x-8 overflow-x-auto py-2">
            {navigation.map((item) => {
              const Icon = item.icon;
              return (
                <Link
                  key={item.name}
                  to={item.href}
                  className={`
                    flex items-center px-3 py-2 text-sm font-medium rounded-md whitespace-nowrap transition-colors
                    ${item.disabled 
                      ? 'text-gray-400 cursor-not-allowed' 
                      : item.current
                      ? 'text-primary-600 bg-primary-50'
                      : 'text-gray-700 hover:text-primary-600 hover:bg-gray-50'
                    }
                  `}
                  onClick={(e) => item.disabled && e.preventDefault()}
                >
                  <Icon className="h-4 w-4 mr-2" />
                  {item.name}
                </Link>
              );
            })}
          </div>
        </div>
      </nav>

      {/* Error Banner */}
      {state.error.hasError && (
        <div className="bg-danger-50 border-l-4 border-danger-400 p-4">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex items-center justify-between">
              <div className="flex">
                <div className="ml-3">
                  <p className="text-sm text-danger-700">
                    <strong>Error:</strong> {state.error.message}
                  </p>
                </div>
              </div>
              <button
                onClick={() => {/* Clear error logic will be added */}}
                className="text-danger-400 hover:text-danger-600"
              >
                <span className="sr-only">Dismiss</span>
                <svg className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                </svg>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <Outlet />
      </main>

      {/* Footer */}
      <footer className="bg-white border-t border-gray-200 mt-auto">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex justify-between items-center text-sm text-gray-500">
            <div>
              <p>&copy; 2025 RVTool Enhanced Migration Analysis Platform</p>
            </div>
            <div className="flex space-x-6">
              <a href="#" className="hover:text-gray-700">Documentation</a>
              <a href="#" className="hover:text-gray-700">Support</a>
              <a href="#" className="hover:text-gray-700">API Status</a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default Layout;
