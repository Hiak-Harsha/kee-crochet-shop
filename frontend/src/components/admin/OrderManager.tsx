"use client";

import { useState } from "react";
import { Eye, X, Check, AlertCircle, ChevronLeft, ChevronRight, Phone, MapPin, Gift, Clock } from "lucide-react";
import { api, Order } from "@/lib/api";

interface OrderManagerProps {
  orders: Order[];
  ordersPage: number;
  onPageChange: (page: number) => void;
  onRefresh: () => void;
}

const ORDER_STATUS_COLORS: Record<string, string> = {
  pending_payment: "bg-amber-100 text-amber-800",
  paid: "bg-emerald-100 text-emerald-800",
  processing: "bg-blue-100 text-blue-800",
  packed: "bg-indigo-100 text-indigo-800",
  shipped: "bg-purple-100 text-purple-800",
  delivered: "bg-teal-100 text-teal-800",
  completed: "bg-green-100 text-green-800",
  cancelled: "bg-rose-100 text-rose-800",
  refunded: "bg-gray-100 text-gray-700",
};

export default function OrderManager({
  orders,
  ordersPage,
  onPageChange,
  onRefresh,
}: OrderManagerProps) {
  const [selectedOrder, setSelectedOrder] = useState<Order | null>(null);
  const [statusFilter, setStatusFilter] = useState("all");
  const [updatingId, setUpdatingId] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const filteredOrders = statusFilter === "all"
    ? orders
    : orders.filter((o) => o.status === statusFilter);

  const handleUpdateStatus = async (orderId: string, newStatus: string) => {
    setUpdatingId(orderId);
    setError("");
    setSuccess("");

    try {
      const updated = await api.orders.adminUpdateStatus(orderId, newStatus);
      if (selectedOrder && selectedOrder.id === orderId) {
        setSelectedOrder(updated);
      }
      setSuccess(`Order updated to ${newStatus}`);
      onRefresh();
      setTimeout(() => setSuccess(""), 2500);
    } catch (err: any) {
      console.error("Order status update failed:", err);
      setError(err.message || "Failed to update order status.");
    } finally {
      setUpdatingId(null);
    }
  };

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-black text-foreground">Order Fulfillment</h2>
          <p className="text-xs text-foreground/60">Track shipments, verify payments, and manage order lifecycle</p>
        </div>

        {/* Filter Pills */}
        <div className="flex flex-wrap gap-1.5 bg-secondary/20 p-1 rounded-xl text-xs font-bold">
          {["all", "paid", "processing", "packed", "shipped", "delivered", "cancelled"].map((st) => (
            <button
              key={st}
              onClick={() => setStatusFilter(st)}
              className={`px-3 py-1 rounded-lg capitalize transition ${
                statusFilter === st ? "bg-white text-foreground shadow-sm" : "text-foreground/60 hover:text-foreground"
              }`}
            >
              {st}
            </button>
          ))}
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

      {/* Orders Table */}
      <div className="bg-white rounded-2xl border border-secondary/40 shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-secondary/15 text-foreground/60 font-bold uppercase tracking-wider border-b border-secondary/30">
              <tr>
                <th className="p-4">Order Ref</th>
                <th className="p-4">Customer</th>
                <th className="p-4">Date</th>
                <th className="p-4">Total</th>
                <th className="p-4">Status</th>
                <th className="p-4">Quick Action</th>
                <th className="p-4 text-right">Details</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-secondary/20">
              {filteredOrders.length === 0 ? (
                <tr>
                  <td colSpan={7} className="p-8 text-center text-foreground/50">
                    No orders found matching this filter.
                  </td>
                </tr>
              ) : (
                filteredOrders.map((order) => (
                  <tr key={order.id} className="hover:bg-secondary/5 transition">
                    <td className="p-4 font-mono font-bold text-foreground">
                      {order.order_number}
                    </td>
                    <td className="p-4">
                      <p className="font-bold text-foreground">{order.shipping_address?.full_name}</p>
                      <p className="text-[10px] text-foreground/50">{order.shipping_address?.city}, {order.shipping_address?.state}</p>
                    </td>
                    <td className="p-4 text-foreground/70">
                      {new Date(order.created_at).toLocaleDateString("en-IN", {
                        month: "short",
                        day: "numeric",
                        year: "numeric",
                      })}
                    </td>
                    <td className="p-4 font-black text-sm text-foreground">
                      ₹{order.total.toFixed(2)}
                    </td>
                    <td className="p-4">
                      <span className={`px-2.5 py-1 rounded-full text-[10px] font-black uppercase tracking-wider ${
                        ORDER_STATUS_COLORS[order.status] || "bg-gray-100 text-gray-800"
                      }`}>
                        {order.status}
                      </span>
                    </td>
                    <td className="p-4">
                      <select
                        value={order.status}
                        onChange={(e) => handleUpdateStatus(order.id, e.target.value)}
                        disabled={updatingId === order.id}
                        className="bg-white border border-secondary text-xs font-semibold rounded-lg px-2.5 py-1 focus:outline-none focus:border-primary"
                      >
                        <option value="pending_payment">Pending Payment</option>
                        <option value="paid">Paid</option>
                        <option value="processing">Processing</option>
                        <option value="packed">Packed</option>
                        <option value="shipped">Shipped</option>
                        <option value="delivered">Delivered</option>
                        <option value="completed">Completed</option>
                        <option value="cancelled">Cancelled</option>
                        <option value="refunded">Refunded</option>
                      </select>
                    </td>
                    <td className="p-4 text-right">
                      <button
                        onClick={() => setSelectedOrder(order)}
                        className="p-1.5 text-foreground/50 hover:text-primary transition rounded-lg hover:bg-secondary/15"
                        title="View order details"
                      >
                        <Eye className="w-4 h-4" />
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination Bar */}
        <div className="p-4 border-t border-secondary/20 flex items-center justify-between text-xs text-foreground/60">
          <span>Page {ordersPage}</span>
          <div className="flex items-center gap-2">
            <button
              onClick={() => onPageChange(Math.max(1, ordersPage - 1))}
              disabled={ordersPage <= 1}
              className="px-3 py-1.5 rounded-lg border border-secondary disabled:opacity-40 flex items-center gap-1 font-bold"
            >
              <ChevronLeft className="w-3.5 h-3.5" /> Prev
            </button>
            <button
              onClick={() => onPageChange(ordersPage + 1)}
              disabled={orders.length < 10}
              className="px-3 py-1.5 rounded-lg border border-secondary disabled:opacity-40 flex items-center gap-1 font-bold"
            >
              Next <ChevronRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>

      {/* Order Detail Modal */}
      {selectedOrder && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4 overflow-y-auto animate-fade-in">
          <div className="bg-white rounded-2xl border border-secondary/40 shadow-2xl max-w-xl w-full p-6 sm:p-8 space-y-6 my-8 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between pb-4 border-b border-secondary/30">
              <div>
                <h3 className="text-lg font-black text-foreground">Order {selectedOrder.order_number}</h3>
                <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-black uppercase tracking-wider ${
                  ORDER_STATUS_COLORS[selectedOrder.status] || "bg-gray-100 text-gray-800"
                }`}>
                  {selectedOrder.status}
                </span>
              </div>
              <button onClick={() => setSelectedOrder(null)} className="text-foreground/40 hover:text-foreground">
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Customer & Address */}
            <div className="bg-secondary/10 p-4 rounded-xl space-y-2 text-xs">
              <p className="font-bold text-foreground text-sm">{selectedOrder.shipping_address?.full_name}</p>
              <p className="flex items-center gap-1.5 text-foreground/75">
                <Phone className="w-3.5 h-3.5 text-foreground/40" /> {selectedOrder.shipping_address?.phone}
              </p>
              <p className="flex items-start gap-1.5 text-foreground/75">
                <MapPin className="w-3.5 h-3.5 text-foreground/40 mt-0.5 flex-shrink-0" />
                {selectedOrder.shipping_address?.address_line1}
                {selectedOrder.shipping_address?.address_line2 && `, ${selectedOrder.shipping_address?.address_line2}`}, {selectedOrder.shipping_address?.city}, {selectedOrder.shipping_address?.state} - {selectedOrder.shipping_address?.postal_code}
              </p>
              {selectedOrder.delivery_slot && (
                <p className="flex items-center gap-1.5 text-primary font-bold pt-1">
                  <Clock className="w-3.5 h-3.5" /> Slot: {selectedOrder.delivery_slot}
                </p>
              )}
            </div>

            {/* Items List */}
            <div className="space-y-3">
              <h4 className="font-bold text-xs uppercase tracking-wider text-foreground/50">Purchased Items</h4>
              <div className="divide-y divide-secondary/20">
                {selectedOrder.items?.map((item) => (
                  <div key={item.id} className="py-3 flex justify-between items-start gap-4 text-xs">
                    <div>
                      <p className="font-bold text-foreground">{item.product_title}</p>
                      {item.variant_name && (
                        <p className="text-[10px] text-foreground/50 font-mono">SKU: {item.sku} ({item.variant_name})</p>
                      )}
                      <p className="text-foreground/60 mt-0.5">Qty: {item.quantity} × ₹{item.unit_price}</p>
                      {item.gift_wrap && (
                        <p className="text-[10px] text-primary font-bold flex items-center gap-1 mt-1">
                          <Gift className="w-3 h-3" /> Gift Wrapped
                        </p>
                      )}
                      {item.note && (
                        <p className="text-[11px] text-foreground/70 bg-secondary/15 p-1.5 rounded mt-1">
                          "{item.note}"
                        </p>
                      )}
                    </div>
                    <span className="font-extrabold text-foreground">
                      ₹{item.total_price ? item.total_price.toFixed(2) : (item.unit_price * item.quantity).toFixed(2)}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* Financial Summary */}
            <div className="bg-secondary/5 p-4 rounded-xl space-y-2 text-xs border border-secondary/20">
              <div className="flex justify-between text-foreground/75">
                <span>Subtotal</span>
                <span>₹{selectedOrder.subtotal.toFixed(2)}</span>
              </div>
              {selectedOrder.gift_wrap_fee > 0 && (
                <div className="flex justify-between text-foreground/75">
                  <span>Gift Wrap Fee</span>
                  <span>₹{selectedOrder.gift_wrap_fee.toFixed(2)}</span>
                </div>
              )}
              <div className="flex justify-between text-foreground/75">
                <span>Shipping Fee</span>
                <span>₹{selectedOrder.shipping_fee.toFixed(2)}</span>
              </div>
              {selectedOrder.coupon_discount > 0 && (
                <div className="flex justify-between text-emerald-700 font-bold">
                  <span>Coupon Discount ({selectedOrder.coupon_code})</span>
                  <span>-₹{selectedOrder.coupon_discount.toFixed(2)}</span>
                </div>
              )}
              <div className="flex justify-between font-black text-sm text-foreground pt-2 border-t border-secondary/20">
                <span>Total Paid</span>
                <span className="text-primary text-base">₹{selectedOrder.total.toFixed(2)}</span>
              </div>
            </div>

            {/* Gateway Info */}
            <div className="text-[11px] font-mono text-foreground/50 space-y-1">
              <p>Razorpay Order: {selectedOrder.razorpay_order_id || "N/A"}</p>
              <p>Payment ID: {selectedOrder.razorpay_payment_id || "N/A"}</p>
            </div>

            <div className="flex justify-end pt-4 border-t border-secondary/30">
              <button
                type="button"
                onClick={() => setSelectedOrder(null)}
                className="px-5 py-2.5 rounded-full bg-secondary/20 hover:bg-secondary/30 text-xs font-bold text-foreground transition"
              >
                Close Details
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
