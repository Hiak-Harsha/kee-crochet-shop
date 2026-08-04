"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Shield, Sparkles, CreditCard, Clock, Calendar, Check, AlertCircle } from "lucide-react";
import Navbar from "@/components/Navbar";
import { api } from "@/lib/api";

export default function CheckoutPage() {
  const router = useRouter();

  // Form Fields
  const [fullName, setFullName] = useState("");
  const [addressLine1, setAddressLine1] = useState("");
  const [addressLine2, setAddressLine2] = useState("");
  const [city, setCity] = useState("");
  const [state, setState] = useState("");
  const [postalCode, setPostalCode] = useState("");
  const [phone, setPhone] = useState("");
  const [deliverySlot, setDeliverySlot] = useState("standard");
  const [couponCode, setCouponCode] = useState("");

  // Payment/Order Flow States
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [createdOrder, setCreatedOrder] = useState<any>(null);
  
  // Razorpay Mock Dialog
  const [showRzpModal, setShowRzpModal] = useState(false);
  const [paying, setPaying] = useState(false);
  const [paymentSuccess, setPaymentSuccess] = useState(false);

  // Cart preview info
  const [cartPreview, setCartPreview] = useState<any>(null);

  // Load Razorpay Checkout SDK dynamically on mount
  useEffect(() => {
    const script = document.createElement("script");
    script.src = "https://checkout.razorpay.com/v1/checkout.js";
    script.async = true;
    document.body.appendChild(script);
    return () => {
      document.body.removeChild(script);
    };
  }, []);

  useEffect(() => {
    // Load cart summary
    const loadCartPreview = async () => {
      try {
        const data = await api.cart.get();
        if (!data || !data.items || data.items.length === 0) {
          setError("Your shopping bag is empty. Please add items to checkout.");
          router.push("/cart");
          return;
        }
        setCartPreview(data);
      } catch (e: any) {
        console.error("Failed to load cart summary:", e);
        setError("Failed to retrieve your shopping bag details. Please verify your connection.");
      }
    };
    loadCartPreview();
  }, [router]);

  const handlePlaceOrder = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!fullName || !addressLine1 || !city || !state || !postalCode || !phone) {
      setError("Please fill in all required shipping fields");
      return;
    }
    setError("");
    setLoading(true);

    const payload = {
      shipping_address: {
        full_name: fullName,
        address_line1: addressLine1,
        address_line2: addressLine2 || null,
        city: city,
        state: state,
        postal_code: postalCode,
        country: "India",
        phone: phone,
      },
      coupon_code: couponCode.trim() || null,
    };

    try {
      const order = await api.orders.create(payload);
      setCreatedOrder(order);

      // Check if this is a mock order (sandbox mode when Razorpay credentials are not configured)
      if (order.razorpay_order_id && order.razorpay_order_id.startsWith("rzp_mock")) {
        setShowRzpModal(true);
        setLoading(false);
      } else {
        // Trigger the REAL Razorpay Checkout SDK
        if (!(window as any).Razorpay) {
          throw new Error("Razorpay payment gateway SDK failed to load. Please verify your connection.");
        }
        
        const options = {
          key: process.env.NEXT_PUBLIC_RAZORPAY_KEY_ID || "rzp_test_51P2c114389025",
          amount: Math.round(order.total * 100), // Amount in paise
          currency: "INR",
          name: "Kee Crochet",
          description: "Handcrafted Crochet Order Purchase",
          order_id: order.razorpay_order_id,
          handler: async function (response: any) {
            setPaying(true);
            try {
              const verifyPayload = {
                order_id: order.id,
                razorpay_order_id: response.razorpay_order_id,
                razorpay_payment_id: response.razorpay_payment_id,
                razorpay_signature: response.razorpay_signature,
              };
              await api.orders.verifyPayment(verifyPayload);
              setPaymentSuccess(true);
              
              // Clear cart counts
              localStorage.setItem("cart_count", "0");
              window.dispatchEvent(new Event("cart-updated"));
              
              setTimeout(() => {
                router.push("/dashboard?tab=orders");
              }, 2000);
            } catch (vErr: any) {
              console.error("Payment verification failed:", vErr);
              setError(vErr.message || "Payment verification failed. Please contact support.");
            } finally {
              setPaying(false);
            }
          },
          prefill: {
            name: fullName,
            contact: phone,
          },
          theme: {
            color: "#d97706",
          },
          modal: {
            ondismiss: function () {
              setLoading(false);
              setError("Payment was cancelled by the user.");
            },
          },
        };
        const rzp = new (window as any).Razorpay(options);
        rzp.open();
      }
    } catch (err: any) {
      console.error("Backend order creation failed:", err);
      setError(err.message || "Failed to place order. Please review stock or details and try again.");
      setLoading(false);
    }
  };

  const handleMockPaymentSuccess = async () => {
    if (!createdOrder) return;
    setPaying(true);
    setError("");

    const verifyPayload = {
      order_id: createdOrder.id,
      razorpay_order_id: createdOrder.razorpay_order_id || "rzp_mock_order_12345",
      razorpay_payment_id: `pay_mock_${Math.random().toString(36).substring(2, 10)}`,
      razorpay_signature: "mock_signature"
    };

    try {
      await api.orders.verifyPayment(verifyPayload);
      setPaymentSuccess(true);
      
      // Clear cart counts
      localStorage.setItem("cart_count", "0");
      window.dispatchEvent(new Event("cart-updated"));

      setTimeout(() => {
        setShowRzpModal(false);
        router.push("/dashboard?tab=orders");
      }, 2000);
    } catch (e: any) {
      console.error("Mock payment verification failed", e);
      setError(e.message || "Mock payment verification failed.");
    } finally {
      setPaying(false);
    }
  };

  const subtotal = cartPreview?.subtotal || 0;
  const shippingFee = subtotal >= 999 ? 0 : 60;
  const total = subtotal + shippingFee;

  return (
    <div className="flex-1 flex flex-col min-h-screen">
      <Navbar />

      <main className="max-w-7xl mx-auto w-full px-4 sm:px-6 lg:px-8 py-10 flex-1">
        <h1 className="text-3xl font-extrabold text-foreground mb-8">Checkout</h1>

        {error && (
          <div className="mb-6 bg-rose-50 border border-rose-200 text-rose-800 text-sm font-bold p-4 rounded-xl flex items-center gap-2">
            <AlertCircle className="w-5 h-5 text-rose-600" /> {error}
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Shipping Form Panel */}
          <form onSubmit={handlePlaceOrder} className="lg:col-span-2 space-y-6 bg-white p-6 sm:p-8 rounded-cozy border border-secondary/50 shadow-sm">
            <h2 className="font-extrabold text-lg text-foreground pb-4 border-b border-secondary/30">Shipping Details</h2>
            
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
              <div className="sm:col-span-2 space-y-1.5">
                <label className="text-xs font-bold text-foreground/75">Full Name *</label>
                <input
                  type="text"
                  required
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  className="w-full p-3 rounded-xl border border-secondary bg-white focus:outline-none focus:ring-2 focus:ring-primary/45 text-sm"
                  placeholder="e.g. Madhav Nair"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-bold text-foreground/75">Phone Number *</label>
                <input
                  type="tel"
                  required
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  className="w-full p-3 rounded-xl border border-secondary bg-white focus:outline-none focus:ring-2 focus:ring-primary/45 text-sm"
                  placeholder="e.g. 9876543210"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-bold text-foreground/75">Postal/Pin Code *</label>
                <input
                  type="text"
                  required
                  value={postalCode}
                  onChange={(e) => setPostalCode(e.target.value)}
                  className="w-full p-3 rounded-xl border border-secondary bg-white focus:outline-none focus:ring-2 focus:ring-primary/45 text-sm"
                  placeholder="e.g. 411001"
                />
              </div>

              <div className="sm:col-span-2 space-y-1.5">
                <label className="text-xs font-bold text-foreground/75">Street Address Line 1 *</label>
                <input
                  type="text"
                  required
                  value={addressLine1}
                  onChange={(e) => setAddressLine1(e.target.value)}
                  className="w-full p-3 rounded-xl border border-secondary bg-white focus:outline-none focus:ring-2 focus:ring-primary/45 text-sm"
                  placeholder="e.g. Flat 402, Cozy Greens Apartment"
                />
              </div>

              <div className="sm:col-span-2 space-y-1.5">
                <label className="text-xs font-bold text-foreground/75">Address Line 2 (Optional)</label>
                <input
                  type="text"
                  value={addressLine2}
                  onChange={(e) => setAddressLine2(e.target.value)}
                  className="w-full p-3 rounded-xl border border-secondary bg-white focus:outline-none focus:ring-2 focus:ring-primary/45 text-sm"
                  placeholder="e.g. near Main Market, Aundh"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-bold text-foreground/75">City *</label>
                <input
                  type="text"
                  required
                  value={city}
                  onChange={(e) => setCity(e.target.value)}
                  className="w-full p-3 rounded-xl border border-secondary bg-white focus:outline-none focus:ring-2 focus:ring-primary/45 text-sm"
                  placeholder="e.g. Pune"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-bold text-foreground/75">State *</label>
                <input
                  type="text"
                  required
                  value={state}
                  onChange={(e) => setState(e.target.value)}
                  className="w-full p-3 rounded-xl border border-secondary bg-white focus:outline-none focus:ring-2 focus:ring-primary/45 text-sm"
                  placeholder="e.g. Maharashtra"
                />
              </div>
            </div>

            {/* Custom delivery date slots */}
            <div className="pt-6 border-t border-secondary/30 space-y-4">
              <h3 className="font-bold text-sm text-foreground/75 uppercase tracking-wider flex items-center gap-1.5">
                <Clock className="w-5 h-5 text-primary" /> Delivery Slot Scheduler
              </h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <button
                  type="button"
                  onClick={() => setDeliverySlot("standard")}
                  className={`p-4 rounded-xl border text-left flex flex-col justify-between transition ${deliverySlot === "standard" ? "border-primary bg-primary/5 text-primary" : "border-secondary hover:bg-secondary/10"}`}
                >
                  <span className="font-bold text-sm">Standard Shipping</span>
                  <span className="text-xs text-foreground/60 mt-1">Delivered in 3-5 working days.</span>
                </button>
                
                <button
                  type="button"
                  onClick={() => setDeliverySlot("festival")}
                  className={`p-4 rounded-xl border text-left flex flex-col justify-between transition ${deliverySlot === "festival" ? "border-primary bg-primary/5 text-primary" : "border-secondary hover:bg-secondary/10"}`}
                >
                  <span className="font-bold text-sm flex items-center gap-1">Festival Rush Slot 🎁</span>
                  <span className="text-xs text-foreground/60 mt-1">Expedited matching for Rakhi / Janmashtami.</span>
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-primary text-white hover:bg-primary/95 py-3.5 rounded-full font-bold shadow-md hover:shadow-lg transition text-base disabled:opacity-50"
            >
              {loading ? "Placing Order..." : "Confirm & Proceed to Payment"}
            </button>
          </form>

          {/* Checkout Bag Summary Card */}
          <div className="lg:col-span-1">
            <div className="bg-white p-6 rounded-cozy border border-secondary/50 shadow-sm space-y-6">
              <h3 className="font-bold text-lg text-foreground border-b border-secondary/30 pb-4">Order Preview</h3>
              
              <div className="space-y-4 max-h-48 overflow-y-auto pr-1">
                {cartPreview?.items?.map((item: any, idx: number) => (
                  <div key={idx} className="flex justify-between items-center text-sm">
                    <span className="text-foreground/80 font-medium line-clamp-1 flex-1 pr-4">
                      {item.product?.title} <span className="text-xs text-foreground/45 font-bold">x{item.quantity}</span>
                    </span>
                    <span className="font-bold text-foreground">₹{item.product?.price * item.quantity}</span>
                  </div>
                ))}
              </div>

              <div className="space-y-3.5 text-sm pt-4 border-t border-secondary/20">
                <div className="flex justify-between text-foreground/85">
                  <span>Cart Subtotal</span>
                  <span>₹{subtotal}</span>
                </div>
                <div className="flex justify-between text-foreground/85">
                  <span>Shipping & Handling</span>
                  <span>{shippingFee === 0 ? "FREE" : `₹${shippingFee}`}</span>
                </div>
                <div className="flex justify-between text-base font-extrabold text-foreground border-t border-secondary/20 pt-4">
                  <span>Total Due</span>
                  <span>₹{total}</span>
                </div>
              </div>

              <div className="pt-4 flex items-center space-x-2.5 text-xs text-foreground/60 justify-center">
                <Shield className="w-4 h-4 text-emerald-600" />
                <span>SSL Encrypted Transaction Gateway</span>
              </div>
            </div>
          </div>
        </div>
      </main>

      {/* Razorpay Mock Sandbox Modal */}
      {showRzpModal && createdOrder && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4 animate-fade-in">
          <div className="bg-[#121217] w-full max-w-sm rounded-cozy overflow-hidden border border-white/10 shadow-2xl text-white">
            {/* RZP Header */}
            <div className="bg-[#1e1e24] px-6 py-4 flex justify-between items-center border-b border-white/5">
              <span className="text-sm font-black tracking-widest text-[#52bcf6]">RAZORPAY CHECKOUT</span>
              <span className="bg-yellow-500/20 text-yellow-500 text-[9px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wider">
                Test Mode
              </span>
            </div>

            {/* Content info */}
            <div className="p-6 space-y-6 text-center">
              <div className="space-y-1">
                <p className="text-xs text-white/55">Paying to Kee Crochet</p>
                <p className="text-3xl font-black">₹{createdOrder.total || total}</p>
                <p className="text-[10px] text-white/45 font-mono mt-1">Order Ref: {createdOrder.order_number}</p>
              </div>

              <div className="bg-white/5 p-4 rounded-xl border border-white/5 space-y-3.5 text-left text-xs text-white/80">
                <p className="font-bold flex items-center gap-1.5 text-yellow-400">
                  <AlertCircle className="w-4 h-4" /> Razorpay Sandbox Gateway
                </p>
                <p className="leading-relaxed text-white/60">
                  We are in development mode. Click the button below to authorize a mock payment transaction. This triggers signature validation securely.
                </p>
              </div>

              {paymentSuccess ? (
                <div className="bg-emerald-500/20 border border-emerald-500/30 text-emerald-300 text-sm font-bold p-3.5 rounded-xl flex items-center justify-center gap-2">
                  <Check className="w-5 h-5 text-emerald-400" /> Payment Authorized!
                </div>
              ) : (
                <div className="flex gap-4">
                  <button
                    onClick={() => setShowRzpModal(false)}
                    className="flex-1 bg-white/10 hover:bg-white/15 py-3 rounded-full text-xs font-bold transition"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleMockPaymentSuccess}
                    disabled={paying}
                    className="flex-1 bg-[#2b72f5] hover:bg-[#1a5ce0] py-3 rounded-full text-xs font-bold transition flex items-center justify-center gap-1.5 shadow"
                  >
                    {paying ? "Verifying..." : (
                      <>
                        <CreditCard className="w-4 h-4" /> Pay Success
                      </>
                    )}
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
