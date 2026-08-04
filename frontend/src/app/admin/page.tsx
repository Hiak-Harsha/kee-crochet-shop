"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Sparkles, LayoutDashboard, Plus, Eye, BarChart, ShoppingCart, RefreshCw, Upload, Instagram, Check, Copy, AlertCircle } from "lucide-react";
import Navbar from "@/components/Navbar";
import { api } from "@/lib/api";

export default function AdminPage() {
  const router = useRouter();
  const [isAdminVerified, setIsAdminVerified] = useState(false);
  const [activeTab, setActiveTab] = useState<"analytics" | "products" | "orders" | "social">("analytics");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // Admin Data lists
  const [products, setProducts] = useState<any[]>([]);
  const [orders, setOrders] = useState<any[]>([]);
  const [stats, setStats] = useState<any>({ total_sales: 0, total_orders: 0, average_order_value: 0 });
  const [categories, setCategories] = useState<any[]>([]);

  // Product Create Form States
  const [newTitle, setNewTitle] = useState("");
  const [newPrice, setNewPrice] = useState(0);
  const [newSlug, setNewSlug] = useState("");
  const [newDesc, setNewDesc] = useState("");
  const [newTags, setNewTags] = useState<string[]>([]);
  const [newColors, setNewColors] = useState<string[]>([]);
  const [newStock, setNewStock] = useState(10);
  const [newCategoryId, setNewCategoryId] = useState("");
  const [productImageUrl, setProductImageUrl] = useState("");
  const [showAddForm, setShowAddForm] = useState(false);

  // Category Create States
  const [showCategoryForm, setShowCategoryForm] = useState(false);
  const [catName, setCatName] = useState("");
  const [catSlug, setCatSlug] = useState("");
  const [catDesc, setCatDesc] = useState("");
  
  // AI Assist States
  const [aiProductFile, setAiProductFile] = useState<File | null>(null);
  const [aiProductLoading, setAiProductLoading] = useState(false);

  // Editing Product Modal States
  const [editingProduct, setEditingProduct] = useState<any>(null);
  const [editTitle, setEditTitle] = useState("");
  const [editPrice, setEditPrice] = useState(0);
  const [editSlug, setEditSlug] = useState("");
  const [editDesc, setEditDesc] = useState("");
  const [editStock, setEditStock] = useState(0);
  const [editCategoryId, setEditCategoryId] = useState("");
  const [editImageUrl, setEditImageUrl] = useState("");
  const [editIsActive, setEditIsActive] = useState(true);
  const [editIsFeatured, setEditIsFeatured] = useState(false);

  // AI Instagram Planner States
  const [selectedProductForCaption, setSelectedProductForCaption] = useState("");
  const [captionStyle, setCaptionStyle] = useState("trendy");
  const [generatedCaption, setGeneratedCaption] = useState<any>(null);
  const [captionLoading, setCaptionLoading] = useState(false);
  const [copied, setCopied] = useState(false);

  // Client-side route guard: verify JWT role claim
  useEffect(() => {
    const checkAdminAuth = () => {
      const token = localStorage.getItem("access_token");
      if (!token) {
        router.push("/dashboard?tab=auth");
        return;
      }
      try {
        const parts = token.split(".");
        if (parts.length !== 3) {
          throw new Error("Invalid JWT token structure");
        }
        const payload = JSON.parse(atob(parts[1]));
        if (payload.role !== "admin") {
          router.push("/dashboard?tab=auth");
          return;
        }
        setIsAdminVerified(true);
        loadAdminData();
      } catch (err) {
        console.error("Token parsing error during admin guard check:", err);
        router.push("/dashboard?tab=auth");
      }
    };
    checkAdminAuth();
  }, []);

  const loadAdminData = async () => {
    setLoading(true);
    setError("");
    try {
      const prods = await api.products.list();
      setProducts(prods || []);
      
      const ords = await api.orders.adminListAll();
      setOrders(ords || []);

      const st = await api.orders.adminGetStats();
      setStats(st || { total_sales: 0, total_orders: 0, average_order_value: 0 });

      const cats = await api.products.listCategories();
      setCategories(cats || []);
    } catch (e: any) {
      console.error("Failed to load admin data from backend", e);
      setError(e.message || "Failed to load admin dashboard data. Please verify your connection.");
    }
    setLoading(false);
  };

  // Update order fulfillment status
  const handleUpdateOrderStatus = async (orderId: string, newStatus: string) => {
    setError("");
    try {
      await api.orders.adminUpdateStatus(orderId, newStatus);
      await loadAdminData();
    } catch (e: any) {
      console.error("Backend order status update failed", e);
      setError(e.message || "Failed to update order status.");
    }
  };

  // AI Product Description Generator & Automatic Photo Upload
  const handleAiProductDescribe = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setAiProductFile(file);
      setAiProductLoading(true);
      setError("");

      try {
        // Upload photo to backend uploads
        const uploadRes = await api.products.uploadImage(file);
        setProductImageUrl(uploadRes.url);

        // Describe via Gemini
        const desc = await api.ai.describeProduct(file);
        setNewTitle(desc.title);
        setNewDesc(desc.description);
        setNewTags(desc.tags);
        setNewSlug(desc.title.toLowerCase().replace(/ /g, "-").replace(/[^\w-]+/g, ""));
      } catch (err: any) {
        console.error("AI description generator failed", err);
        setError("AI description generator failed. Please fill fields manually.");
      }
      setAiProductLoading(false);
    }
  };

  // Manual Product Image Upload Handler
  const handleManualImageUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setLoading(true);
      setError("");
      try {
        const uploadRes = await api.products.uploadImage(file);
        setProductImageUrl(uploadRes.url);
      } catch (err: any) {
        console.error("Manual image upload failed", err);
        setError("Failed to upload image. Please try again (max 5MB).");
      }
      setLoading(false);
    }
  };

  // Manual Edit Product Image Upload Handler
  const handleEditImageUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setLoading(true);
      setError("");
      try {
        const uploadRes = await api.products.uploadImage(file);
        setEditImageUrl(uploadRes.url);
      } catch (err: any) {
        console.error("Edit image upload failed", err);
        setError("Failed to upload image. Please try again (max 5MB).");
      }
      setLoading(false);
    }
  };

  // Create New Product Category
  const handleCreateCategory = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!catName || !catSlug) return;
    setLoading(true);
    setError("");
    try {
      await api.products.createCategory({ name: catName, slug: catSlug, description: catDesc || null });
      await loadAdminData();
      setShowCategoryForm(false);
      setCatName("");
      setCatSlug("");
      setCatDesc("");
    } catch (err: any) {
      console.error("Category creation failed", err);
      setError(err.message || "Failed to create category.");
    }
    setLoading(false);
  };

  // Submit Product Creation
  const handleCreateProduct = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTitle || !newSlug || newPrice <= 0) return;
    setError("");
    setLoading(true);

    const payload = {
      title: newTitle,
      slug: newSlug,
      description: newDesc,
      price: newPrice,
      stock: newStock,
      tags: newTags,
      colors: newColors.length > 0 ? newColors : ["Default Pastel"],
      images: productImageUrl ? [productImageUrl] : ["/images/hero.jpg"],
      category_id: newCategoryId || null,
      variants: []
    };

    try {
      await api.products.create(payload);
      await loadAdminData();
      setShowAddForm(false);
      
      // Reset Form Fields
      setNewTitle("");
      setNewPrice(0);
      setNewSlug("");
      setNewDesc("");
      setNewTags([]);
      setNewColors([]);
      setNewCategoryId("");
      setProductImageUrl("");
    } catch (e: any) {
      console.error("Backend product creation failed", e);
      setError(e.message || "Failed to create product in backend database.");
    }
    setLoading(false);
  };

  // Start editing a product
  const startEditProduct = (p: any) => {
    setEditingProduct(p);
    setEditTitle(p.title);
    setEditPrice(p.price);
    setEditSlug(p.slug);
    setEditDesc(p.description || "");
    setEditStock(p.stock);
    setEditCategoryId(p.category_id || "");
    setEditImageUrl(p.images?.[0] || "");
    setEditIsActive(p.is_active);
    setEditIsFeatured(p.is_featured);
  };

  // Submit Product Update
  const handleUpdateProduct = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingProduct) return;
    setLoading(true);
    setError("");
    try {
      const payload = {
        title: editTitle,
        slug: editSlug,
        description: editDesc,
        price: editPrice,
        stock: editStock,
        category_id: editCategoryId || null,
        images: editImageUrl ? [editImageUrl] : [],
        is_active: editIsActive,
        is_featured: editIsFeatured
      };
      await api.products.update(editingProduct.id, payload);
      await loadAdminData();
      setEditingProduct(null);
    } catch (err: any) {
      console.error("Failed to update product", err);
      setError(err.message || "Failed to update product.");
    }
    setLoading(false);
  };

  // Delete product (Soft-delete)
  const handleDeleteProduct = async (productId: string) => {
    if (!confirm("Are you sure you want to delete this product? It will be soft-deleted and removed from the active catalog.")) return;
    setLoading(true);
    setError("");
    try {
      await api.products.delete(productId);
      await loadAdminData();
    } catch (err: any) {
      console.error("Failed to delete product", err);
      setError(err.message || "Failed to delete product.");
    }
    setLoading(false);
  };

  // AI Instagram Caption Generator
  const handleGenerateCaption = async () => {
    if (!selectedProductForCaption) return;
    setCaptionLoading(true);
    setGeneratedCaption(null);
    setError("");

    try {
      const cap = await api.ai.instagramCaption(selectedProductForCaption, captionStyle);
      setGeneratedCaption(cap);
    } catch (e: any) {
      console.error("AI Caption failed", e);
      setError("AI Instagram caption generator failed.");
    }
    setCaptionLoading(false);
  };

  const copyToClipboard = () => {
    if (!generatedCaption) return;
    const fullText = `${generatedCaption.caption}\n\n${generatedCaption.hashtags.join(" ")}`;
    navigator.clipboard.writeText(fullText);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (!isAdminVerified) {
    return (
      <div className="flex-1 flex flex-col min-h-screen">
        <Navbar />
        <main className="max-w-7xl mx-auto w-full px-4 sm:px-6 lg:px-8 py-20 flex-1 flex flex-col items-center justify-center">
          <RefreshCw className="w-10 h-10 text-primary animate-spin mb-4" />
          <p className="text-foreground/70 font-semibold">Verifying administrative credentials...</p>
        </main>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col min-h-screen">
      <Navbar />

      <main className="max-w-7xl mx-auto w-full px-4 sm:px-6 lg:px-8 py-10 flex-1">
        {error && (
          <div className="mb-6 bg-rose-50 border border-rose-200 text-rose-800 text-sm font-bold p-4 rounded-xl flex items-center gap-2">
            <AlertCircle className="w-5 h-5 text-rose-600 flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}
        <div className="flex justify-between items-center pb-6 border-b border-secondary/35 mb-8">
          <div>
            <h1 className="text-3xl font-extrabold text-foreground">Admin Console</h1>
            <p className="text-xs sm:text-sm text-foreground/75">Manage orders, catalog, inventory, and social posting schedules.</p>
          </div>
          <button onClick={loadAdminData} className="p-2 border border-secondary rounded-full hover:bg-secondary/10">
            <RefreshCw className="w-5 h-5 text-foreground/80" />
          </button>
        </div>

        {/* Tab switch navigation */}
        <div className="flex space-x-6 border-b border-secondary/20 mb-8 overflow-x-auto pb-1.5">
          <button
            onClick={() => setActiveTab("analytics")}
            className={`pb-3 font-bold text-sm transition ${activeTab === "analytics" ? "text-primary border-b-2 border-primary" : "text-foreground/60 hover:text-primary"}`}
          >
            Analytics Overview
          </button>
          <button
            onClick={() => setActiveTab("products")}
            className={`pb-3 font-bold text-sm transition ${activeTab === "products" ? "text-primary border-b-2 border-primary" : "text-foreground/60 hover:text-primary"}`}
          >
            Product CRUD
          </button>
          <button
            onClick={() => setActiveTab("orders")}
            className={`pb-3 font-bold text-sm transition ${activeTab === "orders" ? "text-primary border-b-2 border-primary" : "text-foreground/60 hover:text-primary"}`}
          >
            Order Processing
          </button>
          <button
            onClick={() => setActiveTab("social")}
            className={`pb-3 font-bold text-sm transition ${activeTab === "social" ? "text-primary border-b-2 border-primary" : "text-foreground/60 hover:text-primary"}`}
          >
            Instagram Scheduler
          </button>
        </div>

        {/* Tab 1: Analytics Dashboard */}
        {activeTab === "analytics" && (
          <div className="space-y-8">
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
              <div className="bg-white p-6 rounded-cozy border border-secondary/50 shadow-sm flex items-center justify-between">
                <div>
                  <p className="text-xs text-foreground/60 font-bold uppercase tracking-wider">Total Sales (INR)</p>
                  <p className="text-2xl font-black text-foreground mt-1">₹{stats.total_sales.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</p>
                </div>
                <BarChart className="w-8 h-8 text-primary/45" />
              </div>
              <div className="bg-white p-6 rounded-cozy border border-secondary/50 shadow-sm flex items-center justify-between">
                <div>
                  <p className="text-xs text-foreground/60 font-bold uppercase tracking-wider">Total Orders</p>
                  <p className="text-2xl font-black text-foreground mt-1">{stats.total_orders}</p>
                </div>
                <ShoppingCart className="w-8 h-8 text-primary/45" />
              </div>
              <div className="bg-white p-6 rounded-cozy border border-secondary/50 shadow-sm flex items-center justify-between">
                <div>
                  <p className="text-xs text-foreground/60 font-bold uppercase tracking-wider">Low Stock Items</p>
                  <p className="text-2xl font-black text-rose-500 mt-1">
                    {products.filter((p) => p.stock <= 5).length}
                  </p>
                </div>
                <Plus className="w-8 h-8 text-rose-500/40 rotate-45" />
              </div>
              <div className="bg-white p-6 rounded-cozy border border-secondary/50 shadow-sm flex items-center justify-between">
                <div>
                  <p className="text-xs text-foreground/60 font-bold uppercase tracking-wider">Average Order</p>
                  <p className="text-2xl font-black text-foreground mt-1">₹{stats.average_order_value.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</p>
                </div>
                <Eye className="w-8 h-8 text-primary/45" />
              </div>
            </div>
            
            {/* Stock warnings list */}
            <div className="bg-white p-6 rounded-cozy border border-secondary/50 shadow-sm space-y-4">
              <h3 className="font-extrabold text-base text-foreground">Inventory Watchlist</h3>
              <div className="space-y-3.5">
                {products.filter((p) => p.stock <= 5).map((p) => (
                  <div key={p.id} className="flex justify-between items-center text-xs sm:text-sm border-b border-secondary/20 pb-3">
                    <span className="font-bold text-foreground">{p.title}</span>
                    <span className={`px-3 py-1 rounded-full text-xs font-bold ${p.stock === 0 ? "bg-rose-100 text-rose-800" : "bg-yellow-100 text-yellow-800"}`}>
                      {p.stock === 0 ? "Out of Stock" : `Low: ${p.stock} left`}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Tab 2: Product CRUD Panel */}
        {activeTab === "products" && (
          <div className="space-y-8">
            <div className="flex justify-between items-center flex-wrap gap-4">
              <h2 className="text-xl font-extrabold text-foreground">Shop Catalog CRUD</h2>
              <div className="flex gap-3">
                <button
                  onClick={() => setShowCategoryForm(!showCategoryForm)}
                  className="bg-secondary/40 text-foreground hover:bg-secondary/60 px-5 py-2.5 rounded-full font-bold text-xs shadow flex items-center gap-1 transition"
                >
                  <Plus className="w-4 h-4" /> Create Category
                </button>
                <button
                  onClick={() => setShowAddForm(!showAddForm)}
                  className="bg-primary text-white hover:bg-primary/95 px-5 py-2.5 rounded-full font-bold text-xs shadow flex items-center gap-1 transition"
                >
                  <Plus className="w-4 h-4" /> Add Product
                </button>
              </div>
            </div>

            {/* Create Category Form */}
            {showCategoryForm && (
              <form onSubmit={handleCreateCategory} className="bg-white p-6 sm:p-8 rounded-cozy border border-secondary/50 shadow-md space-y-6">
                <div className="flex justify-between items-center border-b border-secondary/30 pb-4">
                  <h3 className="font-extrabold text-base text-foreground">Create New Product Category</h3>
                  <button type="button" onClick={() => setShowCategoryForm(false)} className="text-xs text-foreground/50 hover:underline">
                    Cancel
                  </button>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
                  <div className="space-y-1.5">
                    <label className="text-xs font-bold text-foreground/75">Category Name *</label>
                    <input
                      type="text"
                      required
                      value={catName}
                      onChange={(e) => {
                        setCatName(e.target.value);
                        setCatSlug(e.target.value.toLowerCase().replace(/ /g, "-").replace(/[^\w-]+/g, ""));
                      }}
                      className="w-full p-3 rounded-xl border border-secondary bg-white focus:outline-none focus:ring-2 focus:ring-primary/45 text-sm"
                      placeholder="e.g. Bouquets"
                    />
                  </div>
                  <div className="space-y-1.5">
                    <label className="text-xs font-bold text-foreground/75">Slug Identifier *</label>
                    <input
                      type="text"
                      required
                      value={catSlug}
                      onChange={(e) => setCatSlug(e.target.value)}
                      className="w-full p-3 rounded-xl border border-secondary bg-white focus:outline-none focus:ring-2 focus:ring-primary/45 text-sm font-mono"
                    />
                  </div>
                  <div className="sm:col-span-2 space-y-1.5">
                    <label className="text-xs font-bold text-foreground/75">Description</label>
                    <textarea
                      rows={2}
                      value={catDesc}
                      onChange={(e) => setCatDesc(e.target.value)}
                      className="w-full p-3 rounded-xl border border-secondary bg-white focus:outline-none focus:ring-2 focus:ring-primary/45 text-sm"
                    />
                  </div>
                </div>
                <button
                  type="submit"
                  className="w-full bg-primary text-white hover:bg-primary/95 py-3 rounded-full font-bold shadow transition"
                >
                  Create Category
                </button>
              </form>
            )}

            {/* AI assisted adding form */}
            {showAddForm && (
              <form onSubmit={handleCreateProduct} className="bg-white p-6 sm:p-8 rounded-cozy border border-primary/20 shadow-lg space-y-6">
                <div className="flex justify-between items-center border-b border-secondary/30 pb-4">
                  <h3 className="font-extrabold text-base text-foreground flex items-center gap-1.5">
                    <Sparkles className="w-5 h-5 text-primary animate-pulse" /> Add Product via AI Assist
                  </h3>
                  <button type="button" onClick={() => setShowAddForm(false)} className="text-xs text-foreground/50 hover:underline">
                    Cancel
                  </button>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {/* AI Image Upload Panel */}
                  <div className="space-y-3">
                    <span className="text-xs font-bold text-foreground/75 block">AI Assist: Upload Product Photo</span>
                    <div className="relative border-2 border-dashed border-primary/40 hover:border-primary p-6 rounded-xl flex flex-col items-center justify-center bg-primary/5 transition cursor-pointer">
                      {aiProductLoading ? (
                        <div className="flex flex-col items-center py-2 text-primary">
                          <div className="w-8 h-8 border-4 border-primary border-t-transparent rounded-full animate-spin mb-2"></div>
                          <span className="text-xs font-bold">Gemini is analyzing & uploading...</span>
                        </div>
                      ) : (
                        <div className="flex flex-col items-center text-primary/70 text-center">
                          <Upload className="w-8 h-8 mb-2" />
                          <span className="text-xs font-bold">Upload image to Auto-Generate details</span>
                        </div>
                      )}
                      <input
                        type="file"
                        accept="image/*"
                        onChange={handleAiProductDescribe}
                        className="absolute inset-0 opacity-0 cursor-pointer"
                      />
                    </div>
                  </div>

                  {/* Manual/Direct Image Upload Panel */}
                  <div className="space-y-3">
                    <span className="text-xs font-bold text-foreground/75 block">Or: Direct Image Upload (No AI)</span>
                    <div className="relative border-2 border-dashed border-secondary hover:border-foreground/50 p-6 rounded-xl flex flex-col items-center justify-center bg-secondary/10 transition cursor-pointer">
                      <div className="flex flex-col items-center text-foreground/60 text-center">
                        <Upload className="w-8 h-8 mb-2" />
                        <span className="text-xs font-bold">Upload product photo directly</span>
                        {productImageUrl && <span className="text-[10px] text-emerald-600 font-bold mt-1">Uploaded! {productImageUrl.split("/").pop()}</span>}
                      </div>
                      <input
                        type="file"
                        accept="image/*"
                        onChange={handleManualImageUpload}
                        className="absolute inset-0 opacity-0 cursor-pointer"
                      />
                    </div>
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 pt-4 border-t border-secondary/20">
                  <div className="space-y-1.5">
                    <label className="text-xs font-bold text-foreground/75">Product Title *</label>
                    <input
                      type="text"
                      required
                      value={newTitle}
                      onChange={(e) => {
                        setNewTitle(e.target.value);
                        setNewSlug(e.target.value.toLowerCase().replace(/ /g, "-").replace(/[^\w-]+/g, ""));
                      }}
                      className="w-full p-3 rounded-xl border border-secondary bg-white focus:outline-none focus:ring-2 focus:ring-primary/45 text-sm"
                    />
                  </div>
                  
                  <div className="space-y-1.5">
                    <label className="text-xs font-bold text-foreground/75">Product Price (INR) *</label>
                    <input
                      type="number"
                      required
                      value={newPrice}
                      onChange={(e) => setNewPrice(parseFloat(e.target.value))}
                      className="w-full p-3 rounded-xl border border-secondary bg-white focus:outline-none focus:ring-2 focus:ring-primary/45 text-sm"
                    />
                  </div>

                  <div className="space-y-1.5">
                    <label className="text-xs font-bold text-foreground/75">Slug Identifier *</label>
                    <input
                      type="text"
                      required
                      value={newSlug}
                      onChange={(e) => setNewSlug(e.target.value)}
                      className="w-full p-3 rounded-xl border border-secondary bg-white focus:outline-none focus:ring-2 focus:ring-primary/45 text-sm font-mono"
                    />
                  </div>

                  <div className="space-y-1.5">
                    <label className="text-xs font-bold text-foreground/75">Initial Inventory Stock *</label>
                    <input
                      type="number"
                      required
                      value={newStock}
                      onChange={(e) => setNewStock(parseInt(e.target.value, 10))}
                      className="w-full p-3 rounded-xl border border-secondary bg-white focus:outline-none focus:ring-2 focus:ring-primary/45 text-sm"
                    />
                  </div>

                  <div className="space-y-1.5">
                    <label className="text-xs font-bold text-foreground/75">Category Assignment</label>
                    <select
                      value={newCategoryId}
                      onChange={(e) => setNewCategoryId(e.target.value)}
                      className="w-full bg-white border border-secondary rounded-xl p-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary/45 cursor-pointer"
                    >
                      <option value="">-- Choose Category --</option>
                      {categories.map((c) => (
                        <option key={c.id} value={c.id}>{c.name}</option>
                      ))}
                    </select>
                  </div>

                  <div className="space-y-1.5">
                    <label className="text-xs font-bold text-foreground/75">Manual Image URL Path (Optional)</label>
                    <input
                      type="text"
                      value={productImageUrl}
                      onChange={(e) => setProductImageUrl(e.target.value)}
                      placeholder="e.g. /images/hero.jpg"
                      className="w-full p-3 rounded-xl border border-secondary bg-white focus:outline-none focus:ring-2 focus:ring-primary/45 text-sm"
                    />
                  </div>

                  <div className="sm:col-span-2 space-y-1.5">
                    <label className="text-xs font-bold text-foreground/75">Description</label>
                    <textarea
                      rows={3}
                      value={newDesc}
                      onChange={(e) => setNewDesc(e.target.value)}
                      className="w-full p-3 rounded-xl border border-secondary bg-white focus:outline-none focus:ring-2 focus:ring-primary/45 text-sm"
                    />
                  </div>
                </div>

                <button
                  type="submit"
                  className="w-full bg-primary text-white hover:bg-primary/95 py-3 rounded-full font-bold shadow transition"
                >
                  Create Product Listing
                </button>
              </form>
            )}

            {/* Products List Table */}
            <div className="bg-white rounded-cozy border border-secondary/50 overflow-hidden shadow-sm">
              <table className="w-full text-left border-collapse text-xs sm:text-sm">
                <thead>
                  <tr className="bg-secondary/20 text-foreground/70 uppercase tracking-wider text-[10px] font-bold border-b border-secondary/30">
                    <th className="p-4">Title</th>
                    <th className="p-4">Price</th>
                    <th className="p-4">Stock</th>
                    <th className="p-4">Category</th>
                    <th className="p-4">Status</th>
                    <th className="p-4">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {products.map((p) => (
                    <tr key={p.id} className="border-b border-secondary/15 hover:bg-secondary/5 transition">
                      <td className="p-4 font-bold text-foreground">
                        <div className="flex items-center gap-2">
                          {p.images?.[0] && (
                            <img src={p.images[0].startsWith("/") ? `${api.products.listCategories.toString().includes("http") ? "https://kee-crochet-api.onrender.com" : ""}${p.images[0]}` : p.images[0]} alt={p.title} className="w-8 h-8 object-cover rounded-md border" />
                          )}
                          <span>{p.title}</span>
                        </div>
                      </td>
                      <td className="p-4">₹{p.price}</td>
                      <td className="p-4">
                        <span className={`px-2 py-0.5 rounded-full font-bold text-[10px] ${p.stock <= 5 ? "bg-rose-100 text-rose-800" : "bg-emerald-100 text-emerald-800"}`}>
                          {p.stock} in stock
                        </span>
                      </td>
                      <td className="p-4 text-foreground/60 font-medium">
                        {categories.find((c) => c.id === p.category_id)?.name || "Uncategorized"}
                      </td>
                      <td className="p-4">
                        <span className={`px-2 py-0.5 rounded-full font-bold text-[10px] ${p.is_active ? "bg-emerald-100 text-emerald-800" : "bg-rose-100 text-rose-800"}`}>
                          {p.is_active ? "Active" : "Inactive"}
                        </span>
                      </td>
                      <td className="p-4">
                        <div className="flex items-center gap-2">
                          <button
                            onClick={() => startEditProduct(p)}
                            className="bg-primary/10 hover:bg-primary/20 text-primary px-3 py-1.5 rounded-full font-bold text-[10px] transition"
                          >
                            Edit
                          </button>
                          <button
                            onClick={() => handleDeleteProduct(p.id)}
                            className="bg-rose-100 hover:bg-rose-200 text-rose-700 px-3 py-1.5 rounded-full font-bold text-[10px] transition"
                          >
                            Delete
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Edit Product Modal */}
            {editingProduct && (
              <div className="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm flex items-center justify-center p-4">
                <form onSubmit={handleUpdateProduct} className="bg-white rounded-cozy border border-secondary p-6 sm:p-8 max-w-lg w-full max-h-[90vh] overflow-y-auto space-y-6 shadow-2xl">
                  <div className="flex justify-between items-center border-b border-secondary/35 pb-4">
                    <h3 className="font-extrabold text-base text-foreground">Edit Product Details</h3>
                    <button type="button" onClick={() => setEditingProduct(null)} className="text-xs text-foreground/50 hover:underline">
                      Close
                    </button>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
                    <div className="space-y-1.5">
                      <label className="text-xs font-bold text-foreground/75">Product Title *</label>
                      <input
                        type="text"
                        required
                        value={editTitle}
                        onChange={(e) => {
                          setEditTitle(e.target.value);
                          setEditSlug(e.target.value.toLowerCase().replace(/ /g, "-").replace(/[^\w-]+/g, ""));
                        }}
                        className="w-full p-3 rounded-xl border border-secondary bg-white focus:outline-none focus:ring-2 focus:ring-primary/45 text-sm"
                      />
                    </div>

                    <div className="space-y-1.5">
                      <label className="text-xs font-bold text-foreground/75">Product Price (INR) *</label>
                      <input
                        type="number"
                        required
                        value={editPrice}
                        onChange={(e) => setEditPrice(parseFloat(e.target.value))}
                        className="w-full p-3 rounded-xl border border-secondary bg-white focus:outline-none focus:ring-2 focus:ring-primary/45 text-sm"
                      />
                    </div>

                    <div className="space-y-1.5">
                      <label className="text-xs font-bold text-foreground/75">Slug Identifier *</label>
                      <input
                        type="text"
                        required
                        value={editSlug}
                        onChange={(e) => setEditSlug(e.target.value)}
                        className="w-full p-3 rounded-xl border border-secondary bg-white focus:outline-none focus:ring-2 focus:ring-primary/45 text-sm font-mono"
                      />
                    </div>

                    <div className="space-y-1.5">
                      <label className="text-xs font-bold text-foreground/75">Inventory Stock *</label>
                      <input
                        type="number"
                        required
                        value={editStock}
                        onChange={(e) => setEditStock(parseInt(e.target.value, 10))}
                        className="w-full p-3 rounded-xl border border-secondary bg-white focus:outline-none focus:ring-2 focus:ring-primary/45 text-sm"
                      />
                    </div>

                    <div className="space-y-1.5">
                      <label className="text-xs font-bold text-foreground/75">Category Assignment</label>
                      <select
                        value={editCategoryId}
                        onChange={(e) => setEditCategoryId(e.target.value)}
                        className="w-full bg-white border border-secondary rounded-xl p-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary/45 cursor-pointer"
                      >
                        <option value="">-- Choose Category --</option>
                        {categories.map((c) => (
                          <option key={c.id} value={c.id}>{c.name}</option>
                        ))}
                      </select>
                    </div>

                    <div className="space-y-1.5">
                      <label className="text-xs font-bold text-foreground/75">Image Upload</label>
                      <input
                        type="file"
                        accept="image/*"
                        onChange={handleEditImageUpload}
                        className="w-full p-2 border border-secondary rounded-xl text-xs"
                      />
                    </div>

                    <div className="sm:col-span-2 space-y-1.5">
                      <label className="text-xs font-bold text-foreground/75">Image URL Path (Saved)</label>
                      <input
                        type="text"
                        value={editImageUrl}
                        onChange={(e) => setEditImageUrl(e.target.value)}
                        className="w-full p-3 rounded-xl border border-secondary bg-white focus:outline-none focus:ring-2 focus:ring-primary/45 text-sm"
                      />
                    </div>

                    <div className="sm:col-span-2 flex gap-6">
                      <label className="flex items-center gap-2 text-xs font-bold text-foreground/75 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={editIsActive}
                          onChange={(e) => setEditIsActive(e.target.checked)}
                          className="w-4 h-4 text-primary focus:ring-primary border-secondary rounded"
                        />
                        Is Product Active?
                      </label>
                      <label className="flex items-center gap-2 text-xs font-bold text-foreground/75 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={editIsFeatured}
                          onChange={(e) => setEditIsFeatured(e.target.checked)}
                          className="w-4 h-4 text-primary focus:ring-primary border-secondary rounded"
                        />
                        Is Featured Product?
                      </label>
                    </div>

                    <div className="sm:col-span-2 space-y-1.5">
                      <label className="text-xs font-bold text-foreground/75">Description</label>
                      <textarea
                        rows={3}
                        value={editDesc}
                        onChange={(e) => setEditDesc(e.target.value)}
                        className="w-full p-3 rounded-xl border border-secondary bg-white focus:outline-none focus:ring-2 focus:ring-primary/45 text-sm"
                      />
                    </div>
                  </div>

                  <div className="flex gap-4">
                    <button
                      type="button"
                      onClick={() => setEditingProduct(null)}
                      className="w-1/2 border border-secondary hover:bg-secondary/15 py-3 rounded-full font-bold text-xs transition"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      className="w-1/2 bg-primary text-white hover:bg-primary/95 py-3 rounded-full font-bold text-xs shadow transition"
                    >
                      Save Changes
                    </button>
                  </div>
                </form>
              </div>
            )}
          </div>
        )}

        {/* Tab 3: Order Processing Pipeline */}
        {activeTab === "orders" && (
          <div className="bg-white p-6 rounded-cozy border border-secondary/50 shadow-sm space-y-6">
            <h2 className="text-xl font-extrabold text-foreground border-b border-secondary/30 pb-4">Pending Orders Pipeline</h2>
            
            <div className="space-y-6">
              {orders.map((o) => (
                <div key={o.id} className="border border-secondary/50 p-6 rounded-2xl bg-yarn-cream/5 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-6">
                  <div className="space-y-1.5">
                    <div className="flex items-center space-x-3">
                      <span className="font-extrabold text-foreground text-sm">{o.order_number}</span>
                      <span className={`font-bold px-2.5 py-0.5 rounded-full text-[10px] uppercase tracking-wider ${o.status === "completed" ? "bg-emerald-100 text-emerald-800" : o.status === "shipped" ? "bg-blue-100 text-blue-800" : "bg-yellow-100 text-yellow-800"}`}>
                        {o.status}
                      </span>
                    </div>
                    <p className="text-xs text-foreground/60">Customer: {o.shipping_address?.full_name} • Phone: {o.shipping_address?.phone}</p>
                    <p className="text-xs font-black text-primary">Order Total: ₹{o.total}</p>
                  </div>

                  {/* Status Dropdown */}
                  <div className="space-y-1">
                    <label className="text-[10px] font-bold text-foreground/50 uppercase tracking-wider block">Update Status</label>
                    <select
                      value={o.status}
                      onChange={(e) => handleUpdateOrderStatus(o.id, e.target.value)}
                      className="bg-white border border-secondary/80 rounded-xl p-2.5 text-xs font-bold text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40 cursor-pointer"
                    >
                      <option value="pending_payment">Pending Payment</option>
                      <option value="processing">Processing</option>
                      <option value="packed">Packed</option>
                      <option value="shipped">Shipped</option>
                      <option value="completed">Completed</option>
                      <option value="cancelled">Cancelled</option>
                    </select>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Tab 4: Instagram Caption Generator */}
        {activeTab === "social" && (
          <div className="max-w-3xl mx-auto grid grid-cols-1 md:grid-cols-2 gap-8">
            <div className="bg-white p-6 rounded-cozy border border-secondary/50 shadow-sm space-y-6">
              <h3 className="font-extrabold text-base text-foreground pb-3 border-b border-secondary/30">AI Instagram Caption Generator</h3>
              
              <div className="space-y-4">
                <div className="space-y-1.5">
                  <label className="text-xs font-bold text-foreground/75">Select Product Catalog Item</label>
                  <select
                    value={selectedProductForCaption}
                    onChange={(e) => setSelectedProductForCaption(e.target.value)}
                    className="w-full bg-white border border-secondary rounded-xl p-3 text-xs sm:text-sm focus:outline-none focus:ring-2 focus:ring-primary/45 cursor-pointer"
                  >
                    <option value="">-- Choose Product --</option>
                    {products.map((p) => (
                      <option key={p.id} value={p.id}>{p.title}</option>
                    ))}
                  </select>
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-bold text-foreground/75">Caption Tone / Style</label>
                  <div className="grid grid-cols-3 gap-2">
                    {["romantic", "festive", "trendy"].map((style) => (
                      <button
                        key={style}
                        type="button"
                        onClick={() => setCaptionStyle(style)}
                        className={`py-2 rounded-xl border text-xs font-bold capitalize transition ${captionStyle === style ? "border-primary bg-primary/10 text-primary" : "border-secondary hover:bg-secondary/10"}`}
                      >
                        {style}
                      </button>
                    ))}
                  </div>
                </div>

                <button
                  onClick={handleGenerateCaption}
                  disabled={!selectedProductForCaption || captionLoading}
                  className="w-full bg-primary text-white hover:bg-primary/95 py-3 rounded-full font-bold shadow transition flex items-center justify-center gap-1.5 text-xs"
                >
                  {captionLoading ? "Weaving Caption..." : (
                    <>
                      <Instagram className="w-4 h-4" /> Generate Caption
                    </>
                  )}
                </button>
              </div>
            </div>

            <div className="bg-white p-6 rounded-cozy border border-secondary/50 shadow-sm flex flex-col justify-between">
              <div>
                <h3 className="font-extrabold text-base text-foreground mb-4">Generated Instagram Copy</h3>
                
                {!generatedCaption ? (
                  <div className="h-60 border-2 border-dashed border-secondary/50 rounded-2xl flex flex-col items-center justify-center p-6 text-center text-foreground/45">
                    <Instagram className="w-8 h-8 mb-2 text-secondary animate-pulse" />
                    <p className="text-sm font-bold">Copy Awaiting Generation</p>
                    <p className="text-xs text-foreground/40 mt-1 max-w-[200px]">Select a catalog item and click generate to generate social media texts.</p>
                  </div>
                ) : (
                  <div className="space-y-4 text-xs sm:text-sm bg-primary/5 p-4 rounded-xl border border-primary/10 relative">
                    <p className="whitespace-pre-line text-foreground/80 leading-relaxed">
                      {generatedCaption.caption}
                    </p>
                    <p className="text-primary font-bold">
                      {generatedCaption.hashtags?.join(" ")}
                    </p>
                  </div>
                )}
              </div>

              {generatedCaption && (
                <button
                  onClick={copyToClipboard}
                  className="w-full mt-6 border border-primary text-primary hover:bg-primary/5 py-2.5 rounded-full font-bold text-xs transition flex items-center justify-center gap-1.5"
                >
                  {copied ? (
                    <>
                      <Check className="w-4 h-4" /> Copied!
                    </>
                  ) : (
                    <>
                      <Copy className="w-4 h-4" /> Copy Caption & Hashtags
                    </>
                  )}
                </button>
              )}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
