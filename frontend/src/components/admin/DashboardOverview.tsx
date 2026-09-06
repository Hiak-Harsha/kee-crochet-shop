"use client";

import { ShoppingBag, TrendingUp, Package, Clock, ArrowUpRight, Plus, Sparkles, Tag } from "lucide-react";
import { Order, Product } from "@/lib/api";

interface DashboardOverviewProps {
  stats: {
    total_sales: number;
    total_orders: number;
    average_order_value: number;
  };
  orders: Order[];
  products: Product[];
  onNavigateTab: (tab: string) => void;
  onRefresh: () => void;
}

export default function DashboardOverview({
  stats,
  orders,
  products,
  onNavigateTab,
}: DashboardOverviewProps) {
  const pendingOrders = orders.filter((o) => o.status === "pending_payment" || o.status === "processing" || o.status === "paid");
  const lowStockProducts = products.filter((p) => p.stock < 5);

  return (
    <div className="space-y-8 animate-fade-in">
      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        <div className="bg-white p-6 rounded-2xl border border-secondary/40 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-xs font-bold uppercase tracking-wider text-foreground/50">Total Revenue</p>
            <p className="text-2xl font-black text-foreground mt-1">₹{stats.total_sales.toLocaleString("en-IN", { minimumFractionDigits: 2 })}</p>
            <span className="text-[11px] font-semibold text-emerald-600 flex items-center gap-1 mt-1">
              <TrendingUp className="w-3 h-3" /> Authoritative Gross
            </span>
          </div>
          <div className="w-12 h-12 rounded-xl bg-amber-500/10 text-amber-600 flex items-center justify-center font-bold text-lg">
            ₹
          </div>
        </div>

        <div className="bg-white p-6 rounded-2xl border border-secondary/40 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-xs font-bold uppercase tracking-wider text-foreground/50">Total Orders</p>
            <p className="text-2xl font-black text-foreground mt-1">{stats.total_orders}</p>
            <span className="text-[11px] font-semibold text-primary flex items-center gap-1 mt-1">
              <ShoppingBag className="w-3 h-3" /> Lifetime Orders
            </span>
          </div>
          <div className="w-12 h-12 rounded-xl bg-primary/10 text-primary flex items-center justify-center">
            <ShoppingBag className="w-6 h-6" />
          </div>
        </div>

        <div className="bg-white p-6 rounded-2xl border border-secondary/40 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-xs font-bold uppercase tracking-wider text-foreground/50">Avg Order Value</p>
            <p className="text-2xl font-black text-foreground mt-1">₹{stats.average_order_value.toFixed(2)}</p>
            <span className="text-[11px] font-semibold text-foreground/60 flex items-center gap-1 mt-1">
              Across all paid carts
            </span>
          </div>
          <div className="w-12 h-12 rounded-xl bg-purple-500/10 text-purple-600 flex items-center justify-center font-bold">
            AOV
          </div>
        </div>

        <div className="bg-white p-6 rounded-2xl border border-secondary/40 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-xs font-bold uppercase tracking-wider text-foreground/50">Action Needed</p>
            <p className="text-2xl font-black text-foreground mt-1">{pendingOrders.length}</p>
            <span className="text-[11px] font-semibold text-amber-600 flex items-center gap-1 mt-1">
              <Clock className="w-3 h-3" /> Orders in pipeline
            </span>
          </div>
          <div className="w-12 h-12 rounded-xl bg-rose-500/10 text-rose-600 flex items-center justify-center">
            <Package className="w-6 h-6" />
          </div>
        </div>
      </div>

      {/* Quick Action Bar */}
      <div className="bg-gradient-to-r from-primary/10 via-secondary/20 to-primary/5 p-6 rounded-2xl border border-primary/20 flex flex-wrap items-center justify-between gap-4">
        <div>
          <h3 className="text-base font-extrabold text-foreground">Kee Studio Quick Actions</h3>
          <p className="text-xs text-foreground/60">Manage your crochet inventory, launch promotions, or create AI captions</p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <button
            onClick={() => onNavigateTab("products")}
            className="bg-primary text-white text-xs font-bold px-4 py-2.5 rounded-full shadow hover:bg-primary/95 transition flex items-center gap-1.5"
          >
            <Plus className="w-4 h-4" /> Add Product
          </button>
          <button
            onClick={() => onNavigateTab("coupons")}
            className="bg-white text-foreground text-xs font-bold px-4 py-2.5 rounded-full border border-secondary/60 shadow-sm hover:bg-secondary/10 transition flex items-center gap-1.5"
          >
            <Tag className="w-4 h-4 text-primary" /> Create Coupon
          </button>
          <button
            onClick={() => onNavigateTab("ai_studio")}
            className="bg-white text-foreground text-xs font-bold px-4 py-2.5 rounded-full border border-secondary/60 shadow-sm hover:bg-secondary/10 transition flex items-center gap-1.5"
          >
            <Sparkles className="w-4 h-4 text-amber-500" /> AI Content Studio
          </button>
        </div>
      </div>

      {/* Two Column Layout: Recent Orders & Inventory Alerts */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Recent Orders */}
        <div className="lg:col-span-2 bg-white p-6 rounded-2xl border border-secondary/40 shadow-sm space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-secondary/30">
            <h3 className="font-extrabold text-base text-foreground">Recent Orders</h3>
            <button
              onClick={() => onNavigateTab("orders")}
              className="text-xs font-bold text-primary hover:underline flex items-center gap-1"
            >
              View All <ArrowUpRight className="w-3.5 h-3.5" />
            </button>
          </div>

          {orders.length === 0 ? (
            <p className="text-xs text-foreground/50 py-8 text-center">No orders recorded yet.</p>
          ) : (
            <div className="divide-y divide-secondary/20">
              {orders.slice(0, 5).map((order) => (
                <div key={order.id} className="py-3.5 flex items-center justify-between gap-4">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-mono font-bold text-xs text-foreground">{order.order_number}</span>
                      <span className={`text-[10px] font-extrabold px-2 py-0.5 rounded-full uppercase tracking-wider ${
                        order.status === "paid" || order.status === "completed" || order.status === "delivered"
                          ? "bg-emerald-100 text-emerald-800"
                          : order.status === "cancelled"
                          ? "bg-rose-100 text-rose-800"
                          : "bg-amber-100 text-amber-800"
                      }`}>
                        {order.status}
                      </span>
                    </div>
                    <p className="text-xs text-foreground/60 mt-0.5">
                      {order.shipping_address?.full_name} • {order.items?.length || 0} items
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-black text-foreground">₹{order.total.toFixed(2)}</p>
                    <p className="text-[10px] text-foreground/45">
                      {new Date(order.created_at).toLocaleDateString("en-IN", { month: "short", day: "numeric" })}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Low Stock Watchlist */}
        <div className="bg-white p-6 rounded-2xl border border-secondary/40 shadow-sm space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-secondary/30">
            <h3 className="font-extrabold text-base text-foreground flex items-center gap-1.5">
              <span>⚠️</span> Low Stock Watch
            </h3>
            <button
              onClick={() => onNavigateTab("inventory")}
              className="text-xs font-bold text-primary hover:underline"
            >
              Manage
            </button>
          </div>

          {lowStockProducts.length === 0 ? (
            <p className="text-xs text-emerald-600 font-medium py-8 text-center">
              All products are adequately stocked!
            </p>
          ) : (
            <div className="space-y-3">
              {lowStockProducts.slice(0, 5).map((p) => (
                <div key={p.id} className="flex items-center justify-between p-3 rounded-xl bg-amber-500/5 border border-amber-500/15">
                  <div className="pr-2">
                    <p className="text-xs font-bold text-foreground line-clamp-1">{p.title}</p>
                    <p className="text-[10px] text-foreground/50">₹{p.price}</p>
                  </div>
                  <span className="text-xs font-black text-amber-700 bg-amber-100 px-2 py-1 rounded-md">
                    {p.stock} left
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
