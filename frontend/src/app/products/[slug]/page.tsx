"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { ShoppingBag, ArrowLeft, Heart, Gift, Sparkles, Check, ChevronRight } from "lucide-react";
import Navbar from "@/components/Navbar";
import Image from "next/image";
import { api } from "@/lib/api";

export default function ProductDetailPage() {
  const params = useParams();
  const router = useRouter();
  const slug = params.slug as string;

  const [product, setProduct] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [selectedImage, setSelectedImage] = useState("");
  const [selectedVariant, setSelectedVariant] = useState<any>(null);
  const [selectedColor, setSelectedColor] = useState("");
  const [quantity, setQuantity] = useState(1);
  
  // Cart customization
  const [giftWrap, setGiftWrap] = useState(false);
  const [customNote, setCustomNote] = useState("");
  const [addingToCart, setAddingToCart] = useState(false);
  const [cartSuccess, setCartSuccess] = useState(false);

  // AI Review Summarizer
  const [aiSummaryLoading, setAiSummaryLoading] = useState(false);
  const [aiSummary, setAiSummary] = useState<any>(null);

  const [error, setError] = useState("");

  useEffect(() => {
    const fetchProduct = async () => {
      setLoading(true);
      setError("");
      try {
        const prod = await api.products.get(slug);
        setProduct(prod);
        if (prod.images && prod.images.length > 0) {
          setSelectedImage(prod.images[0]);
        }
        if (prod.colors && prod.colors.length > 0) {
          setSelectedColor(prod.colors[0]);
        }
        if (prod.variants && prod.variants.length > 0) {
          setSelectedVariant(prod.variants[0]);
        }
      } catch (e: any) {
        console.error("Failed to fetch product details", e);
        setError("Failed to retrieve product details. Please ensure the backend is running and the slug is correct.");
      }
      setLoading(false);
    };

    fetchProduct();
  }, [slug]);

  const handleAddToCart = async () => {
    if (!product) return;
    setAddingToCart(true);
    setCartSuccess(false);
    setError("");
    
    const payload = {
      product_id: product.id,
      variant_id: selectedVariant ? selectedVariant.id : null,
      quantity: quantity,
      gift_wrap: giftWrap,
      note: customNote.trim() || null,
    };

    try {
      await api.cart.addItem(payload);
      const count = parseInt(localStorage.getItem("cart_count") || "0", 10);
      localStorage.setItem("cart_count", String(count + quantity));
      window.dispatchEvent(new Event("cart-updated"));
      setCartSuccess(true);
      
      setTimeout(() => {
        setCartSuccess(false);
      }, 3000);
    } catch (e: any) {
      console.error("Failed to add to backend cart", e);
      setError(e.message || "Failed to add item to shopping bag. Make sure you are signed in.");
    } finally {
      setAddingToCart(false);
    }
  };

  const handleSummarizeReviews = async () => {
    if (!product) return;
    setAiSummaryLoading(true);
    try {
      const summary = await api.ai.summarizeReviews(product.id);
      setAiSummary(summary);
    } catch (e) {
      console.error("AI Review summarizer failed, using mock summary", e);
      setAiSummary({
        summary: "Customers adore the softness of the yarn and are pleased with the neat wrapping. Most comments state the plushie makes an excellent gift.",
        pros: ["Very high quality stitching", "Beautiful custom note cards included", "Incredibly soft feel"],
        cons: ["Needs 3 days extra for large custom stem orders"],
        sentiment: "Highly Positive"
      });
    }
    setAiSummaryLoading(false);
  };

  if (loading) {
    return (
      <div className="flex-1 flex flex-col min-h-screen">
        <Navbar />
        <div className="flex-1 flex flex-col items-center justify-center space-y-4">
          <div className="w-12 h-12 border-4 border-primary border-t-transparent rounded-full animate-spin"></div>
          <p className="text-foreground/75 font-semibold">Weaving your details...</p>
        </div>
      </div>
    );
  }

  if (error && !product) {
    return (
      <div className="flex-1 flex flex-col min-h-screen">
        <Navbar />
        <div className="flex-1 flex flex-col items-center justify-center space-y-4">
          <p className="text-lg font-bold text-rose-600">Connection Error</p>
          <p className="text-sm text-foreground/75 max-w-sm text-center">{error}</p>
          <button onClick={() => router.push("/products")} className="bg-primary text-white px-6 py-2 rounded-full font-bold">
            Back to Catalog
          </button>
        </div>
      </div>
    );
  }

  if (!product) {
    return (
      <div className="flex-1 flex flex-col min-h-screen">
        <Navbar />
        <div className="flex-1 flex flex-col items-center justify-center space-y-4">
          <p className="text-lg font-bold text-foreground">Crochet item not found.</p>
          <button onClick={() => router.push("/products")} className="bg-primary text-white px-6 py-2 rounded-full font-bold">
            Back to Shop
          </button>
        </div>
      </div>
    );
  }

  const finalPrice = product.price + (selectedVariant ? selectedVariant.price_delta : 0);

  return (
    <div className="flex-1 flex flex-col min-h-screen">
      <Navbar />

      <main className="max-w-7xl mx-auto w-full px-4 sm:px-6 lg:px-8 py-10 flex-1">
        {error && (
          <div className="mb-6 bg-rose-50 border border-rose-200 text-rose-800 text-sm font-bold p-4 rounded-xl flex items-center gap-2">
            <span>⚠️</span> {error}
          </div>
        )}
        {/* Back navigation */}
        <button onClick={() => router.back()} className="inline-flex items-center text-foreground/60 hover:text-primary mb-8 font-bold text-sm">
          <ArrowLeft className="w-4 h-4 mr-1.5" /> Back to Catalog
        </button>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-12">
          {/* Gallery Column */}
          <div className="space-y-6">
            <div className="relative aspect-square w-full rounded-cozy overflow-hidden border border-secondary bg-white">
              <Image
                src={selectedImage || "/images/category_bouquets.jpg"}
                alt={product.title}
                fill
                priority
                className="object-cover hover:scale-105 transition-transform duration-500 cursor-zoom-in"
                sizes="(max-width: 768px) 100vw, 50vw"
              />
            </div>
            
            {product.images && product.images.length > 1 && (
              <div className="grid grid-cols-4 gap-4">
                {product.images.map((img: string, idx: number) => (
                  <button
                    key={idx}
                    onClick={() => setSelectedImage(img)}
                    className={`relative aspect-square rounded-lg overflow-hidden border-2 ${selectedImage === img ? "border-primary shadow" : "border-secondary/40"}`}
                  >
                    <Image
                      src={img}
                      alt=""
                      fill
                      className="object-cover"
                      sizes="100px"
                    />
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Info Details Column */}
          <div className="space-y-8">
            <div>
              <h1 className="text-3xl font-extrabold text-foreground">{product.title}</h1>
              <p className="text-sm font-semibold text-primary mt-1.5">100% Hand-stitched crochet yarn</p>
            </div>

            {/* Pricing */}
            <div className="flex items-center space-x-4">
              <span className="text-3xl font-black text-foreground">₹{finalPrice}</span>
              {product.compare_at_price && (
                <span className="text-xl text-foreground/45 line-through">₹{product.compare_at_price}</span>
              )}
            </div>

            <p className="text-foreground/80 leading-relaxed text-sm sm:text-base">
              {product.description}
            </p>

            {/* Color selection */}
            {product.colors && product.colors.length > 0 && (
              <div className="space-y-3">
                <h3 className="font-bold text-sm text-foreground/75 uppercase tracking-wider">Select Yarn Accent Color</h3>
                <div className="flex gap-3 flex-wrap">
                  {product.colors.map((color: string) => (
                    <button
                      key={color}
                      onClick={() => setSelectedColor(color)}
                      className={`px-4 py-2 rounded-full border text-sm font-semibold transition ${selectedColor === color ? "border-primary bg-primary/10 text-primary" : "border-secondary/70 text-foreground/70 hover:bg-secondary/15"}`}
                    >
                      {color}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Variant selection */}
            {product.variants && product.variants.length > 0 && (
              <div className="space-y-3">
                <h3 className="font-bold text-sm text-foreground/75 uppercase tracking-wider">Select Pack/Size</h3>
                <div className="flex gap-3 flex-wrap">
                  {product.variants.map((v: any) => (
                    <button
                      key={v.id}
                      onClick={() => setSelectedVariant(v)}
                      className={`px-4 py-2 rounded-full border text-sm font-semibold transition ${selectedVariant?.id === v.id ? "border-primary bg-primary/10 text-primary" : "border-secondary/70 text-foreground/70 hover:bg-secondary/15"}`}
                    >
                      {v.value} {v.price_delta > 0 && `(+₹${v.price_delta})`}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Customization Details (Gift wrapping, special note) */}
            <div className="bg-secondary/15 border border-secondary/40 p-6 rounded-cozy space-y-4">
              <h3 className="font-bold text-sm text-foreground/75 uppercase tracking-wider flex items-center gap-1.5">
                <Gift className="w-5 h-5 text-primary" /> Gift Customizations
              </h3>
              
              <div className="flex items-center space-x-3">
                <input
                  type="checkbox"
                  id="giftwrap"
                  checked={giftWrap}
                  onChange={(e) => setGiftWrap(e.target.checked)}
                  className="w-4.5 h-4.5 rounded border-secondary accent-primary text-primary focus:ring-primary focus:ring-2 cursor-pointer"
                />
                <label htmlFor="giftwrap" className="text-sm font-bold text-foreground cursor-pointer">
                  Add Aesthetic Wrapping Paper (+₹40)
                </label>
              </div>
              
              <div className="space-y-2">
                <label className="block text-xs font-bold text-foreground/75">
                  Personalized Gift Card Note (Optional)
                </label>
                <textarea
                  rows={2}
                  placeholder="e.g. 'Happy Birthday Sis! Love you.'"
                  value={customNote}
                  onChange={(e) => setCustomNote(e.target.value)}
                  className="w-full p-3 rounded-xl border border-secondary/70 bg-white focus:outline-none focus:ring-2 focus:ring-primary/40 text-sm"
                />
              </div>
            </div>

            {/* Quantity and Cart Button */}
            <div className="flex items-center gap-4 flex-wrap">
              <div className="flex items-center border border-secondary rounded-full bg-white px-3 py-1.5 w-fit">
                <button
                  onClick={() => setQuantity(Math.max(1, quantity - 1))}
                  className="px-2 font-bold text-lg text-foreground/60 hover:text-primary"
                >
                  -
                </button>
                <span className="px-4 font-bold text-foreground">{quantity}</span>
                <button
                  onClick={() => setQuantity(quantity + 1)}
                  className="px-2 font-bold text-lg text-foreground/60 hover:text-primary"
                >
                  +
                </button>
              </div>

              <button
                onClick={handleAddToCart}
                disabled={addingToCart}
                className="flex-1 bg-primary text-white hover:bg-primary/95 px-8 py-3.5 rounded-full font-bold shadow-md hover:shadow-lg transition flex items-center justify-center gap-2 text-sm sm:text-base disabled:opacity-50"
              >
                {addingToCart ? "Adding..." : (
                  <>
                    <ShoppingBag className="w-5 h-5" /> Add to Shopping Bag
                  </>
                )}
              </button>
            </div>

            {cartSuccess && (
              <div className="bg-emerald-50 border border-emerald-200 text-emerald-800 text-sm font-bold p-3 rounded-xl flex items-center gap-2">
                <Check className="w-5 h-5 text-emerald-600" /> Item added to bag successfully!
              </div>
            )}

            {/* Delivery estimate */}
            <div className="text-xs text-foreground/60 space-y-1 pt-4 border-t border-secondary/30">
              <p>📍 Ships from Pune, India.</p>
              <p>🕒 Standard Delivery: 3-5 working days. Custom orders require 4 additional days for stitching.</p>
            </div>

            {/* AI Review Summarizer Section */}
            <div className="border border-primary/20 bg-primary/5 p-6 rounded-cozy space-y-4">
              <div className="flex justify-between items-center flex-wrap gap-2">
                <div>
                  <h3 className="font-extrabold text-sm text-foreground flex items-center gap-1.5">
                    <Sparkles className="w-4 h-4 text-primary animate-pulse" /> AI Review Summarizer (Demo Simulation)
                  </h3>
                  <p className="text-xs text-foreground/60">Generate a sample sentiment report using simulated demonstration reviews.</p>
                </div>
                
                <button
                  onClick={handleSummarizeReviews}
                  disabled={aiSummaryLoading}
                  className="text-xs bg-primary text-white hover:bg-primary/90 px-4 py-2 rounded-full font-extrabold shadow-sm transition"
                >
                  {aiSummaryLoading ? "Analyzing..." : "Generate AI Summary"}
                </button>
              </div>

              {aiSummary && (
                <div className="bg-white p-4 rounded-xl border border-primary/10 space-y-3.5 text-xs">
                  <div>
                    <span className="font-bold text-foreground">Verdict:</span>{" "}
                    <span className="bg-emerald-100 text-emerald-800 font-bold px-2 py-0.5 rounded-full text-[10px]">
                      {aiSummary.sentiment}
                    </span>
                  </div>
                  
                  <p className="text-foreground/80 leading-relaxed font-medium">{aiSummary.summary}</p>
                  
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2 border-t border-secondary/20">
                    <div className="space-y-1.5">
                      <span className="font-extrabold text-emerald-600 uppercase tracking-wider text-[10px]">Pros:</span>
                      <ul className="list-disc list-inside space-y-0.5 text-foreground/70">
                        {aiSummary.pros.map((pro: string, i: number) => <li key={i}>{pro}</li>)}
                      </ul>
                    </div>
                    
                    <div className="space-y-1.5">
                      <span className="font-extrabold text-rose-500 uppercase tracking-wider text-[10px]">Cons:</span>
                      <ul className="list-disc list-inside space-y-0.5 text-foreground/70">
                        {aiSummary.cons.map((con: string, i: number) => <li key={i}>{con}</li>)}
                      </ul>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
