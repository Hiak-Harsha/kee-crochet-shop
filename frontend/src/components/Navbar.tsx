"use client";

import Link from "next/link";
import { useState, useEffect } from "react";
import { ShoppingBag, Sparkles, User, Menu, X, LogOut, LayoutDashboard } from "lucide-react";

export default function Navbar() {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [isAdmin, setIsAdmin] = useState(false);
  const [cartCount, setCartCount] = useState(0);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  useEffect(() => {
    // Check auth status
    const token = localStorage.getItem("access_token");
    if (token) {
      setIsLoggedIn(true);
      try {
        const payload = JSON.parse(atob(token.split(".")[1]));
        if (payload.role === "admin") {
          setIsAdmin(true);
        }
      } catch (e) {
        console.error("Failed to parse token details", e);
      }
    }

    // Load cart count from localStorage / API
    const updateCartCount = () => {
      const stored = localStorage.getItem("cart_count");
      setCartCount(stored ? parseInt(stored, 10) : 0);
    };

    const handleUnauthorized = () => {
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
      localStorage.removeItem("cart_count");
      setIsLoggedIn(false);
      setIsAdmin(false);
      setCartCount(0);
    };

    updateCartCount();
    window.addEventListener("storage", updateCartCount);
    window.addEventListener("cart-updated", updateCartCount);
    window.addEventListener("unauthorized", handleUnauthorized);
    return () => {
      window.removeEventListener("storage", updateCartCount);
      window.removeEventListener("cart-updated", updateCartCount);
      window.removeEventListener("unauthorized", handleUnauthorized);
    };
  }, []);

  const handleLogout = () => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    localStorage.removeItem("cart_count");
    setIsLoggedIn(false);
    setIsAdmin(false);
    setCartCount(0);
    window.location.href = "/";
  };

  return (
    <nav className="sticky top-0 z-50 bg-white/80 backdrop-blur-md border-b border-secondary/50 px-4 sm:px-6 lg:px-8 py-3">
      <div className="max-w-7xl mx-auto flex items-center justify-between">
        {/* Logo */}
        <Link href="/" className="flex items-center space-x-2">
          <span className="text-2xl font-bold tracking-tight text-primary flex items-center gap-1.5">
            Kee Crochet <span className="animate-pulse">🧶</span>
          </span>
        </Link>

        {/* Desktop Navigation Links */}
        <div className="hidden md:flex items-center space-x-8">
          <Link href="/products" className="text-foreground/80 hover:text-primary transition font-medium">
            Shop Catalog
          </Link>
          <Link href="/shop-helper" className="text-primary hover:text-primary/80 transition font-semibold flex items-center gap-1.5">
            <Sparkles className="w-4 h-4" /> AI Personal Shopper
          </Link>
          {isAdmin && (
            <Link href="/admin" className="text-accent-foreground hover:text-accent-foreground/80 transition font-medium flex items-center gap-1.5 bg-accent/30 px-3 py-1.5 rounded-full text-sm">
              <LayoutDashboard className="w-4 h-4" /> Admin Console
            </Link>
          )}
        </div>

        {/* Right Action Icons */}
        <div className="hidden md:flex items-center space-x-6">
          <Link href="/cart" className="relative p-2 text-foreground/80 hover:text-primary transition">
            <ShoppingBag className="w-6 h-6" />
            {cartCount > 0 && (
              <span className="absolute -top-1 -right-1 bg-primary text-white text-xs w-5 h-5 rounded-full flex items-center justify-center font-bold">
                {cartCount}
              </span>
            )}
          </Link>
          
          {isLoggedIn ? (
            <div className="flex items-center space-x-4">
              <Link href="/dashboard" className="p-2 text-foreground/80 hover:text-primary transition flex items-center gap-1">
                <User className="w-6 h-6" />
                <span className="text-sm font-medium">Dashboard</span>
              </Link>
              <button onClick={handleLogout} className="p-2 text-foreground/80 hover:text-red-500 transition flex items-center gap-1">
                <LogOut className="w-5 h-5" />
              </button>
            </div>
          ) : (
            <Link href="/dashboard?tab=auth" className="bg-primary text-white hover:bg-primary/90 px-5 py-2 rounded-full font-medium shadow-sm transition hover:shadow-md">
              Sign In
            </Link>
          )}
        </div>

        {/* Mobile menu button */}
        <div className="md:hidden flex items-center space-x-4">
          <Link href="/cart" className="relative p-2 text-foreground/80 hover:text-primary transition">
            <ShoppingBag className="w-6 h-6" />
            {cartCount > 0 && (
              <span className="absolute -top-1 -right-1 bg-primary text-white text-xs w-5 h-5 rounded-full flex items-center justify-center font-bold">
                {cartCount}
              </span>
            )}
          </Link>
          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="p-2 text-foreground/85 hover:text-primary"
          >
            {mobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
          </button>
        </div>
      </div>

      {/* Mobile Drawer menu */}
      {mobileMenuOpen && (
        <div className="md:hidden absolute top-full left-0 right-0 bg-white border-b border-secondary/50 py-4 px-6 flex flex-col space-y-4 shadow-lg transition">
          <Link href="/products" onClick={() => setMobileMenuOpen(false)} className="text-foreground font-medium py-2">
            Shop Catalog
          </Link>
          <Link href="/shop-helper" onClick={() => setMobileMenuOpen(false)} className="text-primary font-semibold py-2 flex items-center gap-1.5">
            <Sparkles className="w-4 h-4" /> AI Personal Shopper
          </Link>
          {isAdmin && (
            <Link href="/admin" onClick={() => setMobileMenuOpen(false)} className="text-accent-foreground font-medium py-2 flex items-center gap-1.5">
              <LayoutDashboard className="w-4 h-4" /> Admin Console
            </Link>
          )}
          {isLoggedIn ? (
            <>
              <Link href="/dashboard" onClick={() => setMobileMenuOpen(false)} className="text-foreground font-medium py-2 flex items-center gap-1.5">
                <User className="w-5 h-5" /> My Account Dashboard
              </Link>
              <button
                onClick={() => {
                  handleLogout();
                  setMobileMenuOpen(false);
                }}
                className="text-red-500 font-medium py-2 text-left flex items-center gap-1.5"
              >
                <LogOut className="w-5 h-5" /> Logout
              </button>
            </>
          ) : (
            <Link href="/dashboard?tab=auth" onClick={() => setMobileMenuOpen(false)} className="bg-primary text-white text-center py-2.5 rounded-full font-medium transition">
              Sign In
            </Link>
          )}
        </div>
      )}
    </nav>
  );
}
