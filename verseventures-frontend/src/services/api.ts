import axios from 'axios';
import { User, Subscription, ApiKey, UsageStats, PricingPlan } from '../types';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('auth_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor to handle auth errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('auth_token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// Auth endpoints
export const authAPI = {
  register: async (email: string, password: string, firstName: string, lastName: string) => {
    const response = await api.post('/auth/register', {
      email,
      password,
      first_name: firstName,
      last_name: lastName,
    });
    return response.data;
  },

  login: async (email: string, password: string) => {
    const response = await api.post('/auth/login', { email, password });
    const { access_token, user } = response.data;
    localStorage.setItem('auth_token', access_token);
    return { user, access_token };
  },

  verifyEmail: async (token: string) => {
    const response = await api.post('/auth/verify-email', { token });
    return response.data;
  },

  resendVerification: async (email: string) => {
    const response = await api.post('/auth/resend-verification', { email });
    return response.data;
  },

  getProfile: async (): Promise<User> => {
    const response = await api.get('/auth/profile');
    return response.data;
  },

  updateProfile: async (data: Partial<User>) => {
    const response = await api.patch('/auth/profile', data);
    return response.data;
  },
};

// Subscription endpoints
export const subscriptionAPI = {
  getSubscription: async (): Promise<Subscription | null> => {
    const response = await api.get('/subscriptions/current');
    return response.data;
  },

  createCheckoutSession: async (planType: string, interval: 'month' | 'year') => {
    const response = await api.post('/subscriptions/create-checkout-session', {
      plan_type: planType,
      interval,
    });
    return response.data;
  },

  createPortalSession: async () => {
    const response = await api.post('/subscriptions/create-portal-session');
    return response.data;
  },

  cancelSubscription: async () => {
    const response = await api.post('/subscriptions/cancel');
    return response.data;
  },

  reactivateSubscription: async () => {
    const response = await api.post('/subscriptions/reactivate');
    return response.data;
  },
};

// API Key endpoints
export const apiKeyAPI = {
  getApiKeys: async (): Promise<ApiKey[]> => {
    const response = await api.get('/api-keys');
    return response.data;
  },

  createApiKey: async (name: string): Promise<ApiKey> => {
    const response = await api.post('/api-keys', { name });
    return response.data;
  },

  deleteApiKey: async (id: string) => {
    const response = await api.delete(`/api-keys/${id}`);
    return response.data;
  },
};

// AWS endpoints
export const awsAPI = {
  getCredentials: async () => {
    const response = await api.post('/aws/credentials');
    return response.data;
  },

  getUsageStats: async (): Promise<UsageStats> => {
    const response = await api.get('/aws/usage');
    return response.data;
  },
};

// Public endpoints
export const publicAPI = {
  getPricingPlans: async (): Promise<PricingPlan[]> => {
    const response = await api.get('/public/pricing');
    return response.data;
  },

  contactSupport: async (name: string, email: string, message: string) => {
    const response = await api.post('/public/contact', { name, email, message });
    return response.data;
  },
};

export default api; 