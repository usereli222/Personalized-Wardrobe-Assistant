import { api } from './api';

export const fetchOutfitSuggestions = () => api.get('/outfits/suggestions');
