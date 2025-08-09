import React from 'react';
import { 
  FileText, 
  BarChart3, 
  Zap, 
  FileOutput,
  CheckCircle,
  Clock,
  Circle
} from 'lucide-react';
import { AnalysisPhase } from '../types';

interface PhaseNavigationProps {
  currentPhase: AnalysisPhase;
  completedPhases?: AnalysisPhase[]; // Made optional to handle undefined
  activePhase: AnalysisPhase;
  onPhaseChange: (phase: AnalysisPhase) => void;
}

const PhaseNavigation: React.FC<PhaseNavigationProps> = ({
  currentPhase,
  completedPhases,
  activePhase,
  onPhaseChange,
}) => {
  const phases = [
    {
      id: AnalysisPhase.MIGRATION_SCOPE,
      name: 'Migration Scope',
      description: 'Analyze blockers & workloads',
      icon: FileText,
    },
    {
      id: AnalysisPhase.COST_ESTIMATES,
      name: 'Cost Estimates',
      description: 'Calculate AWS TCO',
      icon: BarChart3,
    },
    {
      id: AnalysisPhase.MODERNIZATION,
      name: 'Modernization',
      description: 'Find opportunities',
      icon: Zap,
    },
    {
      id: AnalysisPhase.REPORT_GENERATION,
      name: 'Reports',
      description: 'Export & share',
      icon: FileOutput,
    },
  ];

  const getPhaseStatus = (phaseId: AnalysisPhase) => {
    // Handle undefined completedPhases
    const phases = completedPhases || [];
    if (phases.includes(phaseId)) {
      return 'completed';
    } else if (phaseId === currentPhase) {
      return 'current';
    } else {
      return 'pending';
    }
  };

  const isPhaseClickable = (phaseId: AnalysisPhase) => {
    // Handle undefined completedPhases
    const phases = completedPhases || [];
    return phases.includes(phaseId) || phaseId === currentPhase;
  };

  const getStatusIcon = (phaseId: AnalysisPhase) => {
    const status = getPhaseStatus(phaseId);
    
    if (status === 'completed') {
      return <CheckCircle className="h-5 w-5 text-success-600" />;
    } else if (status === 'current') {
      return <Clock className="h-5 w-5 text-primary-600" />;
    } else {
      return <Circle className="h-5 w-5 text-gray-300" />;
    }
  };

  return (
    <nav aria-label="Progress">
      <ol className="flex items-center">
        {phases.map((phase, phaseIdx) => {
          const Icon = phase.icon;
          const status = getPhaseStatus(phase.id);
          const isActive = activePhase === phase.id;
          const isClickable = isPhaseClickable(phase.id);
          
          return (
            <li key={phase.id} className={`relative ${phaseIdx !== phases.length - 1 ? 'pr-8 sm:pr-20' : ''}`}>
              {/* Connector Line */}
              {phaseIdx !== phases.length - 1 && (
                <div className="absolute inset-0 flex items-center" aria-hidden="true">
                  <div className={`h-0.5 w-full ${
                    (completedPhases || []).includes(phases[phaseIdx + 1].id) 
                      ? 'bg-success-600' 
                      : 'bg-gray-200'
                  }`} />
                </div>
              )}
              
              {/* Phase Button */}
              <button
                onClick={() => isClickable && onPhaseChange(phase.id)}
                disabled={!isClickable}
                className={`
                  relative flex items-center space-x-3 p-3 rounded-lg transition-all duration-200
                  ${isActive 
                    ? 'bg-primary-50 border-2 border-primary-200' 
                    : 'hover:bg-gray-50'
                  }
                  ${isClickable 
                    ? 'cursor-pointer' 
                    : 'cursor-not-allowed opacity-60'
                  }
                `}
              >
                {/* Phase Icon */}
                <div className={`
                  flex-shrink-0 w-10 h-10 flex items-center justify-center rounded-full border-2
                  ${status === 'completed' 
                    ? 'bg-success-100 border-success-600' 
                    : status === 'current'
                    ? 'bg-primary-100 border-primary-600'
                    : 'bg-gray-100 border-gray-300'
                  }
                `}>
                  <Icon className={`h-5 w-5 ${
                    status === 'completed' 
                      ? 'text-success-600' 
                      : status === 'current'
                      ? 'text-primary-600'
                      : 'text-gray-400'
                  }`} />
                </div>
                
                {/* Phase Info */}
                <div className="min-w-0 flex-1 text-left">
                  <div className="flex items-center space-x-2">
                    <span className={`text-sm font-medium ${
                      status === 'completed' 
                        ? 'text-success-900' 
                        : status === 'current'
                        ? 'text-primary-900'
                        : 'text-gray-500'
                    }`}>
                      {phase.name}
                    </span>
                    {getStatusIcon(phase.id)}
                  </div>
                  <p className={`text-xs ${
                    status === 'completed' 
                      ? 'text-success-700' 
                      : status === 'current'
                      ? 'text-primary-700'
                      : 'text-gray-400'
                  }`}>
                    {phase.description}
                  </p>
                </div>
              </button>
            </li>
          );
        })}
      </ol>
    </nav>
  );
};

export default PhaseNavigation;
