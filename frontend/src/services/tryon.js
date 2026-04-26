import { dataUrlToBlob } from './wardrobeStore';

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000/api';

export async function generateTryOn({ bodyDataUrl, topDataUrl, bottomDataUrl, extraInstructions }) {
  if (!bodyDataUrl) throw new Error('Upload a full-body photo first.');
  if (!topDataUrl) throw new Error('Pick a top.');
  if (!bottomDataUrl) throw new Error('Pick a bottom.');

  const [body, top, bottom] = await Promise.all([
    dataUrlToBlob(bodyDataUrl),
    dataUrlToBlob(topDataUrl),
    dataUrlToBlob(bottomDataUrl),
  ]);

  const form = new FormData();
  form.append('body_photo', body, 'body.png');
  form.append('top', top, 'top.png');
  form.append('bottom', bottom, 'bottom.png');
  if (extraInstructions) form.append('extra_instructions', extraInstructions);

  const res = await fetch(`${API_BASE}/tryon/generate`, {
    method: 'POST',
    body: form,
  });

  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      if (body?.detail) detail = body.detail;
    } catch {
      // body wasn't JSON
    }
    throw new Error(detail);
  }

  const blob = await res.blob();
  return URL.createObjectURL(blob);
}
