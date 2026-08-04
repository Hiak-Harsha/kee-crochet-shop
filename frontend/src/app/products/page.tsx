"use client";

import { useState, useEffect } from "react";
import { Search, Sparkles, Filter, RefreshCw, ShoppingCart, Heart } from "lucide-react";
import Link from "next/link";
import Image from "next/image";
import Navbar from "@/components/Navbar";
import { api } from "@/lib/api";

export default function ProductsPage() {
  const [products, setProducts] = useState<any[]>([]);
  const [categories, setCategories] = useState<any[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<string>("");
  const [searchQuery, setSearchQuery] = useState("");
  const [aiSearchActive, setAiSearchActive] = useState(false);
  const [aiSearchQuery, setAiSearchQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [priceRange, setPriceRange] = useState(1500);
  const [error, setError] = useState("");

  // Load products and categories
  const loadData = async () => {
    setLoading(true);
    setError("");
    try {
      const cats = await api.products.listCategories();
      setCategories(cats || []);
      const prods = await api.products.list();
      setProducts(prods || []);
    } catch (e: any) {
      console.error("Failed to load catalog data from backend", e);
      setError("Unable to load the products. Please verify the backend API server is online.");
    }
    setLoading(false);
  };

  useEffect(() => {
    loadData();
  }, []);

  // Standard search / filters
  const filteredProducts = products.filter((p) => {
    // Category slug filter
    if (selectedCategory) {
      if (!p.category_id) return false;
      const cat = categories.find((c) => c.slug === selectedCategory);
      if (cat && p.category_id !== cat.id) return false;
    }
    
    // Price filter
    if (parseFloat(p.price) > priceRange) return false;
    
    // Keyword search (only if AI search isn't override)
    if (!aiSearchActive && searchQuery) {
      const q = searchQuery.toLowerCase();
      const matchTitle = p.title.toLowerCase().includes(q);
      const matchDesc = (p.description || "").toLowerCase().includes(q);
      const matchTag = p.tags.some((t: string) => t.toLowerCase().includes(q));
      return matchTitle || matchDesc || matchTag;
    }
    
    return true;
  });

  // AI Semantic Search Handler
  const handleAiSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!aiSearchQuery.trim()) return;
    setLoading(true);
    setAiSearchActive(true);
    try {
      const matchedIds = await api.ai.search(aiSearchQuery);
      if (matchedIds && matchedIds.length > 0) {
        // Refilter active products based on IDs returned by Gemini
        const matchedProducts = products.filter((p) => matchedIds.includes(String(p.id)) || matchedIds.includes(p.slug));
        if (matchedProducts.length > 0) {
          setProducts(matchedProducts);
        } else {
          // Fallback keyword search
          setSearchQuery(aiSearchQuery);
          setAiSearchActive(false);
        }
      } else {
        setSearchQuery(aiSearchQuery);
        setAiSearchActive(false);
      }
    } catch (err) {
      console.error("AI Search failed, running fallback filter", err);
      setSearchQuery(aiSearchQuery);
      setAiSearchActive(false);
    }
    setLoading(false);
  };

  const resetSearch = () => {
    setSearchQuery("");
    setAiSearchQuery("");
    setAiSearchActive(false);
    loadData();
  };

  return (
    <div className="flex-1 flex flex-col min-h-screen">
      <Navbar />

      <main className="max-w-7xl mx-auto w-full px-4 sm:px-6 lg:px-8 py-10 flex-1">
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-6 mb-10">
          <div>
            <h1 className="text-3xl font-extrabold text-foreground tracking-tight">Kee Crochet Store</h1>
            <p className="text-foreground/70 mt-1">Browse our hand-knitted creations or use AI search to locate a custom gift.</p>
          </div>
          
          {/* AI Search Box */}
          <form onSubmit={handleAiSearch} className="w-full md:w-auto flex items-center space-x-2">
            <div className="relative flex-1 md:w-80">
              <input
                type="text"
                placeholder="AI: I want a flower under ₹500..."
                value={aiSearchQuery}
                onChange={(e) => setAiSearchQuery(e.target.value)}
                className="w-full pl-10 pr-4 py-2.5 rounded-full border border-primary/30 focus:outline-none focus:ring-2 focus:ring-primary/45 bg-primary/5 placeholder-primary/60 text-sm font-medium"
              />
              <Sparkles className="w-4 h-4 absolute left-4 top-3 text-primary animate-pulse" />
            </div>
            <button type="submit" className="bg-primary text-white hover:bg-primary/95 px-5 py-2.5 rounded-full font-bold text-sm shadow transition">
              AI Find
            </button>
          </form>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
          {/* Filter Sidebar */}
          <div className="space-y-8 lg:col-span-1 bg-white p-6 rounded-cozy border border-secondary/50 h-fit">
            <div className="flex justify-between items-center pb-4 border-b border-secondary/30">
              <h2 className="font-bold text-lg flex items-center gap-2 text-foreground">
                <Filter className="w-5 h-5 text-primary" /> Filters
              </h2>
              {(selectedCategory || searchQuery || aiSearchActive || priceRange < 1500) && (
                <button onClick={resetSearch} className="text-xs text-primary font-bold hover:underline flex items-center gap-1">
                  <RefreshCw className="w-3 h-3" /> Reset
                </button>
              )}
            </div>

            {/* Categories */}
            <div className="space-y-3">
              <h3 className="font-bold text-sm uppercase tracking-wider text-foreground/75">Categories</h3>
              <div className="flex flex-col space-y-2">
                <button
                  onClick={() => setSelectedCategory("")}
                  className={`text-left text-sm py-1.5 px-3 rounded-full font-semibold transition ${!selectedCategory ? "bg-primary text-white" : "hover:bg-secondary/20 text-foreground/80"}`}
                >
                  All Items
                </button>
                {categories.map((cat) => (
                  <button
                    key={cat.id}
                    onClick={() => setSelectedCategory(cat.slug)}
                    className={`text-left text-sm py-1.5 px-3 rounded-full font-semibold transition ${selectedCategory === cat.slug ? "bg-primary text-white" : "hover:bg-secondary/20 text-foreground/80"}`}
                  >
                    {cat.name}
                  </button>
                ))}
              </div>
            </div>

            {/* Price Slider */}
            <div className="space-y-3">
              <div className="flex justify-between text-sm font-bold text-foreground">
                <span>Max Price</span>
                <span>₹{priceRange}</span>
              </div>
              <input
                type="range"
                min="100"
                max="1500"
                step="50"
                value={priceRange}
                onChange={(e) => setPriceRange(parseInt(e.target.value, 10))}
                className="w-full accent-primary bg-secondary/50 h-2 rounded-lg cursor-pointer"
              />
            </div>
            
            {/* Store Information */}
            <div className="pt-6 border-t border-secondary/30 space-y-2">
              <p className="text-xs text-foreground/60 leading-relaxed">
                🧶 Custom order requests take 4-7 days.
              </p>
              <p className="text-xs text-foreground/60 leading-relaxed">
                🚚 Free shipping on orders over ₹999.
              </p>
            </div>
          </div>

          {/* Product Grid */}
          <div className="lg:col-span-3">
            {aiSearchActive && (
              <div className="mb-6 bg-primary/10 border border-primary/20 p-4 rounded-cozy flex justify-between items-center">
                <p className="text-sm font-medium text-foreground">
                  Showing products matched semantically by Gemini for: <span className="italic font-bold text-primary">"{aiSearchQuery}"</span>
                </p>
                <button onClick={resetSearch} className="text-xs text-primary font-extrabold hover:underline">
                  Clear AI Filter
                </button>
              </div>
            )}

            {error ? (
              <div className="text-center py-20 border border-dashed border-rose-300 rounded-cozy bg-rose-50/50 space-y-4">
                <p className="text-lg font-bold text-rose-800">Connection Error</p>
                <p className="text-sm text-rose-700 max-w-sm mx-auto">{error}</p>
                <button onClick={loadData} className="bg-rose-600 hover:bg-rose-700 text-white px-6 py-2 rounded-full font-bold text-sm shadow transition flex items-center gap-1.5 mx-auto">
                  <RefreshCw className="w-4 h-4" /> Retry Loading Catalog
                </button>
              </div>
            ) : loading ? (
              <div className="flex flex-col items-center justify-center py-20 space-y-4">
                <div className="w-10 h-10 border-4 border-primary border-t-transparent rounded-full animate-spin"></div>
                <p className="text-sm font-medium text-foreground/60">Searching catalog...</p>
              </div>
            ) : filteredProducts.length === 0 ? (
              <div className="text-center py-20 border border-dashed border-secondary rounded-cozy bg-white space-y-4">
                <p className="text-lg font-bold text-foreground/75">No crochet products found</p>
                <p className="text-sm text-foreground/60 max-w-sm mx-auto">Try clearing your filters or type a new query into the AI search.</p>
                <button onClick={resetSearch} className="bg-primary text-white px-6 py-2 rounded-full font-bold text-sm shadow">
                  Show All Products
                </button>
              </div>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-6">
                {filteredProducts.map((p) => (
                  <div key={p.id} className="group bg-white border border-secondary/50 rounded-cozy overflow-hidden shadow-sm hover:shadow-lg transition-all duration-300 flex flex-col justify-between">
                    <Link href={`/products/${p.slug}`} className="block relative aspect-square overflow-hidden bg-secondary/10">
                      <Image
                        src={p.images?.[0] || "/images/category_bouquets.jpg"}
                        alt={p.title}
                        fill
                        className="object-cover group-hover:scale-105 transition-transform duration-500"
                        sizes="(max-width: 768px) 100vw, (max-width: 1200px) 33vw, 25vw"
                      />
                    </Link>
                    
                    <div className="p-5 flex-1 flex flex-col justify-between">
                      <div>
                        <Link href={`/products/${p.slug}`} className="block font-bold text-foreground hover:text-primary transition line-clamp-1 mb-1">
                          {p.title}
                        </Link>
                        
                        <div className="flex flex-wrap gap-1 mb-4">
                          {p.colors?.slice(0, 3).map((col: string, idx: number) => (
                            <span key={idx} className="bg-secondary/30 text-secondary-foreground text-[10px] font-bold px-2 py-0.5 rounded-full">
                              {col}
                            </span>
                          ))}
                        </div>
                      </div>

                      <div className="flex items-center justify-between mt-2 pt-4 border-t border-secondary/20">
                        <span className="text-lg font-extrabold text-foreground">₹{parseFloat(p.price)}</span>
                        <Link href={`/products/${p.slug}`} className="bg-primary/10 hover:bg-primary text-primary hover:text-white px-4 py-2 rounded-full text-xs font-bold transition flex items-center gap-1.5">
                          View details
                        </Link>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
