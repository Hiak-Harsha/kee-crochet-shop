"use client";

import { useState, useEffect } from "react";
import { Trash2, ShoppingBag, ArrowRight, Gift, Edit3, Check } from "lucide-react";
import Link from "next/link";
import Image from "next/image";
import Navbar from "@/components/Navbar";
import { api, Cart, CartItem } from "@/lib/api";

export default function CartPage() {
  const [cart, setCart] = useState<Cart | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [editingNoteId, setEditingNoteId] = useState<string | null>(null);
  const [tempNote, setTempNote] = useState("");

  const loadCart = async () => {
    setLoading(true);
    setError("");

    try {
      const data = await api.cart.get();
      setCart(data);
      const totalQty = (data?.items || []).reduce((acc, item) => acc + item.quantity, 0);
      localStorage.setItem("cart_count", String(totalQty));
      window.dispatchEvent(new Event("cart-updated"));
    } catch (e: any) {
      console.error("Failed to load cart", e);
      setError(e.message || "Failed to retrieve your shopping bag. Please try again.");
      setCart(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadCart();
  }, []);

  const handleUpdateQuantity = async (itemId: string, currentQty: number, delta: number) => {
    const newQty = currentQty + delta;
    if (newQty < 1) return;
    setError("");

    try {
      const updated = await api.cart.updateItem(itemId, { quantity: newQty });
      setCart(updated);
      const totalQty = (updated.items || []).reduce((acc, item) => acc + item.quantity, 0);
      localStorage.setItem("cart_count", String(totalQty));
      window.dispatchEvent(new Event("cart-updated"));
    } catch (e: any) {
      console.error("Update quantity failed", e);
      setError(e.message || "Failed to update quantity.");
    }
  };

  const handleToggleGiftWrap = async (item: CartItem) => {
    setError("");
    try {
      const updated = await api.cart.updateItem(item.id, { gift_wrap: !item.gift_wrap });
      setCart(updated);
    } catch (e: any) {
      console.error("Toggle gift wrap failed", e);
      setError(e.message || "Failed to update gift wrapping.");
    }
  };

  const handleSaveNote = async (itemId: string) => {
    setError("");
    try {
      const updated = await api.cart.updateItem(itemId, { note: tempNote });
      setCart(updated);
      setEditingNoteId(null);
      setTempNote("");
    } catch (e: any) {
      console.error("Save note failed", e);
      setError(e.message || "Failed to save note.");
    }
  };

  const handleRemoveItem = async (itemId: string) => {
    setError("");
    try {
      const updated = await api.cart.removeItem(itemId);
      setCart(updated);
      const totalQty = (updated.items || []).reduce((acc, item) => acc + item.quantity, 0);
      localStorage.setItem("cart_count", String(totalQty));
      window.dispatchEvent(new Event("cart-updated"));
    } catch (e: any) {
      console.error("Remove item failed", e);
      setError(e.message || "Failed to remove item.");
    }
  };

  if (loading) {
    return (
      <div className="flex-1 flex flex-col min-h-screen">
        <Navbar />
        <div className="flex-1 flex flex-col items-center justify-center space-y-4">
          <div className="w-10 h-10 border-4 border-primary border-t-transparent rounded-full animate-spin"></div>
          <p className="text-foreground/75 font-semibold">Tying up your shopping bag...</p>
        </div>
      </div>
    );
  }

  const items = cart?.items || [];
  const subtotal = cart?.subtotal || 0;
  const wrapFee = cart?.gift_wrap_fee || 0;
  const shippingFee = cart?.shipping_fee || 0;
  const total = cart?.total || 0;

  return (
    <div className="flex-1 flex flex-col min-h-screen">
      <Navbar />

      <main className="max-w-7xl mx-auto w-full px-4 sm:px-6 lg:px-8 py-10 flex-1">
        <h1 className="text-3xl font-extrabold text-foreground mb-8">Shopping Bag</h1>

        {error && (
          <div className="mb-6 bg-rose-50 border border-rose-200 text-rose-800 text-sm font-bold p-4 rounded-xl flex items-center gap-2">
            <span>⚠️</span> {error}
          </div>
        )}

        {items.length === 0 ? (
          <div className="text-center py-20 bg-white border border-secondary/50 rounded-cozy space-y-4">
            <ShoppingBag className="w-16 h-16 mx-auto text-secondary/70 animate-bounce-slow" />
            <h2 className="text-xl font-bold text-foreground">Your bag is empty!</h2>
            <p className="text-sm text-foreground/60 max-w-xs mx-auto">Fill it with soft, handcrafted crochet creations made with love.</p>
            <Link href="/products" className="bg-primary text-white px-8 py-3 rounded-full font-bold shadow inline-block">
              Explore Collections
            </Link>
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            {/* Cart Items List */}
            <div className="lg:col-span-2 space-y-6">
              {items.map((item) => (
                <div key={item.id} className="bg-white p-6 rounded-cozy border border-secondary/50 flex space-x-6 hover:shadow transition relative">
                  <div className="relative w-24 h-24 rounded-xl overflow-hidden bg-secondary/15 flex-shrink-0 border border-secondary/30">
                    <Image
                      src={item.product?.images?.[0] || "/images/category_bouquets.jpg"}
                      alt={item.product?.title || "Crochet item"}
                      fill
                      className="object-cover"
                      sizes="96px"
                    />
                  </div>

                  <div className="flex-1 space-y-2">
                    <div className="flex justify-between items-start gap-4">
                      <div>
                        <h3 className="font-extrabold text-base text-foreground line-clamp-1">{item.product?.title}</h3>
                        {item.variant_id && item.product?.variants && (
                          <p className="text-xs text-foreground/60">
                            Variant: {item.product.variants.find((v) => v.id === item.variant_id)?.name} - {item.product.variants.find((v) => v.id === item.variant_id)?.value}
                          </p>
                        )}
                      </div>
                      <button onClick={() => handleRemoveItem(item.id)} className="text-foreground/45 hover:text-red-500 transition" title="Remove item">
                        <Trash2 className="w-5 h-5" />
                      </button>
                    </div>

                    <p className="text-sm font-black text-primary">₹{item.unit_price}</p>

                    {/* Gift wrap & personalization note */}
                    <div className="space-y-2 pt-1">
                      <div className="flex items-center gap-3">
                        <button
                          onClick={() => handleToggleGiftWrap(item)}
                          className={`text-xs px-2.5 py-1 rounded-full font-bold border transition flex items-center gap-1.5 ${
                            item.gift_wrap
                              ? "bg-primary text-white border-primary"
                              : "bg-secondary/10 text-foreground/70 border-secondary/30 hover:border-primary"
                          }`}
                        >
                          <Gift className="w-3.5 h-3.5" />
                          {item.gift_wrap ? "Gift Wrapped (+₹50)" : "Add Gift Wrap (+₹50)"}
                        </button>

                        <button
                          onClick={() => {
                            if (editingNoteId === item.id) {
                              setEditingNoteId(null);
                            } else {
                              setEditingNoteId(item.id);
                              setTempNote(item.note || "");
                            }
                          }}
                          className="text-xs text-primary hover:underline font-semibold flex items-center gap-1"
                        >
                          <Edit3 className="w-3.5 h-3.5" />
                          {item.note ? "Edit note" : "Add note"}
                        </button>
                      </div>

                      {editingNoteId === item.id ? (
                        <div className="flex items-center gap-2 pt-1">
                          <input
                            type="text"
                            value={tempNote}
                            onChange={(e) => setTempNote(e.target.value)}
                            placeholder="Personalization note..."
                            maxLength={150}
                            className="text-xs border border-secondary rounded-lg px-2.5 py-1 flex-1 focus:outline-none focus:border-primary"
                          />
                          <button
                            onClick={() => handleSaveNote(item.id)}
                            className="bg-primary text-white text-xs px-2.5 py-1 rounded-lg font-bold flex items-center gap-1"
                          >
                            <Check className="w-3.5 h-3.5" /> Save
                          </button>
                        </div>
                      ) : (
                        item.note && (
                          <p className="text-xs text-foreground/70 bg-secondary/10 px-2.5 py-1 rounded-lg">
                            <span className="font-bold text-foreground">Note:</span> {item.note}
                          </p>
                        )
                      )}
                    </div>

                    <div className="flex items-center justify-between pt-2">
                      <div className="flex items-center border border-secondary rounded-full px-2 py-0.5 bg-white">
                        <button
                          onClick={() => handleUpdateQuantity(item.id, item.quantity, -1)}
                          className="px-2 font-bold text-foreground/50 hover:text-primary"
                        >
                          -
                        </button>
                        <span className="px-3 text-sm font-bold text-foreground">{item.quantity}</span>
                        <button
                          onClick={() => handleUpdateQuantity(item.id, item.quantity, 1)}
                          className="px-2 font-bold text-foreground/50 hover:text-primary"
                        >
                          +
                        </button>
                      </div>
                      <span className="font-extrabold text-foreground text-sm">
                        Total: ₹{item.total_price || (item.unit_price * item.quantity)}
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>

            {/* Authoritative Order Summary Card */}
            <div className="lg:col-span-1">
              <div className="bg-white p-6 rounded-cozy border border-secondary/50 shadow-sm space-y-6 sticky top-24">
                <h3 className="font-bold text-lg text-foreground border-b border-secondary/30 pb-4">Order Summary</h3>

                <div className="space-y-3 text-sm">
                  <div className="flex justify-between text-foreground/80">
                    <span>Subtotal</span>
                    <span className="font-semibold">₹{subtotal.toFixed(2)}</span>
                  </div>
                  {wrapFee > 0 && (
                    <div className="flex justify-between text-foreground/80">
                      <span>Gift Wrapping Fee</span>
                      <span className="font-semibold">₹{wrapFee.toFixed(2)}</span>
                    </div>
                  )}
                  <div className="flex justify-between text-foreground/80">
                    <span>Shipping Fee</span>
                    <span>{shippingFee === 0 ? <span className="text-emerald-600 font-bold">FREE</span> : <span className="font-semibold">₹{shippingFee.toFixed(2)}</span>}</span>
                  </div>
                  {shippingFee > 0 && subtotal < 999 && (
                    <p className="text-[11px] text-foreground/60 bg-amber-50 border border-amber-200 p-2 rounded-lg">
                      Add ₹{(999 - subtotal).toFixed(2)} more to qualify for <span className="font-bold text-emerald-700">Free Shipping</span>!
                    </p>
                  )}

                  <div className="flex justify-between text-base font-extrabold text-foreground border-t border-secondary/30 pt-4">
                    <span>Estimated Total</span>
                    <span className="text-primary text-xl">₹{total.toFixed(2)}</span>
                  </div>
                </div>

                <Link
                  href="/checkout"
                  className="w-full bg-primary text-white hover:bg-primary/95 py-3.5 rounded-full font-bold shadow flex items-center justify-center gap-2 text-base transition"
                >
                  Proceed to Checkout <ArrowRight className="w-5 h-5" />
                </Link>

                <div className="text-center pt-2">
                  <Link href="/products" className="text-xs text-primary hover:underline font-bold">
                    Continue Shopping
                  </Link>
                </div>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
