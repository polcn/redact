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

export default api;