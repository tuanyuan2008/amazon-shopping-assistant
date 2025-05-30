import { useState } from 'react';
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

  const isPreSearchState = products.length === 0 && !isLoading && !error && !summary;

  return (
    // The outermost div: In pre-search, centers its child (the div below) vertically and horizontally.
    // Otherwise, it only centers its child horizontally (items-center) and lets content flow from top.
    <div className={`min-h-screen bg-baby-robin-blue text-slate-800 flex flex-col p-4 ${isPreSearchState ? 'justify-center items-center' : 'items-center'}`}>
      {/* This div wraps all content. In pre-search, it becomes a flex container to center the query-section.
          It takes w-full and max-w-3xl as before.
          The 'mx-auto' is for non-pre-search state to center it when header/footer are visible.
          In pre-search, items-center will horizontally center query-section (if it's not w-full).
          justify-center will vertically center query-section.
      */}
      <div className={`w-full max-w-3xl ${isPreSearchState ? 'flex flex-col justify-center items-center' : 'mx-auto'}`}>
        {!isPreSearchState && (
          <header className="text-center my-8">
            <h1 className="text-4xl md:text-5xl font-bold text-baby-robin-blue-dark">
              Amazon Shopping Assistant
            </h1>
          </header>
        )}

        <section className={`query-section p-6 ${isPreSearchState ? '' : 'mb-8'}`}>
          <QueryInput
            currentQuery={currentQuery}
            setCurrentQuery={setCurrentQuery}
            handleSubmitQuery={handleSubmitQuery}
            isLoading={isLoading}
          />
        </section>

        {error && (
          <section className="error-section mb-8 p-4 bg-red-100 border border-red-400 text-red-700 rounded-xl shadow-md">
            <h2 className="text-xl font-semibold mb-2">Error</h2>
            <p>{error.message}</p>
            {error.details && 
              <pre className="mt-2 p-2 bg-red-50 text-sm overflow-x-auto rounded-xl">
                {JSON.stringify(error.details, null, 2)}
              </pre>
            }
          </section>
        )}

        {!isPreSearchState && !error && (isLoading || products.length > 0 || summary) && (
          <>
            <section className="summary-section w-full max-w-3xl mx-auto mb-8">
              <SummaryDisplay summary={summary} isLoading={isLoading && !summary} />
            </section>
            <div className="w-full flex justify-center mb-8">
              <div className="h-1 w-24 rounded-full bg-gradient-to-r from-baby-robin-blue/40 to-baby-robin-blue-dark/40 opacity-60"></div>
            </div>
            <section className="results-section w-full max-w-3xl mx-auto">
              <ResultsDisplay products={products} isLoading={isLoading && products.length === 0} />
            </section>
          </>
        )}
        
        {!isPreSearchState && !error && !isLoading && products.length === 0 && !summary && (
             <div className="text-center p-6 bg-white rounded-xl shadow-lg">
                <p className="text-slate-500 text-lg">Enter a query above to start searching!</p>
            </div>
        )}

        {!isPreSearchState && (
          <footer className="text-center mt-12 py-6 text-sm text-slate-500">
            <p>Amazon Shopping Assistant UI - Tailwind Version</p>
          </footer>
        )}
      </div>
    </div>
  );
}

export default App;