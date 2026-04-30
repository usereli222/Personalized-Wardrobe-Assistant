import { api } from './api';

export const listWardrobeItems = () => api.get('/wardrobe/items');

export const uploadWardrobeItem = ({ file, name, category }) => {
  const form = new FormData();
  form.append('image', file);
  if (name) form.append('name', name);
  if (category) form.append('category', category);
  return api.postForm('/wardrobe/items', form);
};

export const deleteWardrobeItem = (id) => api.del(`/wardrobe/items/${id}`);

export const fetchSimilarItems = (id, k = 8) =>
  api.get(`/wardrobe/items/${id}/similar?k=${k}`);

export const warmModels = () =>
  api.postJson('/health/warm', {});

export const uploadWardrobeArchive = (zipFile) => {
  const form = new FormData();
  form.append('archive', zipFile);
  return api.postForm('/wardrobe/items/bulk', form);
};

export const uploadBodyPhoto = (file) => {
  const form = new FormData();
  form.append('image', file);
  return api.postForm('/wardrobe/body-photo', form);
};

export const fetchBodyPhoto = () => api.get('/wardrobe/body-photo');
