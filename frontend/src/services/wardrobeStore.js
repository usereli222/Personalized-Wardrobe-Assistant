const KEY_PREFIX = 'wardrobe.items.';
const BODY_PREFIX = 'wardrobe.body.';

const keyFor = (username) => `${KEY_PREFIX}${username || 'guest'}`;
const bodyKeyFor = (username) => `${BODY_PREFIX}${username || 'guest'}`;

export const listItems = (username) => {
  const raw = localStorage.getItem(keyFor(username));
  if (!raw) return [];
  try {
    return JSON.parse(raw);
  } catch {
    return [];
  }
};

const saveAll = (username, items) => {
  localStorage.setItem(keyFor(username), JSON.stringify(items));
};

export const addItem = (username, { name, category, dataUrl }) => {
  const items = listItems(username);
  const item = {
    id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    name: name || '',
    category,
    dataUrl,
    createdAt: Date.now(),
  };
  items.push(item);
  saveAll(username, items);
  return item;
};

export const deleteItem = (username, id) => {
  const items = listItems(username).filter((i) => i.id !== id);
  saveAll(username, items);
};

export const fileToDataUrl = (file) =>
  new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });

export const getBodyPhoto = (username) => {
  return localStorage.getItem(bodyKeyFor(username));
};

export const setBodyPhoto = (username, dataUrl) => {
  localStorage.setItem(bodyKeyFor(username), dataUrl);
};

export const clearBodyPhoto = (username) => {
  localStorage.removeItem(bodyKeyFor(username));
};

export const dataUrlToBlob = async (dataUrl) => {
  const res = await fetch(dataUrl);
  return res.blob();
};
