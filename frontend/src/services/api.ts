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
  return new Promise(async (resolve, reject) => {
    console.log('uploadFile: Starting upload for:', file.name, 'Size:', file.size);
    
    // Use presigned URL for files over 3MB (to account for base64 overhead)
    // 3MB * 1.33 (base64 overhead) = ~4MB which is safely under limits
    // Note: API Gateway seems to have a lower practical limit than 10MB
    const USE_PRESIGNED_URL_THRESHOLD = 3 * 1024 * 1024; // 3MB
    
    if (file.size > USE_PRESIGNED_URL_THRESHOLD) {
      console.log('uploadFile: File is large, using presigned URL upload');
      try {
        // Get presigned URL from backend
        console.log('uploadFile: Requesting presigned URL');
        const urlResponse = await api.post('/documents/upload-url', {
          filename: file.name
        });
        
        const { upload_url, fields, document_id, s3_key } = urlResponse.data;
        console.log('uploadFile: Got presigned URL, uploading directly to S3');
        
        // Create FormData for S3 upload
        const formData = new FormData();
        
        // Add all fields from presigned POST data
        Object.keys(fields).forEach(key => {
          formData.append(key, fields[key]);
        });
        
        // File must be the last field
        formData.append('file', file);
        
        // Upload directly to S3
        // DO NOT set Content-Type header - let axios set it with the boundary
        const uploadResponse = await axios.post(upload_url, formData, {
          onUploadProgress: (progressEvent) => {
            const percentCompleted = progressEvent.total ? Math.round((progressEvent.loaded * 100) / progressEvent.total) : 0;
            console.log(`Upload progress: ${percentCompleted}% (${progressEvent.loaded}/${progressEvent.total} bytes)`);
          }
        });
        
        console.log('uploadFile: Direct S3 upload successful');
        
        // Return success response in same format as regular upload
        resolve({
          message: 'Document uploaded successfully',
          document_id: document_id,
          filename: file.name,
          status: 'processing',
          status_url: `/documents/status/${document_id}`
        });
        
      } catch (error: any) {
        console.error('uploadFile: Error during presigned URL upload:', error);
        
        // Log the actual S3 error response for debugging
        if (error.response?.data) {
          console.error('S3 Error Response:', error.response.data);
          // Try to parse XML error response
          try {
            const parser = new DOMParser();
            const xmlDoc = parser.parseFromString(error.response.data, 'text/xml');
            const errorCode = xmlDoc.getElementsByTagName('Code')[0]?.textContent;
            const errorMessage = xmlDoc.getElementsByTagName('Message')[0]?.textContent;
            console.error('S3 Error Details:', { code: errorCode, message: errorMessage });
          } catch (e) {
            // Not XML, ignore
          }
        }
        
        // Check for auth error
        if (error.response?.status === 401) {
          reject(new Error('Authentication expired. Please refresh the page and log in again.'));
        }
        // Check for server error
        else if (error.response?.status >= 500) {
          reject(new Error('Server error. Please try again in a few moments.'));
        } else {
          reject(new Error('Upload failed. Please try again.'));
        }
      }
    } else {
      // Use traditional base64 upload for smaller files
      console.log('uploadFile: Using traditional base64 upload');
      
      const reader = new FileReader();
      reader.onload = async () => {
      try {
        console.log('uploadFile: File read complete, converting to base64');
        const base64 = reader.result?.toString().split(',')[1];
        if (!base64) {
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
          timeout: 60000, // 60 second timeout for large files
          onUploadProgress: (progressEvent) => {
            const percentCompleted = progressEvent.total ? Math.round((progressEvent.loaded * 100) / progressEvent.total) : 0;
            console.log(`Upload progress: ${percentCompleted}% (${progressEvent.loaded}/${progressEvent.total} bytes)`);
          }
        });
        
        console.timeEnd('upload-request');
        console.log('uploadFile: Success!', response.data);
        console.log('uploadFile: Response status:', response.status);
        console.log('uploadFile: Response headers:', response.headers);
        resolve(response.data);
      } catch (error: any) {
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
          reject(new Error('Upload timeout - file may be too large. Please try a smaller file or check your connection.'));
        }
        // Check for network error or CORS issue
        else if (!error.response) {
          console.error('uploadFile: Network error - no response from server');
          console.error('Possible causes: CORS issue, network failure, or server not responding');
          reject(new Error('Network error - unable to reach server. Please refresh the page and try again.'));
        }
        // Check for auth error
        else if (error.response?.status === 401) {
          console.error('uploadFile: Authentication error');
          reject(new Error('Authentication expired. Please refresh the page and log in again.'));
        }
        // Check for server error
        else if (error.response?.status >= 500) {
          console.error('uploadFile: Server error:', error.response.status);
          reject(new Error('Server error. Please try again in a few moments.'));
        } else {
          reject(error);
        }
      }
    };
    reader.onerror = (error) => {
      console.error('uploadFile: FileReader error:', error);
      reject(new Error('Failed to read file'));
    };
    
    console.log('uploadFile: Reading file as data URL...');
    reader.readAsDataURL(file);
    }
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