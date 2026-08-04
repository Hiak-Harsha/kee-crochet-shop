"use client";

import { useState, useEffect } from "react";
import { Trash2, ShoppingBag, ArrowRight, Heart, Gift } from "lucide-react";
import Link from "next/link";
import Image from "next/image";
import Navbar from "@/components/Navbar";
import { api } from "@/lib/api";

export default function CartPage() {
  const [cart, setCart] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  // Load cart data
  const [error, setError] = useState("");

  const loadCart = async () => {
    setLoading(true);
    setError("");
    let itemsList = [];
    try {
      const data = await api.cart.get();
      setCart(data);
      itemsList = data?.items || [];
    } catch (e: any) {
      console.error("Failed to load backend cart", e);
      setError("Failed to retrieve your shopping bag. Please sign in or check if the backend is online.");
      setCart(null);
    }
    
    // Update local cart count
    const totalQty = itemsList.reduce((acc: number, item: any) => acc + item.quantity, 0);
    localStorage.setItem("cart_count", String(totalQty));
    window.dispatchEvent(new Event("cart-updated"));
    
    setLoading(false);
  };

  useEffect(() => {
    loadCart();
  }, []);

  const handleUpdateQuantity = async (itemId: string, currentQty: number, delta: number) => {
    const newQty = currentQty + delta;
    if (newQty < 1) return;
    setError("");

    try {
      await api.cart.updateItem(itemId, { quantity: newQty });
      loadCart();
    } catch (e: any) {
      console.error("Backend update failed", e);
      setError(e.message || "Failed to update item quantity in shopping bag.");
    }
  };

  const handleRemoveItem = async (itemId: string) => {
    setError("");
    try {
      await api.cart.removeItem(itemId);
      loadCart();
    } catch (e: any) {
      console.error("Backend delete failed", e);
      setError(e.message || "Failed to remove item from shopping bag.");
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
  const subtotal = items.reduce((acc: number, item: any) => acc + (item.product.price * item.quantity), 0);
  const wrapFee = items.filter((i: any) => i.gift_wrap).length * 40;
  const shippingFee = subtotal >= 999 ? 0 : 60;
  const total = subtotal + wrapFee + shippingFee;

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
            <p className="text-sm text-foreground/60 max-w-xs mx-auto">Fill it with some soft, handmade crochet items today.</p>
            <Link href="/products" className="bg-primary text-white px-8 py-3 rounded-full font-bold shadow inline-block">
              Shop Collections
            </Link>
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            {/* Cart Items List */}
            <div className="lg:col-span-2 space-y-6">
              {items.map((item: any) => (
                <div key={item.id} className="bg-white p-6 rounded-cozy border border-secondary/50 flex space-x-6 hover:shadow transition relative">
                  <div className="relative w-24 h-24 rounded-xl overflow-hidden bg-secondary/15 flex-shrink-0 border border-secondary/30">
                    <Image
                      src={item.product?.images?.[0] || "/images/category_bouquets.jpg"}
                      alt={item.product?.title || "Crochet product"}
                      fill
                      className="object-cover"
                      sizes="96px"
                    />
                  </div>

                  <div className="flex-1 space-y-2">
                    <div className="flex justify-between items-start gap-4">
                      <h3 className="font-extrabold text-base text-foreground line-clamp-1">{item.product?.title}</h3>
                      <button onClick={() => handleRemoveItem(item.id)} className="text-foreground/45 hover:text-red-500 transition">
                        <Trash2 className="w-5 h-5" />
                      </button>
                    </div>

                    <p className="text-sm font-black text-primary">₹{item.product?.price}</p>
                    
                    {/* Item Customizations */}
                    {(item.gift_wrap || item.note) && (
                      <div className="bg-primary/5 border border-primary/10 px-3.5 py-2 rounded-lg text-xs space-y-1">
                        {item.gift_wrap && (
                          <p className="font-bold text-primary flex items-center gap-1">
                            <Gift className="w-3.5 h-3.5" /> Gift-wrapped (+₹40)
                          </p>
                        )}
                        {item.note && (
                          <p className="text-foreground/75">
                            <span className="font-bold">Note:</span> "{item.note}"
                          </p>
                        )}
                      </div>
                    )}

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
                        Total: ₹{item.product?.price * item.quantity}
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>

            {/* Order Summary Checkout Card */}
            <div className="lg:col-span-1">
              <div className="bg-white p-6 rounded-cozy border border-secondary/50 shadow-sm space-y-6">
                <h3 className="font-bold text-lg text-foreground border-b border-secondary/30 pb-4">Order Summary</h3>
                
                <div className="space-y-3 text-sm">
                  <div className="flex justify-between text-foreground/80">
                    <span>Subtotal</span>
                    <span>₹{subtotal}</span>
                  </div>
                  {wrapFee > 0 && (
                    <div className="flex justify-between text-foreground/80">
                      <span>Gift Wrapping Fee</span>
                      <span>₹{wrapFee}</span>
                    </div>
                  )}
                  <div className="flex justify-between text-foreground/80">
                    <span>Shipping Fee</span>
                    <span>{shippingFee === 0 ? <span className="text-emerald-600 font-bold">FREE</span> : `₹${shippingFee}`}</span>
                  </div>
                  {shippingFee > 0 && (
                    <p className="text-[10px] text-foreground/50">
                      Add ₹{999 - subtotal} more to qualify for Free Shipping!
                    </p>
                  )}
                  
                  <div className="flex justify-between text-base font-extrabold text-foreground border-t border-secondary/30 pt-4">
                    <span>Order Total</span>
                    <span>₹{total}</span>
                  </div>
                </div>

                <Link
                  href="/checkout"
                  className="w-full bg-primary text-white hover:bg-primary/95 py-3 rounded-full font-bold shadow flex items-center justify-center gap-2 text-sm sm:text-base transition"
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
