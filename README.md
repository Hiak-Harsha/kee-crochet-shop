<p align="center">
  <img src="frontend/public/images/hero.jpg" alt="Kee Crochet" width="180" style="border-radius: 50%;" />
</p>

<h1 align="center">Kee Crochet Shop 🧶</h1>

<p align="center">
  <strong>A full-stack AI-powered e-commerce platform for handmade crochet products</strong>
</p>

<p align="center">
  <a href="#tech-stack"><img src="https://img.shields.io/badge/Next.js-16-black?logo=next.js" alt="Next.js" /></a>
  <a href="#tech-stack"><img src="https://img.shields.io/badge/FastAPI-0.115+-009688?logo=fastapi" alt="FastAPI" /></a>
  <a href="#tech-stack"><img src="https://img.shields.io/badge/React-19-61DAFB?logo=react" alt="React" /></a>
  <a href="#tech-stack"><img src="https://img.shields.io/badge/Gemini_AI-1.5_Flash-4285F4?logo=google" alt="Gemini" /></a>
  <a href="#tech-stack"><img src="https://img.shields.io/badge/Razorpay-Payments-2962FF?logo=razorpay" alt="Razorpay" /></a>
  <a href="#tech-stack"><img src="https://img.shields.io/badge/Tailwind-v4-06B6D4?logo=tailwindcss" alt="Tailwind" /></a>
</p>

<p align="center">
  🚀 <strong><a href="https://kee-crochet-shop.vercel.app">Live Demo Website (Vercel)</a></strong> | ⚙️ <strong><a href="https://kee-crochet-api.onrender.com">Backend API (Render)</a></strong>
</p>

<p align="center">
  Built for <a href="https://instagram.com/kee_crochet">@kee_crochet</a> — a real Instagram crochet business selling handmade bouquets, plushies, and keychains.
</p>

---

## ✨ Features

### 🛍️ Core E-Commerce
- **Product Catalog** — Filterable grid with category, price range, and keyword search
- **Product Detail Pages** — Image gallery, variant/color selection, gift wrapping, custom notes
- **Shopping Cart** — Real-time quantity management, gift wrap fees, free shipping threshold (₹999+)
- **Checkout & Payments** — Full Razorpay SDK integration with sandbox simulator for development
- **Order Management** — Order history, status tracking, unique order number generation
- **User Authentication** — JWT-based login/register with token refresh and OTP support

### 🤖 AI-Powered Features (Google Gemini)
- **AI Semantic Search** — Natural language queries like *"a flower gift under ₹500 for my sister"* matched against the real product catalog
- **AI Personal Shopper** — Conversational chatbot that understands gift context, budget, and occasion to recommend products
- **AI Room Color Matcher** — Upload a photo of your room; Gemini Vision analyzes the color palette and suggests matching crochet items
- **AI Review Summarizer** — Summarizes customer reviews into pros, cons, and sentiment score

### 🔐 Security & Production Hardening
- **Payment Verification** — HMAC signature verification; mock bypasses disabled in production
- **Stock Enforcement** — Row-level database locking prevents overselling on concurrent orders
- **Rate Limiting** — Sliding-window rate limiter on auth, login, OTP, and AI endpoints
- **Admin Route Guard** — JWT role-based access control; non-admin users redirected
- **No Silent Fallbacks** — Zero fake data substitution; honest error states throughout
- **CORS Policies** — Restrictive origin allowlists (not `*`) in production
- **Password Validation** — Minimum 8-character enforcement on registration

### 📱 Frontend Experience
- **Responsive Design** — Mobile-first layouts across all pages
- **Custom Design System** — Warm pastel palette with cozy rounded corners (`rounded-cozy`)
- **Micro-Animations** — Floating hero, spin loaders, hover scale effects, pulse indicators
- **Dynamic Admin Dashboard** — Real-time sales stats, order management, product CRUD grid

---

## 🏗️ Architecture

```
kee-crochet-shop/
├── backend/                    # FastAPI + SQLAlchemy (async)
│   ├── app/
│   │   ├── api/routes/         # REST endpoints
│   │   │   ├── ai.py           # Gemini-powered AI features
│   │   │   ├── auth.py         # JWT login, register, refresh, OTP
│   │   │   ├── cart.py         # Cart CRUD with stock validation
│   │   │   ├── orders.py       # Order lifecycle + Razorpay verification
│   │   │   └── products.py     # Catalog listing, categories, detail
│   │   ├── core/
│   │   │   ├── config.py       # Pydantic settings with .env support
│   │   │   ├── database.py     # Async SQLAlchemy engine + session
│   │   │   ├── rate_limiter.py # Sliding-window memory rate limiter
│   │   │   ├── security.py     # JWT token creation/validation, bcrypt
│   │   │   └── seed.py         # Database seeding (admin + demo products)
│   │   ├── models/             # SQLAlchemy ORM models
│   │   │   ├── cart.py         # Cart + CartItem
│   │   │   ├── order.py        # Order + OrderItem + Address
│   │   │   ├── product.py      # Product + ProductVariant + Category
│   │   │   └── user.py         # User + OTP + Address
│   │   ├── schemas/            # Pydantic request/response schemas
│   │   ├── services/
│   │   │   └── ai_service.py   # Gemini integration (413 lines)
│   │   └── main.py             # FastAPI app, lifespan, middleware
│   ├── requirements.txt
│   └── .env.example
│
└── frontend/                   # Next.js 16 + React 19 + Tailwind v4
    ├── src/
    │   ├── app/
    │   │   ├── page.tsx            # Landing page (hero, categories, Instagram)
    │   │   ├── products/page.tsx   # Product catalog with AI search
    │   │   ├── products/[slug]/    # Product detail + add to cart
    │   │   ├── cart/page.tsx       # Shopping bag management
    │   │   ├── checkout/page.tsx   # Razorpay payment flow
    │   │   ├── dashboard/page.tsx  # Customer account + order history
    │   │   ├── admin/page.tsx      # Admin panel (stats, products, orders)
    │   │   └── shop-helper/page.tsx # AI chatbot + room color matcher
    │   ├── components/
    │   │   └── Navbar.tsx          # Sticky nav with cart badge + auth state
    │   └── lib/
    │       └── api.ts              # Typed API client (all backend routes)
    └── public/images/              # Product + hero imagery
```

---

## <a id="tech-stack"></a>🔧 Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Frontend** | Next.js 16, React 19, TypeScript | App Router, SSR/SSG, Turbopack |
| **Styling** | Tailwind CSS v4, Geist Font | Custom design tokens, responsive layouts |
| **Backend** | FastAPI, Python 3.12+ | Async REST API, dependency injection |
| **ORM** | SQLAlchemy 2.0 (async) | Models, relationships, row-level locking |
| **Database** | SQLite (dev) / PostgreSQL (prod) | aiosqlite / asyncpg drivers |
| **Auth** | python-jose, passlib[bcrypt] | JWT access/refresh tokens, bcrypt hashing |
| **Payments** | Razorpay Checkout SDK | Order creation, HMAC signature verification |
| **AI** | Google Gemini 1.5 Flash | Semantic search, chatbot, vision analysis |
| **Image Processing** | Pillow | Room photo preprocessing for Gemini Vision |

---

## 🚀 Quick Start

### Prerequisites

- **Python** 3.12+
- **Node.js** 20+
- **npm** or **pnpm**

### 1. Clone the repository

```bash
git clone https://github.com/Hiak-Harsha/kee-crochet-shop.git
cd kee-crochet-shop
```

### 2. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv .venv

# Activate it
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys (see Environment Variables below)

# Start the backend server
uvicorn app.main:app --reload --port 8000
```

The backend auto-creates the SQLite database and seeds demo products + an admin account on first run.

### 3. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start the development server
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) to view the app.

---

## ⚙️ Environment Variables

Create a `.env` file in the `backend/` directory:

| Variable | Required | Description |
|----------|----------|-------------|
| `ENVIRONMENT` | Yes | `development` or `production` |
| `SECRET_KEY` | Yes | JWT signing secret (**must change in production**) |
| `DATABASE_URL` | No | Defaults to SQLite; use `postgresql+asyncpg://...` for prod |
| `GEMINI_API_KEY` | Recommended | [Google AI Studio](https://aistudio.google.com/) key — enables all AI features |
| `RAZORPAY_KEY_ID` | Optional | Razorpay dashboard key ID — enables real payments |
| `RAZORPAY_KEY_SECRET` | Optional | Razorpay secret — enables signature verification |
| `GOOGLE_CLIENT_ID` | Optional | Google OAuth client ID for social login |

> **Note:** The app runs fully without optional keys. AI features fall back to keyword matching, and payments use a sandbox simulator.

---

## 🧪 API Endpoints

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/auth/register` | Create new customer account |
| `POST` | `/api/auth/login` | Login with email/password → JWT |
| `POST` | `/api/auth/refresh` | Refresh access token |
| `POST` | `/api/auth/send-otp` | Send email OTP for verification |
| `POST` | `/api/auth/verify-otp` | Verify OTP code |

### Products
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/products` | List all products (filterable) |
| `GET` | `/api/products/{slug}` | Get product by slug |
| `GET` | `/api/products/categories` | List all categories |
| `POST` | `/api/products` | Create product (admin) |

### Cart
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/cart` | Get current user's cart |
| `POST` | `/api/cart/items` | Add item to cart |
| `PUT` | `/api/cart/items/{id}` | Update item quantity |
| `DELETE` | `/api/cart/items/{id}` | Remove item from cart |

### Orders
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/orders` | List user's orders |
| `POST` | `/api/orders` | Place order → creates Razorpay order |
| `POST` | `/api/orders/verify-payment` | Verify Razorpay HMAC signature |
| `PUT` | `/api/orders/{id}/status` | Update order status (admin) |
| `GET` | `/api/orders/admin/stats` | Sales analytics (admin) |

### AI Features
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/ai/search` | Semantic product search via Gemini |
| `POST` | `/api/ai/chat` | Conversational shopping assistant |
| `POST` | `/api/ai/color-match` | Room image → color palette analysis |
| `POST` | `/api/ai/summarize-reviews` | Review sentiment summarizer |

---

## 👤 Default Accounts

On first startup, the backend seeds these accounts:

| Role | Email | Password |
|------|-------|----------|
| Admin | `admin@keecrochet.com` | `admin123` |
| Customer | *(register via UI)* | *(min 8 chars)* |

> ⚠️ Change admin credentials via `ADMIN_EMAIL` / `ADMIN_PASSWORD` environment variables in production.

---

## 🖼️ Pages Overview

| Page | Route | Description |
|------|-------|-------------|
| **Home** | `/` | Hero section, category cards, Instagram feed, AI banner |
| **Products** | `/products` | Filterable catalog grid with AI semantic search |
| **Product Detail** | `/products/[slug]` | Gallery, variants, colors, gift wrap, add-to-cart |
| **Shopping Bag** | `/cart` | Cart items, quantity controls, price breakdown |
| **Checkout** | `/checkout` | Address form + Razorpay payment modal |
| **Dashboard** | `/dashboard` | Auth forms + customer order history + custom design requests |
| **Admin Panel** | `/admin` | Sales stats, product CRUD, order management |
| **AI Shop Helper** | `/shop-helper` | AI chatbot + room color matcher (dual-tab) |

---

## 📐 Design Decisions

- **No silent fallbacks** — When the backend is down, every page shows an explicit error state with retry buttons instead of silently substituting fake data. This was a deliberate architectural decision to prevent data integrity issues.
- **Optimistic cart updates removed** — Cart mutations (add/update/delete) only reflect in the UI after server confirmation. This prevents "phantom items" that exist in localStorage but not in the database.
- **Mock sandbox isolation** — Payment bypass codes (`mock_signature`, `rzp_mock_*`) are compile-time gated behind `ENVIRONMENT !== "production"`. They cannot accidentally run in production.
- **Row-level stock locking** — `SELECT ... FOR UPDATE` prevents two concurrent checkouts from both claiming the last item in stock.

---

## 🛣️ Roadmap

- [ ] Product reviews system (database model + frontend forms)
- [ ] Image upload pipeline (local storage → Cloudinary/S3)
- [ ] Guest cart support (localStorage merge on login)
- [ ] Automatic JWT refresh on 401 responses
- [ ] Coupon/discount code validation engine
- [ ] Admin product edit/deactivate/delete actions
- [ ] Email notifications (order confirmation, shipping updates)
- [ ] Wishlist / favorites system

---

## 📄 License

This project is built for [@kee_crochet](https://instagram.com/kee_crochet) as a portfolio + production platform. All rights reserved.

---

<p align="center">
  Made with 🧶 and ❤️ by <a href="https://github.com/Hiak-Harsha">Hiak-Harsha</a>
</p>
