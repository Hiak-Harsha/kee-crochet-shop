"use client";

import { useState, useEffect } from "react";
import { Star, Sparkles, AlertCircle, MessageSquare } from "lucide-react";
import { api, Product } from "@/lib/api";

interface ReviewModeratorProps {
  products: Product[];
}

interface ProductReviewItem {
  id: string;
  product_id: string;
  product_title: string;
  rating: number;
  comment: string;
  user_name: string;
  created_at: string;
}

export default function ReviewModerator({ products }: ReviewModeratorProps) {
  const [selectedProductId, setSelectedProductId] = useState<string>(products[0]?.id || "");
  const [reviews, setReviews] = useState<ProductReviewItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [summarizing, setSummarizing] = useState(false);
  const [aiSummary, setAiSummary] = useState<string | null>(null);
  const [error, setError] = useState("");

  const loadReviewsForProduct = async (prodId: string) => {
    if (!prodId) return;
    setLoading(true);
    setError("");
    setAiSummary(null);

    try {
      const data = await api.products.getReviews(prodId);
      const prod = products.find((p) => p.id === prodId);
      const mapped = (data || []).map((r: any) => ({
        id: r.id,
        product_id: prodId,
        product_title: prod?.title || "Product",
        rating: r.rating,
        comment: r.comment,
        user_name: r.user_name || "Customer",
        created_at: r.created_at,
      }));
      setReviews(mapped);
    } catch (err: any) {
      console.error("Failed to load reviews:", err);
      setError(err.message || "Failed to load reviews for this product.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (selectedProductId) {
      loadReviewsForProduct(selectedProductId);
    }
  }, [selectedProductId]);

  const handleSummarizeReviews = async () => {
    if (!selectedProductId) return;
    setSummarizing(true);
    setError("");

    try {
      const res = await api.ai.summarizeReviews(selectedProductId);
      setAiSummary(res?.summary || res?.sentiment || "Reviews analyzed successfully.");
    } catch (err: any) {
      console.error("AI summarize failed:", err);
      setError(err.message || "Failed to summarize reviews with AI.");
    } finally {
      setSummarizing(false);
    }
  };

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-black text-foreground">Review Moderator</h2>
          <p className="text-xs text-foreground/60">Inspect verified customer reviews and generate AI sentiment summaries</p>
        </div>

        <div className="flex items-center gap-3">
          <select
            value={selectedProductId}
            onChange={(e) => setSelectedProductId(e.target.value)}
            className="bg-white border border-secondary text-xs font-bold rounded-xl px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary/45"
          >
            {products.map((p) => (
              <option key={p.id} value={p.id}>{p.title}</option>
            ))}
          </select>

          <button
            onClick={handleSummarizeReviews}
            disabled={summarizing || reviews.length === 0}
            className="bg-primary text-white text-xs font-bold px-4 py-2 rounded-full shadow hover:bg-primary/95 transition flex items-center gap-1.5 disabled:opacity-50"
          >
            <Sparkles className="w-3.5 h-3.5" />
            {summarizing ? "Analyzing..." : "AI Sentiment"}
          </button>
        </div>
      </div>

      {error && (
        <div className="bg-rose-50 border border-rose-200 text-rose-800 text-xs font-bold p-3.5 rounded-xl flex items-center gap-2">
          <AlertCircle className="w-4 h-4 text-rose-600" /> {error}
        </div>
      )}

      {/* AI Sentiment Summary Card */}
      {aiSummary && (
        <div className="bg-gradient-to-r from-primary/10 via-secondary/15 to-primary/5 p-5 rounded-2xl border border-primary/20 space-y-2">
          <div className="flex items-center gap-1.5 font-extrabold text-sm text-foreground">
            <Sparkles className="w-4 h-4 text-amber-500" />
            <span>AI Review Insights & Sentiment</span>
          </div>
          <p className="text-xs text-foreground/80 leading-relaxed whitespace-pre-wrap">{aiSummary}</p>
        </div>
      )}

      {/* Reviews List */}
      <div className="space-y-4">
        {loading ? (
          <div className="py-12 text-center text-xs text-foreground/50">
            Fetching product reviews...
          </div>
        ) : reviews.length === 0 ? (
          <div className="bg-white p-12 rounded-2xl border border-secondary/40 text-center space-y-2">
            <MessageSquare className="w-10 h-10 text-foreground/30 mx-auto" />
            <p className="font-bold text-sm text-foreground">No reviews yet for this product</p>
            <p className="text-xs text-foreground/50">Verified purchasers will be able to share feedback after delivery.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {reviews.map((rev) => (
              <div key={rev.id} className="bg-white p-5 rounded-2xl border border-secondary/40 shadow-sm space-y-3">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-bold text-xs text-foreground">{rev.user_name}</p>
                    <span className="text-[10px] text-emerald-700 bg-emerald-50 border border-emerald-200 px-1.5 py-0.5 rounded font-bold">
                      Verified Purchase
                    </span>
                  </div>
                  <div className="flex text-amber-400">
                    {[...Array(5)].map((_, i) => (
                      <Star
                        key={i}
                        className={`w-3.5 h-3.5 ${i < rev.rating ? "fill-current" : "text-gray-200"}`}
                      />
                    ))}
                  </div>
                </div>

                <p className="text-xs text-foreground/80 leading-relaxed italic">
                  "{rev.comment}"
                </p>

                <p className="text-[10px] text-foreground/40 font-mono pt-1 border-t border-secondary/20">
                  {new Date(rev.created_at).toLocaleDateString("en-IN", { month: "short", day: "numeric", year: "numeric" })}
                </p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
