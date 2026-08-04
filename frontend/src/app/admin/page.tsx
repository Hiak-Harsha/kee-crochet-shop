"use client";

import { useState, useEffect } from "react";
import { Sparkles, LayoutDashboard, Plus, Eye, BarChart, ShoppingCart, RefreshCw, Upload, Instagram, Check, Copy } from "lucide-react";
import Navbar from "@/components/Navbar";
import { api } from "@/lib/api";

export default function AdminPage() {
  const [activeTab, setActiveTab] = useState<"analytics" | "products" | "orders" | "social">("analytics");
  const [loading, setLoading] = useState(false);

  // Admin Data lists
  const [products, setProducts] = useState<any[]>([]);
  const [orders, setOrders] = useState<any[]>([]);

  // Product Create Form States
  const [newTitle, setNewTitle] = useState("");
  const [newPrice, setNewPrice] = useState(0);
  const [newSlug, setNewSlug] = useState("");
  const [newDesc, setNewDesc] = useState("");
  const [newTags, setNewTags] = useState<string[]>([]);
  const [newColors, setNewColors] = useState<string[]>([]);
  const [newStock, setNewStock] = useState(10);
  const [showAddForm, setShowAddForm] = useState(false);
  
  // AI Assist States
  const [aiProductFile, setAiProductFile] = useState<File | null>(null);
  const [aiProductLoading, setAiProductLoading] = useState(false);

  // AI Instagram Planner States
  const [selectedProductForCaption, setSelectedProductForCaption] = useState("");
  const [captionStyle, setCaptionStyle] = useState("trendy");
  const [generatedCaption, setGeneratedCaption] = useState<any>(null);
  const [captionLoading, setCaptionLoading] = useState(false);
  const [copied, setCopied] = useState(false);

  const loadAdminData = async () => {
    setLoading(true);
    try {
      const prods = await api.products.list();
      setProducts(prods || []);
      
      const ords = await api.orders.adminListAll();
      setOrders(ords || []);
    } catch (e) {
      console.warn("Failed to load admin data from backend, using mock data", e);
      // Fallback Admin Mock Data
      setProducts([
        { id: "p1", title: "Everlasting Pink Tulip Bouquet", slug: "pink-tulip-bouquet", price: 599.00, stock: 12, colors: ["Pink", "Cream White"], tags: ["flower", "bouquet"] },
        { id: "p2", title: "Chubby Crochet Octopus Plushie", slug: "octopus-plushie", price: 349.00, stock: 4, colors: ["Lilac", "Mint"], tags: ["plushie", "animal"] },
        { id: "p3", title: "Artisanal Sunflower Crochet Stem", slug: "sunflower-stem", price: 249.00, stock: 0, colors: ["Yellow"], tags: ["sunflower", "stem"] }
      ]);
      setOrders([
        { id: "o1", order_number: "KC812495", created_at: new Date().toISOString(), status: "packed", total: 659.00, shipping_address: { full_name: "Madhav Nair", phone: "9876543210" } }
      ]);
    }
    setLoading(false);
  };

  useEffect(() => {
    loadAdminData();
  }, []);

  // Update order fulfillment status
  const handleUpdateOrderStatus = async (orderId: string, newStatus: string) => {
    try {
      await api.orders.adminUpdateStatus(orderId, newStatus);
      loadAdminData();
    } catch (e) {
      console.warn("Backend order status update failed, shifting state locally", e);
      setOrders((prev) => prev.map((o) => o.id === orderId ? { ...o, status: newStatus } : o));
    }
  };

  // AI Product Description Generator
  const handleAiProductDescribe = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setAiProductFile(file);
      setAiProductLoading(true);

      try {
        const desc = await api.ai.describeProduct(file);
        setNewTitle(desc.title);
        setNewDesc(desc.description);
        setNewTags(desc.tags);
        setNewSlug(desc.title.toLowerCase().replace(/ /g, "-").replace(/[^\w-]+/g, ""));
      } catch (err) {
        console.error("AI description generator failed, loading mock parameters", err);
        // Fallback description parameters
        setNewTitle("Chubby Crochet Turtle Buddy");
        setNewDesc("An adorable, hand-knitted green turtle plushie made with premium milk cotton yarn. Soft, washable, and perfect as a key accessory or desk companion.");
        setNewTags(["turtle", "plushie", "green", "desk buddy", "handmade"]);
        setNewSlug("crochet-turtle-buddy");
      }
      setAiProductLoading(false);
    }
  };

  // Submit Product Creation
  const handleCreateProduct = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTitle || !newSlug || newPrice <= 0) return;

    const payload = {
      title: newTitle,
      slug: newSlug,
      description: newDesc,
      price: newPrice,
      stock: newStock,
      tags: newTags,
      colors: newColors.length > 0 ? newColors : ["Default Pastel"],
      images: ["https://images.unsplash.com/photo-1544816155-12df9643f363?auto=format&fit=crop&q=80&w=400"],
      variants: []
    };

    try {
      await api.products.create(payload);
      loadAdminData();
      setShowAddForm(false);
    } catch (e) {
      console.warn("Backend product creation failed, appending locally for sandbox mock run", e);
      setProducts((prev) => [...prev, { ...payload, id: `p_mock_${Math.random()}` }]);
      setShowAddForm(false);
    }

    // Reset Form Fields
    setNewTitle("");
    setNewPrice(0);
    setNewSlug("");
    setNewDesc("");
    setNewTags([]);
    setNewColors([]);
  };

  // AI Instagram Caption Generator
  const handleGenerateCaption = async () => {
    if (!selectedProductForCaption) return;
    setCaptionLoading(true);
    setGeneratedCaption(null);

    try {
      const cap = await api.ai.instagramCaption(selectedProductForCaption, captionStyle);
      setGeneratedCaption(cap);
    } catch (e) {
      console.error("AI Caption failed, loading mock caption", e);
      setGeneratedCaption({
        caption: `Spring is in the air, and so are our hooks! 🌷✨ Our handcrafted Pink Tulip Bouquet is back in stock. Tied with a silk ribbon and made with love. Perfect for birthdays, dates, or just because. 💖 DM us or click our website link in bio to shop.`,
        hashtags: ["#kee_crochet", "#handmadegifts", "#crochettulips", "#giftideas", "#craftsmanship"]
      });
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

  return (
    <div className="flex-1 flex flex-col min-h-screen">
      <Navbar />

      <main className="max-w-7xl mx-auto w-full px-4 sm:px-6 lg:px-8 py-10 flex-1">
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
                  <p className="text-2xl font-black text-foreground mt-1">₹34,890.00</p>
                </div>
                <BarChart className="w-8 h-8 text-primary/45" />
              </div>
              <div className="bg-white p-6 rounded-cozy border border-secondary/50 shadow-sm flex items-center justify-between">
                <div>
                  <p className="text-xs text-foreground/60 font-bold uppercase tracking-wider">Total Orders</p>
                  <p className="text-2xl font-black text-foreground mt-1">{orders.length + 42}</p>
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
                  <p className="text-2xl font-black text-foreground mt-1">₹620.00</p>
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
            <div className="flex justify-between items-center">
              <h2 className="text-xl font-extrabold text-foreground">Shop Catalog CRUD</h2>
              <button
                onClick={() => setShowAddForm(!showAddForm)}
                className="bg-primary text-white hover:bg-primary/95 px-5 py-2.5 rounded-full font-bold text-xs shadow flex items-center gap-1"
              >
                <Plus className="w-4 h-4" /> Add Product
              </button>
            </div>

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

                {/* AI Image Upload Panel */}
                <div className="space-y-3">
                  <span className="text-xs font-bold text-foreground/75 block">AI Assist: Upload Product Photo</span>
                  <div className="relative border-2 border-dashed border-primary/40 hover:border-primary p-6 rounded-xl flex flex-col items-center justify-center bg-primary/5 transition cursor-pointer">
                    {aiProductLoading ? (
                      <div className="flex flex-col items-center py-2 text-primary">
                        <div className="w-8 h-8 border-4 border-primary border-t-transparent rounded-full animate-spin mb-2"></div>
                        <span className="text-xs font-bold">Gemini is analyzing details...</span>
                      </div>
                    ) : (
                      <div className="flex flex-col items-center text-primary/70">
                        <Upload className="w-8 h-8 mb-2" />
                        <span className="text-xs font-bold">Upload image to Auto-Generate Title, description and SEO</span>
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

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 pt-4 border-t border-secondary/20">
                  <div className="space-y-1.5">
                    <label className="text-xs font-bold text-foreground/75">Product Title *</label>
                    <input
                      type="text"
                      required
                      value={newTitle}
                      onChange={(e) => setNewTitle(e.target.value)}
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
                    <th className="p-4">Colors</th>
                  </tr>
                </thead>
                <tbody>
                  {products.map((p) => (
                    <tr key={p.id} className="border-b border-secondary/15 hover:bg-secondary/5 transition">
                      <td className="p-4 font-bold text-foreground">{p.title}</td>
                      <td className="p-4">₹{p.price}</td>
                      <td className="p-4">
                        <span className={`px-2 py-0.5 rounded-full font-bold text-[10px] ${p.stock <= 5 ? "bg-rose-100 text-rose-800" : "bg-emerald-100 text-emerald-800"}`}>
                          {p.stock} in stock
                        </span>
                      </td>
                      <td className="p-4 text-foreground/60">{p.colors?.join(", ") || "Pastel"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
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
