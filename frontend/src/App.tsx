import React, { useState } from 'react';
import QueryInput from './components/QueryInput';
import ResultsDisplay from './components/ResultsDisplay';
import SummaryDisplay from './components/SummaryDisplay';
import * as ApiService from './services/api';
import './App.css'; // Keep for any global non-Tailwind overrides or specific component styles if needed

// Removed local Product interface alias:
// interface Product extends ApiProduct {}

function App() {
  const [currentQuery, setCurrentQuery] = useState<string>('');
  const [products, setProducts] = useState<ApiService.Product[]>([]);
  const [summary, setSummary] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<ApiService.ApiError | null>(null);
  const [previousContext, setPreviousContext] = useState<Record<string, any>>({});

  const handleSubmitQuery = async () => {
    if (!currentQuery.trim()) {
      // alert('Please enter a query.'); // Or handle differently
      return;
    }
    
    console.log('Submitting query:', currentQuery, 'with context:', previousContext);
    setIsLoading(true);
    setError(null); 

    try {
      const apiResponse = await ApiService.fetchQueryResults(currentQuery, previousContext);
      setProducts(apiResponse.products);
      setSummary(apiResponse.summary);
      setPreviousContext(apiResponse.new_context);
    } catch (err) {
      console.error('API Error:', err);
      const apiErr = err as ApiService.ApiError;
      setError({ message: apiErr.message || 'An unexpected error occurred.' , details: apiErr.details });
      setProducts([]);
      setSummary(null);  
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-100 text-slate-800 flex flex-col items-center p-4">
      <div className="w-full max-w-3xl mx-auto">
        <header className="text-center my-8">
          <h1 className="text-4xl md:text-5xl font-bold text-sky-700">
            Amazon Shopping Assistant
          </h1>
        </header>

        <section className="query-section mb-8 p-6 bg-white rounded-lg shadow-lg">
          <QueryInput
            currentQuery={currentQuery}
            setCurrentQuery={setCurrentQuery}
            handleSubmitQuery={handleSubmitQuery}
            isLoading={isLoading}
          />
        </section>

        {error && (
          <section className="error-section mb-8 p-4 bg-red-100 border border-red-400 text-red-700 rounded-md shadow-md">
            <h2 className="text-xl font-semibold mb-2">Error</h2>
            <p>{error.message}</p>
            {error.details && 
              <pre className="mt-2 p-2 bg-red-50 text-sm overflow-x-auto rounded">
                {JSON.stringify(error.details, null, 2)}
              </pre>
            }
          </section>
        )}

        {!error && (isLoading || products.length > 0 || summary) && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <section className="summary-section md:col-span-1 p-6 bg-white rounded-lg shadow-lg">
              <SummaryDisplay summary={summary} isLoading={isLoading && !summary} />
            </section>
            <section className="results-section md:col-span-2 p-6 bg-white rounded-lg shadow-lg">
              <ResultsDisplay products={products} isLoading={isLoading && products.length === 0} />
            </section> 
          </div>
        )}
        
        {!error && !isLoading && products.length === 0 && !summary && (
             <div className="text-center p-6 bg-white rounded-lg shadow-lg">
                <p className="text-slate-500 text-lg">Enter a query above to start searching!</p>
            </div>
        )}

        <footer className="text-center mt-12 py-6 text-sm text-slate-500">
          <p>Amazon Shopping Assistant UI - Tailwind Version</p>
        </footer>
      </div>
    </div>
  );
}

export default App;