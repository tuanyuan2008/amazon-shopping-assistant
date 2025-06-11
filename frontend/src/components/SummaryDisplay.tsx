import React from 'react';

interface SummaryDisplayProps {
  summary: string | null; 
  isLoading: boolean;
}

const SummaryDisplay: React.FC<SummaryDisplayProps> = ({ summary, isLoading }) => {
  let content;
  if (!summary && !isLoading) {
    content = <p className="text-slate-500">No summary available for the current results.</p>;
  } else if (summary) {
    content = (
      <p
        className="text-slate-800 leading-relaxed whitespace-pre-line font-normal"
        style={{ fontFamily: 'Nunito, ui-sans-serif, system-ui' }}
      >
        {summary}
      </p>
    );
  }

  return (
    <div
      className="summary-container relative p-8 rounded-2xl shadow-xl backdrop-blur-md bg-white/60 border border-white/30"
      style={{ boxShadow: '0 8px 32px 0 rgba(31, 38, 135, 0.10)' }}
    >
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-2xl md:text-3xl font-bold text-baby-robin-blue-dark tracking-tight" style={{ fontFamily: 'Nunito, ui-sans-serif, system-ui' }}>
          Summary
        </h2>
      </div>
      <div className="mb-2">{content}</div>
    </div>
  );
};

export default SummaryDisplay;
