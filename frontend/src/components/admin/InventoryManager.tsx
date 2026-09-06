"use client";

import { useState } from "react";
import Image from "next/image";
import { AlertCircle, Check, Search, Plus, Minus } from "lucide-react";
import { api, Product } from "@/lib/api";

interface InventoryManagerProps {
  products: Product[];
  onRefresh: () => void;
}

export default function InventoryManager({
  products,
  onRefresh,
}: InventoryManagerProps) {
  const [filterMode, setFilterMode] = useState<"all" | "low" | "out">("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [updatingId, setUpdatingId] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const filteredProducts = products.filter((p) => {
    const matchesSearch = p.title.toLowerCase().includes(searchQuery.toLowerCase()) || p.slug.includes(searchQuery.toLowerCase());
    if (!matchesSearch) return false;
    if (filterMode === "low") return p.stock > 0 && p.stock < 5;
    if (filterMode === "out") return p.stock <= 0;
    return true;
  });

  const handleQuickAdjustStock = async (product: Product, delta: number) => {
    const newStock = Math.max(0, product.stock + delta);
    setUpdatingId(product.id);
    setError("");

    try {
      await api.products.update(product.id, { stock: newStock });
      setSuccess(`Updated stock for ${product.title} to ${newStock}`);
      onRefresh();
      setTimeout(() => setSuccess(""), 2500);
    } catch (err: any) {
      console.error("Stock adjust failed:", err);
      setError(err.message || "Failed to adjust stock");
    } finally {
      setUpdatingId(null);
    }
  };

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-black text-foreground">Inventory & Stock Levels</h2>
          <p className="text-xs text-foreground/60">Live stock ledger and transactional inventory management</p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex bg-secondary/20 p-1 rounded-full text-xs font-bold">
            <button
              onClick={() => setFilterMode("all")}
              className={`px-3 py-1.5 rounded-full transition ${filterMode === "all" ? "bg-white text-foreground shadow-sm" : "text-foreground/60"}`}
            >
              All Items ({products.length})
            </button>
            <button
              onClick={() => setFilterMode("low")}
              className={`px-3 py-1.5 rounded-full transition ${filterMode === "low" ? "bg-amber-100 text-amber-800 shadow-sm" : "text-foreground/60"}`}
            >
              Low Stock (&lt;5)
            </button>
            <button
              onClick={() => setFilterMode("out")}
              className={`px-3 py-1.5 rounded-full transition ${filterMode === "out" ? "bg-rose-100 text-rose-800 shadow-sm" : "text-foreground/60"}`}
            >
              Out of Stock
            </button>
          </div>
        </div>
      </div>

      {success && (
        <div className="bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs font-bold p-3.5 rounded-xl flex items-center gap-2">
          <Check className="w-4 h-4 text-emerald-600" /> {success}
        </div>
      )}

      {error && (
        <div className="bg-rose-50 border border-rose-200 text-rose-800 text-xs font-bold p-3.5 rounded-xl flex items-center gap-2">
          <AlertCircle className="w-4 h-4 text-rose-600" /> {error}
        </div>
      )}

      {/* Search Input */}
      <div className="relative max-w-sm">
        <Search className="w-4 h-4 text-foreground/40 absolute left-3 top-3" />
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Filter by product name..."
          className="w-full pl-9 pr-4 py-2 rounded-xl border border-secondary text-xs focus:outline-none focus:ring-2 focus:ring-primary/45 bg-white"
        />
      </div>

      {/* Inventory Table */}
      <div className="bg-white rounded-2xl border border-secondary/40 shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-secondary/15 text-foreground/60 font-bold uppercase tracking-wider border-b border-secondary/30">
              <tr>
                <th className="p-4">Item</th>
                <th className="p-4">SKU / Variants</th>
                <th className="p-4">Current Stock</th>
                <th className="p-4">Status</th>
                <th className="p-4 text-right">Quick Stock Adjustment</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-secondary/20">
              {filteredProducts.length === 0 ? (
                <tr>
                  <td colSpan={5} className="p-8 text-center text-foreground/50">
                    No items match the selected inventory filter.
                  </td>
                </tr>
              ) : (
                filteredProducts.map((p) => (
                  <tr key={p.id} className="hover:bg-secondary/5 transition">
                    <td className="p-4 flex items-center gap-3">
                      <div className="relative w-10 h-10 rounded-lg overflow-hidden bg-secondary/20 flex-shrink-0 border border-secondary/30">
                        <Image
                          src={p.images?.[0] || "/images/category_bouquets.jpg"}
                          alt={p.title}
                          fill
                          className="object-cover"
                          sizes="40px"
                        />
                      </div>
                      <div>
                        <p className="font-bold text-foreground line-clamp-1">{p.title}</p>
                        <p className="text-[10px] text-foreground/45 font-mono">₹{p.price}</p>
                      </div>
                    </td>
                    <td className="p-4 text-foreground/70">
                      {p.variants?.length > 0 ? (
                        <div className="space-y-1">
                          {p.variants.map((v) => (
                            <span key={v.id} className="inline-block mr-1 text-[10px] bg-secondary/20 px-2 py-0.5 rounded-md font-mono">
                              {v.name}: {v.value} ({v.stock})
                            </span>
                          ))}
                        </div>
                      ) : (
                        <span className="font-mono text-foreground/50">STD-{p.slug.slice(0, 8).toUpperCase()}</span>
                      )}
                    </td>
                    <td className="p-4 font-black text-sm text-foreground">
                      {p.stock}
                    </td>
                    <td className="p-4">
                      <span className={`px-2.5 py-1 rounded-full text-[10px] font-black uppercase tracking-wider ${
                        p.stock <= 0
                          ? "bg-rose-100 text-rose-800"
                          : p.stock < 5
                          ? "bg-amber-100 text-amber-800"
                          : "bg-emerald-100 text-emerald-800"
                      }`}>
                        {p.stock <= 0 ? "Sold Out" : p.stock < 5 ? "Low Stock" : "In Stock"}
                      </span>
                    </td>
                    <td className="p-4 text-right">
                      <div className="inline-flex items-center gap-1.5 border border-secondary rounded-full p-1 bg-white">
                        <button
                          onClick={() => handleQuickAdjustStock(p, -1)}
                          disabled={p.stock <= 0 || updatingId === p.id}
                          className="w-7 h-7 rounded-full flex items-center justify-center hover:bg-secondary/20 text-foreground/70 disabled:opacity-30"
                          title="Decrease stock"
                        >
                          <Minus className="w-3.5 h-3.5" />
                        </button>
                        <span className="w-8 text-center font-black text-xs">{p.stock}</span>
                        <button
                          onClick={() => handleQuickAdjustStock(p, 1)}
                          disabled={updatingId === p.id}
                          className="w-7 h-7 rounded-full flex items-center justify-center hover:bg-secondary/20 text-foreground/70 disabled:opacity-30"
                          title="Increase stock"
                        >
                          <Plus className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
