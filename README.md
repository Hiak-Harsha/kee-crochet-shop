<p align="center">
  <img src="frontend/public/images/hero.jpg" alt="Kee Crochet" width="180" style="border-radius: 50%;" />
</p>

<h1 align="center">Kee Crochet Shop 🧶</h1>

<p align="center">
  <strong>Production-Hardened, Full-Stack AI E-Commerce Platform for Handcrafted Crochet Artistry</strong>
</p>

<p align="center">
  <a href="#tech-stack"><img src="https://img.shields.io/badge/Next.js-16.3-black?logo=next.js" alt="Next.js" /></a>
  <a href="#tech-stack"><img src="https://img.shields.io/badge/FastAPI-0.115+-009688?logo=fastapi" alt="FastAPI" /></a>
  <a href="#tech-stack"><img src="https://img.shields.io/badge/React-19-61DAFB?logo=react" alt="React" /></a>
  <a href="#tech-stack"><img src="https://img.shields.io/badge/Gemini_AI-1.5_Flash-4285F4?logo=google" alt="Gemini" /></a>
  <a href="#tech-stack"><img src="https://img.shields.io/badge/Razorpay-Payments-2962FF?logo=razorpay" alt="Razorpay" /></a>
  <a href="#tech-stack"><img src="https://img.shields.io/badge/PostgreSQL_%2F_SQLite-Alembic-336791?logo=postgresql" alt="PostgreSQL" /></a>
  <a href="#tech-stack"><img src="https://img.shields.io/badge/Pytest-100%25_Passing-brightgreen?logo=pytest" alt="Pytest" /></a>
</p>

<p align="center">
  Built for <a href="https://instagram.com/kee_crochet">@kee_crochet</a> — a handcrafted crochet brand specializing in artisan bouquets, plushies, wearables, and custom commissions.
</p>

---

## 🌟 Executive Summary & Production Readiness

This repository has been comprehensively refactored, audited, and hardened into a **production-ready e-commerce platform**. Zero mock data, simulated payments, or fake AI responses are used in production. All financial calculations, coupon validations, inventory locks, and access controls are **server-authoritative**.

- **Clean Build & Linting**: 100% passing across TypeScript 5, Turbopack, and ESLint (0 errors).
- **Comprehensive Test Suite**: Automated Pytest suite with 13 unit, integration, and high-concurrency race condition tests (100% green).
- **24-Entity Domain Model**: Complete lifecycle support managed via Alembic migrations.
- **Race Condition Immunity**: Database-agnostic atomic conditional stock decrement (`UPDATE products SET stock = stock - :qty WHERE id = :id AND stock >= :qty`) with 15-minute TTL reservation records and an append-only audit ledger.
- **Server-Authoritative Pricing**: High-precision `Decimal` financial engine for subtotal, free shipping thresholds (₹999), gift wrapping (₹50/item), and percentage discounts with maximum caps.
- **Production Payment Security**: Razorpay HMAC-SHA256 signature verification, strict order-to-payment amount matching, and idempotent webhook handling.
- **Enterprise Session Authentication**: Multi-device token rotation, salted SHA-256 OTP hashing with rate limits, token revocation blacklist, and single-flight client mutex refresh.
- **12-Module Admin Suite**: Modular control center with granular sub-dashboards under `frontend/src/components/admin/`.

---

## 🏗️ Architecture & Domain Model

```
kee-crochet-shop/
├── .github/workflows/          # Automated CI/CD pipelines
│   ├── ci.yml                  # Linting, migrations, pytest & Next.js build
│   └── keep_alive.yml          # Render health ping cron
├── backend/                    # FastAPI + SQLAlchemy 2.0 Async
│   ├── alembic/                # Database migrations & version control
│   ├── app/
│   │   ├── api/routes/         # REST API routers
│   │   │   ├── ai.py           # Gemini 1.5 Flash assistant & visual matcher
│   │   │   ├── auth.py         # Registration, sessions, OTP, token rotation
│   │   │   ├── cart.py         # Guest carts, quote engine, stock locks
│   │   │   ├── orders.py       # Order lifecycle, payments, cancellation
│   │   │   └── products.py     # Catalog, reviews, coupons, image uploads
│   │   ├── core/
│   │   │   ├── config.py       # Pydantic Settings with env validation
│   │   │   ├── database.py     # Async session factory (SQLite/PostgreSQL)
│   │   │   ├── rate_limiter.py # Sliding-window IP/endpoint rate limiting
│   │   │   └── security.py     # Salted password & OTP hashing, JWT
│   │   ├── models/             # 24 Domain entities (ORM)
│   │   │   ├── cart.py         # Cart, CartItem
│   │   │   ├── custom_request.py # Bespoke inquiries & palettes
│   │   │   ├── order.py        # Order, OrderItem, Reservation, Ledger
│   │   │   ├── product.py      # Product, Variant, Review, Coupon
│   │   │   └── user.py         # User, Session, TokenRevocation, OTP
│   │   ├── schemas/            # Pydantic validation schemas
│   │   ├── services/           # Authoritative business logic
│   │   │   ├── ai_service.py   # Gemini AI vision and conversational logic
│   │   │   ├── email_service.py # Transactional notification service
│   │   │   ├── inventory_service.py # Atomic stock reservations & release
│   │   │   ├── payment_service.py # Razorpay HMAC & webhook idempotency
│   │   │   ├── pricing_service.py # Decimal financial calculation engine
│   │   │   └── storage_service.py # WebP sanitization & image pipeline
│   │   └── main.py             # App factory, CORS, exception handlers
│   ├── tests/                  # Pytest test suite & concurrency tests
│   ├── requirements.txt        # Backend dependencies
│   └── alembic.ini             # Migration configuration
│
└── frontend/                   # Next.js 16 + React 19 + Tailwind CSS
    ├── src/
    │   ├── app/
    │   │   ├── admin/          # 12-Module Admin Dashboard
    │   │   ├── cart/           # Interactive cart & quote breakdown
    │   │   ├── checkout/       # Address form & Razorpay modal
    │   │   ├── dashboard/      # Customer portal & order tracking
    │   │   ├── products/       # Catalog & detail pages
    │   │   └── shop-helper/    # AI Personal Shopper & Room Matcher
    │   ├── components/
    │   │   ├── admin/          # 12 Modular Admin Panels
    │   │   └── Navbar.tsx      # Reactive header with cart badge
    │   └── lib/
    │       └── api.ts          # Unified client with refresh mutex
    └── public/images/          # Product and brand assets
```

---

## 🔒 Hardened Concurrency & Financial Protections

### 1. The 10-Concurrent-Checkout Race Condition Guarantee
Traditional e-commerce architectures fail under flash sales when multiple customers check out the last remaining stock item simultaneously. Kee Crochet employs **atomic conditional decrement**:
```sql
UPDATE products 
SET stock = stock - :quantity 
WHERE id = :product_id AND stock >= :quantity AND is_active = true
```
Because the row update condition requires `stock >= :quantity`, the database serialization lock guarantees that **only 1 request can decrement the stock from 1 to 0**. The remaining 9 concurrent requests receive zero rows updated, immediately triggering an HTTP 400 with `"Insufficient stock"`. Database stock never drops below zero.

### 2. Inventory Reservations with 15-Minute TTL
When an order is created, an `InventoryReservation` record is registered in `ACTIVE` status. If payment is not completed within 15 minutes, the stock is automatically returned to available inventory via `InventoryService.release_expired_reservations()`.

### 3. Server-Authoritative Pricing Engine
Clients cannot tamper with prices. The frontend transmits only item IDs and quantities; `PricingService` recalculates all financials from database rows:
- **Subtotal**: Calculated using `Decimal` precision.
- **Shipping**: Free shipping threshold at **₹999.00**; standard flat fee of **₹79.00** otherwise.
- **Gift Wrapping**: **₹50.00** per wrapped item.
- **Discounts**: Coupons enforce validity windows, minimum spend thresholds, per-customer usage limits, and maximum discount caps.

---

## 🎛️ Modular Admin Suite (12 Modules)

The admin panel at `/admin` is decomposed into 12 dedicated, isolated components located in [`frontend/src/components/admin/`](frontend/src/components/admin/):

1. **`DashboardOverview.tsx`** — Executive KPIs: Gross revenue, active orders, conversion rate, low-stock warnings, and recent transaction stream.
2. **`ProductManagement.tsx`** — Catalog CRUD with image upload pipeline, variant builder (sizes, colors), and AI photo description assistant.
3. **`CategoryManagement.tsx`** — Taxonomy manager for slugs, starting prices, banners, and product counts.
4. **`InventoryManager.tsx`** — Real-time stock matrix with instant `+`/`-` stock adjustments, low-stock alerts, and SKU filters.
5. **`OrderManager.tsx`** — Order fulfillment terminal with status filters (`pending_payment`, `paid`, `processing`, `shipped`, `delivered`), tracking number assignment, and address inspection.
6. **`CustomerDirectory.tsx`** — Customer directory showing lifetime spend, total orders, last order date, and phone numbers.
7. **`ReviewModerator.tsx`** — Review management interface with verified purchase badges, approve/delete controls, and AI sentiment summarizer.
8. **`CouponManager.tsx`** — Promotion creator supporting percentage/flat discounts, expiry schedules, usage limits, and active toggles.
9. **`CustomRequestInbox.tsx`** — Inbox for custom bespoke crochet inquiries, reference photos, budget limits, and yarn color palette viewer.
10. **`AIStudio.tsx`** — Social content generator that produces Instagram captions and visual yarn palette color matchers.
11. **`StoreAnalytics.tsx`** — Performance charts for top-selling crochet items, average order value (AOV), and gift wrap uptake.
12. **`StoreSettings.tsx`** — Security and financial settings: shipping fee controls, free shipping thresholds, payment gateway health, and security status.

---

## 🚀 Getting Started

### Prerequisites
- **Python 3.12+**
- **Node.js 20+**
- **Git**

### 1. Backend Setup

```bash
cd backend

# Create and activate virtual environment
python -m venv .venv

# Windows:
.\.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Start development server
uvicorn app.main:app --reload --port 8000
```

The backend starts at `http://localhost:8000`. Interactive OpenAPI documentation is accessible at `http://localhost:8000/docs`.

### 2. Frontend Setup

```bash
cd frontend

# Install packages
npm install

# Run Next.js development server
npm run dev
```

The frontend application starts at `http://localhost:3000`.

---

## 🧪 Testing & Verification

### Running Backend Pytest Suite
Run the test suite from the `backend/` directory:
```bash
pytest -v
```

**Test Coverage Highlights**:
- `test_pricing.py`: Verifies subtotal, ₹999 shipping threshold, ₹50 gift wrap, and percentage discount caps.
- `test_auth.py`: Verifies registration, login, Bearer token access, and salted OTP hashing.
- `test_inventory_concurrency.py`: Fires 10 simultaneous concurrent checkout attempts for the last stock unit to verify zero overselling.
- `test_orders_and_payments.py`: Verifies stock reservation on order creation, stock commitment on payment verification, and stock restoration on cancellation.
- `test_reviews.py`: Enforces verified purchase checks before permitting customer reviews.

### Running Frontend Verification
Run from the `frontend/` directory:
```bash
# TypeScript type check & Next.js production build
npm run build

# ESLint validation
npm run lint
```

---

## ⚙️ Environment Variables

### Backend (`backend/.env`)

```ini
ENVIRONMENT=development
SECRET_KEY=your-super-secret-minimum-32-character-key
DATABASE_URL=sqlite+aiosqlite:///./crochet.db
# For PostgreSQL production:
# DATABASE_URL=postgresql+asyncpg://user:password@hostname:5432/keecrochet

# AI Features (Google Gemini)
GEMINI_API_KEY=your_gemini_api_key

# Payment Gateway (Razorpay)
RAZORPAY_KEY_ID=your_razorpay_key_id
RAZORPAY_KEY_SECRET=your_razorpay_key_secret
RAZORPAY_WEBHOOK_SECRET=your_razorpay_webhook_secret

# Default Admin Credentials (Seeded on first boot)
ADMIN_EMAIL=admin@keecrochet.com
ADMIN_PASSWORD=AdminMasterKey123!

# Frontend Origin
CORS_ORIGINS=["http://localhost:3000", "https://kee-crochet-shop.vercel.app"]
```

### Frontend (`frontend/.env.local`)

```ini
NEXT_PUBLIC_API_URL=http://localhost:8000/api
NEXT_PUBLIC_RAZORPAY_KEY_ID=your_razorpay_key_id
```

---

## 📜 Default Credentials (Local Development)

| Role | Email | Password |
|------|-------|----------|
| **Administrator** | `admin@keecrochet.com` | `admin123` (or `ADMIN_PASSWORD` in `.env`) |
| **Customer** | Registered via UI | Minimum 8 characters |

---

<p align="center">
  Crafted with 🧶 and precision for <a href="https://instagram.com/kee_crochet">@kee_crochet</a>.
</p>
