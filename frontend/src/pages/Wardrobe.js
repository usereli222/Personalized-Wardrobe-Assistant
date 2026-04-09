import React, { useState, useEffect, useRef } from 'react';
import { getItems, uploadItem, deleteItem } from '../services/api';

const API_HOST = process.env.REACT_APP_API_HOST || 'http://localhost:8000';

function Wardrobe({ userId }) {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [category, setCategory] = useState('top');
  const [itemName, setItemName] = useState('');
  const fileRef = useRef();

  const fetchItems = async () => {
    try {
      const res = await getItems(userId);
      setItems(res.data);
    } catch (err) {
      console.error('Failed to fetch items:', err);
    }
    setLoading(false);
  };

  useEffect(() => { fetchItems(); }, [userId]);

  const handleUpload = async (e) => {
    e.preventDefault();
    const file = fileRef.current?.files[0];
    if (!file) return;

    setUploading(true);
    const formData = new FormData();
    formData.append('image', file);
    formData.append('user_id', userId);
    formData.append('category', category);
    if (itemName) formData.append('name', itemName);

    try {
      await uploadItem(formData);
      setItemName('');
      fileRef.current.value = '';
      fetchItems();
    } catch (err) {
      alert('Upload failed: ' + (err.response?.data?.detail || err.message));
    }
    setUploading(false);
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Delete this item?')) return;
    await deleteItem(id);
    fetchItems();
  };

  if (loading) return <div className="loading">Loading wardrobe...</div>;

  return (
    <div>
      <h1>My Wardrobe</h1>

      {/* Upload form */}
      <div className="card" style={{ marginBottom: 24 }}>
        <h2>Add Clothing Item</h2>
        <form onSubmit={handleUpload} style={{ display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'flex-end' }}>
          <div>
            <label>Name (optional)</label>
            <input value={itemName} onChange={(e) => setItemName(e.target.value)} placeholder="e.g. Blue Oxford Shirt" style={{ width: 200 }} />
          </div>
          <div>
            <label>Category</label>
            <select value={category} onChange={(e) => setCategory(e.target.value)} style={{ width: 150 }}>
              <option value="top">Top</option>
              <option value="bottom">Bottom</option>
              <option value="shoes">Shoes</option>
              <option value="outerwear">Outerwear</option>
              <option value="accessory">Accessory</option>
            </select>
          </div>
          <div>
            <label>Photo</label>
            <input type="file" ref={fileRef} accept="image/*" required />
          </div>
          <button type="submit" className="btn-primary" disabled={uploading}>
            {uploading ? 'Uploading...' : 'Upload'}
          </button>
        </form>
      </div>

      {/* Items grid */}
      {items.length === 0 ? (
        <div className="card" style={{ textAlign: 'center', padding: 40 }}>
          <p style={{ color: '#6e6e73' }}>No items yet. Upload your first clothing item above!</p>
        </div>
      ) : (
        <div className="grid">
          {items.map((item) => (
            <div key={item.id} className="item-card">
              <img src={`${API_HOST}/uploads/${item.image_path}`} alt={item.name || item.category} />
              <div className="item-info">
                <div className="item-category">{item.category}</div>
                <div style={{ fontWeight: 500 }}>{item.name || 'Unnamed'}</div>
                {item.dominant_colors && (
                  <div className="color-palette">
                    {item.dominant_colors.map((c, i) => (
                      <span
                        key={i}
                        className="color-swatch"
                        title={`H:${c.h} S:${c.s} L:${c.l}`}
                        style={{ background: `hsl(${c.h}, ${c.s}%, ${c.l}%)` }}
                      />
                    ))}
                  </div>
                )}
                <button className="btn-danger" style={{ fontSize: 12, padding: '4px 10px', marginTop: 8 }} onClick={() => handleDelete(item.id)}>
                  Delete
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default Wardrobe;
