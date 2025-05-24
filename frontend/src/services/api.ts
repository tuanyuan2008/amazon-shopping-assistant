// Define the expected structure for products and the API response.
// These should ideally match or be adaptable from the backend's actual response.

export interface Product {
  title: string;
  price: string | number;
  url: string;
  ranking_explanation?: string;
  price_per_count?: string;
  // Add other fields that the backend might return for a product
}

export interface ApiQueryResponse {
  products: Product[];
  summary: string | null;
  new_context: Record<string, any>; // Or a more specific type if known
}

export interface ApiError {
  message: string;
  details?: any; // For additional error details if provided by backend
}

const API_BASE_URL = 'http://localhost:5001/api'; // Ensure this matches your backend URL

export const fetchQueryResults = async (
  userInput: string,
  previousContext: Record<string, any>
): Promise<ApiQueryResponse> => {
  const requestBody = {
    user_input: userInput,
    previous_context: previousContext,
  };

  try {
    const response = await fetch(`${API_BASE_URL}/query`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        // Add any other headers like Authorization if needed in the future
      },
      body: JSON.stringify(requestBody),
    });

    if (!response.ok) {
      // Try to parse error response from backend if available
      let errorData: ApiError = { message: `HTTP error! status: ${response.status}` };
      try {
        const backendError = await response.json();
        errorData = { 
            message: backendError.error || `HTTP error! status: ${response.status}`,
            details: backendError.details 
        };
      } catch (e) {
        // Could not parse JSON error, stick with the status
      }
      throw errorData;
    }

    const data: ApiQueryResponse = await response.json();
    return data;

  } catch (error) {
    // Handle network errors or errors thrown from response.ok check
    console.error('API call failed:', error);
    if ((error as ApiError).message) {
        throw error; // Re-throw the structured ApiError
    }
    throw { message: 'Failed to fetch results. Please check your network connection or try again later.' } as ApiError;
  }
};
