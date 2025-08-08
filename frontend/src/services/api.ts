import axios from 'axios';
import { fetchAuthSession } from 'aws-amplify/auth';

const API_URL = process.env.REACT_APP_API_URL || '';

// Create axios instance
const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000, // 30 second timeout
});

// Add auth token to requests
api.interceptors.request.use(async (config) => {
  try {
    console.log('Interceptor: Fetching auth session for request to:', config.url);
    const session = await fetchAuthSession();
    if (session.tokens?.idToken) {
      config.headers.Authorization = `Bearer ${session.tokens.idToken.toString()}`;
      console.log('Interceptor: Added auth token to request');
    } else {
      console.warn('Interceptor: No ID token found in session');
    }
  } catch (error) {
    console.error('Error getting auth token:', error);
  }
  console.log('Request config:', {
    url: config.url,
    method: config.method,
    headers: config.headers,
    baseURL: config.baseURL,
    data: config.data ? `Data size: ${JSON.stringify(config.data).length} bytes` : 'No data'
  });
  return config;
});

// Add response interceptor for better error handling
api.interceptors.response.use(
  (response) => {
    console.log('Response received:', {
      url: response.config.url,
      status: response.status,
      data: response.data
    });
    return response;
  },
  (error) => {
    console.error('API Error:', {
      url: error.config?.url,
      method: error.config?.method,
      status: error.response?.status,
      statusText: error.response?.statusText,
      data: error.response?.data,
      message: error.message
    });
    
    // Check for network errors
    if (!error.response) {
      console.error('Network error - no response received. Possible CORS issue or network failure.');
    }
    
    return Promise.reject(error);
  }
);

// File upload with custom timeout
export const uploadFile = async (file: File): Promise<any> => {
  return new Promise((resolve, reject) => {
    console.log('uploadFile: Starting upload for:', file.name, 'Size:', file.size);
    
    // Set a timer to reject if upload takes too long
    const uploadTimeout = setTimeout(() => {
      console.error('uploadFile: Upload timed out after 10 seconds');
      reject(new Error('Upload timeout - please try again'));
    }, 10000); // 10 second timeout for uploads
    
    const reader = new FileReader();
    reader.onload = async () => {
      try {
        console.log('uploadFile: File read complete, converting to base64');
        const base64 = reader.result?.toString().split(',')[1];
        if (!base64) {
          clearTimeout(uploadTimeout);
          throw new Error('Failed to convert file to base64');
        }
        console.log('uploadFile: Base64 length:', base64.length);
        console.log('uploadFile: Making API call to /documents/upload');
        console.log('uploadFile: API URL:', API_URL);
        console.time('upload-request');
        
        // Make the upload request with a specific timeout
        const response = await api.post('/documents/upload', {
          filename: file.name,
          content: base64,
        }, {
          timeout: 10000, // 10 second timeout
          onUploadProgress: (progressEvent) => {
            console.log('Upload progress:', progressEvent.loaded, '/', progressEvent.total);
          }
        });
        
        clearTimeout(uploadTimeout);
        console.timeEnd('upload-request');
        console.log('uploadFile: Success!', response.data);
        console.log('uploadFile: Response status:', response.status);
        console.log('uploadFile: Response headers:', response.headers);
        resolve(response.data);
      } catch (error: any) {
        clearTimeout(uploadTimeout);
        console.timeEnd('upload-request');
        console.error('uploadFile: Error during upload:', error);
        console.error('uploadFile: Error details:', {
          message: error.message,
          response: error.response,
          request: error.request,
          config: error.config
        });
        
        // Check for timeout
        if (error.code === 'ECONNABORTED' || error.message.includes('timeout')) {
          console.error('uploadFile: Request timeout');
          reject(new Error('Upload timeout - please try again'));
        }
        // Check for network error
        else if (!error.response) {
          console.error('uploadFile: Network error - no response from server');
          reject(new Error('Network error - please check your connection'));
        } else {
          reject(error);
        }
      }
    };
    reader.onerror = (error) => {
      clearTimeout(uploadTimeout);
      console.error('uploadFile: FileReader error:', error);
      reject(new Error('Failed to read file'));
    };
    
    console.log('uploadFile: Reading file as data URL...');
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
  const response = await api.get('/user/files');
  return response.data;
};

// Get configuration
export const getConfig = async (): Promise<any> => {
  const response = await api.get('/api/config');
  return response.data;
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
  download_url: string;
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
  summaryType: 'brief' | 'standard' | 'detailed' = 'standard'
): Promise<{
  success: boolean;
  message: string;
  document_id: string;
  new_filename: string;
  download_url: string;
  summary_metadata: any;
}> => {
  const response = await api.post('/documents/ai-summary', {
    document_id: documentId,
    summary_type: summaryType
  });
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

export default api;