"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import {
  LayoutDashboard,
  Package,
  Tag,
  Boxes,
  ShoppingBag,
  Users,
  Star,
  Ticket,
  Inbox,
  Sparkles,
  BarChart3,
  Settings,
  RefreshCw,
  LogOut,
  ChevronRight,
  ShieldCheck,
} from "lucide-react";
import Navbar from "@/components/Navbar";
import { api, Category, Order, Product } from "@/lib/api";

// 12 Modular Admin Components
import DashboardOverview from "@/components/admin/DashboardOverview";
import ProductManagement from "@/components/admin/ProductManagement";
import CategoryManagement from "@/components/admin/CategoryManagement";
import InventoryManager from "@/components/admin/InventoryManager";
import OrderManager from "@/components/admin/OrderManager";
import CustomerDirectory from "@/components/admin/CustomerDirectory";
import ReviewModerator from "@/components/admin/ReviewModerator";
import CouponManager from "@/components/admin/CouponManager";
import CustomRequestInbox from "@/components/admin/CustomRequestInbox";
import AIStudio from "@/components/admin/AIStudio";
import StoreAnalytics from "@/components/admin/StoreAnalytics";
import StoreSettings from "@/components/admin/StoreSettings";

type AdminTab =
  | "overview"
  | "products"
  | "categories"
  | "inventory"
  | "orders"
  | "customers"
  | "reviews"
  | "coupons"
  | "custom_requests"
  | "ai_studio"
  | "analytics"
  | "settings";

const NAV_ITEMS: Array<{ id: AdminTab; label: string; icon: any; category: string }> = [
  { id: "overview", label: "Dashboard", icon: LayoutDashboard, category: "Overview" },
  { id: "analytics", label: "Analytics", icon: BarChart3, category: "Overview" },
  { id: "products", label: "Products", icon: Package, category: "Catalog" },
  { id: "categories", label: "Categories", icon: Tag, category: "Catalog" },
  { id: "inventory", label: "Inventory", icon: Boxes, category: "Catalog" },
  { id: "orders", label: "Orders", icon: ShoppingBag, category: "Sales" },
  { id: "coupons", label: "Coupons", icon: Ticket, category: "Sales" },
  { id: "customers", label: "Customers", icon: Users, category: "Sales" },
  { id: "reviews", label: "Reviews", icon: Star, category: "Engagement" },
  { id: "custom_requests", label: "Custom Requests", icon: Inbox, category: "Engagement" },
  { id: "ai_studio", label: "AI Studio", icon: Sparkles, category: "AI & Growth" },
  { id: "settings", label: "Settings", icon: Settings, category: "System" },
];

export default function AdminPage() {
  const router = useRouter();
  const [isAdminVerified, setIsAdminVerified] = useState(false);
  const [activeTab, setActiveTab] = useState<AdminTab>("overview");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // Global Admin Data Lists
  const [products, setProducts] = useState<Product[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [orders, setOrders] = useState<Order[]>([]);
  const [stats, setStats] = useState<{ total_sales: number; total_orders: number; average_order_value: number }>({
    total_sales: 0,
    total_orders: 0,
    average_order_value: 0,
  });
  const [ordersPage, setOrdersPage] = useState(1);

  const loadAdminData = async () => {
    setLoading(true);
    setError("");
    try {
      const [prods, cats, ords, st] = await Promise.all([
        api.products.list(),
        api.products.listCategories(),
        api.orders.adminListAll(ordersPage, 20),
        api.orders.adminGetStats(),
      ]);
      setProducts(prods || []);
      setCategories(cats || []);
      setOrders(ords || []);
      setStats(st || { total_sales: 0, total_orders: 0, average_order_value: 0 });
    } catch (e: any) {
      console.error("Failed to load admin data:", e);
      setError(e.message || "Failed to load dashboard data. Please verify backend connection.");
    } finally {
      setLoading(false);
    }
  };

  const handleOrdersPageChange = async (newPage: number) => {
    setOrdersPage(newPage);
    try {
      const ords = await api.orders.adminListAll(newPage, 20);
      setOrders(ords || []);
    } catch (e: any) {
      console.error("Page change failed:", e);
    }
  };

  // Admin JWT Auth Guard
  useEffect(() => {
    const checkAdminAuth = () => {
      const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
      if (!token) {
        router.push("/dashboard?tab=auth");
        return;
      }
      try {
        const parts = token.split(".");
        if (parts.length !== 3) throw new Error("Invalid token");
        const payload = JSON.parse(atob(parts[1]));
        if (payload.role !== "admin") {
          router.push("/dashboard?tab=auth");
          return;
        }
        setIsAdminVerified(true);
        loadAdminData();
      } catch {
        router.push("/dashboard?tab=auth");
      }
    };
    checkAdminAuth();
  }, [router]);

  const handleLogout = () => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    router.push("/dashboard?tab=auth");
  };

  if (!isAdminVerified) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-secondary/10">
        <div className="text-center space-y-3">
          <div className="w-10 h-10 border-4 border-primary border-t-transparent rounded-full animate-spin mx-auto"></div>
          <p className="text-xs font-bold text-foreground/60">Verifying administrative credentials...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col min-h-screen bg-secondary/10">
      <Navbar />

      <main className="max-w-7xl mx-auto w-full px-4 sm:px-6 lg:px-8 py-8 flex-1">
        {/* Top Header */}
        <div className="flex flex-wrap items-center justify-between gap-4 pb-6 border-b border-secondary/30 mb-6">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-primary text-white flex items-center justify-center font-black shadow-sm">
              KC
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-xl font-black text-foreground">Kee Studio Admin</h1>
                <span className="text-[10px] font-black uppercase tracking-wider bg-emerald-100 text-emerald-800 px-2 py-0.5 rounded-full flex items-center gap-1">
                  <ShieldCheck className="w-3 h-3" /> Verified
                </span>
              </div>
              <p className="text-xs text-foreground/50">Production Management Suite</p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={loadAdminData}
              disabled={loading}
              className="p-2 rounded-xl border border-secondary bg-white text-foreground/60 hover:text-primary transition shadow-xs disabled:opacity-40"
              title="Refresh all data"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
            </button>
            <button
              onClick={handleLogout}
              className="px-3.5 py-2 rounded-xl border border-rose-200 text-rose-700 bg-rose-50/50 hover:bg-rose-100/70 text-xs font-bold transition flex items-center gap-1.5"
            >
              <LogOut className="w-3.5 h-3.5" /> Logout
            </button>
          </div>
        </div>

        {error && (
          <div className="mb-6 bg-rose-50 border border-rose-200 text-rose-800 text-xs font-bold p-3.5 rounded-xl">
            {error}
          </div>
        )}

        {/* Layout: Sidebar + Main Tab Content */}
        <div className="grid grid-cols-1 lg:grid-cols-5 gap-8 items-start">
          {/* Navigation Sidebar */}
          <aside className="lg:col-span-1 bg-white p-3 rounded-2xl border border-secondary/40 shadow-sm space-y-1">
            {NAV_ITEMS.map((item) => {
              const Icon = item.icon;
              const isActive = activeTab === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => setActiveTab(item.id)}
                  className={`w-full flex items-center justify-between px-3.5 py-2.5 rounded-xl text-xs font-bold transition ${
                    isActive
                      ? "bg-primary text-white shadow-sm"
                      : "text-foreground/70 hover:bg-secondary/15 hover:text-foreground"
                  }`}
                >
                  <div className="flex items-center gap-2.5">
                    <Icon className={`w-4 h-4 ${isActive ? "text-white" : "text-foreground/50"}`} />
                    <span>{item.label}</span>
                  </div>
                  {isActive && <ChevronRight className="w-3.5 h-3.5" />}
                </button>
              );
            })}
          </aside>

          {/* Active Tab View */}
          <section className="lg:col-span-4 min-h-[600px]">
            {activeTab === "overview" && (
              <DashboardOverview
                stats={stats}
                orders={orders}
                products={products}
                onNavigateTab={(tab) => setActiveTab(tab as AdminTab)}
                onRefresh={loadAdminData}
              />
            )}

            {activeTab === "products" && (
              <ProductManagement
                products={products}
                categories={categories}
                onRefresh={loadAdminData}
              />
            )}

            {activeTab === "categories" && (
              <CategoryManagement
                categories={categories}
                onRefresh={loadAdminData}
              />
            )}

            {activeTab === "inventory" && (
              <InventoryManager
                products={products}
                onRefresh={loadAdminData}
              />
            )}

            {activeTab === "orders" && (
              <OrderManager
                orders={orders}
                ordersPage={ordersPage}
                onPageChange={handleOrdersPageChange}
                onRefresh={loadAdminData}
              />
            )}

            {activeTab === "customers" && (
              <CustomerDirectory orders={orders} />
            )}

            {activeTab === "reviews" && (
              <ReviewModerator products={products} />
            )}

            {activeTab === "coupons" && (
              <CouponManager />
            )}

            {activeTab === "custom_requests" && (
              <CustomRequestInbox />
            )}

            {activeTab === "ai_studio" && (
              <AIStudio products={products} />
            )}

            {activeTab === "analytics" && (
              <StoreAnalytics
                orders={orders}
                stats={stats}
              />
            )}

            {activeTab === "settings" && (
              <StoreSettings />
            )}
          </section>
        </div>
      </main>
    </div>
  );
}
