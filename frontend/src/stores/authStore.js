import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import axios from '../utils/axios';

const useAuthStore = create(
  persist(
    (set, get) => ({
      token: null,
      user: null,
      isLoading: false,
      error: null,

      setToken: (token) => set({ token }),
      setUser: (user) => set({ user }),
      setError: (error) => set({ error }),
      setLoading: (isLoading) => set({ isLoading }),

      loginUser: async (userData) => {
        set({ isLoading: true, error: null });
        try {
          const response = await axios.post('/api/auth/login', userData);
          const { access_token, user } = response.data;
          
          set({ 
            token: access_token, 
            user, 
            isLoading: false 
          });
          
          // Also update localStorage for backward compatibility
          localStorage.setItem('user', JSON.stringify(response.data));
          return response;
        } catch (error) {
          set({ 
            error: error.response?.data?.detail || 'Login failed',
            isLoading: false 
          });
          return error;
        }
      },

      registerUser: async (userData) => {
        set({ isLoading: true, error: null });
        try {
          const response = await axios.post('/api/auth/register', userData);
          set({ isLoading: false });
          return response;
        } catch (error) {
          set({ 
            error: error.response?.data?.detail || 'Registration failed',
            isLoading: false 
          });
          return error;
        }
      },

      logout: async () => {
        try {
          await axios.post('/api/auth/logout/');
        } catch (error) {
          // Continue with logout even if API call fails
        } finally {
          set({ token: null, user: null, error: null });
          localStorage.removeItem('user');
        }
        return { success: true };
      },

      clearError: () => set({ error: null }),
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({ 
        token: state.token, 
        user: state.user 
      }),
    }
  )
);

export default useAuthStore;
