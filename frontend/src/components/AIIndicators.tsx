import React from 'react';
import { Brain, Zap, TrendingUp, Shield, CheckCircle, AlertTriangle } from 'lucide-react';

interface AIBadgeProps {
  variant?: 'primary' | 'success' | 'warning' | 'info';
  size?: 'sm' | 'md' | 'lg';
  showIcon?: boolean;
  className?: string;
}

export const AIBadge: React.FC<AIBadgeProps> = ({ 
  variant = 'primary', 
  size = 'md', 
  showIcon = true,
  className = '' 
}) => {
  const baseClasses = 'inline-flex items-center font-medium rounded-full';
  
  const variantClasses = {
    primary: 'bg-blue-100 text-blue-800 border border-blue-200',
    success: 'bg-green-100 text-green-800 border border-green-200',
    warning: 'bg-yellow-100 text-yellow-800 border border-yellow-200',
    info: 'bg-purple-100 text-purple-800 border border-purple-200'
  };
  
  const sizeClasses = {
    sm: 'px-2 py-1 text-xs',
    md: 'px-3 py-1 text-sm',
    lg: 'px-4 py-2 text-base'
  };
  
  const iconSizes = {
    sm: 'h-3 w-3',
    md: 'h-4 w-4',
    lg: 'h-5 w-5'
  };
  
  return (
    <span className={`${baseClasses} ${variantClasses[variant]} ${sizeClasses[size]} ${className}`}>
      {showIcon && <Brain className={`${iconSizes[size]} mr-1`} />}
      AI-Powered
    </span>
  );
};

interface ConfidenceScoreProps {
  score: number;
  showLabel?: boolean;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

export const ConfidenceScore: React.FC<ConfidenceScoreProps> = ({ 
  score, 
  showLabel = true, 
  size = 'md',
  className = '' 
}) => {
  const percentage = Math.round(score * 100);
  
  const getConfidenceColor = (score: number) => {
    if (score >= 0.8) return 'text-green-600 bg-green-100';
    if (score >= 0.6) return 'text-yellow-600 bg-yellow-100';
    return 'text-red-600 bg-red-100';
  };
  
  const getConfidenceIcon = (score: number) => {
    if (score >= 0.8) return <CheckCircle className="h-4 w-4" />;
    if (score >= 0.6) return <AlertTriangle className="h-4 w-4" />;
    return <AlertTriangle className="h-4 w-4" />;
  };
  
  const sizeClasses = {
    sm: 'text-xs px-2 py-1',
    md: 'text-sm px-3 py-1',
    lg: 'text-base px-4 py-2'
  };
  
  return (
    <div className={`inline-flex items-center rounded-full ${getConfidenceColor(score)} ${sizeClasses[size]} ${className}`}>
      {getConfidenceIcon(score)}
      {showLabel && (
        <span className="ml-1 font-medium">
          {percentage}% Confidence
        </span>
      )}
    </div>
  );
};

interface AIEnhancedSectionProps {
  title: string;
  confidence?: number;
  children: React.ReactNode;
  variant?: 'analysis' | 'recommendation' | 'insight';
  className?: string;
}

export const AIEnhancedSection: React.FC<AIEnhancedSectionProps> = ({
  title,
  confidence,
  children,
  variant = 'analysis',
  className = ''
}) => {
  const getVariantIcon = () => {
    switch (variant) {
      case 'analysis': return <Brain className="h-5 w-5 text-blue-600" />;
      case 'recommendation': return <TrendingUp className="h-5 w-5 text-green-600" />;
      case 'insight': return <Zap className="h-5 w-5 text-purple-600" />;
      default: return <Brain className="h-5 w-5 text-blue-600" />;
    }
  };
  
  const getVariantBorder = () => {
    switch (variant) {
      case 'analysis': return 'border-l-blue-500';
      case 'recommendation': return 'border-l-green-500';
      case 'insight': return 'border-l-purple-500';
      default: return 'border-l-blue-500';
    }
  };
  
  return (
    <div className={`bg-white rounded-lg border-l-4 ${getVariantBorder()} shadow-sm ${className}`}>
      <div className="p-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center">
            {getVariantIcon()}
            <h3 className="ml-2 text-lg font-semibold text-gray-900">{title}</h3>
            <AIBadge variant="info" size="sm" className="ml-3" />
          </div>
          {confidence && (
            <ConfidenceScore score={confidence} size="sm" />
          )}
        </div>
        {children}
      </div>
    </div>
  );
};

interface AIProcessingIndicatorProps {
  isProcessing: boolean;
  message?: string;
  progress?: number;
  className?: string;
}

export const AIProcessingIndicator: React.FC<AIProcessingIndicatorProps> = ({
  isProcessing,
  message = "AI is analyzing your data...",
  progress,
  className = ''
}) => {
  if (!isProcessing) return null;
  
  return (
    <div className={`bg-blue-50 border border-blue-200 rounded-lg p-4 ${className}`}>
      <div className="flex items-center">
        <div className="flex-shrink-0">
          <Brain className="h-6 w-6 text-blue-600 animate-pulse" />
        </div>
        <div className="ml-3 flex-1">
          <div className="flex items-center justify-between">
            <p className="text-sm font-medium text-blue-900">{message}</p>
            {progress !== undefined && (
              <span className="text-sm text-blue-700">{Math.round(progress)}%</span>
            )}
          </div>
          {progress !== undefined && (
            <div className="mt-2 w-full bg-blue-200 rounded-full h-2">
              <div 
                className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                style={{ width: `${progress}%` }}
              />
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

interface AIInsightCardProps {
  title: string;
  insight: string;
  confidence: number;
  actionable?: boolean;
  priority?: 'high' | 'medium' | 'low';
  className?: string;
}

export const AIInsightCard: React.FC<AIInsightCardProps> = ({
  title,
  insight,
  confidence,
  actionable = false,
  priority = 'medium',
  className = ''
}) => {
  const getPriorityColor = () => {
    switch (priority) {
      case 'high': return 'border-red-200 bg-red-50';
      case 'medium': return 'border-yellow-200 bg-yellow-50';
      case 'low': return 'border-green-200 bg-green-50';
      default: return 'border-gray-200 bg-gray-50';
    }
  };
  
  const getPriorityIcon = () => {
    switch (priority) {
      case 'high': return <AlertTriangle className="h-4 w-4 text-red-600" />;
      case 'medium': return <AlertTriangle className="h-4 w-4 text-yellow-600" />;
      case 'low': return <CheckCircle className="h-4 w-4 text-green-600" />;
      default: return <Brain className="h-4 w-4 text-gray-600" />;
    }
  };
  
  return (
    <div className={`border rounded-lg p-4 ${getPriorityColor()} ${className}`}>
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center">
          {getPriorityIcon()}
          <h4 className="ml-2 font-medium text-gray-900">{title}</h4>
        </div>
        <ConfidenceScore score={confidence} size="sm" showLabel={false} />
      </div>
      <p className="text-sm text-gray-700 mb-3">{insight}</p>
      <div className="flex items-center justify-between">
        <AIBadge variant="info" size="sm" />
        {actionable && (
          <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
            <Zap className="h-3 w-3 mr-1" />
            Actionable
          </span>
        )}
      </div>
    </div>
  );
};

interface AIMetricsDisplayProps {
  metrics: {
    totalAnalyzed: number;
    aiConfidence: number;
    insightsGenerated: number;
    recommendationsCount: number;
  };
  className?: string;
}

export const AIMetricsDisplay: React.FC<AIMetricsDisplayProps> = ({ metrics, className = '' }) => {
  return (
    <div className={`bg-gradient-to-r from-blue-50 to-purple-50 rounded-lg p-6 ${className}`}>
      <div className="flex items-center mb-4">
        <Brain className="h-6 w-6 text-blue-600" />
        <h3 className="ml-2 text-lg font-semibold text-gray-900">AI Analysis Summary</h3>
      </div>
      
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="text-center">
          <div className="text-2xl font-bold text-blue-600">{metrics.totalAnalyzed}</div>
          <div className="text-sm text-gray-600">VMs Analyzed</div>
        </div>
        <div className="text-center">
          <div className="text-2xl font-bold text-green-600">{Math.round(metrics.aiConfidence * 100)}%</div>
          <div className="text-sm text-gray-600">AI Confidence</div>
        </div>
        <div className="text-center">
          <div className="text-2xl font-bold text-purple-600">{metrics.insightsGenerated}</div>
          <div className="text-sm text-gray-600">Insights Generated</div>
        </div>
        <div className="text-center">
          <div className="text-2xl font-bold text-orange-600">{metrics.recommendationsCount}</div>
          <div className="text-sm text-gray-600">Recommendations</div>
        </div>
      </div>
    </div>
  );
};
