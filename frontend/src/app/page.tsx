"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import Image from "next/image";
import { Sparkles, ArrowRight, Heart, Gift, MessageCircle, Instagram } from "lucide-react";
import Navbar from "@/components/Navbar";
import { api } from "@/lib/api";

export default function Home() {
  const fallbackCategories = [
    {
      name: "Handmade Bouquets",
      slug: "bouquets",
      description: "Everlasting crochet flowers, tulips, and sunflowers wrapped with love.",
      image: "/images/category_bouquets.jpg",
      price: "From ₹499",
    },
    {
      name: "Cozy Plushies",
      slug: "plushies",
      description: "Super soft, squishy animals and dolls hand-knitted for cozy companions.",
      image: "/images/category_plushies.jpg",
      price: "From ₹349",
    },
    {
      name: "Cute Keychains",
      slug: "keychains",
      description: "Miniature crochet accessories to carry warmth wherever you go.",
      image: "/images/category_keychains.jpg",
      price: "From ₹149",
    },
  ];

  const instagramPosts = [
    { id: 1, url: "/images/insta_1.jpg", likes: 245 },
    { id: 2, url: "/images/insta_2.jpg", likes: 189 },
    { id: 3, url: "/images/insta_3.jpg", likes: 312 },
    { id: 4, url: "/images/insta_4.jpg", likes: 420 },
  ];

  const [categories, setCategories] = useState<any[]>([]);
  const [featuredProducts, setFeaturedProducts] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function loadData() {
      setLoading(true);
      setError("");
      try {
        const cats = await api.products.listCategories();
        if (cats && cats.length > 0) {
          setCategories(
            cats.map((c: any) => ({
              name: c.name,
              slug: c.slug,
              description: c.description,
              price: c.slug === "bouquets" ? "From ₹499" : c.slug === "plushies" ? "From ₹349" : "From ₹149",
              image: c.slug === "bouquets" 
                ? "/images/category_bouquets.jpg" 
                : c.slug === "plushies" 
                ? "/images/category_plushies.jpg" 
                : "/images/category_keychains.jpg",
            }))
          );
        } else {
          setCategories(fallbackCategories);
        }
      } catch (err) {
        console.warn("Failed to load categories from backend, using fallbacks:", err);
        setCategories(fallbackCategories);
      }

      try {
        const prods = await api.products.list({ featured: true });
        setFeaturedProducts(prods || []);
      } catch (err: any) {
        console.warn("Failed to load featured products from backend:", err);
        setError("Failed to fetch featured products from database. Running in offline fallback mode.");
      }
      setLoading(false);
    }
    loadData();
  }, []);

  return (
    <div className="flex-1 flex flex-col min-h-screen">
      <Navbar />

      {error && (
        <div className="bg-rose-50 border-b border-rose-200 text-rose-800 text-sm font-bold p-4 flex items-center justify-center gap-2">
          <span>⚠️</span> {error}
        </div>
      )}

      {/* Hero Section */}
      <section className="relative overflow-hidden py-20 px-6 sm:px-12 lg:px-24 bg-gradient-to-b from-yarn-cream to-background">
        <div className="max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
          <div className="space-y-8 text-center lg:text-left">
            <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-primary/10 text-primary text-sm font-semibold">
              <Sparkles className="w-4 h-4 animate-spin-slow" /> 100% Handcrafted with Love
            </div>
            
            <h1 className="text-4xl sm:text-6xl font-bold leading-tight tracking-tight text-foreground">
              Cozy Crochet, <br />
              <span className="text-primary">Stitched to Last Forever.</span>
            </h1>
            
            <p className="text-lg text-foreground/80 max-w-xl mx-auto lg:mx-0">
              Upgrade your gifting game with our premium, hand-knitted bouquets, cute animal plushies, and custom accessories made from soft milk cotton yarn.
            </p>

            <div className="flex flex-col sm:flex-row gap-4 justify-center lg:justify-start">
              <Link href="/products" className="bg-primary text-white hover:bg-primary/90 px-8 py-3.5 rounded-full font-bold shadow-md hover:shadow-lg transition flex items-center justify-center gap-2 group">
                Browse Shop <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
              </Link>
              <Link href="/shop-helper" className="glass-panel border-primary/20 text-primary hover:bg-primary/5 px-8 py-3.5 rounded-full font-bold shadow-sm transition flex items-center justify-center gap-2">
                <Sparkles className="w-5 h-5" /> Chat with AI Assistant
              </Link>
            </div>
          </div>

          {/* Right Floating Crochet Image Visualizer */}
          <div className="relative flex justify-center lg:justify-end animate-float">
            <div className="relative w-80 h-80 sm:w-96 sm:h-96 rounded-full overflow-hidden border-8 border-white shadow-2xl">
              <Image
                src="/images/hero.jpg"
                alt="Cozy Handmade Crochet"
                fill
                priority
                className="object-cover"
              />
            </div>
            <div className="absolute -bottom-4 -left-4 bg-white/90 backdrop-blur p-4 rounded-cozy shadow-lg border border-secondary flex items-center space-x-3 z-10">
              <span className="bg-rose-100 p-2.5 rounded-full text-primary">
                <Heart className="w-5 h-5 fill-current" />
              </span>
              <div>
                <p className="text-xs font-semibold text-foreground/70">Signature Product</p>
                <p className="text-sm font-bold text-foreground">Everlasting Tulips</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Category Grid Section */}
      <section className="py-20 px-6 sm:px-12 lg:px-24 max-w-7xl mx-auto w-full">
        <div className="text-center max-w-xl mx-auto space-y-4 mb-16">
          <h2 className="text-3xl font-bold text-foreground">Explore Our Cozy Collections</h2>
          <p className="text-foreground/70">From desk buddies to birthday bouquets, find a hand-knitted gift that fits every mood.</p>
        </div>

        {loading ? (
          <div className="flex justify-center py-10">
            <div className="w-8 h-8 border-4 border-primary border-t-transparent rounded-full animate-spin"></div>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {categories.map((cat, idx) => (
              <div key={idx} className="group bg-white rounded-cozy border border-secondary/50 overflow-hidden shadow-sm hover:shadow-xl transition-all duration-300 flex flex-col">
                <div className="relative h-64 overflow-hidden">
                  <Image
                    src={cat.image}
                    alt={cat.name}
                    fill
                    className="object-cover group-hover:scale-105 transition-transform duration-500"
                  />
                  <span className="absolute top-4 right-4 bg-white/90 backdrop-blur px-3 py-1 rounded-full text-xs font-bold text-primary border border-secondary z-10">
                    {cat.price}
                  </span>
                </div>
                <div className="p-6 flex-1 flex flex-col justify-between">
                  <div>
                    <h3 className="text-xl font-bold text-foreground mb-2">{cat.name}</h3>
                    <p className="text-foreground/70 text-sm mb-6 leading-relaxed">{cat.description}</p>
                  </div>
                  <Link href={`/products?category_slug=${cat.slug}`} className="text-primary hover:text-primary/80 font-bold text-sm inline-flex items-center gap-1">
                    View Collection <ArrowRight className="w-4 h-4" />
                  </Link>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Featured Products Section */}
      {!loading && featuredProducts.length > 0 && (
        <section className="py-20 bg-primary/5 border-y border-secondary/30 px-6 sm:px-12 lg:px-24">
          <div className="max-w-7xl mx-auto">
            <div className="flex flex-col sm:flex-row justify-between items-center mb-12 gap-4 text-center sm:text-left">
              <div className="space-y-2">
                <h2 className="text-3xl font-extrabold text-foreground">Featured Stitches</h2>
                <p className="text-foreground/70">Our most-loved, best-selling crochet creations.</p>
              </div>
              <Link href="/products" className="bg-primary text-white hover:bg-primary/95 px-6 py-2.5 rounded-full font-bold shadow text-sm transition inline-flex items-center gap-2">
                Browse Full Catalog <ArrowRight className="w-4 h-4" />
              </Link>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-6">
              {featuredProducts.slice(0, 4).map((p) => (
                <div key={p.id} className="group bg-white border border-secondary/50 rounded-cozy overflow-hidden shadow-sm hover:shadow-lg transition flex flex-col justify-between">
                  <Link href={`/products/${p.slug}`} className="block relative aspect-square overflow-hidden bg-secondary/10">
                    <Image
                      src={p.images?.[0] || "/images/category_bouquets.jpg"}
                      alt={p.title}
                      fill
                      className="object-cover group-hover:scale-105 transition-transform duration-500"
                    />
                  </Link>
                  <div className="p-5 flex-1 flex flex-col justify-between">
                    <div>
                      <Link href={`/products/${p.slug}`} className="block font-bold text-foreground hover:text-primary transition line-clamp-1 mb-1">
                        {p.title}
                      </Link>
                      <p className="text-xs text-foreground/60 line-clamp-2 leading-relaxed mb-4">{p.description}</p>
                    </div>
                    <div className="flex items-center justify-between pt-3 border-t border-secondary/20">
                      <span className="text-base font-extrabold text-foreground">₹{parseFloat(p.price)}</span>
                      <Link href={`/products/${p.slug}`} className="bg-primary/10 hover:bg-primary text-primary hover:text-white px-4 py-1.5 rounded-full text-xs font-bold transition">
                        View Details
                      </Link>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>
      )}

      {/* AI Features Highlight */}
      <section className="bg-primary/5 py-20 px-6 sm:px-12 lg:px-24">
        <div className="max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
          <div className="relative h-80 lg:h-96 rounded-cozy overflow-hidden shadow-xl border-4 border-white">
            <Image
              src="/images/room_color_match.jpg"
              alt="AI Shopping Helper"
              fill
              className="object-cover"
            />
            <div className="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent flex items-end p-6 z-10">
              <div className="text-white space-y-1">
                <span className="bg-primary px-2.5 py-0.5 rounded-full text-xs font-bold">New Feature</span>
                <h4 className="text-lg font-bold">AI Aesthetic Room Color Matcher</h4>
              </div>
            </div>
          </div>
          
          <div className="space-y-6">
            <h2 className="text-3xl font-bold text-foreground">Stitch Together Your Dream Space</h2>
            <p className="text-foreground/80 leading-relaxed">
              Don't know what colors fit your desk or bedroom bookshelf? Our integrated <strong className="font-semibold text-primary">Gemini AI</strong> lets you upload a picture of your space to instantly recommend accent yarn colors and matching crochet designs.
            </p>
            
            <div className="space-y-4">
              <div className="flex items-start space-x-3">
                <span className="bg-primary/10 p-2 rounded-full text-primary mt-1">
                  <Gift className="w-5 h-5" />
                </span>
                <div>
                  <h4 className="font-bold text-foreground">AI Gift Finder</h4>
                  <p className="text-sm text-foreground/70">"I need something cute for my sister turning 20." Get instant matched proposals.</p>
                </div>
              </div>
              
              <div className="flex items-start space-x-3">
                <span className="bg-primary/10 p-2 rounded-full text-primary mt-1">
                  <MessageCircle className="w-5 h-5" />
                </span>
                <div>
                  <h4 className="font-bold text-foreground">Instant Customizer Chat</h4>
                  <p className="text-sm text-foreground/70">Chat naturally with Kee to design a bouquet color palette or add personalization tags.</p>
                </div>
              </div>
            </div>
            
            <div className="pt-4">
              <Link href="/shop-helper" className="bg-primary text-white hover:bg-primary/90 px-6 py-3 rounded-full font-bold shadow transition inline-flex items-center gap-2">
                Launch AI Assistant <Sparkles className="w-4 h-4" />
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Instagram Live Showcase */}
      <section className="py-20 px-6 sm:px-12 lg:px-24 max-w-7xl mx-auto w-full">
        <div className="flex flex-col sm:flex-row justify-between items-center mb-12 gap-4">
          <div className="space-y-2 text-center sm:text-left">
            <h2 className="text-3xl font-bold text-foreground flex items-center justify-center sm:justify-start gap-2">
              <Instagram className="text-primary w-8 h-8" /> From Instagram @kee_crochet
            </h2>
            <p className="text-foreground/70">Follow our journey and view daily crochet drops direct from our workshop.</p>
          </div>
          <a
            href="https://www.instagram.com/kee_crochet"
            target="_blank"
            rel="noopener noreferrer"
            className="border border-primary text-primary hover:bg-primary/5 px-6 py-2.5 rounded-full font-bold transition flex items-center gap-2"
          >
            Visit Instagram Page
          </a>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
          {instagramPosts.map((post) => (
            <div key={post.id} className="group relative rounded-cozy overflow-hidden aspect-square border border-secondary shadow-sm hover:shadow-lg transition">
              <Image
                src={post.url}
                alt="Instagram post"
                fill
                className="object-cover group-hover:scale-105 transition-transform duration-500"
              />
              <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center text-white font-bold gap-2 z-10">
                <Heart className="w-5 h-5 fill-current" /> {post.likes} Likes
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Footer */}
      <footer className="mt-auto bg-foreground text-secondary px-6 sm:px-12 lg:px-24 py-12 border-t border-secondary/15">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row justify-between items-center gap-6">
          <div className="space-y-2 text-center md:text-left">
            <p className="text-xl font-bold text-white">Kee Crochet 🧶</p>
            <p className="text-sm text-secondary/60">Everlasting handmade crochet gifts crafted with premium cotton yarn.</p>
          </div>
          <div className="flex space-x-6 text-sm text-secondary/70">
            <Link href="/products" className="hover:text-white transition">Catalog</Link>
            <Link href="/shop-helper" className="hover:text-white transition">AI Personal Shopper</Link>
            <a href="https://www.instagram.com/kee_crochet" target="_blank" rel="noopener" className="hover:text-white transition">Instagram</a>
          </div>
        </div>
        <div className="max-w-7xl mx-auto text-center border-t border-secondary/10 mt-8 pt-6 text-xs text-secondary/40">
          &copy; {new Date().getFullYear()} Kee Crochet. All rights reserved. Hand-stitched with love in India.
        </div>
      </footer>
    </div>
  );
}
