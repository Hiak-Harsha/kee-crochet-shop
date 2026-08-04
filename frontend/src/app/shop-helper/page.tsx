"use client";

import { useState, useRef, useEffect } from "react";
import { Sparkles, Send, Upload, Heart, Image as ImageIcon, ShoppingCart, MessageSquare, Paintbrush, ArrowRight } from "lucide-react";
import Navbar from "@/components/Navbar";
import { api } from "@/lib/api";
import Link from "next/link";

export default function ShopHelperPage() {
  const [activeTab, setActiveTab] = useState<"shopper" | "color">("shopper");

  // AI Chat States
  const [messages, setMessages] = useState<any[]>([
    { role: "assistant", content: "Hi! I'm Kee, your AI Personal Shopper 🧶. Whether you're looking for a birthday bouquet, a desk friend, or a custom gift under budget, tell me who it's for, and I will recommend some ideas!" }
  ]);
  const [chatInput, setChatInput] = useState("");
  const [chatLoading, setChatLoading] = useState(false);
  const [recommendedProducts, setRecommendedProducts] = useState<any[]>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // AI Color Matcher States
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [colorMatchLoading, setColorMatchLoading] = useState(false);
  const [colorMatchResult, setColorMatchResult] = useState<any>(null);
  
  // Store Catalog reference for mapping recommendation IDs
  const [catalog, setCatalog] = useState<any[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    // Scroll chat to bottom
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    // Pre-fetch product list for matching recommendations
    const fetchCatalog = async () => {
      try {
        setError("");
        const prods = await api.products.list();
        setCatalog(prods || []);
      } catch (e: any) {
        console.error("Failed to load catalog:", e);
        setError("Failed to fetch product catalog from the database. Please verify the backend is online.");
      }
    };
    fetchCatalog();
  }, []);

  // Handle Send Chat
  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!chatInput.trim() || chatLoading) return;

    const userMessage = chatInput.trim();
    setMessages((prev) => [...prev, { role: "user", content: userMessage }]);
    setChatInput("");
    setChatLoading(true);
    setError("");

    try {
      const history = [...messages, { role: "user", content: userMessage }];
      const response = await api.ai.chat(history);
      
      setMessages((prev) => [...prev, { role: "assistant", content: response.reply }]);
      
      if (response.recommended_product_ids && response.recommended_product_ids.length > 0) {
        // Map recommended IDs to full product catalog
        const matches = catalog.filter((p) => 
          response.recommended_product_ids.includes(String(p.id)) || 
          response.recommended_product_ids.includes(p.slug)
        );
        setRecommendedProducts(matches);
      } else {
        setRecommendedProducts([]);
      }
    } catch (err: any) {
      console.error("AI Chat failed:", err);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "I'm sorry, I'm having trouble connecting to the AI helper right now. Please verify the backend is online and try again." }
      ]);
    }
    setChatLoading(false);
  };

  // Handle Image Selection
  const handleImageChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setSelectedFile(file);
      const reader = new FileReader();
      reader.onloadend = () => {
        setImagePreview(reader.result as string);
      };
      reader.readAsDataURL(file);
    }
  };

  // Handle Room Image Match Submit
  const handleColorMatchSubmit = async () => {
    if (!selectedFile) return;
    setColorMatchLoading(true);
    setColorMatchResult(null);
    setError("");

    try {
      const result = await api.ai.colorMatch(selectedFile);
      setColorMatchResult(result);
    } catch (e: any) {
      console.error("Color match failed:", e);
      setError("AI Room color matcher failed. Please verify the backend is online and try again.");
    }
    setColorMatchLoading(false);
  };

  const matchedItems = colorMatchResult
    ? catalog.filter((p) => colorMatchResult.matching_product_ids.includes(String(p.id)) || colorMatchResult.matching_product_ids.includes(p.slug))
    : [];

  return (
    <div className="flex-1 flex flex-col min-h-screen">
      <Navbar />

      <main className="max-w-7xl mx-auto w-full px-4 sm:px-6 lg:px-8 py-10 flex-1 flex flex-col">
        {error && (
          <div className="mb-6 bg-rose-50 border border-rose-200 text-rose-800 text-sm font-bold p-4 rounded-xl flex items-center gap-2">
            <span>⚠️</span> {error}
          </div>
        )}
        {/* Toggle tabs */}
        <div className="flex justify-center mb-8">
          <div className="bg-secondary/40 p-1.5 rounded-full flex space-x-1 border border-secondary/50">
            <button
              onClick={() => setActiveTab("shopper")}
              className={`px-6 py-2 rounded-full text-sm font-bold transition flex items-center gap-1.5 ${activeTab === "shopper" ? "bg-primary text-white shadow-sm" : "text-foreground/80 hover:text-primary"}`}
            >
              <MessageSquare className="w-4 h-4" /> AI Personal Shopper
            </button>
            <button
              onClick={() => setActiveTab("color")}
              className={`px-6 py-2 rounded-full text-sm font-bold transition flex items-center gap-1.5 ${activeTab === "color" ? "bg-primary text-white shadow-sm" : "text-foreground/80 hover:text-primary"}`}
            >
              <Paintbrush className="w-4 h-4" /> AI Room Color Matcher
            </button>
          </div>
        </div>

        {/* Tab 1: AI Personal Shopper */}
        {activeTab === "shopper" && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 flex-1">
            {/* Chat Area */}
            <div className="lg:col-span-2 bg-white rounded-cozy border border-secondary/50 flex flex-col h-[600px] overflow-hidden shadow-sm">
              <div className="bg-primary/5 p-4 border-b border-secondary/30 flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <div className="bg-primary text-white p-2 rounded-full animate-bounce-slow">
                    <Sparkles className="w-5 h-5" />
                  </div>
                  <div>
                    <h2 className="font-extrabold text-sm text-foreground">Personal Shopper "Kee"</h2>
                    <span className="text-[10px] bg-emerald-100 text-emerald-800 font-bold px-2 py-0.5 rounded-full">
                      Online • Gemini Powered
                    </span>
                  </div>
                </div>
              </div>

              {/* Message History */}
              <div className="flex-1 overflow-y-auto p-6 space-y-6">
                {messages.map((msg, index) => (
                  <div key={index} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
                    <div className={`max-w-[75%] p-4 rounded-2xl text-sm leading-relaxed ${msg.role === "user" ? "bg-primary text-white rounded-br-none" : "bg-secondary/20 text-foreground rounded-bl-none border border-secondary/30"}`}>
                      {msg.content}
                    </div>
                  </div>
                ))}
                
                {chatLoading && (
                  <div className="flex justify-start">
                    <div className="bg-secondary/20 border border-secondary/30 max-w-[75%] p-4 rounded-2xl rounded-bl-none flex items-center space-x-2">
                      <div className="w-2 h-2 bg-primary rounded-full animate-bounce"></div>
                      <div className="w-2 h-2 bg-primary rounded-full animate-bounce [animation-delay:0.2s]"></div>
                      <div className="w-2 h-2 bg-primary rounded-full animate-bounce [animation-delay:0.4s]"></div>
                    </div>
                  </div>
                )}
                
                <div ref={messagesEndRef} />
              </div>

              {/* Chat Input form */}
              <form onSubmit={handleSendMessage} className="p-4 border-t border-secondary/30 flex space-x-2 bg-yarn-cream/35">
                <input
                  type="text"
                  placeholder="Ask Kee anything... (e.g. 'I want keychains under ₹200')"
                  value={chatInput}
                  onChange={(e) => setChatInput(e.target.value)}
                  className="flex-1 px-4 py-2.5 rounded-full border border-secondary bg-white focus:outline-none focus:ring-2 focus:ring-primary/40 text-sm font-medium"
                />
                <button type="submit" className="bg-primary text-white p-3 rounded-full hover:bg-primary/95 shadow transition">
                  <Send className="w-5 h-5" />
                </button>
              </form>
            </div>

            {/* Recommendations Column */}
            <div className="space-y-6 lg:col-span-1">
              <div className="bg-white p-6 rounded-cozy border border-secondary/50 h-full shadow-sm">
                <h3 className="font-extrabold text-base text-foreground mb-6 flex items-center gap-1.5">
                  <Sparkles className="w-5 h-5 text-primary" /> AI Recommendations
                </h3>
                
                {recommendedProducts.length === 0 ? (
                  <div className="h-[450px] border-2 border-dashed border-secondary/50 rounded-2xl flex flex-col items-center justify-center p-6 text-center text-foreground/50">
                    <Sparkles className="w-8 h-8 mb-3 text-secondary animate-pulse" />
                    <p className="text-sm font-bold text-foreground/60">No Live Recommendations Yet</p>
                    <p className="text-xs text-foreground/45 mt-1 max-w-[200px]">Chat with Kee to receive custom matches on this panel.</p>
                  </div>
                ) : (
                  <div className="space-y-4 max-h-[500px] overflow-y-auto pr-1">
                    {recommendedProducts.map((p) => (
                      <div key={p.id} className="border border-secondary/50 p-4 rounded-xl flex space-x-4 bg-yarn-cream/10 hover:shadow-md transition">
                        <img
                          src={p.images?.[0] || "https://images.unsplash.com/photo-1544816155-12df9643f363?auto=format&fit=crop&q=80&w=200"}
                          alt={p.title}
                          className="w-16 h-16 rounded-lg object-cover border border-secondary"
                        />
                        <div className="flex-1 space-y-1">
                          <h4 className="font-bold text-sm text-foreground line-clamp-1">{p.title}</h4>
                          <p className="text-sm font-black text-primary">₹{p.price}</p>
                          <Link href={`/products/${p.slug}`} className="text-xs text-primary hover:underline font-bold inline-flex items-center gap-1 mt-1">
                            Buy Now <ArrowRight className="w-3.5 h-3.5" />
                          </Link>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Tab 2: AI Color Customizer */}
        {activeTab === "color" && (
          <div className="max-w-4xl mx-auto w-full grid grid-cols-1 md:grid-cols-2 gap-8">
            {/* Upload Area */}
            <div className="bg-white p-6 rounded-cozy border border-secondary/50 flex flex-col items-center space-y-6 shadow-sm">
              <h3 className="font-bold text-lg text-foreground text-center">Room Aesthetics Photo Matcher</h3>
              <p className="text-sm text-foreground/75 text-center leading-relaxed max-w-xs">
                Upload a picture of your bedroom shelf, office desk, or living room table, and our AI will select accent yarn colors and coordinate matching products!
              </p>

              <div className="relative w-full border-2 border-dashed border-secondary hover:border-primary rounded-cozy h-64 flex flex-col items-center justify-center bg-secondary/5 transition cursor-pointer">
                {imagePreview ? (
                  <img src={imagePreview} alt="Room aesthetic" className="w-full h-full object-cover rounded-cozy" />
                ) : (
                  <div className="flex flex-col items-center text-foreground/45">
                    <ImageIcon className="w-12 h-12 mb-3 text-secondary" />
                    <span className="text-sm font-bold">Drop room image here</span>
                    <span className="text-xs mt-1 text-foreground/35">PNG, JPG up to 5MB</span>
                  </div>
                )}
                <input
                  type="file"
                  accept="image/*"
                  onChange={handleImageChange}
                  className="absolute inset-0 opacity-0 cursor-pointer"
                />
              </div>

              <button
                onClick={handleColorMatchSubmit}
                disabled={!selectedFile || colorMatchLoading}
                className="w-full bg-primary text-white hover:bg-primary/95 py-3 rounded-full font-bold shadow transition flex items-center justify-center gap-2 disabled:opacity-50"
              >
                {colorMatchLoading ? "Weaving Palette..." : (
                  <>
                    <Sparkles className="w-5 h-5" /> Match Room Aesthetics
                  </>
                )}
              </button>
            </div>

            {/* Results Area */}
            <div className="bg-white p-6 rounded-cozy border border-secondary/50 shadow-sm flex flex-col justify-between">
              <div>
                <h3 className="font-extrabold text-base text-foreground mb-4">Aesthetic Match Analysis</h3>
                
                {!colorMatchResult ? (
                  <div className="h-60 border-2 border-dashed border-secondary/50 rounded-2xl flex flex-col items-center justify-center p-6 text-center text-foreground/40">
                    <Paintbrush className="w-8 h-8 mb-3 text-secondary animate-pulse" />
                    <p className="text-sm font-bold">Analysis Awaiting</p>
                    <p className="text-xs text-foreground/45 mt-1 max-w-[200px]">Upload a photo of your desk or bookshelf to view the matched yarn palettes.</p>
                  </div>
                ) : (
                  <div className="space-y-6">
                    {/* Color pills */}
                    <div className="space-y-2">
                      <span className="text-xs font-bold text-foreground/60 uppercase tracking-wider">Recommended Accent Colors</span>
                      <div className="flex gap-2.5 flex-wrap">
                        {colorMatchResult.recommended_colors.map((col: string, i: number) => (
                          <span key={i} className="bg-secondary text-secondary-foreground text-xs font-bold px-3 py-1.5 rounded-full flex items-center gap-1.5 border border-secondary/50 shadow-sm">
                            <span className="w-3.5 h-3.5 rounded-full bg-primary inline-block" style={{ backgroundColor: col === "Sage Green" ? "#9cbcae" : col === "Warm Beige" ? "#ebd8bd" : col === "Soft Yellow" ? "#fce18d" : "#c97d7b" }}></span>
                            {col}
                          </span>
                        ))}
                      </div>
                    </div>

                    {/* Reasoning */}
                    <div className="space-y-2">
                      <span className="text-xs font-bold text-foreground/60 uppercase tracking-wider block">AI Stylist reasoning</span>
                      <p className="text-sm text-foreground/80 leading-relaxed bg-primary/5 p-4 rounded-xl border border-primary/10">
                        {colorMatchResult.reasoning}
                      </p>
                    </div>

                    {/* Matched Products */}
                    {matchedItems.length > 0 && (
                      <div className="space-y-3">
                        <span className="text-xs font-bold text-foreground/60 uppercase tracking-wider block">Recommended matching items</span>
                        <div className="grid grid-cols-2 gap-4">
                          {matchedItems.map((p) => (
                            <Link href={`/products/${p.slug}`} key={p.id} className="border border-secondary/50 p-3 rounded-xl flex items-center space-x-3 hover:shadow transition">
                              <img src={p.images?.[0]} alt="" className="w-10 h-10 object-cover rounded border border-secondary" />
                              <div className="overflow-hidden">
                                <p className="text-xs font-bold text-foreground line-clamp-1">{p.title}</p>
                                <p className="text-[10px] font-black text-primary">₹{p.price}</p>
                              </div>
                            </Link>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
