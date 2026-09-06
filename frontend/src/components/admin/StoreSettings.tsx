"use client";

import { Shield, Truck, CreditCard, Cloud, Info } from "lucide-react";

export default function StoreSettings() {
  return (
    <div className="space-y-8 animate-fade-in max-w-4xl">
      <div>
        <h2 className="text-xl font-black text-foreground">Store Configuration & Policies</h2>
        <p className="text-xs text-foreground/60">Server financial limits, shipping rates, gift wrap options, and infrastructure statuses</p>
      </div>

      {/* Commerce Financial Rules (Server Authoritative) */}
      <div className="bg-white p-6 sm:p-7 rounded-2xl border border-secondary/40 shadow-sm space-y-5">
        <h3 className="font-extrabold text-sm text-foreground flex items-center gap-2">
          <Truck className="w-4 h-4 text-primary" /> Authoritative Shipping & Packaging Rules
        </h3>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="bg-secondary/10 p-4 rounded-xl space-y-1">
            <span className="text-[10px] font-bold uppercase tracking-wider text-foreground/50">Free Shipping Min</span>
            <p className="text-xl font-black text-foreground">₹999.00</p>
            <p className="text-[10px] text-foreground/50">Carts at or above qualify for free delivery</p>
          </div>

          <div className="bg-secondary/10 p-4 rounded-xl space-y-1">
            <span className="text-[10px] font-bold uppercase tracking-wider text-foreground/50">Standard Delivery Fee</span>
            <p className="text-xl font-black text-foreground">₹60.00</p>
            <p className="text-[10px] text-foreground/50">Applied on all orders below ₹999</p>
          </div>

          <div className="bg-secondary/10 p-4 rounded-xl space-y-1">
            <span className="text-[10px] font-bold uppercase tracking-wider text-foreground/50">Gift Wrapping Unit Fee</span>
            <p className="text-xl font-black text-foreground">₹50.00</p>
            <p className="text-[10px] text-foreground/50">Per gift-wrapped item with satin ribbon</p>
          </div>
        </div>

        <div className="bg-amber-50 border border-amber-200 p-3.5 rounded-xl text-xs text-amber-800 flex items-start gap-2">
          <Info className="w-4 h-4 text-amber-600 flex-shrink-0 mt-0.5" />
          <span>
            These financial parameters are enforced authoritatively by <code className="font-mono font-bold">PricingService</code> on the backend. Frontend prices are automatically computed from these exact constants.
          </span>
        </div>
      </div>

      {/* Service & Gateway Health */}
      <div className="bg-white p-6 sm:p-7 rounded-2xl border border-secondary/40 shadow-sm space-y-5">
        <h3 className="font-extrabold text-sm text-foreground flex items-center gap-2">
          <Shield className="w-4 h-4 text-emerald-600" /> Gateway & Infrastructure Integrations
        </h3>

        <div className="divide-y divide-secondary/20 text-xs">
          <div className="py-3 flex items-center justify-between">
            <div>
              <p className="font-bold text-foreground flex items-center gap-1.5">
                <CreditCard className="w-4 h-4 text-foreground/40" /> Razorpay Payment Gateway
              </p>
              <p className="text-[11px] text-foreground/50">Authoritative order creation and signature verification</p>
            </div>
            <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-800">
              Active (INR)
            </span>
          </div>

          <div className="py-3 flex items-center justify-between">
            <div>
              <p className="font-bold text-foreground flex items-center gap-1.5">
                <Cloud className="w-4 h-4 text-foreground/40" /> Storage Engine (PIL / WebP)
              </p>
              <p className="text-[11px] text-foreground/50">EXIF sanitization, WebP compression, and Cloudinary/S3 support</p>
            </div>
            <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-800">
              Active
            </span>
          </div>

          <div className="py-3 flex items-center justify-between">
            <div>
              <p className="font-bold text-foreground flex items-center gap-1.5">
                <Shield className="w-4 h-4 text-foreground/40" /> Session Security & Token Rotation
              </p>
              <p className="text-[11px] text-foreground/50">Hashed OTPs, short-lived JWTs, and database revocation table</p>
            </div>
            <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-800">
              Enforced
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
