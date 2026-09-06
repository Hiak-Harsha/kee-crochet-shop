"use client";

import { useState, useEffect } from "react";
import { Plus, Check, AlertCircle } from "lucide-react";
import { api, Coupon } from "@/lib/api";

export default function CouponManager() {
  const [coupons, setCoupons] = useState<Coupon[]>([]);
  const [showAddForm, setShowAddForm] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  // Create Form fields
  const [code, setCode] = useState("");
  const [description, setDescription] = useState("");
  const [type, setType] = useState<"percentage" | "fixed" | "free_shipping">("percentage");
  const [value, setValue] = useState<number>(10);
  const [minOrderValue, setMinOrderValue] = useState<number>(0);
  const [maxDiscount, setMaxDiscount] = useState<number | undefined>(undefined);
  const [usageLimit, setUsageLimit] = useState<number | undefined>(undefined);
  const [expiresAt, setExpiresAt] = useState("");

  const loadCoupons = async () => {
    setError("");
    try {
      const data = await api.coupons.adminList();
      setCoupons(data || []);
    } catch (err: any) {
      console.error("Failed to load coupons:", err);
      setError(err.message || "Failed to load coupons.");
    }
  };

  useEffect(() => {
    loadCoupons();
  }, []);

  const handleCreateCoupon = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!code) return;

    setError("");
    setSuccess("");

    const payload = {
      code: code.trim().toUpperCase(),
      description: description || null,
      type,
      value: Number(value),
      minimum_order_value: Number(minOrderValue),
      maximum_discount: maxDiscount ? Number(maxDiscount) : null,
      usage_limit: usageLimit ? Number(usageLimit) : null,
      per_customer_limit: 1,
      expires_at: expiresAt ? new Date(expiresAt).toISOString() : null,
      is_active: true,
    };

    try {
      await api.coupons.adminCreate(payload);
      setSuccess(`Coupon ${payload.code} created!`);
      setShowAddForm(false);
      setCode("");
      setDescription("");
      setValue(10);
      setMinOrderValue(0);
      setMaxDiscount(undefined);
      setUsageLimit(undefined);
      setExpiresAt("");
      loadCoupons();
      setTimeout(() => setSuccess(""), 3000);
    } catch (err: any) {
      console.error("Create coupon failed:", err);
      setError(err.message || "Failed to create coupon.");
    }
  };

  const handleToggleActive = async (coupon: Coupon) => {
    setError("");
    try {
      await api.coupons.adminUpdate(coupon.id, { is_active: !coupon.is_active });
      loadCoupons();
    } catch (err: any) {
      console.error("Toggle coupon status failed:", err);
      setError(err.message || "Failed to update coupon.");
    }
  };

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-black text-foreground">Discount Coupons & Promotions</h2>
          <p className="text-xs text-foreground/60">Define promotional discounts, free shipping vouchers, and minimum thresholds</p>
        </div>
        <button
          onClick={() => setShowAddForm(!showAddForm)}
          className="bg-primary text-white text-xs font-bold px-4 py-2.5 rounded-full shadow hover:bg-primary/95 transition flex items-center gap-1.5"
        >
          <Plus className="w-4 h-4" /> {showAddForm ? "Close Form" : "Create Coupon"}
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

      {/* Add Coupon Form */}
      {showAddForm && (
        <form onSubmit={handleCreateCoupon} className="bg-white p-6 rounded-2xl border border-secondary/40 shadow-sm space-y-4">
          <h3 className="font-extrabold text-sm text-foreground">Create New Discount Voucher</h3>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="space-y-1">
              <label className="text-xs font-bold text-foreground/75">Coupon Code *</label>
              <input
                type="text"
                required
                value={code}
                onChange={(e) => setCode(e.target.value)}
                placeholder="e.g. FESTIVAL20"
                className="w-full p-2.5 rounded-xl border border-secondary text-xs focus:outline-none focus:ring-2 focus:ring-primary/45 uppercase font-mono font-bold"
              />
            </div>

            <div className="space-y-1">
              <label className="text-xs font-bold text-foreground/75">Discount Type *</label>
              <select
                value={type}
                onChange={(e: any) => setType(e.target.value)}
                className="w-full p-2.5 rounded-xl border border-secondary text-xs focus:outline-none focus:ring-2 focus:ring-primary/45 bg-white font-semibold"
              >
                <option value="percentage">Percentage Off (%)</option>
                <option value="fixed">Fixed Amount (₹)</option>
                <option value="free_shipping">Free Shipping</option>
              </select>
            </div>

            <div className="space-y-1">
              <label className="text-xs font-bold text-foreground/75">Discount Value *</label>
              <input
                type="number"
                required
                min="0"
                value={value}
                onChange={(e) => setValue(Number(e.target.value))}
                placeholder={type === "percentage" ? "10 (%)" : "100 (₹)"}
                className="w-full p-2.5 rounded-xl border border-secondary text-xs focus:outline-none focus:ring-2 focus:ring-primary/45"
              />
            </div>

            <div className="space-y-1">
              <label className="text-xs font-bold text-foreground/75">Min Order Value (₹)</label>
              <input
                type="number"
                min="0"
                value={minOrderValue}
                onChange={(e) => setMinOrderValue(Number(e.target.value))}
                placeholder="0"
                className="w-full p-2.5 rounded-xl border border-secondary text-xs focus:outline-none focus:ring-2 focus:ring-primary/45"
              />
            </div>

            <div className="space-y-1">
              <label className="text-xs font-bold text-foreground/75">Max Discount Cap (₹)</label>
              <input
                type="number"
                min="0"
                value={maxDiscount || ""}
                onChange={(e) => setMaxDiscount(e.target.value ? Number(e.target.value) : undefined)}
                placeholder="Optional max cap"
                className="w-full p-2.5 rounded-xl border border-secondary text-xs focus:outline-none focus:ring-2 focus:ring-primary/45"
              />
            </div>

            <div className="space-y-1">
              <label className="text-xs font-bold text-foreground/75">Expiration Date</label>
              <input
                type="date"
                value={expiresAt}
                onChange={(e) => setExpiresAt(e.target.value)}
                className="w-full p-2.5 rounded-xl border border-secondary text-xs focus:outline-none focus:ring-2 focus:ring-primary/45 bg-white"
              />
            </div>
          </div>

          <div className="space-y-1">
            <label className="text-xs font-bold text-foreground/75">Description</label>
            <input
              type="text"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="e.g. 15% off on all Rakhi crochet hampers"
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
              className="px-5 py-2 rounded-full bg-primary text-white text-xs font-bold shadow hover:bg-primary/95 transition"
            >
              Create Voucher
            </button>
          </div>
        </form>
      )}

      {/* Coupons Table */}
      <div className="bg-white rounded-2xl border border-secondary/40 shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-secondary/15 text-foreground/60 font-bold uppercase tracking-wider border-b border-secondary/30">
              <tr>
                <th className="p-4">Code</th>
                <th className="p-4">Type & Value</th>
                <th className="p-4">Min Order</th>
                <th className="p-4">Times Used</th>
                <th className="p-4">Expires</th>
                <th className="p-4">Status</th>
                <th className="p-4 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-secondary/20">
              {coupons.length === 0 ? (
                <tr>
                  <td colSpan={7} className="p-8 text-center text-foreground/50">
                    No promotional coupons registered. Click "Create Coupon" to launch your first offer.
                  </td>
                </tr>
              ) : (
                coupons.map((c) => (
                  <tr key={c.id} className="hover:bg-secondary/5 transition">
                    <td className="p-4">
                      <div className="flex items-center gap-2">
                        <span className="font-mono font-black text-foreground text-sm bg-secondary/15 px-2 py-0.5 rounded border border-secondary/30">
                          {c.code}
                        </span>
                      </div>
                      {c.description && (
                        <p className="text-[10px] text-foreground/50 mt-1">{c.description}</p>
                      )}
                    </td>
                    <td className="p-4 font-bold text-foreground">
                      {c.type === "percentage" ? `${c.value}% OFF` : c.type === "fixed" ? `₹${c.value} OFF` : "FREE SHIPPING"}
                    </td>
                    <td className="p-4 text-foreground/70">
                      ₹{c.minimum_order_value}
                    </td>
                    <td className="p-4 text-foreground/80 font-mono">
                      {c.times_used} {c.usage_limit ? `/ ${c.usage_limit}` : "redemptions"}
                    </td>
                    <td className="p-4 text-foreground/60 font-mono">
                      {c.expires_at ? new Date(c.expires_at).toLocaleDateString("en-IN", { month: "short", day: "numeric", year: "numeric" }) : "Never"}
                    </td>
                    <td className="p-4">
                      <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold ${
                        c.is_active ? "bg-emerald-100 text-emerald-800" : "bg-gray-100 text-gray-500"
                      }`}>
                        {c.is_active ? "Active" : "Inactive"}
                      </span>
                    </td>
                    <td className="p-4 text-right">
                      <button
                        onClick={() => handleToggleActive(c)}
                        className={`text-xs font-bold px-3 py-1 rounded-full border transition ${
                          c.is_active
                            ? "border-rose-300 text-rose-700 hover:bg-rose-50"
                            : "border-emerald-300 text-emerald-700 hover:bg-emerald-50"
                        }`}
                      >
                        {c.is_active ? "Deactivate" : "Activate"}
                      </button>
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
