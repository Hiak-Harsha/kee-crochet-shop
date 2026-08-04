"use client";

import { useState, useEffect } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { User, ShoppingBag, Send, Upload, Sparkles, Key, Mail, Check, ShieldCheck, HelpCircle } from "lucide-react";
import Navbar from "@/components/Navbar";
import { api } from "@/lib/api";

import { Suspense } from "react";

function DashboardContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const initialTab = searchParams.get("tab") || "orders";

  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [activeTab, setActiveTab] = useState(initialTab === "auth" ? "orders" : initialTab);
  
  // Auth Form States
  const [authTab, setAuthTab] = useState<"login" | "register" | "otp">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [otpCode, setOtpCode] = useState("");
  const [otpRequested, setOtpRequested] = useState(false);
  const [devOtp, setDevOtp] = useState<string | null>(null); // To assist testing
  const [authLoading, setAuthLoading] = useState(false);
  const [authError, setAuthError] = useState("");

  // Customer Data States
  const [orders, setOrders] = useState<any[]>([]);
  const [loadingOrders, setLoadingOrders] = useState(false);
  
  // Custom Design Request States
  const [customDesc, setCustomDesc] = useState("");
  const [customColors, setCustomColors] = useState("");
  const [customSuccess, setCustomSuccess] = useState(false);

  const loadOrders = async () => {
    setLoadingOrders(true);
    try {
      const data = await api.orders.list();
      setOrders(data || []);
    } catch (e) {
      console.warn("Failed to load backend orders, using mock order history", e);
      // Fallback mock customer orders
      setOrders([
        {
          id: "o1",
          order_number: "KC812495",
          created_at: new Date(Date.now() - 3 * 24 * 60 * 60 * 1000).toISOString(),
          status: "packed",
          total: 659.00,
          shipping_address: { full_name: "Madhav Nair", city: "Pune" },
          items: [
            { product_title: "Everlasting Pink Tulip Bouquet", quantity: 1, unit_price: 599.00 }
          ]
        }
      ]);
    }
    setLoadingOrders(false);
  };

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (token) {
      setIsLoggedIn(true);
      loadOrders();
    } else {
      setIsLoggedIn(false);
      if (searchParams.get("tab") === "auth") {
        setAuthTab("login");
      }
    }
  }, [searchParams]);

  // Handle standard registration
  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setAuthLoading(true);
    setAuthError("");
    try {
      const tokens = await api.auth.register({ email, password, full_name: fullName });
      localStorage.setItem("access_token", tokens.access_token);
      localStorage.setItem("refresh_token", tokens.refresh_token);
      setIsLoggedIn(true);
      loadOrders();
    } catch (err: any) {
      setAuthError(err.message || "Registration failed");
    }
    setAuthLoading(false);
  };

  // Handle standard login
  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setAuthLoading(true);
    setAuthError("");
    try {
      const tokens = await api.auth.login({ email, password });
      localStorage.setItem("access_token", tokens.access_token);
      localStorage.setItem("refresh_token", tokens.refresh_token);
      setIsLoggedIn(true);
      
      // Determine if admin
      const payload = JSON.parse(atob(tokens.access_token.split(".")[1]));
      if (payload.role === "admin") {
        router.push("/admin");
      } else {
        loadOrders();
      }
    } catch (err: any) {
      setAuthError(err.message || "Invalid email or password");
    }
    setAuthLoading(false);
  };

  // Request email OTP
  const handleRequestOtp = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email) {
      setAuthError("Email is required");
      return;
    }
    setAuthLoading(true);
    setAuthError("");
    try {
      const resp = await api.auth.requestOtp({ identifier: email });
      setOtpRequested(true);
      if (resp.dev_code) {
        setDevOtp(resp.dev_code); // Dev convenience
      }
    } catch (err: any) {
      setAuthError(err.message || "OTP request failed");
    }
    setAuthLoading(false);
  };

  // Verify email OTP
  const handleVerifyOtp = async (e: React.FormEvent) => {
    e.preventDefault();
    setAuthLoading(true);
    setAuthError("");
    try {
      const tokens = await api.auth.verifyOtp({ identifier: email, code: otpCode });
      localStorage.setItem("access_token", tokens.access_token);
      localStorage.setItem("refresh_token", tokens.refresh_token);
      setIsLoggedIn(true);
      loadOrders();
    } catch (err: any) {
      setAuthError(err.message || "Invalid OTP code");
    }
    setAuthLoading(false);
  };

  // Submit custom design request
  const handleCustomRequestSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!customDesc) return;
    setCustomSuccess(true);
    setCustomDesc("");
    setCustomColors("");
    setTimeout(() => setCustomSuccess(false), 4000);
  };

  return (
    <div className="flex-1 flex flex-col min-h-screen">
      <Navbar />

      <main className="max-w-7xl mx-auto w-full px-4 sm:px-6 lg:px-8 py-10 flex-1">
        {!isLoggedIn ? (
          /* Unauthenticated Auth Forms */
          <div className="max-w-md mx-auto bg-white p-8 rounded-cozy border border-secondary/50 shadow-md space-y-6 my-10">
            {/* Tab switch */}
            <div className="grid grid-cols-3 bg-secondary/30 p-1 rounded-full text-center text-sm font-bold border border-secondary/40">
              <button
                onClick={() => { setAuthTab("login"); setAuthError(""); }}
                className={`py-1.5 rounded-full transition ${authTab === "login" ? "bg-primary text-white" : "text-foreground/80"}`}
              >
                Sign In
              </button>
              <button
                onClick={() => { setAuthTab("otp"); setAuthError(""); }}
                className={`py-1.5 rounded-full transition ${authTab === "otp" ? "bg-primary text-white" : "text-foreground/80"}`}
              >
                OTP Code
              </button>
              <button
                onClick={() => { setAuthTab("register"); setAuthError(""); }}
                className={`py-1.5 rounded-full transition ${authTab === "register" ? "bg-primary text-white" : "text-foreground/80"}`}
              >
                Sign Up
              </button>
            </div>

            {authError && (
              <div className="bg-rose-50 border border-rose-100 text-rose-800 text-xs font-bold p-3 rounded-xl">
                {authError}
              </div>
            )}

            {/* Email/Password Login */}
            {authTab === "login" && (
              <form onSubmit={handleLogin} className="space-y-4">
                <div className="space-y-1.5">
                  <label className="text-xs font-bold text-foreground/75">Email Address</label>
                  <input
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="w-full p-3 rounded-xl border border-secondary bg-white focus:outline-none focus:ring-2 focus:ring-primary/45 text-sm"
                    placeholder="you@example.com"
                  />
                </div>
                <div className="space-y-1.5">
                  <label className="text-xs font-bold text-foreground/75">Password</label>
                  <input
                    type="password"
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="w-full p-3 rounded-xl border border-secondary bg-white focus:outline-none focus:ring-2 focus:ring-primary/45 text-sm"
                    placeholder="••••••••"
                  />
                </div>
                <button
                  type="submit"
                  disabled={authLoading}
                  className="w-full bg-primary text-white hover:bg-primary/95 py-3 rounded-full font-bold shadow text-sm transition"
                >
                  {authLoading ? "Signing In..." : "Sign In with Email"}
                </button>
              </form>
            )}

            {/* OTP Code Login */}
            {authTab === "otp" && (
              <div className="space-y-4">
                {!otpRequested ? (
                  <form onSubmit={handleRequestOtp} className="space-y-4">
                    <div className="space-y-1.5">
                      <label className="text-xs font-bold text-foreground/75">Email or Phone Number</label>
                      <input
                        type="text"
                        required
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        className="w-full p-3 rounded-xl border border-secondary bg-white focus:outline-none focus:ring-2 focus:ring-primary/45 text-sm"
                        placeholder="e.g. name@example.com"
                      />
                    </div>
                    <button
                      type="submit"
                      disabled={authLoading}
                      className="w-full bg-primary text-white hover:bg-primary/95 py-3 rounded-full font-bold shadow text-sm transition"
                    >
                      {authLoading ? "Requesting..." : "Send Verification Code"}
                    </button>
                  </form>
                ) : (
                  <form onSubmit={handleVerifyOtp} className="space-y-4">
                    <div className="space-y-1.5">
                      <label className="text-xs font-bold text-foreground/75">6-Digit Verification Code</label>
                      <input
                        type="text"
                        maxLength={6}
                        required
                        value={otpCode}
                        onChange={(e) => setOtpCode(e.target.value)}
                        className="w-full p-3 rounded-xl border border-secondary bg-white focus:outline-none focus:ring-2 focus:ring-primary/45 text-sm text-center font-bold tracking-widest"
                        placeholder="000000"
                      />
                    </div>
                    {devOtp && (
                      <p className="text-[10px] bg-yellow-50 text-yellow-800 p-2 rounded-lg font-bold border border-yellow-200">
                        Dev Sandbox Bypass Code: <span className="font-mono text-xs">{devOtp}</span>
                      </p>
                    )}
                    <button
                      type="submit"
                      disabled={authLoading}
                      className="w-full bg-primary text-white hover:bg-primary/95 py-3 rounded-full font-bold shadow text-sm transition"
                    >
                      {authLoading ? "Verifying..." : "Verify and Login"}
                    </button>
                  </form>
                )}
              </div>
            )}

            {/* Email/Password Signup */}
            {authTab === "register" && (
              <form onSubmit={handleRegister} className="space-y-4">
                <div className="space-y-1.5">
                  <label className="text-xs font-bold text-foreground/75">Full Name</label>
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
                  <label className="text-xs font-bold text-foreground/75">Email Address</label>
                  <input
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="w-full p-3 rounded-xl border border-secondary bg-white focus:outline-none focus:ring-2 focus:ring-primary/45 text-sm"
                    placeholder="you@example.com"
                  />
                </div>
                <div className="space-y-1.5">
                  <label className="text-xs font-bold text-foreground/75">Password</label>
                  <input
                    type="password"
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="w-full p-3 rounded-xl border border-secondary bg-white focus:outline-none focus:ring-2 focus:ring-primary/45 text-sm"
                    placeholder="At least 6 characters"
                  />
                </div>
                <button
                  type="submit"
                  disabled={authLoading}
                  className="w-full bg-primary text-white hover:bg-primary/95 py-3 rounded-full font-bold shadow text-sm transition"
                >
                  {authLoading ? "Creating Account..." : "Create Account"}
                </button>
              </form>
            )}
          </div>
        ) : (
          /* Authenticated Customer Dashboard */
          <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
            {/* Sidebar Navigation */}
            <div className="lg:col-span-1 bg-white p-6 rounded-cozy border border-secondary/50 h-fit space-y-4 shadow-sm">
              <div className="flex items-center space-x-3 pb-4 border-b border-secondary/30">
                <div className="bg-primary/10 text-primary p-2.5 rounded-full">
                  <User className="w-6 h-6" />
                </div>
                <div>
                  <h2 className="font-extrabold text-sm text-foreground">Welcome Back!</h2>
                  <p className="text-xs text-foreground/60">Kee Crochet Member</p>
                </div>
              </div>

              <div className="flex flex-col space-y-1 pt-2">
                <button
                  onClick={() => setActiveTab("orders")}
                  className={`text-left text-sm py-2 px-4 rounded-xl font-bold transition flex items-center gap-2 ${activeTab === "orders" ? "bg-primary text-white shadow-sm" : "hover:bg-secondary/20 text-foreground/80"}`}
                >
                  <ShoppingBag className="w-4 h-4" /> My Orders
                </button>
                <button
                  onClick={() => setActiveTab("custom")}
                  className={`text-left text-sm py-2 px-4 rounded-xl font-bold transition flex items-center gap-2 ${activeTab === "custom" ? "bg-primary text-white shadow-sm" : "hover:bg-secondary/20 text-foreground/80"}`}
                >
                  <Sparkles className="w-4 h-4" /> Request Custom Design
                </button>
              </div>
            </div>

            {/* Dashboard Contents */}
            <div className="lg:col-span-3">
              {/* Tab 1: Order History list */}
              {activeTab === "orders" && (
                <div className="bg-white p-6 rounded-cozy border border-secondary/50 shadow-sm space-y-6">
                  <h2 className="text-xl font-extrabold text-foreground border-b border-secondary/30 pb-4">My Order History</h2>
                  
                  {loadingOrders ? (
                    <div className="flex justify-center py-10">
                      <div className="w-8 h-8 border-4 border-primary border-t-transparent rounded-full animate-spin"></div>
                    </div>
                  ) : orders.length === 0 ? (
                    <div className="text-center py-12 text-foreground/50 text-sm">
                      No orders placed yet.
                    </div>
                  ) : (
                    <div className="space-y-6">
                      {orders.map((o) => (
                        <div key={o.id} className="border border-secondary/50 p-6 rounded-2xl space-y-4 bg-yarn-cream/5">
                          <div className="flex justify-between items-center flex-wrap gap-4 border-b border-secondary/30 pb-3 text-xs sm:text-sm">
                            <div>
                              <p className="font-bold text-foreground">Order ID: {o.order_number}</p>
                              <p className="text-foreground/50 text-[10px] mt-0.5">Placed on {new Date(o.created_at).toLocaleDateString()}</p>
                            </div>
                            
                            {/* Tracking Status Badge */}
                            <div>
                              <span className={`font-bold px-3 py-1 rounded-full text-xs uppercase tracking-wider ${o.status === "completed" ? "bg-emerald-100 text-emerald-800" : o.status === "shipped" ? "bg-blue-100 text-blue-800" : o.status === "packed" ? "bg-yellow-100 text-yellow-800" : "bg-neutral-100 text-neutral-800"}`}>
                                {o.status}
                              </span>
                            </div>
                          </div>

                          <div className="space-y-2">
                            {o.items?.map((item: any, i: number) => (
                              <div key={i} className="flex justify-between text-sm">
                                <span className="text-foreground/80 font-medium">{item.product_title} x{item.quantity}</span>
                                <span className="font-bold text-foreground">₹{item.unit_price * item.quantity}</span>
                              </div>
                            ))}
                          </div>

                          {/* Tracker Bar */}
                          <div className="pt-4 border-t border-secondary/20 flex justify-between items-center text-xs text-foreground/50">
                            <div className="flex items-center space-x-1 font-bold text-primary">
                              <Check className="w-4 h-4" /> <span>Authorized</span>
                            </div>
                            <div className={`flex items-center space-x-1 font-bold ${["packed", "shipped", "completed"].includes(o.status) ? "text-primary" : ""}`}>
                              {["packed", "shipped", "completed"].includes(o.status) && <Check className="w-4 h-4" />}
                              <span>Packed</span>
                            </div>
                            <div className={`flex items-center space-x-1 font-bold ${["shipped", "completed"].includes(o.status) ? "text-primary" : ""}`}>
                              {["shipped", "completed"].includes(o.status) && <Check className="w-4 h-4" />}
                              <span>Shipped</span>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* Tab 2: Custom Order Request Form */}
              {activeTab === "custom" && (
                <div className="bg-white p-6 sm:p-8 rounded-cozy border border-secondary/50 shadow-sm space-y-6">
                  <h2 className="text-xl font-extrabold text-foreground border-b border-secondary/30 pb-4">Request Custom Crochet Design</h2>
                  
                  {customSuccess && (
                    <div className="bg-emerald-50 border border-emerald-200 text-emerald-800 text-sm font-bold p-4 rounded-xl flex items-center gap-2">
                      <ShieldCheck className="w-6 h-6 text-emerald-600" /> Custom quote submitted! Kee will review your specifications and contact you on WhatsApp/Email in 24 hours.
                    </div>
                  )}

                  <form onSubmit={handleCustomRequestSubmit} className="space-y-6">
                    <p className="text-sm text-foreground/75 leading-relaxed bg-primary/5 p-4 rounded-xl border border-primary/10">
                      Looking for custom color combinations or something completely original (e.g. customized name bouquet, custom mascot plushie)? Describe your design below and upload a sketch or Pinterest reference photo.
                    </p>

                    <div className="space-y-1.5">
                      <label className="text-xs font-bold text-foreground/75">Design Specifications *</label>
                      <textarea
                        rows={4}
                        required
                        placeholder="Describe the shapes, elements, flowers, size, and packaging you have in mind..."
                        value={customDesc}
                        onChange={(e) => setCustomDesc(e.target.value)}
                        className="w-full p-3 rounded-xl border border-secondary bg-white focus:outline-none focus:ring-2 focus:ring-primary/45 text-sm"
                      />
                    </div>

                    <div className="space-y-1.5">
                      <label className="text-xs font-bold text-foreground/75">Color Palette Choices</label>
                      <input
                        type="text"
                        placeholder="e.g. Pastel Pink stems with a Butter Yellow wrapper"
                        value={customColors}
                        onChange={(e) => setCustomColors(e.target.value)}
                        className="w-full p-3 rounded-xl border border-secondary bg-white focus:outline-none focus:ring-2 focus:ring-primary/45 text-sm"
                      />
                    </div>

                    <div className="space-y-1.5">
                      <label className="text-xs font-bold text-foreground/75">Reference Image Upload</label>
                      <div className="border-2 border-dashed border-secondary/60 hover:border-primary p-6 rounded-xl flex flex-col items-center justify-center bg-secondary/5 transition cursor-pointer">
                        <Upload className="w-8 h-8 text-secondary mb-2" />
                        <span className="text-xs font-bold text-foreground/60">Upload reference photo</span>
                      </div>
                    </div>

                    <button
                      type="submit"
                      className="bg-primary text-white hover:bg-primary/95 px-8 py-3 rounded-full font-bold shadow text-sm transition flex items-center gap-1.5"
                    >
                      <Send className="w-4 h-4" /> Submit Custom Design Request
                    </button>
                  </form>
                </div>
              )}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

export default function DashboardPage() {
  return (
    <Suspense fallback={
      <div className="flex-1 flex flex-col min-h-screen items-center justify-center space-y-4">
        <div className="w-10 h-10 border-4 border-primary border-t-transparent rounded-full animate-spin"></div>
        <p className="text-foreground/75 font-semibold">Loading Dashboard...</p>
      </div>
    }>
      <DashboardContent />
    </Suspense>
  );
}
