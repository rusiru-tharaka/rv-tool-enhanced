import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { 
  FileText, 
  BarChart3, 
  Zap, 
  FileOutput,
  CheckCircle,
  Clock,
  AlertCircle,
  ArrowRight,
  ArrowLeft
} from 'lucide-react';
import { useSession } from '../contexts/SessionContext';
import { AnalysisPhase } from '../types';
import PhaseNavigation from '../components/PhaseNavigation';
import MigrationScopePhase from '../components/phases/MigrationScopePhase';
import CostEstimatesPhase from '../components/phases/CostEstimatesPhase';
import ModernizationPhase from '../components/phases/ModernizationPhase';
import ReportsPhase from '../components/phases/ReportsPhase';

const Analysis: React.FC = () => {
  const { sessionId } = useParams<{ sessionId: string }>();
  const navigate = useNavigate();
  const { state, loadSession, advancePhase } = useSession();
  const [activePhase, setActivePhase] = useState<AnalysisPhase>(AnalysisPhase.MIGRATION_SCOPE);

  // Load session if not already loaded
  useEffect(() => {
    if (sessionId && (!state.currentSession || state.currentSession.session_id !== sessionId)) {
      loadSession(sessionId);
    }
  }, [sessionId, state.currentSession]);

  // Update active phase based on current session
  useEffect(() => {
    if (state.currentSession) {
      setActivePhase(state.currentSession.current_phase);
    }
  }, [state.currentSession]);

  // Redirect to dashboard if no session
  useEffect(() => {
    if (!sessionId) {
      navigate('/dashboard');
    }
  }, [sessionId, navigate]);

  const handlePhaseChange = (phase: AnalysisPhase) => {
    // Only allow navigation to completed phases or current phase
    if (state.currentSession) {
      const completedPhases = state.currentSession.completed_phases || [];
      const isCompleted = completedPhases.includes(phase);
      const isCurrent = state.currentSession.current_phase === phase;
      
      if (isCompleted || isCurrent) {
        setActivePhase(phase);
      }
    }
  };

  const handleAdvancePhase = async () => {
    if (sessionId) {
      await advancePhase(sessionId);
    }
  };

  const canAdvancePhase = () => {
    if (!state.currentSession) return false;
    
    // In direct analysis mode, allow advancing between phases
    // since cost estimates are auto-populated and phases are accessible
    switch (state.currentSession.current_phase) {
      case AnalysisPhase.MIGRATION_SCOPE:
        return true; // Can advance to cost estimates (already populated)
      case AnalysisPhase.COST_ESTIMATES:
        return true; // Can advance to modernization
      case AnalysisPhase.MODERNIZATION:
        return true; // Can advance to reports
      case AnalysisPhase.REPORT_GENERATION:
        return false; // Final phase
      default:
        return false;
    }
  };

  const renderPhaseContent = () => {
    if (!sessionId) return null;

    switch (activePhase) {
      case AnalysisPhase.MIGRATION_SCOPE:
        return <MigrationScopePhase sessionId={sessionId} />;
      case AnalysisPhase.COST_ESTIMATES:
        return <CostEstimatesPhase sessionId={sessionId} />;
      case AnalysisPhase.MODERNIZATION:
        return <ModernizationPhase sessionId={sessionId} />;
      case AnalysisPhase.REPORT_GENERATION:
        return <ReportsPhase sessionId={sessionId} />;
      default:
        return <div>Unknown phase</div>;
    }
  };

  const getPhaseTitle = (phase: AnalysisPhase) => {
    switch (phase) {
      case AnalysisPhase.MIGRATION_SCOPE:
        return 'Migration Scope Analysis';
      case AnalysisPhase.COST_ESTIMATES:
        return 'Cost Estimates & TCO';
      case AnalysisPhase.MODERNIZATION:
        return 'Modernization Opportunities';
      case AnalysisPhase.REPORT_GENERATION:
        return 'Reports & Export';
      default:
        return 'Analysis';
    }
  };

  const getPhaseDescription = (phase: AnalysisPhase) => {
    switch (phase) {
      case AnalysisPhase.MIGRATION_SCOPE:
        return 'Identify migration blockers, classify workloads, and assess infrastructure complexity';
      case AnalysisPhase.COST_ESTIMATES:
        return 'Calculate AWS costs with real-time pricing and optimize TCO parameters';
      case AnalysisPhase.MODERNIZATION:
        return 'Discover containerization, serverless, and managed services opportunities';
      case AnalysisPhase.REPORT_GENERATION:
        return 'Generate comprehensive reports and export analysis results';
      default:
        return '';
    }
  };

  if (!state.currentSession) {
    return (
      <div className="flex items-center justify-center min-h-96">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading analysis session...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Session Header */}
      <div className="bg-white rounded-lg border border-gray-200 shadow-sm">
        <div className="px-6 py-4 border-b border-gray-200">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">
                Migration Analysis
              </h1>
              <p className="text-sm text-gray-500">
                Session: {state.currentSession.session_id.slice(0, 8)}... • 
                Created: {new Date(state.currentSession.created_at).toLocaleDateString()}
              </p>
            </div>
            <div className="flex items-center space-x-4">
              {state.loading.isLoading && (
                <div className="flex items-center space-x-2 text-sm text-primary-600">
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-primary-600"></div>
                  <span>{state.loading.message}</span>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Phase Navigation */}
        <div className="px-6 py-4">
          {state.currentSession && (
            <PhaseNavigation
              currentPhase={state.currentSession.current_phase}
              completedPhases={state.currentSession.completed_phases}
              activePhase={activePhase}
              onPhaseChange={handlePhaseChange}
            />
          )}
        </div>
      </div>

      {/* Phase Content */}
      <div className="bg-white rounded-lg border border-gray-200 shadow-sm">
        <div className="px-6 py-4 border-b border-gray-200">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-xl font-semibold text-gray-900">
                {getPhaseTitle(activePhase)}
              </h2>
              <p className="text-sm text-gray-600 mt-1">
                {getPhaseDescription(activePhase)}
              </p>
            </div>
            
            {/* Phase Actions */}
            {state.currentSession && activePhase === state.currentSession.current_phase && (
              <div className="flex items-center space-x-3">
                {canAdvancePhase() && activePhase !== AnalysisPhase.REPORT_GENERATION && (
                  <button
                    onClick={handleAdvancePhase}
                    disabled={state.loading.isLoading}
                    className="btn-primary"
                  >
                    Next Phase
                    <ArrowRight className="h-4 w-4 ml-2" />
                  </button>
                )}
              </div>
            )}
          </div>
        </div>

        <div className="p-6">
          {renderPhaseContent()}
        </div>
      </div>

      {/* Error Display */}
      {state.error.hasError && (
        <div className="bg-danger-50 border border-danger-200 rounded-lg p-4">
          <div className="flex items-start">
            <AlertCircle className="h-5 w-5 text-danger-400 mt-0.5" />
            <div className="ml-3">
              <h3 className="text-sm font-medium text-danger-800">
                Analysis Error
              </h3>
              <p className="text-sm text-danger-700 mt-1">
                {state.error.message}
              </p>
              {state.error.details && (
                <details className="mt-2">
                  <summary className="text-xs text-danger-600 cursor-pointer">
                    Show details
                  </summary>
                  <pre className="text-xs text-danger-600 mt-1 whitespace-pre-wrap">
                    {JSON.stringify(state.error.details, null, 2)}
                  </pre>
                </details>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Analysis;
