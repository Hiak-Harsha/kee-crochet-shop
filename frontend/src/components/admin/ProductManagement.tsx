"use client";

import { useState } from "react";
import Image from "next/image";
import { Plus, Edit, Trash2, Upload, Sparkles, X, AlertCircle } from "lucide-react";
import { api, Category, Product } from "@/lib/api";

interface ProductManagementProps {
  products: Product[];
  categories: Category[];
  onRefresh: () => void;
}

export default function ProductManagement({
  products,
  categories,
  onRefresh,
}: ProductManagementProps) {
  const [showAddModal, setShowAddModal] = useState(false);
  const [editingProduct, setEditingProduct] = useState<Product | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [uploadingImage, setUploadingImage] = useState(false);
  const [aiGenerating, setAiGenerating] = useState(false);

  // Form fields
  const [title, setTitle] = useState("");
  const [slug, setSlug] = useState("");
  const [description, setDescription] = useState("");
  const [price, setPrice] = useState<number>(0);
  const [compareAtPrice, setCompareAtPrice] = useState<number | undefined>(undefined);
  const [categoryId, setCategoryId] = useState("");
  const [images, setImages] = useState<string[]>([]);
  const [stock, setStock] = useState<number>(10);
  const [isFeatured, setIsFeatured] = useState(false);
  const [variants, setVariants] = useState<Array<{ name: string; value: string; price_delta: number; stock: number }>>([]);

  const resetForm = () => {
    setTitle("");
    setSlug("");
    setDescription("");
    setPrice(0);
    setCompareAtPrice(undefined);
    setCategoryId(categories[0]?.id || "");
    setImages([]);
    setStock(10);
    setIsFeatured(false);
    setVariants([]);
    setError("");
  };

  const handleOpenCreate = () => {
    resetForm();
    setShowAddModal(true);
  };

  const handleOpenEdit = (p: Product) => {
    setEditingProduct(p);
    setTitle(p.title);
    setSlug(p.slug);
    setDescription(p.description || "");
    setPrice(p.price);
    setCompareAtPrice(p.compare_at_price || undefined);
    setCategoryId(p.category_id || "");
    setImages(p.images || []);
    setStock(p.stock);
    setIsFeatured(p.is_featured);
    setError("");
  };

  const handleImageUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files || !e.target.files[0]) return;
    const file = e.target.files[0];
    setUploadingImage(true);
    setError("");

    try {
      const res = await api.products.uploadImage(file);
      if (res && res.url) {
        setImages((prev) => [...prev, res.url]);
      }
    } catch (err: any) {
      console.error("Image upload failed:", err);
      setError(err.message || "Failed to upload image. Must be JPEG, PNG, or WebP under 5MB.");
    } finally {
      setUploadingImage(false);
    }
  };

  const handleAiDescribe = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files || !e.target.files[0]) return;
    const file = e.target.files[0];
    setAiGenerating(true);
    setError("");

    try {
      // 1. Upload the image first
      const uploadRes = await api.products.uploadImage(file);
      if (uploadRes && uploadRes.url) {
        setImages((prev) => [...prev, uploadRes.url]);
      }

      // 2. Call AI describe
      const aiData = await api.ai.describeProduct(file);
      if (aiData) {
        if (aiData.title && !title) setTitle(aiData.title);
        if (aiData.description) setDescription(aiData.description);
        if (aiData.suggested_price && (!price || price === 0)) setPrice(aiData.suggested_price);
        if (aiData.slug && !slug) setSlug(aiData.slug);
      }
    } catch (err: any) {
      console.error("AI describe failed:", err);
      setError("AI generation failed. You can still enter details manually.");
    } finally {
      setAiGenerating(false);
    }
  };

  const handleAddVariant = () => {
    setVariants((prev) => [
      ...prev,
      { name: "Color", value: "Pastel Pink", price_delta: 0, stock: 5 },
    ]);
  };

  const handleRemoveVariant = (index: number) => {
    setVariants((prev) => prev.filter((_, i) => i !== index));
  };

  const handleCreateProduct = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title || price <= 0) {
      setError("Please provide a valid product title and price");
      return;
    }

    setLoading(true);
    setError("");

    const autoSlug = slug.trim() || title.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");

    const payload = {
      title,
      slug: autoSlug,
      description,
      price: Number(price),
      compare_at_price: compareAtPrice ? Number(compareAtPrice) : null,
      category_id: categoryId || null,
      images: images.length > 0 ? images : ["/images/category_bouquets.jpg"],
      tags: [],
      colors: [],
      stock: Number(stock),
      is_featured: isFeatured,
      variants,
    };

    try {
      await api.products.create(payload);
      setShowAddModal(false);
      resetForm();
      onRefresh();
    } catch (err: any) {
      console.error("Failed to create product:", err);
      setError(err.message || "Failed to create product.");
    } finally {
      setLoading(false);
    }
  };

  const handleUpdateProduct = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingProduct) return;

    setLoading(true);
    setError("");

    const payload = {
      title,
      slug,
      description,
      price: Number(price),
      compare_at_price: compareAtPrice ? Number(compareAtPrice) : null,
      category_id: categoryId || null,
      images,
      stock: Number(stock),
      is_featured: isFeatured,
    };

    try {
      await api.products.update(editingProduct.id, payload);
      setEditingProduct(null);
      onRefresh();
    } catch (err: any) {
      console.error("Failed to update product:", err);
      setError(err.message || "Failed to update product.");
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteProduct = async (productId: string, productTitle: string) => {
    if (!confirm(`Are you sure you want to deactivate '${productTitle}'?`)) return;
    try {
      await api.products.delete(productId);
      onRefresh();
    } catch (err: any) {
      console.error("Delete product failed:", err);
      alert(err.message || "Failed to deactivate product");
    }
  };

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-black text-foreground">Catalog & Products</h2>
          <p className="text-xs text-foreground/60">Manage your crochet inventory, prices, variants, and imagery</p>
        </div>
        <button
          onClick={handleOpenCreate}
          className="bg-primary text-white text-xs font-bold px-4 py-2.5 rounded-full shadow hover:bg-primary/95 transition flex items-center gap-1.5"
        >
          <Plus className="w-4 h-4" /> Add New Creation
        </button>
      </div>

      {error && (
        <div className="bg-rose-50 border border-rose-200 text-rose-800 text-xs font-bold p-3.5 rounded-xl flex items-center gap-2">
          <AlertCircle className="w-4 h-4 text-rose-600" /> {error}
        </div>
      )}

      {/* Products Table */}
      <div className="bg-white rounded-2xl border border-secondary/40 shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-secondary/15 text-foreground/60 font-bold uppercase tracking-wider border-b border-secondary/30">
              <tr>
                <th className="p-4">Product</th>
                <th className="p-4">Category</th>
                <th className="p-4">Price (MRP)</th>
                <th className="p-4">Stock</th>
                <th className="p-4">Variants</th>
                <th className="p-4">Status</th>
                <th className="p-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-secondary/20">
              {products.length === 0 ? (
                <tr>
                  <td colSpan={7} className="p-8 text-center text-foreground/50">
                    No products found in catalog. Click "Add New Creation" above to add your first item.
                  </td>
                </tr>
              ) : (
                products.map((p) => {
                  const cat = categories.find((c) => c.id === p.category_id);
                  return (
                    <tr key={p.id} className="hover:bg-secondary/5 transition">
                      <td className="p-4 flex items-center gap-3">
                        <div className="relative w-12 h-12 rounded-lg overflow-hidden bg-secondary/20 flex-shrink-0 border border-secondary/30">
                          <Image
                            src={p.images?.[0] || "/images/category_bouquets.jpg"}
                            alt={p.title}
                            fill
                            className="object-cover"
                            sizes="48px"
                          />
                        </div>
                        <div>
                          <p className="font-bold text-foreground line-clamp-1">{p.title}</p>
                          <p className="text-[10px] text-foreground/45 font-mono">{p.slug}</p>
                        </div>
                      </td>
                      <td className="p-4 font-semibold text-foreground/75">
                        {cat?.name || "Uncategorized"}
                      </td>
                      <td className="p-4 font-extrabold text-foreground">
                        ₹{p.price}
                        {p.compare_at_price && (
                          <span className="text-[10px] line-through text-foreground/40 ml-1.5">
                            ₹{p.compare_at_price}
                          </span>
                        )}
                      </td>
                      <td className="p-4">
                        <span className={`px-2 py-0.5 rounded-full text-[10px] font-black ${
                          p.stock <= 0
                            ? "bg-rose-100 text-rose-800"
                            : p.stock < 5
                            ? "bg-amber-100 text-amber-800"
                            : "bg-emerald-100 text-emerald-800"
                        }`}>
                          {p.stock} units
                        </span>
                      </td>
                      <td className="p-4 text-foreground/70">
                        {p.variants?.length > 0 ? `${p.variants.length} SKUs` : "Standard"}
                      </td>
                      <td className="p-4">
                        <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                          p.is_active ? "bg-emerald-50 text-emerald-700 border border-emerald-200" : "bg-gray-100 text-gray-500"
                        }`}>
                          {p.is_active ? "Active" : "Inactive"}
                        </span>
                        {p.is_featured && (
                          <span className="ml-1.5 text-[9px] bg-amber-100 text-amber-800 px-1.5 py-0.5 rounded font-bold">
                            Featured
                          </span>
                        )}
                      </td>
                      <td className="p-4 text-right space-x-2">
                        <button
                          onClick={() => handleOpenEdit(p)}
                          className="p-1.5 text-foreground/50 hover:text-primary transition rounded-lg hover:bg-secondary/15"
                          title="Edit product"
                        >
                          <Edit className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => handleDeleteProduct(p.id, p.title)}
                          className="p-1.5 text-foreground/50 hover:text-rose-600 transition rounded-lg hover:bg-rose-50"
                          title="Deactivate product"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Create Product Modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4 overflow-y-auto animate-fade-in">
          <div className="bg-white rounded-2xl border border-secondary/40 shadow-2xl max-w-2xl w-full p-6 sm:p-8 space-y-6 my-8 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between pb-4 border-b border-secondary/30">
              <h3 className="text-lg font-black text-foreground">Add New Crochet Creation</h3>
              <button onClick={() => setShowAddModal(false)} className="text-foreground/40 hover:text-foreground">
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* AI Assistant Banner */}
            <div className="bg-primary/10 border border-primary/20 p-4 rounded-xl flex items-center justify-between gap-4">
              <div>
                <p className="text-xs font-bold text-foreground flex items-center gap-1.5">
                  <Sparkles className="w-4 h-4 text-primary" /> Auto-fill with AI Photo Assist
                </p>
                <p className="text-[11px] text-foreground/60">Upload an image of your crochet creation to automatically write description, title & pricing.</p>
              </div>
              <label className="bg-primary text-white text-xs font-bold px-3 py-2 rounded-xl cursor-pointer hover:bg-primary/95 transition flex items-center gap-1.5 shadow-sm">
                <Upload className="w-3.5 h-3.5" />
                {aiGenerating ? "Analyzing..." : "Pick Photo"}
                <input type="file" accept="image/*" onChange={handleAiDescribe} disabled={aiGenerating} className="hidden" />
              </label>
            </div>

            <form onSubmit={handleCreateProduct} className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-1">
                  <label className="text-xs font-bold text-foreground/75">Title *</label>
                  <input
                    type="text"
                    required
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    className="w-full p-2.5 rounded-xl border border-secondary text-xs focus:outline-none focus:ring-2 focus:ring-primary/45"
                    placeholder="e.g. Sunflower Crochet Bouquet"
                  />
                </div>

                <div className="space-y-1">
                  <label className="text-xs font-bold text-foreground/75">Slug</label>
                  <input
                    type="text"
                    value={slug}
                    onChange={(e) => setSlug(e.target.value)}
                    className="w-full p-2.5 rounded-xl border border-secondary text-xs focus:outline-none focus:ring-2 focus:ring-primary/45"
                    placeholder="auto-generated-from-title"
                  />
                </div>

                <div className="space-y-1">
                  <label className="text-xs font-bold text-foreground/75">Price (₹) *</label>
                  <input
                    type="number"
                    required
                    min="1"
                    value={price || ""}
                    onChange={(e) => setPrice(Number(e.target.value))}
                    className="w-full p-2.5 rounded-xl border border-secondary text-xs focus:outline-none focus:ring-2 focus:ring-primary/45"
                    placeholder="499"
                  />
                </div>

                <div className="space-y-1">
                  <label className="text-xs font-bold text-foreground/75">Compare at Price (₹)</label>
                  <input
                    type="number"
                    min="1"
                    value={compareAtPrice || ""}
                    onChange={(e) => setCompareAtPrice(e.target.value ? Number(e.target.value) : undefined)}
                    className="w-full p-2.5 rounded-xl border border-secondary text-xs focus:outline-none focus:ring-2 focus:ring-primary/45"
                    placeholder="699"
                  />
                </div>

                <div className="space-y-1">
                  <label className="text-xs font-bold text-foreground/75">Stock *</label>
                  <input
                    type="number"
                    required
                    min="0"
                    value={stock}
                    onChange={(e) => setStock(Number(e.target.value))}
                    className="w-full p-2.5 rounded-xl border border-secondary text-xs focus:outline-none focus:ring-2 focus:ring-primary/45"
                  />
                </div>

                <div className="space-y-1">
                  <label className="text-xs font-bold text-foreground/75">Category</label>
                  <select
                    value={categoryId}
                    onChange={(e) => setCategoryId(e.target.value)}
                    className="w-full p-2.5 rounded-xl border border-secondary text-xs focus:outline-none focus:ring-2 focus:ring-primary/45 bg-white"
                  >
                    <option value="">Select Category</option>
                    {categories.map((c) => (
                      <option key={c.id} value={c.id}>{c.name}</option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="space-y-1">
                <label className="text-xs font-bold text-foreground/75">Description</label>
                <textarea
                  rows={3}
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  className="w-full p-2.5 rounded-xl border border-secondary text-xs focus:outline-none focus:ring-2 focus:ring-primary/45"
                  placeholder="Detailed crochet specs, yarn blend, care instructions..."
                />
              </div>

              {/* Upload Images */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <label className="text-xs font-bold text-foreground/75">Images</label>
                  <label className="text-xs text-primary font-bold cursor-pointer hover:underline flex items-center gap-1">
                    <Upload className="w-3.5 h-3.5" /> Upload WebP Image
                    <input type="file" accept="image/*" onChange={handleImageUpload} disabled={uploadingImage} className="hidden" />
                  </label>
                </div>
                <div className="flex flex-wrap gap-2">
                  {images.map((img, idx) => (
                    <div key={idx} className="relative w-16 h-16 rounded-lg overflow-hidden border border-secondary/40 group">
                      <Image src={img} alt="Product image" fill className="object-cover" />
                      <button
                        type="button"
                        onClick={() => setImages((prev) => prev.filter((_, i) => i !== idx))}
                        className="absolute inset-0 bg-black/60 text-white flex items-center justify-center opacity-0 group-hover:opacity-100 transition"
                      >
                        <X className="w-4 h-4" />
                      </button>
                    </div>
                  ))}
                </div>
              </div>

              {/* Variants Section */}
              <div className="space-y-3 pt-3 border-t border-secondary/20">
                <div className="flex items-center justify-between">
                  <div>
                    <h4 className="text-xs font-bold text-foreground">Product Variants (SKUs)</h4>
                    <p className="text-[10px] text-foreground/50">Optional: Add colors or sizes with specific stock & price deltas</p>
                  </div>
                  <button
                    type="button"
                    onClick={handleAddVariant}
                    className="text-xs text-primary font-bold hover:underline flex items-center gap-1"
                  >
                    <Plus className="w-3.5 h-3.5" /> Add Variant
                  </button>
                </div>

                {variants.map((v, idx) => (
                  <div key={idx} className="grid grid-cols-4 gap-2 bg-secondary/10 p-2.5 rounded-xl items-center">
                    <input
                      type="text"
                      value={v.name}
                      onChange={(e) => {
                        const val = e.target.value;
                        setVariants((prev) => prev.map((item, i) => i === idx ? { ...item, name: val } : item));
                      }}
                      placeholder="e.g. Color"
                      className="p-1.5 text-xs rounded-lg border border-secondary/40 bg-white"
                    />
                    <input
                      type="text"
                      value={v.value}
                      onChange={(e) => {
                        const val = e.target.value;
                        setVariants((prev) => prev.map((item, i) => i === idx ? { ...item, value: val } : item));
                      }}
                      placeholder="e.g. Lavender"
                      className="p-1.5 text-xs rounded-lg border border-secondary/40 bg-white"
                    />
                    <input
                      type="number"
                      value={v.stock}
                      onChange={(e) => {
                        const val = Number(e.target.value);
                        setVariants((prev) => prev.map((item, i) => i === idx ? { ...item, stock: val } : item));
                      }}
                      placeholder="Stock"
                      className="p-1.5 text-xs rounded-lg border border-secondary/40 bg-white"
                    />
                    <div className="flex items-center gap-2">
                      <input
                        type="number"
                        value={v.price_delta}
                        onChange={(e) => {
                          const val = Number(e.target.value);
                          setVariants((prev) => prev.map((item, i) => i === idx ? { ...item, price_delta: val } : item));
                        }}
                        placeholder="±₹"
                        className="p-1.5 text-xs rounded-lg border border-secondary/40 bg-white w-full"
                      />
                      <button
                        type="button"
                        onClick={() => handleRemoveVariant(idx)}
                        className="text-rose-500 hover:text-rose-700"
                      >
                        <X className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>

              {/* Toggles */}
              <div className="flex items-center gap-6 pt-2">
                <label className="flex items-center gap-2 cursor-pointer text-xs font-semibold text-foreground">
                  <input
                    type="checkbox"
                    checked={isFeatured}
                    onChange={(e) => setIsFeatured(e.target.checked)}
                    className="w-4 h-4 rounded text-primary"
                  />
                  Featured on Homepage
                </label>
              </div>

              <div className="flex justify-end gap-3 pt-4 border-t border-secondary/30">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="px-5 py-2.5 rounded-full border border-secondary text-xs font-bold text-foreground/70 hover:bg-secondary/15 transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={loading}
                  className="px-6 py-2.5 rounded-full bg-primary text-white text-xs font-bold shadow hover:bg-primary/95 transition disabled:opacity-50"
                >
                  {loading ? "Saving..." : "Save Product"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Edit Product Modal */}
      {editingProduct && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4 overflow-y-auto animate-fade-in">
          <div className="bg-white rounded-2xl border border-secondary/40 shadow-2xl max-w-xl w-full p-6 sm:p-8 space-y-6 my-8 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between pb-4 border-b border-secondary/30">
              <h3 className="text-lg font-black text-foreground">Edit Product</h3>
              <button onClick={() => setEditingProduct(null)} className="text-foreground/40 hover:text-foreground">
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleUpdateProduct} className="space-y-4">
              <div className="space-y-1">
                <label className="text-xs font-bold text-foreground/75">Title</label>
                <input
                  type="text"
                  required
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  className="w-full p-2.5 rounded-xl border border-secondary text-xs focus:outline-none focus:ring-2 focus:ring-primary/45"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1">
                  <label className="text-xs font-bold text-foreground/75">Price (₹)</label>
                  <input
                    type="number"
                    required
                    min="1"
                    value={price}
                    onChange={(e) => setPrice(Number(e.target.value))}
                    className="w-full p-2.5 rounded-xl border border-secondary text-xs focus:outline-none focus:ring-2 focus:ring-primary/45"
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-xs font-bold text-foreground/75">Stock</label>
                  <input
                    type="number"
                    required
                    min="0"
                    value={stock}
                    onChange={(e) => setStock(Number(e.target.value))}
                    className="w-full p-2.5 rounded-xl border border-secondary text-xs focus:outline-none focus:ring-2 focus:ring-primary/45"
                  />
                </div>
              </div>

              <div className="space-y-1">
                <label className="text-xs font-bold text-foreground/75">Description</label>
                <textarea
                  rows={3}
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  className="w-full p-2.5 rounded-xl border border-secondary text-xs focus:outline-none focus:ring-2 focus:ring-primary/45"
                />
              </div>

              <div className="flex items-center gap-6 pt-2">
                <label className="flex items-center gap-2 cursor-pointer text-xs font-semibold text-foreground">
                  <input
                    type="checkbox"
                    checked={isFeatured}
                    onChange={(e) => setIsFeatured(e.target.checked)}
                    className="w-4 h-4 rounded text-primary"
                  />
                  Featured Product
                </label>
              </div>

              <div className="flex justify-end gap-3 pt-4 border-t border-secondary/30">
                <button
                  type="button"
                  onClick={() => setEditingProduct(null)}
                  className="px-5 py-2.5 rounded-full border border-secondary text-xs font-bold text-foreground/70 hover:bg-secondary/15 transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={loading}
                  className="px-6 py-2.5 rounded-full bg-primary text-white text-xs font-bold shadow hover:bg-primary/95 transition disabled:opacity-50"
                >
                  {loading ? "Updating..." : "Update Product"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
