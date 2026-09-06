"use client";

import { useMemo } from "react";
import { Award } from "lucide-react";
import { Order } from "@/lib/api";

interface StoreAnalyticsProps {
  orders: Order[];
  stats: {
    total_sales: number;
    total_orders: number;
    average_order_value: number;
  };
}

export default function StoreAnalytics({
  orders,
  stats,
}: StoreAnalyticsProps) {
  // Compute top performing products
  const topProducts = useMemo(() => {
    const productStats = new Map<string, { title: string; count: number; revenue: number }>();

    for (const order of orders) {
      if (order.status === "cancelled" || order.status === "refunded") continue;
      for (const item of order.items || []) {
        const key = item.product_id;
        const existing = productStats.get(key);
        if (existing) {
          existing.count += item.quantity;
          existing.revenue += item.total_price || (item.unit_price * item.quantity);
        } else {
          productStats.set(key, {
            title: item.product_title,
            count: item.quantity,
            revenue: item.total_price || (item.unit_price * item.quantity),
          });
        }
      }
    }

    return Array.from(productStats.values())
      .sort((a, b) => b.revenue - a.revenue)
      .slice(0, 5);
  }, [orders]);

  // Adoption statistics
  const giftWrapOrders = orders.filter((o) => o.gift_wrap_fee > 0).length;
  const giftWrapPercentage = orders.length > 0 ? ((giftWrapOrders / orders.length) * 100).toFixed(1) : "0";

  const freeShippingOrders = orders.filter((o) => o.shipping_fee === 0).length;
  const freeShippingPercentage = orders.length > 0 ? ((freeShippingOrders / orders.length) * 100).toFixed(1) : "0";

  return (
    <div className="space-y-8 animate-fade-in">
      <div>
        <h2 className="text-xl font-black text-foreground">Commerce Analytics & Trends</h2>
        <p className="text-xs text-foreground/60">Comprehensive order performance, popular collections, and customer purchase behaviors</p>
      </div>

      {/* KPI Overview */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        <div className="bg-white p-6 rounded-2xl border border-secondary/40 shadow-sm">
          <p className="text-xs font-bold uppercase tracking-wider text-foreground/50">Gross Revenue</p>
          <p className="text-2xl font-black text-foreground mt-1">₹{stats.total_sales.toFixed(2)}</p>
          <p className="text-[11px] text-emerald-600 font-bold mt-1">Server-verified sales</p>
        </div>

        <div className="bg-white p-6 rounded-2xl border border-secondary/40 shadow-sm">
          <p className="text-xs font-bold uppercase tracking-wider text-foreground/50">Average Order Value</p>
          <p className="text-2xl font-black text-foreground mt-1">₹{stats.average_order_value.toFixed(2)}</p>
          <p className="text-[11px] text-foreground/50 font-semibold mt-1">Per transaction</p>
        </div>

        <div className="bg-white p-6 rounded-2xl border border-secondary/40 shadow-sm">
          <p className="text-xs font-bold uppercase tracking-wider text-foreground/50">Gift Wrap Adoption</p>
          <p className="text-2xl font-black text-purple-700 mt-1">{giftWrapPercentage}%</p>
          <p className="text-[11px] text-purple-600 font-semibold mt-1">{giftWrapOrders} orders gift-wrapped</p>
        </div>

        <div className="bg-white p-6 rounded-2xl border border-secondary/40 shadow-sm">
          <p className="text-xs font-bold uppercase tracking-wider text-foreground/50">Free Shipping Ratio</p>
          <p className="text-2xl font-black text-emerald-700 mt-1">{freeShippingPercentage}%</p>
          <p className="text-[11px] text-emerald-600 font-semibold mt-1">Orders &gt;= ₹999</p>
        </div>
      </div>

      {/* Top Products Table */}
      <div className="bg-white p-6 rounded-2xl border border-secondary/40 shadow-sm space-y-4">
        <h3 className="font-extrabold text-base text-foreground flex items-center gap-2">
          <Award className="w-5 h-5 text-amber-500" /> Best Selling Crochet Creations
        </h3>

        {topProducts.length === 0 ? (
          <p className="text-xs text-foreground/50 py-8 text-center">No sales records to rank best sellers yet.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-secondary/15 text-foreground/60 font-bold uppercase tracking-wider border-b border-secondary/30">
                <tr>
                  <th className="p-3">Rank</th>
                  <th className="p-3">Product Name</th>
                  <th className="p-3">Units Sold</th>
                  <th className="p-3 text-right">Revenue Generated</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-secondary/20">
                {topProducts.map((tp, idx) => (
                  <tr key={idx} className="hover:bg-secondary/5 transition">
                    <td className="p-3 font-bold text-foreground">
                      <span className="w-6 h-6 rounded-full bg-secondary/20 flex items-center justify-center text-xs font-black">
                        #{idx + 1}
                      </span>
                    </td>
                    <td className="p-3 font-bold text-foreground">{tp.title}</td>
                    <td className="p-3 font-semibold text-foreground/80">{tp.count} units</td>
                    <td className="p-3 font-black text-foreground text-right">₹{tp.revenue.toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
