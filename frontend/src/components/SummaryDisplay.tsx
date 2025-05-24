import React from 'react';

interface SummaryDisplayProps {
  summary: string | null; 
  isLoading: boolean;
}

const SummaryDisplay: React.FC<SummaryDisplayProps> = ({ summary, isLoading }) => {
  
  // Scenario 1: Loading a new summary (isLoading is true, and summary might be from a previous query or null)
  if (isLoading && !summary) { // If truly loading and there's no stale summary to show
    return (
      <div className="summary-container p-4 rounded-xl shadow bg-white">
        <h2 className="text-2xl md:text-3xl font-semibold text-slate-700 border-b pb-3 mb-4">Summary</h2>
        <p className="text-slate-600">Loading summary...</p>
        {/* Optional: Add a spinner here */}
      </div>
    );
  }

  // Scenario 2: No summary available after loading (and not currently loading something new)
  if (!summary && !isLoading) {
    return (
      <div className="summary-container p-4 rounded-xl shadow bg-white">
        <h2 className="text-2xl md:text-3xl font-semibold text-slate-700 border-b pb-3 mb-4">Summary</h2>
        <p className="text-slate-500">No summary available for the current results.</p>
      </div>
    );
  }
  
  // Scenario 3: Summary is available (isLoading might be true if a new query is loading, but we show stale summary)
  // or isLoading is false and summary is present.
  if (summary) {
    return (
      <div className="summary-container p-6 rounded-xl shadow-lg bg-gradient-to-r from-baby-robin-blue/30 to-baby-robin-blue-dark/30 border border-baby-robin-blue/50">
        <h2 className="text-2xl md:text-3xl font-semibold text-baby-robin-blue-dark border-b border-baby-robin-blue/70 pb-3 mb-4">
          AI Summary
        </h2>
        {isLoading && <p className="text-sm text-baby-robin-blue-dark mb-2">(Updating summary...)</p>}
        <p className="text-slate-700 leading-relaxed whitespace-pre-line">
          {summary}
        </p>
      </div>
    );
  }

  // Fallback (should ideally not be reached if logic above is correct)
  return null; 
};

export default SummaryDisplay;
