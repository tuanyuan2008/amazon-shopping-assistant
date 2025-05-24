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
    <form onSubmit={handleSubmit} className="flex items-center w-full">
      <input
        type="text"
        value={currentQuery}
        onChange={handleChange}
        placeholder="e.g., organic coffee beans under $20"
        className="flex-grow p-3 border border-slate-300 rounded-l-md shadow-sm 
                   focus:ring-2 focus:ring-sky-500 focus:border-sky-500 outline-none
                   disabled:bg-slate-100 disabled:text-slate-500"
        disabled={isLoading}
      />
      <button 
        type="submit" 
        className="p-3 bg-sky-600 text-white rounded-r-md shadow-sm 
                   hover:bg-sky-700 focus:outline-none focus:ring-2 
                   focus:ring-sky-500 focus:ring-offset-2
                   disabled:bg-sky-300"
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
    </form>
  );
};

export default QueryInput;
