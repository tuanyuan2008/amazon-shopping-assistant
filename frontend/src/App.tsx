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
    <div className={`min-h-screen bg-baby-robin-blue text-slate-800 flex flex-col p-4 ${isPreSearchState ? 'justify-center items-center' : 'items-center justify-between'}`}>
      {/* This div wraps all content. In pre-search, it becomes a flex container to center the query-section.
          It takes w-full and max-w-4xl as before.
          The 'mx-auto' is for non-pre-search state to center it when header/footer are visible.
          In pre-search, items-center will horizontally center query-section (if it's not w-full).
          justify-center will vertically center query-section.
      */}
      <div className={`w-full max-w-4xl px-8 ${isPreSearchState ? 'flex flex-col justify-center items-center' : 'mx-auto'}`}>
        {!isPreSearchState && (
          <header className="text-center py-10">
            <h1 className="text-5xl md:text-6xl font-bold text-baby-robin-blue-dark">
              Shopping Assistant
            </h1>
          </header>
        )}

        <section className={`query-section w-full max-w-4xl mx-auto ${isPreSearchState ? '' : 'mb-12'}`}>
          <QueryInput
            currentQuery={currentQuery}
            setCurrentQuery={setCurrentQuery}
            handleSubmitQuery={handleSubmitQuery}
            isLoading={isLoading}
          />
        </section>
        
        {/* Loading indicator moved here */}
        {isLoading && !isPreSearchState && (
          <div className="w-full flex flex-col items-center mb-12">
            <div className="h-1.5 w-32 rounded-full bg-gradient-to-r from-baby-robin-blue/40 to-baby-robin-blue-dark/40 opacity-60 animate-pulse mb-4"></div>
          </div>
        )}

        {error && (
          <section className="error-section mb-12 p-6 bg-red-100 border border-red-400 text-red-700 rounded-xl shadow-md">
            <h2 className="text-xl font-semibold mb-2">Error</h2>
            <p>{error.message}</p>
            {error.details && 
              <pre className="mt-2 p-2 bg-red-50 text-sm overflow-x-auto rounded-xl">
                {JSON.stringify(error.details, null, 2)}
              </pre>
            }
          </section>
        )}

        {!isPreSearchState && !error && !isLoading && (products.length > 0 || summary) && (
          <div className="w-full max-w-4xl mx-auto">
            <section className="summary-section w-full mb-12">
              <SummaryDisplay summary={summary} isLoading={false} />
            </section>
            <section className="results-section w-full">
              <ResultsDisplay products={products} isLoading={false} />
            </section>
          </div>
        )}
        
        {!isPreSearchState && !error && !isLoading && products.length === 0 && !summary && (
             <div className="text-center p-8 bg-white rounded-xl shadow-lg">
                <p className="text-slate-500 text-lg">Enter a query above to start searching!</p>
            </div>
        )}

        {/* Adjusted footer for stick-to-bottom behavior */}
        {!isPreSearchState && (
          <footer className="text-center py-8 text-sm text-slate-500">
            <p>Shopping Assistant - Tailwind Version</p>
          </footer>
        )}
      </div>
    </div>
  );
}

export default App;