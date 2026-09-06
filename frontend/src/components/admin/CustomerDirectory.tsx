import { useState, useMemo, useEffect } from "react";
import { Search } from "lucide-react";
import { Order, api } from "@/lib/api";

interface CustomerDirectoryProps {
  orders: Order[];
}

interface CustomerRecord {
  id: string;
  name: string;
  phone: string;
  city: string;
  state: string;
  totalOrders: number;
  totalSpend: number;
  lastOrderDate: string;
}

export default function CustomerDirectory({ orders }: CustomerDirectoryProps) {
  const [search, setSearch] = useState("");
  const [serverCustomers, setServerCustomers] = useState<CustomerRecord[] | null>(null);

  useEffect(() => {
    let active = true;
    api.admin.getCustomers(search)
      .then((data) => {
        if (!active || !Array.isArray(data)) return;
        const mapped: CustomerRecord[] = data.map((d: any) => ({
          id: d.id,
          name: d.full_name || "Customer",
          phone: d.phone || "—",
          city: "—",
          state: "—",
          totalOrders: d.total_orders || 0,
          totalSpend: d.total_spend || 0,
          lastOrderDate: d.last_order_date || d.account_date || "—",
        }));
        setServerCustomers(mapped);
      })
      .catch(() => {
        // Graceful fallback to client orders
      });
    return () => { active = false; };
  }, [search]);

  const fallbackCustomers: CustomerRecord[] = useMemo(() => {
    const map = new Map<string, CustomerRecord>();

    for (const order of orders) {
      const key = order.user_id || order.shipping_address?.phone || "unknown";
      const existing = map.get(key);

      if (existing) {
        existing.totalOrders += 1;
        existing.totalSpend += order.total;
        if (new Date(order.created_at) > new Date(existing.lastOrderDate)) {
          existing.lastOrderDate = order.created_at;
        }
      } else {
        map.set(key, {
          id: key,
          name: order.shipping_address?.full_name || "Guest Customer",
          phone: order.shipping_address?.phone || "—",
          city: order.shipping_address?.city || "—",
          state: order.shipping_address?.state || "—",
          totalOrders: 1,
          totalSpend: order.total,
          lastOrderDate: order.created_at,
        });
      }
    }

    return Array.from(map.values()).sort((a, b) => b.totalSpend - a.totalSpend);
  }, [orders]);

  const displayCustomers = serverCustomers !== null ? serverCustomers : fallbackCustomers;

  const filtered = displayCustomers.filter(
    (c) =>
      c.name.toLowerCase().includes(search.toLowerCase()) ||
      c.phone.includes(search) ||
      c.city.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-black text-foreground">Customer Directory</h2>
          <p className="text-xs text-foreground/60">Registered shoppers, order frequencies, and lifetime customer values</p>
        </div>
        <div className="relative max-w-xs w-full">
          <Search className="w-4 h-4 text-foreground/40 absolute left-3 top-3" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search customers..."
            className="w-full pl-9 pr-4 py-2 rounded-xl border border-secondary text-xs focus:outline-none focus:ring-2 focus:ring-primary/45 bg-white"
          />
        </div>
      </div>

      <div className="bg-white rounded-2xl border border-secondary/40 shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-secondary/15 text-foreground/60 font-bold uppercase tracking-wider border-b border-secondary/30">
              <tr>
                <th className="p-4">Customer Name</th>
                <th className="p-4">Contact Phone</th>
                <th className="p-4">Location</th>
                <th className="p-4">Total Orders</th>
                <th className="p-4">Lifetime Spend</th>
                <th className="p-4 text-right">Last Purchase</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-secondary/20">
              {filtered.length === 0 ? (
                <tr>
                  <td colSpan={6} className="p-8 text-center text-foreground/50">
                    No customers found in directory.
                  </td>
                </tr>
              ) : (
                filtered.map((c) => (
                  <tr key={c.id} className="hover:bg-secondary/5 transition">
                    <td className="p-4 font-bold text-foreground flex items-center gap-2.5">
                      <div className="w-8 h-8 rounded-full bg-primary/10 text-primary font-black flex items-center justify-center text-xs">
                        {c.name.charAt(0).toUpperCase()}
                      </div>
                      <span>{c.name}</span>
                    </td>
                    <td className="p-4 text-foreground/75 font-mono">
                      {c.phone}
                    </td>
                    <td className="p-4 text-foreground/70">
                      {c.city}, {c.state}
                    </td>
                    <td className="p-4 font-bold text-foreground">
                      {c.totalOrders} {c.totalOrders === 1 ? "order" : "orders"}
                    </td>
                    <td className="p-4 font-black text-sm text-foreground">
                      ₹{c.totalSpend.toFixed(2)}
                    </td>
                    <td className="p-4 text-right text-foreground/60 font-mono">
                      {new Date(c.lastOrderDate).toLocaleDateString("en-IN", {
                        month: "short",
                        day: "numeric",
                        year: "numeric",
                      })}
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
