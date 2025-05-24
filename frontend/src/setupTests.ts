// src/setupTests.ts
import '@testing-library/jest-dom';

// If you have other global setup, you can add it here.
// For example, you might want to mock global objects or functions.

// Example: Mocking matchMedia (often needed for components that use responsive queries)
// Object.defineProperty(window, 'matchMedia', {
//   writable: true,
//   value: vi.fn().mockImplementation(query => ({
//     matches: false,
//     media: query,
//     onchange: null,
//     addListener: vi.fn(), // deprecated
//     removeListener: vi.fn(), // deprecated
//     addEventListener: vi.fn(),
//     removeEventListener: vi.fn(),
//     dispatchEvent: vi.fn(),
//   })),
// });
