"use client";

import { useState, useEffect } from "react";
import { Inbox, Palette, User, AlertCircle } from "lucide-react";

interface CustomRequestItem {
  id: string;
  user_id: string;
  description: string;
  color_palette?: string | null;
  status?: string;
  created_at: string;
}

export default function CustomRequestInbox() {
  const [requests, setRequests] = useState<CustomRequestItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const loadRequests = async () => {
    setLoading(true);
    setError("");
    try {
      // In products route: GET /products/custom-requests/admin
      const rawBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";
      const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
      const res = await fetch(`${rawBase.replace(/\/$/, "")}/products/custom-requests/admin`, {
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
      });
      if (res.ok) {
        const data = await res.json();
        setRequests(data || []);
      }
    } catch (err: any) {
      console.error("Failed to load custom requests:", err);
      setError(err.message || "Failed to load custom requests.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadRequests();
  }, []);

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-black text-foreground">Custom Commission Inbox</h2>
          <p className="text-xs text-foreground/60">Bespoke crochet requests, custom color palettes, and personalized orders</p>
        </div>
      </div>

      {error && (
        <div className="bg-rose-50 border border-rose-200 text-rose-800 text-xs font-bold p-3.5 rounded-xl flex items-center gap-2">
          <AlertCircle className="w-4 h-4 text-rose-600" /> {error}
        </div>
      )}

      {loading ? (
        <div className="py-12 text-center text-xs text-foreground/50">
          Loading custom requests...
        </div>
      ) : requests.length === 0 ? (
        <div className="bg-white p-12 rounded-2xl border border-secondary/40 text-center space-y-2">
          <Inbox className="w-10 h-10 text-foreground/30 mx-auto" />
          <p className="font-bold text-sm text-foreground">No bespoke custom requests right now</p>
          <p className="text-xs text-foreground/50">Custom requests submitted by shoppers will show up here.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {requests.map((req) => (
            <div key={req.id} className="bg-white p-5 rounded-2xl border border-secondary/40 shadow-sm space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-mono text-foreground/50 flex items-center gap-1">
                  <User className="w-3 h-3" /> Customer: {req.user_id.slice(0, 8)}...
                </span>
                <span className="text-[10px] text-foreground/45 font-mono">
                  {new Date(req.created_at).toLocaleDateString("en-IN", { month: "short", day: "numeric", year: "numeric" })}
                </span>
              </div>

              <p className="text-xs text-foreground/85 leading-relaxed bg-secondary/10 p-3 rounded-xl">
                "{req.description}"
              </p>

              {req.color_palette && (
                <div className="flex items-center gap-2 pt-1">
                  <Palette className="w-3.5 h-3.5 text-primary flex-shrink-0" />
                  <span className="text-xs font-bold text-foreground/75">Palette:</span>
                  <span className="text-xs text-primary font-mono bg-primary/10 px-2 py-0.5 rounded-md">
                    {req.color_palette}
                  </span>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
