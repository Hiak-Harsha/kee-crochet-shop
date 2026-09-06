"use client";

import { useState } from "react";
import { Plus, Tag, AlertCircle, Check } from "lucide-react";
import { api, Category } from "@/lib/api";

interface CategoryManagementProps {
  categories: Category[];
  onRefresh: () => void;
}

export default function CategoryManagement({
  categories,
  onRefresh,
}: CategoryManagementProps) {
  const [showAddForm, setShowAddForm] = useState(false);
  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");
  const [description, setDescription] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const handleCreateCategory = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name) return;

    setLoading(true);
    setError("");
    setSuccess("");

    const autoSlug = slug.trim() || name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");

    try {
      await api.products.createCategory({
        name,
        slug: autoSlug,
        description: description || null,
      });
      setName("");
      setSlug("");
      setDescription("");
      setShowAddForm(false);
      setSuccess("Category created successfully!");
      onRefresh();
      setTimeout(() => setSuccess(""), 3000);
    } catch (err: any) {
      console.error("Create category failed:", err);
      setError(err.message || "Failed to create category.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-black text-foreground">Categories</h2>
          <p className="text-xs text-foreground/60">Organize your crochet catalog into shop collections</p>
        </div>
        <button
          onClick={() => setShowAddForm(!showAddForm)}
          className="bg-primary text-white text-xs font-bold px-4 py-2.5 rounded-full shadow hover:bg-primary/95 transition flex items-center gap-1.5"
        >
          <Plus className="w-4 h-4" /> {showAddForm ? "Close Form" : "New Category"}
        </button>
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

      {/* Add Category Drawer/Form */}
      {showAddForm && (
        <form onSubmit={handleCreateCategory} className="bg-white p-6 rounded-2xl border border-secondary/40 shadow-sm space-y-4">
          <h3 className="font-extrabold text-sm text-foreground">Create New Category</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-1">
              <label className="text-xs font-bold text-foreground/75">Category Name *</label>
              <input
                type="text"
                required
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. Handmade Bouquets"
                className="w-full p-2.5 rounded-xl border border-secondary text-xs focus:outline-none focus:ring-2 focus:ring-primary/45"
              />
            </div>
            <div className="space-y-1">
              <label className="text-xs font-bold text-foreground/75">URL Slug</label>
              <input
                type="text"
                value={slug}
                onChange={(e) => setSlug(e.target.value)}
                placeholder="e.g. handmade-bouquets"
                className="w-full p-2.5 rounded-xl border border-secondary text-xs focus:outline-none focus:ring-2 focus:ring-primary/45"
              />
            </div>
          </div>
          <div className="space-y-1">
            <label className="text-xs font-bold text-foreground/75">Description</label>
            <input
              type="text"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Brief description for SEO and category banner"
              className="w-full p-2.5 rounded-xl border border-secondary text-xs focus:outline-none focus:ring-2 focus:ring-primary/45"
            />
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={() => setShowAddForm(false)}
              className="px-4 py-2 rounded-full border border-secondary text-xs font-bold text-foreground/70"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="px-5 py-2 rounded-full bg-primary text-white text-xs font-bold shadow hover:bg-primary/95 transition disabled:opacity-50"
            >
              {loading ? "Creating..." : "Save Category"}
            </button>
          </div>
        </form>
      )}

      {/* Categories Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
        {categories.map((c) => (
          <div key={c.id} className="bg-white p-6 rounded-2xl border border-secondary/40 shadow-sm space-y-3">
            <div className="flex items-start justify-between">
              <div>
                <h3 className="font-extrabold text-base text-foreground">{c.name}</h3>
                <p className="text-[11px] font-mono text-foreground/45 mt-0.5">/{c.slug}</p>
              </div>
              <div className="w-10 h-10 rounded-xl bg-primary/10 text-primary flex items-center justify-center">
                <Tag className="w-5 h-5" />
              </div>
            </div>
            <p className="text-xs text-foreground/60 line-clamp-2">
              {c.description || "No custom description set."}
            </p>
            {c.starting_price && (
              <div className="pt-2 border-t border-secondary/20 flex items-center justify-between text-xs">
                <span className="text-foreground/50">Starting from</span>
                <span className="font-black text-primary">₹{c.starting_price}</span>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
