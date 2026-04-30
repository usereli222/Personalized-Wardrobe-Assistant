import { api, fileUrl } from './api';

// Fetches an image from the backend (e.g. /uploads/foo.png) and returns a Blob.
async function urlToBlob(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Could not load image at ${url}`);
  return res.blob();
}

export async function generateTryOn({ bodyPhotoUrl, topImageUrl, bottomImageUrl, extraInstructions }) {
  if (!bodyPhotoUrl) throw new Error('Upload a full-body photo first.');
  if (!topImageUrl) throw new Error('Pick a top.');
  if (!bottomImageUrl) throw new Error('Pick a bottom.');

  const [body, top, bottom] = await Promise.all([
    urlToBlob(fileUrl(bodyPhotoUrl)),
    urlToBlob(fileUrl(topImageUrl)),
    urlToBlob(fileUrl(bottomImageUrl)),
  ]);

  const form = new FormData();
  form.append('body_photo', body, 'body.png');
  form.append('top', top, 'top.png');
  form.append('bottom', bottom, 'bottom.png');
  if (extraInstructions) form.append('extra_instructions', extraInstructions);

  const blob = await api.postFormBlob('/tryon/generate', form);
  return { url: URL.createObjectURL(blob), blob };
}

export async function saveTryOnOutfit({
  blob,
  topImageUrl,
  bottomImageUrl,
  bodyPhotoUrl,
  topName,
  bottomName,
  name,
}) {
  const form = new FormData();
  form.append('image', blob, 'tryon.png');
  if (topImageUrl) form.append('top_image_url', topImageUrl);
  if (bottomImageUrl) form.append('bottom_image_url', bottomImageUrl);
  if (bodyPhotoUrl) form.append('body_photo_url', bodyPhotoUrl);
  if (topName) form.append('top_name', topName);
  if (bottomName) form.append('bottom_name', bottomName);
  if (name) form.append('name', name);
  return api.postForm('/tryon/saved', form);
}

export const listSavedOutfits = () => api.get('/tryon/saved');

export const deleteSavedOutfit = (id) => api.del(`/tryon/saved/${id}`);
