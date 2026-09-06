"use client";

import { useState } from "react";
import Image from "next/image";
import { Sparkles, Instagram, Copy, Check, Upload, Palette, AlertCircle } from "lucide-react";
import { api, Product } from "@/lib/api";

interface AIStudioProps {
  products: Product[];
}

export default function AIStudio({ products }: AIStudioProps) {
  // Instagram Caption States
  const [selectedProductId, setSelectedProductId] = useState<string>(products[0]?.id || "");
  const [captionStyle, setCaptionStyle] = useState("trendy");
  const [captionLoading, setCaptionLoading] = useState(false);
  const [captionResult, setCaptionResult] = useState<any>(null);
  const [copied, setCopied] = useState(false);

  // Color Match States
  const [colorMatchPreview, setColorMatchPreview] = useState<string | null>(null);
  const [colorMatchLoading, setColorMatchLoading] = useState(false);
  const [colorMatchResult, setColorMatchResult] = useState<any>(null);

  const [error, setError] = useState("");

  const handleGenerateCaption = async () => {
    if (!selectedProductId) return;
    setCaptionLoading(true);
    setError("");

    try {
      const res = await api.ai.instagramCaption(selectedProductId, captionStyle);
      setCaptionResult(res);
    } catch (err: any) {
      console.error("Caption generation failed:", err);
      setError(err.message || "Failed to generate Instagram caption.");
    } finally {
      setCaptionLoading(false);
    }
  };

  const handleCopyCaption = () => {
    if (!captionResult) return;
    const textToCopy = `${captionResult.caption || captionResult.text || ""}\n\n${(captionResult.hashtags || []).join(" ")}`;
    navigator.clipboard.writeText(textToCopy);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleColorMatchUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files || !e.target.files[0]) return;
    const file = e.target.files[0];
    setColorMatchPreview(URL.createObjectURL(file));
    setColorMatchLoading(true);
    setError("");

    try {
      const res = await api.ai.colorMatch(file);
      setColorMatchResult(res);
    } catch (err: any) {
      console.error("Color match failed:", err);
      setError(err.message || "Failed to analyze yarn palette from image.");
    } finally {
      setColorMatchLoading(false);
    }
  };

  return (
    <div className="space-y-8 animate-fade-in">
      <div>
        <h2 className="text-xl font-black text-foreground">AI Creative Studio</h2>
        <p className="text-xs text-foreground/60">Generate Instagram reels captions, extract harmonious yarn color palettes, and craft listings</p>
      </div>

      {error && (
        <div className="bg-rose-50 border border-rose-200 text-rose-800 text-xs font-bold p-3.5 rounded-xl flex items-center gap-2">
          <AlertCircle className="w-4 h-4 text-rose-600" /> {error}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Instagram Post & Reel Caption Generator */}
        <div className="bg-white p-6 sm:p-7 rounded-2xl border border-secondary/40 shadow-sm space-y-5">
          <div className="flex items-center gap-2 pb-3 border-b border-secondary/30">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-amber-500 to-rose-500 text-white flex items-center justify-center">
              <Instagram className="w-4 h-4" />
            </div>
            <div>
              <h3 className="font-extrabold text-sm text-foreground">Instagram Caption Generator</h3>
              <p className="text-[11px] text-foreground/50">Generates engaging copy, hooks, and targeted hashtags</p>
            </div>
          </div>

          <div className="space-y-4">
            <div className="space-y-1">
              <label className="text-xs font-bold text-foreground/75">Select Crochet Creation</label>
              <select
                value={selectedProductId}
                onChange={(e) => setSelectedProductId(e.target.value)}
                className="w-full p-2.5 rounded-xl border border-secondary text-xs focus:outline-none focus:ring-2 focus:ring-primary/45 bg-white font-semibold"
              >
                {products.map((p) => (
                  <option key={p.id} value={p.id}>{p.title} (₹{p.price})</option>
                ))}
              </select>
            </div>

            <div className="space-y-1">
              <label className="text-xs font-bold text-foreground/75">Content Tone / Style</label>
              <div className="grid grid-cols-3 gap-2">
                {["trendy", "cozy", "aesthetic", "storytelling", "promotional", "humorous"].map((style) => (
                  <button
                    key={style}
                    type="button"
                    onClick={() => setCaptionStyle(style)}
                    className={`py-2 px-3 rounded-xl text-xs font-bold capitalize transition border ${
                      captionStyle === style
                        ? "bg-primary text-white border-primary shadow-sm"
                        : "bg-secondary/10 text-foreground/70 border-secondary/30 hover:border-primary"
                    }`}
                  >
                    {style}
                  </button>
                ))}
              </div>
            </div>

            <button
              type="button"
              onClick={handleGenerateCaption}
              disabled={captionLoading || !selectedProductId}
              className="w-full bg-primary text-white py-3 rounded-full text-xs font-bold shadow hover:bg-primary/95 transition flex items-center justify-center gap-1.5 disabled:opacity-50"
            >
              <Sparkles className="w-4 h-4" />
              {captionLoading ? "Crafting viral caption..." : "Generate Instagram Caption"}
            </button>

            {captionResult && (
              <div className="bg-secondary/10 p-4 rounded-xl space-y-3 pt-4 border border-secondary/20 relative">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-primary">Generated Caption</span>
                  <button
                    onClick={handleCopyCaption}
                    className="text-xs font-bold text-foreground/70 hover:text-primary flex items-center gap-1 bg-white px-2.5 py-1 rounded-lg border border-secondary/30 shadow-xs"
                  >
                    {copied ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5" />}
                    {copied ? "Copied!" : "Copy All"}
                  </button>
                </div>

                <p className="text-xs text-foreground/85 leading-relaxed whitespace-pre-wrap">
                  {captionResult.caption || captionResult.text || JSON.stringify(captionResult)}
                </p>

                {captionResult.hashtags && (
                  <div className="flex flex-wrap gap-1 pt-2 border-t border-secondary/20">
                    {captionResult.hashtags.map((tag: string, idx: number) => (
                      <span key={idx} className="text-[10px] text-primary font-mono bg-white px-2 py-0.5 rounded border border-secondary/30">
                        {tag.startsWith("#") ? tag : `#${tag}`}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Visual Color Matcher */}
        <div className="bg-white p-6 sm:p-7 rounded-2xl border border-secondary/40 shadow-sm space-y-5">
          <div className="flex items-center gap-2 pb-3 border-b border-secondary/30">
            <div className="w-8 h-8 rounded-lg bg-emerald-500/10 text-emerald-600 flex items-center justify-center">
              <Palette className="w-4 h-4" />
            </div>
            <div>
              <h3 className="font-extrabold text-sm text-foreground">Visual Yarn Color Matcher</h3>
              <p className="text-[11px] text-foreground/50">Extract harmonious yarn palettes from reference photos</p>
            </div>
          </div>

          <div className="space-y-4">
            <label className="border-2 border-dashed border-secondary/60 hover:border-primary p-6 rounded-2xl flex flex-col items-center justify-center cursor-pointer transition bg-secondary/5 hover:bg-secondary/10">
              <Upload className="w-8 h-8 text-primary mb-2" />
              <span className="text-xs font-bold text-foreground">Upload Reference Photo</span>
              <span className="text-[10px] text-foreground/50 mt-0.5">JPEG, PNG, or WebP under 5MB</span>
              <input type="file" accept="image/*" onChange={handleColorMatchUpload} className="hidden" />
            </label>

            {colorMatchPreview && (
              <div className="relative w-full h-36 rounded-xl overflow-hidden border border-secondary/30">
                <Image src={colorMatchPreview} alt="Palette preview" fill className="object-cover" />
              </div>
            )}

            {colorMatchLoading && (
              <p className="text-xs text-primary font-bold text-center animate-pulse">
                Extracting yarn color harmonies with Gemini Vision...
              </p>
            )}

            {colorMatchResult && (
              <div className="bg-secondary/10 p-4 rounded-xl space-y-3 border border-secondary/20">
                <span className="text-[10px] font-bold uppercase tracking-wider text-primary block">Extracted Color Harmonies</span>
                <div className="flex flex-wrap gap-2">
                  {(colorMatchResult.palette || colorMatchResult.colors || []).map((color: any, idx: number) => {
                    const colorName = typeof color === "string" ? color : color.name;
                    const hex = typeof color === "object" && color.hex ? color.hex : "#c084fc";
                    return (
                      <div key={idx} className="flex items-center gap-2 bg-white px-3 py-1.5 rounded-xl border border-secondary/30 shadow-xs">
                        <span className="w-4 h-4 rounded-full border border-black/10 flex-shrink-0" style={{ backgroundColor: hex }} />
                        <span className="text-xs font-bold text-foreground">{colorName}</span>
                      </div>
                    );
                  })}
                </div>
                {colorMatchResult.recommendation && (
                  <p className="text-xs text-foreground/75 mt-2 bg-white/70 p-2.5 rounded-lg border border-secondary/20">
                    {colorMatchResult.recommendation}
                  </p>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
