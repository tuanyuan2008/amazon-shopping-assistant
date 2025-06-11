import React from 'react';

interface QueryInputProps {
  currentQuery: string;
  setCurrentQuery: (query: string) => void;
  handleSubmitQuery: () => void; 
  isLoading: boolean;
}

const QueryInput: React.FC<QueryInputProps> = ({
  currentQuery,
  setCurrentQuery,
  handleSubmitQuery,
  isLoading,
}) => {
  const handleChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    setCurrentQuery(event.target.value);
  };

  const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!currentQuery.trim()) {
      alert('Please enter a search query.');
      return;
    }
    handleSubmitQuery(); 
  };

  return (
    <form onSubmit={handleSubmit} className="w-full flex justify-center items-center py-4">
      <div className="flex w-full max-w-3xl items-center bg-white/80 backdrop-blur-sm rounded-full shadow-lg border border-slate-200 px-3 py-2">
        <span className="pl-4 pr-3 text-slate-400 flex-shrink-0">
          {/* Minimalist search icon (outline) */}
          <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <circle cx="11" cy="11" r="7" stroke="currentColor" strokeWidth="2" fill="none" />
            <line x1="16.5" y1="16.5" x2="21" y2="21" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
          </svg>
        </span>
        <input
          type="text"
          value={currentQuery}
          onChange={handleChange}
          placeholder="Shop for anything..."
          className="flex-grow min-w-0 bg-transparent border-none outline-none text-lg placeholder:text-slate-400 px-3 py-3 disabled:bg-slate-100 disabled:text-slate-500 overflow-x-auto whitespace-nowrap input-scroll"
          disabled={isLoading}
        />
        <button
          type="submit"
          className="ml-3 px-8 py-3 rounded-full bg-baby-robin-blue-dark text-white font-semibold shadow hover:bg-baby-robin-blue focus:outline-none focus:ring-2 focus:ring-baby-robin-blue-dark focus:ring-offset-2 transition-all duration-200 disabled:bg-baby-robin-blue flex-shrink-0"
          disabled={isLoading}
        >
          {isLoading ? (
            <svg className="animate-spin h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
          ) : (
            'Search'
          )}
        </button>
      </div>
    </form>
  );
};

export default QueryInput;
