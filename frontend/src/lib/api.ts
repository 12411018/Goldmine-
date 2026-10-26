const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export function uploadFile<T>(path: string, file: File, token: string, onProgress: (percent: number) => void): Promise<T> {
  return new Promise((resolve, reject) => {
    const request = new XMLHttpRequest();
    request.open('POST', `${API_URL}${path}`);
    request.setRequestHeader('Authorization', `Bearer ${token}`);
    request.upload.onprogress = (event) => {
      if (event.lengthComputable) onProgress(Math.round((event.loaded / event.total) * 100));
    };
    request.onerror = () => reject(new Error('Upload connection failed'));
    request.onabort = () => reject(new DOMException('Upload cancelled', 'AbortError'));
    request.onload = () => {
      let result: any;
      try { result = JSON.parse(request.responseText); } catch { result = {}; }
      if (request.status >= 200 && request.status < 300) resolve(result as T);
      else reject(new Error(result.detail || 'Upload failed'));
    };
    const form = new FormData();
    form.append('file', file);
    request.send(form);
  });
}

export async function apiClient(
  path: string,
  options: RequestInit & { token?: string } = {},
) {
  const { token, ...fetchOptions } = options;

  const headers = new Headers(fetchOptions.headers);
  if (!(fetchOptions.body instanceof FormData)) headers.set('Content-Type', 'application/json');

  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  const response = await fetch(`${API_URL}${path}`, {
    ...fetchOptions,
    headers,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || 'API request failed');
  }

  // Handle streaming responses
  if (response.headers.get('content-type')?.includes('text/event-stream')) {
    return response;
  }

  return response.json();
}
