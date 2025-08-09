import React from 'react';
import { Zap, Database, Container, Cloud, TrendingUp } from 'lucide-react';
import { useSession } from '../../contexts/SessionContext';
import { 
  AIBadge, 
  ConfidenceScore, 
  AIEnhancedSection, 
  AIProcessingIndicator,
  AIInsightCard,
  AIMetricsDisplay 
} from '../AIIndicators';

interface ModernizationPhaseProps {
  sessionId: string;
}

const ModernizationPhase: React.FC<ModernizationPhaseProps> = ({ sessionId }) => {
  const { state, analyzeModernization } = useSession();

  const handleAnalyze = async () => {
    await analyzeModernization(sessionId);
  };

  if (!state.modernizationAnalysis) {
    return (
      <div className="space-y-6">
        {state.loading.isLoading && (
          <AIProcessingIndicator 
            isProcessing={true}
            message="AI is analyzing your infrastructure for modernization opportunities..."
            progress={undefined}
          />
        )}
        
        <div className="text-center py-12">
          <Zap className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">
            AI-Powered Modernization Analysis
          </h3>
          <p className="text-gray-600 mb-4">
            Discover containerization, serverless, and managed services opportunities with intelligent ROI analysis
          </p>
          <div className="flex items-center justify-center mb-6">
            <AIBadge variant="primary" size="md" />
          </div>
          <button
            onClick={handleAnalyze}
            disabled={state.loading.isLoading}
            className="btn-primary"
          >
            {state.loading.isLoading ? 'AI Analyzing...' : 'Start AI Modernization Analysis'}
          </button>
        </div>
      </div>
    );
  }

  const getModernizationIcon = (type: string) => {
    switch (type?.toLowerCase()) {
      case 'managed_database':
      case 'database':
        return <Database className="h-5 w-5 text-blue-600" />;
      case 'containerization':
        return <Container className="h-5 w-5 text-green-600" />;
      case 'serverless':
        return <Cloud className="h-5 w-5 text-purple-600" />;
      default:
        return <Zap className="h-5 w-5 text-orange-600" />;
    }
  };

  return (
    <div className="space-y-6">
      {/* Cost Impact Summary */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="card">
          <div className="card-content">
            <div className="flex items-center">
              <TrendingUp className="h-8 w-8 text-success-600" />
              <div className="ml-4">
                <p className="text-2xl font-semibold text-gray-900">
                  ${state.modernizationAnalysis.summary?.total_monthly_savings?.toLocaleString(undefined, {maximumFractionDigits: 0}) || '0'}
                </p>
                <p className="text-sm text-gray-600">Monthly Savings</p>
              </div>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="card-content">
            <div className="flex items-center">
              <TrendingUp className="h-8 w-8 text-primary-600" />
              <div className="ml-4">
                <p className="text-2xl font-semibold text-gray-900">
                  {state.modernizationAnalysis.summary?.average_savings_percentage?.toFixed(1) || '0'}%
                </p>
                <p className="text-sm text-gray-600">Cost Reduction</p>
              </div>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="card-content">
            <div className="flex items-center">
              <Zap className="h-8 w-8 text-orange-600" />
              <div className="ml-4">
                <p className="text-2xl font-semibold text-gray-900">
                  {state.modernizationAnalysis.total_opportunities || state.modernizationAnalysis.modernization_opportunities?.length || 0}
                </p>
                <p className="text-sm text-gray-600">Opportunities</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* AI-Enhanced Modernization Opportunities */}
      <AIEnhancedSection 
        title="Modernization Opportunities" 
        variant="recommendation"
        confidence={state.modernizationAnalysis?.ai_metadata?.confidence || 0.8}
        className="mb-6"
      >
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center space-x-4">
            <AIBadge variant="success" size="sm" />
            <span className="text-sm text-gray-600">
              AI-powered modernization recommendations with ROI analysis
            </span>
          </div>
          <ConfidenceScore 
            score={state.modernizationAnalysis?.ai_metadata?.confidence || 0.8} 
            size="sm" 
          />
        </div>
        
        <div className="space-y-4">
          {state.modernizationAnalysis.modernization_opportunities?.slice(0, 5).map((opportunity, index) => (
            <div key={opportunity.id || index} className="bg-gradient-to-r from-green-50 to-blue-50 border border-green-200 rounded-lg p-4">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center space-x-3">
                  {getModernizationIcon(opportunity.modernization_type)}
                  <div>
                    <h4 className="text-lg font-medium text-gray-900">{opportunity.vm_name}</h4>
                    <p className="text-sm text-gray-600">{opportunity.current_workload_type} → {opportunity.target_aws_service}</p>
                  </div>
                </div>
                <div className="flex items-center space-x-2">
                  <AIBadge variant="info" size="sm" showIcon={false} />
                  <ConfidenceScore 
                    score={opportunity.ai_confidence || 0.8} 
                    size="sm" 
                    showLabel={false}
                  />
                </div>
              </div>
              
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm mb-3">
                <div>
                  <p className="text-gray-600">Estimated Cost</p>
                  <p className="font-medium">${opportunity.modernized_monthly_cost?.toFixed(2) || '0'}/month</p>
                </div>
                <div>
                  <p className="text-gray-600">Monthly Savings</p>
                  <p className="font-medium text-green-600">${opportunity.monthly_savings?.toFixed(2) || '0'}</p>
                </div>
                <div>
                  <p className="text-gray-600">ROI Timeline</p>
                  <p className="font-medium">{opportunity.roi_months || 12} months</p>
                </div>
                <div>
                  <p className="text-gray-600">Complexity</p>
                  <p className="font-medium">{opportunity.implementation_complexity || 'Medium'}</p>
                </div>
              </div>
              
              {opportunity.business_justification && (
                <div className="bg-white rounded-md p-3 border-l-4 border-blue-500">
                  <p className="text-sm text-gray-700">
                    <strong>AI Business Justification:</strong> {opportunity.business_justification}
                  </p>
                </div>
              )}
            </div>
          ))}
        </div>
      </AIEnhancedSection>

      {/* Implementation Roadmap */}
      <div className="card">
        <div className="card-header">
          <h3 className="text-lg font-medium text-gray-900">Implementation Roadmap</h3>
        </div>
        <div className="card-content">
          <div className="space-y-4">
            <div className="flex items-center space-x-3">
              <div className="w-8 h-8 bg-green-100 rounded-full flex items-center justify-center">
                <span className="text-sm font-medium text-green-600">1</span>
              </div>
              <div>
                <h4 className="font-medium text-gray-900">Low Complexity Opportunities</h4>
                <p className="text-sm text-gray-600">Start with serverless and managed services migrations</p>
              </div>
            </div>
            <div className="flex items-center space-x-3">
              <div className="w-8 h-8 bg-yellow-100 rounded-full flex items-center justify-center">
                <span className="text-sm font-medium text-yellow-600">2</span>
              </div>
              <div>
                <h4 className="font-medium text-gray-900">Medium Complexity Opportunities</h4>
                <p className="text-sm text-gray-600">Containerize applications and implement CI/CD</p>
              </div>
            </div>
            <div className="flex items-center space-x-3">
              <div className="w-8 h-8 bg-red-100 rounded-full flex items-center justify-center">
                <span className="text-sm font-medium text-red-600">3</span>
              </div>
              <div>
                <h4 className="font-medium text-gray-900">High Complexity Opportunities</h4>
                <p className="text-sm text-gray-600">Database migrations and legacy system modernization</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ModernizationPhase;
