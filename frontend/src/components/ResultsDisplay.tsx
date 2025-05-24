import React from 'react';
import { Product } from '../../services/api';

interface ResultsDisplayProps {
  products: Product[];
  isLoading: boolean;
}

const ResultsDisplay: React.FC<ResultsDisplayProps> = ({ products, isLoading }) => {
  if (isLoading) {
    return (
      <div className="text-center p-4">
        <p className="text-lg text-slate-600">Loading results...</p>
        {/* Optional: Add a spinner here too */}
      </div>
    );
  }

  if (!products || products.length === 0) {
    return (
      <div className="text-center p-4">
        <p className="text-lg text-slate-500">No products found. Try a different search!</p>
      </div>
    );
  }

  return (
    <div className="results-area space-y-6">
      <h2 className="text-2xl md:text-3xl font-semibold text-slate-700 border-b pb-3 mb-6">
        Results
      </h2>
      {products.map((product, index) => (
        <div 
          key={index} 
          className="product-item bg-white p-5 rounded-lg shadow-md border border-slate-200 hover:shadow-xl transition-shadow duration-300 ease-in-out"
        >
          <h3 className="text-xl font-semibold text-sky-600 mb-2">
            <a 
              href={product.url} 
              target="_blank" 
              rel="noopener noreferrer"
              className="hover:text-sky-700 hover:underline"
            >
              {product.title || 'N/A'}
            </a>
          </h3>
          <p className="text-slate-700 mb-1">
            <strong>Price:</strong> 
            <span className="text-green-600 font-medium ml-1">${product.price || 'N/A'}</span>
          </p>
          {product.price_per_count && (
            <p className="text-sm text-slate-500 mb-3">
              <strong>Unit Price:</strong> {product.price_per_count}
            </p>
          )}
          {product.ranking_explanation && (
            <div className="ranking-explanation mt-3 p-3 bg-sky-50 border-l-4 border-sky-500 rounded-r-md text-sm text-slate-700">
              <p className="italic"><strong className="font-medium">Agent's Note:</strong> {product.ranking_explanation}</p>
            </div>
          )}
        </div>
      ))}
    </div>
  );
};

export default ResultsDisplay;
