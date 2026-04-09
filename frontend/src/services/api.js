import axios from 'axios';

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000/api';

const api = axios.create({ baseURL: API_BASE });

// Users
export const createUser = (data) => api.post('/users/', data);
export const getUser = (id) => api.get(`/users/${id}`);
export const updateUser = (id, data) => api.patch(`/users/${id}`, data);

// Wardrobe
export const uploadItem = (formData) =>
  api.post('/wardrobe/items', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
export const getItems = (userId) => api.get(`/wardrobe/items?user_id=${userId}`);
export const deleteItem = (id) => api.delete(`/wardrobe/items/${id}`);

// Recommendations
export const getRecommendedColors = (userId) => api.get(`/recommendations/colors?user_id=${userId}`);
export const getOutfitRecommendation = (userId) => api.get(`/recommendations/outfit?user_id=${userId}`);

export default api;
