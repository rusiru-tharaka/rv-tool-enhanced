import React from 'react';
import { FileText } from 'lucide-react';

const Reports: React.FC = () => {
  return (
    <div className="text-center py-12">
      <FileText className="h-12 w-12 text-gray-400 mx-auto mb-4" />
      <h1 className="text-2xl font-bold text-gray-900 mb-2">Reports</h1>
      <p className="text-gray-600">Comprehensive analysis reports will be available here</p>
    </div>
  );
};

export default Reports;
