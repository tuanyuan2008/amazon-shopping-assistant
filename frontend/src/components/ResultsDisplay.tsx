import React, { useState } from 'react';

interface Product {
  title: string;
  price: string | number;
  url: string;
  ranking_explanation?: string; 
  price_per_count?: string; 
}

interface ResultsDisplayProps {
  products: Product[];
  isLoading: boolean;
}

const ResultsDisplay: React.FC<ResultsDisplayProps> = ({ products, isLoading }) => {
  const [visibleCount, setVisibleCount] = useState(10);
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null);
  const [expandedNotes, setExpandedNotes] = useState<{ [key: number]: boolean }>({});

  const handleCopy = (product: Product, idx: number) => {
    const text = `${product.title}\nPrice: $${product.price}\n${product.url}`;
    navigator.clipboard.writeText(text);
    setCopiedIndex(idx);
    setTimeout(() => setCopiedIndex(null), 1200);
  };

  const toggleNote = (idx: number) => {
    setExpandedNotes(prev => ({ ...prev, [idx]: !prev[idx] }));
  };

  if (!products || products.length === 0) {
    return (
      <div className="text-center p-4">
        <p className="text-lg text-slate-500">No products found. Try a different search!</p>
      </div>
    );
  }

  const visibleProducts = products.slice(0, visibleCount);

  return (
    <div className="results-area space-y-8">
      <h2 className="text-2xl md:text-3xl font-bold text-baby-robin-blue-dark mb-6 tracking-tight" style={{ fontFamily: 'Nunito, ui-sans-serif, system-ui' }}>
        Results
      </h2>
      {visibleProducts.map((product, index) => (
        <div 
          key={index} 
          className="product-item relative bg-white/90 backdrop-blur-md p-6 rounded-2xl shadow-lg border border-white/30 transition-all duration-300 hover:scale-[1.01] hover:shadow-xl hover:bg-white/95 group"
          style={{ fontFamily: 'Nunito, ui-sans-serif, system-ui' }}
        >
          <div className="flex items-center gap-2 mb-2">
            <h3 className="text-xl font-bold text-baby-robin-blue-dark group-hover:text-baby-robin-blue-dark transition-colors">
              <a 
                href={product.url} 
                target="_blank" 
                rel="noopener noreferrer"
                className="hover:text-baby-robin-blue hover:underline focus:text-baby-robin-blue-dark"
              >
                {product.title || 'N/A'}
              </a>
            </h3>
            {product.ranking_explanation && product.ranking_explanation.toLowerCase().includes('best value') && (
              <span className="ml-2 px-2 py-0.5 rounded-full bg-green-100 text-green-700 text-xs font-semibold border border-green-200">Best Value</span>
            )}
            <button
              onClick={() => handleCopy(product, index)}
              className="ml-auto flex items-center px-3 py-1 rounded-full hover:bg-baby-robin-blue/20 focus:outline-none focus:ring-2 focus:ring-baby-robin-blue-dark text-baby-robin-blue-dark text-sm transition-colors"
              aria-label="Copy product info"
              title="Copy product info"
            >
              {copiedIndex === index ? (
                <span className="text-green-500 font-semibold">Copied!</span>
              ) : (
                <>
                  <svg xmlns="http://www.w3.org/2000/svg" className="inline w-5 h-5 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16h8M8 12h8m-7 8h6a2 2 0 002-2V6a2 2 0 00-2-2H8a2 2 0 00-2 2v12a2 2 0 002 2z" /></svg>
                  <span>Copy</span>
                </>
              )}
            </button>
          </div>
          <div className="flex flex-wrap items-center gap-4 mb-2">
            <span className="text-lg text-green-700 font-bold group-hover:text-green-800">${product.price || 'N/A'}</span>
            {product.price_per_count && (
              <span className="text-xs text-slate-600 bg-slate-100 rounded px-2 py-0.5 group-hover:text-slate-800">{product.price_per_count}</span>
            )}
          </div>
          {product.ranking_explanation && (
            <div className="ranking-explanation mt-3">
              <button
                onClick={() => toggleNote(index)}
                className="mb-2 text-baby-robin-blue-dark hover:underline text-xs font-semibold focus:outline-none"
                aria-label={expandedNotes[index] ? 'Collapse note' : 'Expand note'}
              >
                {expandedNotes[index] ? "Hide Agent's Note" : "Show Agent's Note"}
              </button>
              {expandedNotes[index] && (
                <div className="transition-all duration-300 bg-baby-robin-blue/20 border-l-4 border-baby-robin-blue-dark/40 rounded-xl text-sm text-slate-800 p-3 mt-1">
                  <p className="italic"><strong className="font-medium">Agent's Note:</strong> {product.ranking_explanation}</p>
                </div>
              )}
            </div>
          )}
          {index < visibleProducts.length - 1 && (
            <div className="absolute left-6 right-6 bottom-[-1.5rem] h-0.5 bg-gradient-to-r from-baby-robin-blue/10 via-baby-robin-blue/30 to-baby-robin-blue/10 opacity-60 rounded-full" />
          )}
        </div>
      ))}
      {products.length > visibleCount && (
        <div className="flex justify-center mt-8">
          <button
            onClick={() => setVisibleCount(c => c + 10)}
            className="px-8 py-3 rounded-xl bg-baby-robin-blue-dark text-white font-semibold shadow hover:bg-baby-robin-blue transition-colors"
          >
            Show More
          </button>
        </div>
      )}
    </div>
  );
};

export default ResultsDisplay;
