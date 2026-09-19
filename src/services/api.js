const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '/api';

export async function fetchCommunityData(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      Accept: 'application/json',
      ...options.headers,
    },
  });

  if (!response.ok) {
    throw new Error(`Community data request failed (${response.status})`);
  }

  return response.json();
}
