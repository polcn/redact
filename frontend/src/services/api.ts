import axios from 'axios';
import { fetchAuthSession } from 'aws-amplify/auth';

const API_URL = process.env.REACT_APP_API_URL || '';

// Create axios instance
const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add auth token to requests
api.interceptors.request.use(async (config) => {
  try {
    const session = await fetchAuthSession();
    if (session.tokens?.idToken) {
      config.headers.Authorization = `Bearer ${session.tokens.idToken.toString()}`;
    }
  } catch (error) {
    console.error('Error getting auth token:', error);
  }
  return config;
});

// Add response interceptor for better error handling
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      // Token might be expired, try to refresh
      console.log('401 error, attempting to refresh token...');
      try {
        const session = await fetchAuthSession({ forceRefresh: true });
        if (session.tokens?.idToken) {
          // Retry the original request with new token
          error.config.headers.Authorization = `Bearer ${session.tokens.idToken.toString()}`;
          return api.request(error.config);
        }
      } catch (refreshError) {
        console.error('Failed to refresh token:', refreshError);
      }
    }
    return Promise.reject(error);
  }
);

// File upload
export const uploadFile = async (file: File): Promise<any> => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = async () => {
      try {
        const base64 = reader.result?.toString().split(',')[1];
        const response = await api.post('/documents/upload', {
          filename: file.name,
          content: base64,
        });
        resolve(response.data);
      } catch (error) {
        reject(error);
      }
    };
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
};

// Check file status
export const checkFileStatus = async (documentId: string): Promise<any> => {
  const response = await api.get(`/documents/status/${documentId}`);
  return response.data;
};

// List user files
export const listUserFiles = async (): Promise<any> => {
  try {
    const response = await api.get('/user/files');
    return response.data;
  } catch (error: any) {
    console.error('Error listing user files:', error);
    // Return empty data structure instead of throwing
    return { files: [] };
  }
};

// Get configuration with retry
export const getConfig = async (): Promise<any> => {
  let retries = 2;
  let lastError: any = null;
  
  while (retries >= 0) {
    try {
      const response = await api.get('/api/config');
      return response.data;
    } catch (error: any) {
      lastError = error;
      console.error(`Error getting config (${2 - retries}/2 retries):`, error);
      
      if (retries > 0) {
        // Wait a bit before retrying
        await new Promise(resolve => setTimeout(resolve, 1000));
      }
      retries--;
    }
  }
  
  // If all retries failed, throw the last error
  throw lastError;
};

// Update configuration (admin only)
export const updateConfig = async (config: any): Promise<any> => {
  const response = await api.put('/api/config', config);
  return response.data;
};

// Delete file
export const deleteFile = async (documentId: string): Promise<any> => {
  const response = await api.delete(`/documents/${documentId}`);
  return response.data;
};

// Health check
export const healthCheck = async (): Promise<any> => {
  const response = await api.get('/health');
  return response.data;
};

// Batch download files as ZIP
export const batchDownloadFiles = async (documentIds: string[]): Promise<{ download_url: string; filename: string }> => {
  const response = await api.post('/documents/batch-download', {
    document_ids: documentIds
  });
  return response.data;
};

// Combine multiple files into one
export const combineFiles = async (
  documentIds: string[],
  outputFilename: string = 'combined_document.txt',
  separator: string = '\n\n--- Document Break ---\n\n'
): Promise<{
  message: string;
  document_id: string;
  filename: string;
  file_count: number;
  s3_key: string;
  size: number;
}> => {
  const response = await api.post('/documents/combine', {
    document_ids: documentIds,
    output_filename: outputFilename,
    separator: separator
  });
  return response.data;
};

// Generate AI summary for a document
export const generateAISummary = async (
  documentId: string,
  summaryType: 'brief' | 'standard' | 'detailed' = 'standard',
  model?: string
): Promise<{
  success: boolean;
  message: string;
  document_id: string;
  new_filename: string;
  s3_key: string;
  summary_metadata: any;
}> => {
  const payload: any = {
    document_id: documentId,
    summary_type: summaryType
  };
  
  if (model) {
    payload.model = model;
  }
  
  const response = await api.post('/documents/ai-summary', payload);
  return response.data;
};

// Get AI configuration (admin only gets full config)
export const getAIConfig = async (): Promise<any> => {
  const response = await api.get('/api/ai-config');
  return response.data;
};

// Update AI configuration (admin only)
export const updateAIConfig = async (config: any): Promise<any> => {
  const response = await api.put('/api/ai-config', config);
  return response.data;
};

// Get external AI key status
export const getExternalAIKeys = async (): Promise<any> => {
  const response = await api.get('/api/external-ai-keys');
  return response.data;
};

// Update external AI keys (admin only)
export const updateExternalAIKeys = async (keys: { openai_key?: string; gemini_key?: string }): Promise<any> => {
  const response = await api.put('/api/external-ai-keys', keys);
  return response.data;
};

export default api;