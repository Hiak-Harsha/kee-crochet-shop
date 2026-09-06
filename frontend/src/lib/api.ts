// API Client for Kee Crochet AI Platform backend

export interface User {
  id: string;
  email: string;
  full_name: string;
  phone?: string | null;
  role: "customer" | "admin";
  is_active: boolean;
  avatar_url?: string | null;
  created_at: string;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: User;
}

export interface ProductVariant {
  id: string;
  name: string;
  value: string;
  sku?: string | null;
  price?: number | null;
  price_delta?: number;
  stock: number;
  is_active: boolean;
}

export interface Product {
  id: string;
  title: string;
  slug: string;
  description?: string | null;
  price: number;
  compare_at_price?: number | null;
  category_id?: string | null;
  images: string[];
  tags: string[];
  colors: string[];
  stock: number;
  is_active: boolean;
  is_featured: boolean;
  variants: ProductVariant[];
  created_at: string;
  updated_at: string;
}

export interface Category {
  id: string;
  name: string;
  slug: string;
  description?: string | null;
  starting_price?: number | null;
}

export interface CartItem {
  id: string;
  cart_id: string;
  product_id: string;
  variant_id?: string | null;
  quantity: number;
  gift_wrap: boolean;
  note?: string | null;
  product?: Product;
  unit_price: number;
  total_price: number;
}

export interface Cart {
  id: string;
  user_id?: string | null;
  session_token?: string | null;
  items: CartItem[];
  subtotal: number;
  gift_wrap_fee: number;
  shipping_fee: number;
  discount: number;
  total: number;
}

export interface CartQuote {
  subtotal: number;
  item_discounts: number;
  coupon_discount: number;
  gift_wrap_fee: number;
  shipping_fee: number;
  tax: number;
  total: number;
  coupon_code?: string | null;
}

export interface CouponValidation {
  code: string;
  type: string;
  value: number;
  discount_amount: number;
  description?: string | null;
}

export interface Coupon {
  id: string;
  code: string;
  description?: string | null;
  type: "percentage" | "fixed" | "free_shipping";
  value: number;
  minimum_order_value: number;
  maximum_discount?: number | null;
  usage_limit?: number | null;
  times_used: number;
  per_customer_limit: number;
  is_active: boolean;
  start_at?: string | null;
  expires_at?: string | null;
  created_at: string;
}

export interface OrderItem {
  id: string;
  product_id: string;
  variant_id?: string | null;
  product_title: string;
  variant_name?: string | null;
  sku?: string | null;
  unit_price: number;
  quantity: number;
  total_price: number;
  gift_wrap: boolean;
  note?: string | null;
}

export interface ShippingAddress {
  full_name: string;
  address_line1: string;
  address_line2?: string | null;
  city: string;
  state: string;
  postal_code: string;
  country: string;
  phone: string;
}

export interface Order {
  id: string;
  order_number: string;
  user_id: string;
  status: string;
  subtotal: number;
  item_discounts: number;
  coupon_discount: number;
  discount: number;
  gift_wrap_fee: number;
  shipping_fee: number;
  tax: number;
  total: number;
  shipping_address: ShippingAddress;
  razorpay_order_id?: string | null;
  razorpay_payment_id?: string | null;
  coupon_code?: string | null;
  delivery_slot?: string | null;
  created_at: string;
  updated_at: string;
  items: OrderItem[];
}

let rawBaseUrl = process.env.NEXT_PUBLIC_API_URL;

if (!rawBaseUrl) {
  if (typeof window !== "undefined" && (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1")) {
    rawBaseUrl = "http://localhost:8000/api";
  } else {
    rawBaseUrl = "https://kee-crochet-api.onrender.com/api";
  }
}

if (rawBaseUrl.endsWith("/")) {
  rawBaseUrl = rawBaseUrl.slice(0, -1);
}
if (!rawBaseUrl.endsWith("/api")) {
  rawBaseUrl = `${rawBaseUrl}/api`;
}
const BASE_URL = rawBaseUrl;

// Single-flight mutex for token refresh
let isRefreshing = false;
let refreshSubscribers: ((token: string) => void)[] = [];

function subscribeTokenRefresh(cb: (token: string) => void) {
  refreshSubscribers.push(cb);
}

function onRefreshed(token: string) {
  refreshSubscribers.forEach((cb) => cb(token));
  refreshSubscribers = [];
}

async function getHeaders(multipart = false): Promise<Record<string, string>> {
  const headers: Record<string, string> = {};
  if (!multipart) {
    headers["Content-Type"] = "application/json";
  }

  if (typeof window !== "undefined") {
    const token = localStorage.getItem("access_token");
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    // Guest cart session token
    const cartToken = localStorage.getItem("kc_cart_token");
    if (cartToken) {
      headers["X-Session-Token"] = cartToken;
    }
  }
  return headers;
}

async function request<T = any>(endpoint: string, options: RequestInit = {}, multipart = false): Promise<T> {
  const headers = await getHeaders(multipart);

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 45000);

  const config = {
    ...options,
    signal: controller.signal,
    headers: {
      ...headers,
      ...(options.headers || {}),
    },
  };

  try {
    let response = await fetch(`${BASE_URL}${endpoint}`, config);

    // Save session token if returned in header
    const returnedSessionToken = response.headers.get("X-Session-Token");
    if (returnedSessionToken && typeof window !== "undefined") {
      localStorage.setItem("kc_cart_token", returnedSessionToken);
    }

    // Automatically attempt token refresh on 401 if a refresh token is available and we aren't calling auth routes
    if (response.status === 401 && !endpoint.includes("/auth/")) {
      const refreshToken = typeof window !== "undefined" ? localStorage.getItem("refresh_token") : null;

      if (refreshToken) {
        if (!isRefreshing) {
          isRefreshing = true;
          try {
            const refreshResp = await fetch(`${BASE_URL}/auth/refresh`, {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ refresh_token: refreshToken }),
            });

            if (refreshResp.ok) {
              const tokens: AuthTokens = await refreshResp.json();
              localStorage.setItem("access_token", tokens.access_token);
              localStorage.setItem("refresh_token", tokens.refresh_token);
              isRefreshing = false;
              onRefreshed(tokens.access_token);

              // Retry original
              const newHeaders = await getHeaders(multipart);
              const retryConfig = {
                ...config,
                headers: {
                  ...newHeaders,
                  ...(options.headers || {}),
                },
              };
              response = await fetch(`${BASE_URL}${endpoint}`, retryConfig);
            } else {
              isRefreshing = false;
              localStorage.removeItem("access_token");
              localStorage.removeItem("refresh_token");
              window.dispatchEvent(new Event("unauthorized"));
            }
          } catch (refreshErr) {
            isRefreshing = false;
            console.error("Auto-refresh token failed:", refreshErr);
          }
        } else {
          // Wait for the single-flight refresh to complete
          const retryToken = await new Promise<string>((resolve) => {
            subscribeTokenRefresh((token) => resolve(token));
          });
          const newHeaders = await getHeaders(multipart);
          newHeaders["Authorization"] = `Bearer ${retryToken}`;
          const retryConfig = {
            ...config,
            headers: {
              ...newHeaders,
              ...(options.headers || {}),
            },
          };
          response = await fetch(`${BASE_URL}${endpoint}`, retryConfig);
        }
      } else {
        window.dispatchEvent(new Event("unauthorized"));
      }
    }

    clearTimeout(timeoutId);

    if (!response.ok) {
      const errorText = await response.text();
      let errorMessage = "Request failed";
      try {
        const errorJson = JSON.parse(errorText);
        if (Array.isArray(errorJson.detail)) {
          errorMessage = errorJson.detail.map((d: any) => d.msg).join(", ");
        } else {
          errorMessage = errorJson.detail || errorMessage;
        }
      } catch {
        errorMessage = errorText || errorMessage;
      }
      throw new Error(errorMessage);
    }

    if (response.status === 204) {
      return null as any;
    }

    const data = await response.json();

    // Persist session token if returned in JSON (e.g. cart response)
    if (data && data.session_token && typeof window !== "undefined") {
      localStorage.setItem("kc_cart_token", data.session_token);
    }

    return data as T;
  } catch (err: any) {
    clearTimeout(timeoutId);
    if (err.name === "AbortError") {
      throw new Error("The database server is waking up from standby. This can take up to a minute on first load. Please refresh in a moment.");
    }
    throw err;
  }
}

export const api = {
  // Authentication
  auth: {
    register: (payload: any) => request<AuthTokens>("/auth/register", { method: "POST", body: JSON.stringify(payload) }),
    login: (payload: any) => request<AuthTokens>("/auth/login", { method: "POST", body: JSON.stringify(payload) }),
    requestOtp: (payload: { email?: string; identifier?: string }) => 
      request("/auth/otp/request", { method: "POST", body: JSON.stringify({ email: payload.email || payload.identifier }) }),
    verifyOtp: (payload: { email?: string; identifier?: string; otp?: string; code?: string }) => 
      request<AuthTokens>("/auth/otp/verify", { 
        method: "POST", 
        body: JSON.stringify({ email: payload.email || payload.identifier, otp: payload.otp || payload.code }) 
      }),
    googleLogin: (idToken: string) => request<AuthTokens>("/auth/google", { method: "POST", body: JSON.stringify({ id_token: idToken }) }),
    refresh: (refreshToken: string) => request<AuthTokens>("/auth/refresh", { method: "POST", body: JSON.stringify({ refresh_token: refreshToken }) }),
    me: () => request<User>("/auth/me"),
    logout: () => request("/auth/logout", { method: "POST" }),
    logoutAll: () => request("/auth/logout-all", { method: "POST" }),
  },

  // Products and Categories
  products: {
    list: (params: { category_slug?: string; q?: string; min_price?: number; max_price?: number; featured?: boolean } = {}) => {
      const query = new URLSearchParams();
      if (params.category_slug) query.append("category_slug", params.category_slug);
      if (params.q) query.append("q", params.q);
      if (params.min_price !== undefined) query.append("min_price", String(params.min_price));
      if (params.max_price !== undefined) query.append("max_price", String(params.max_price));
      if (params.featured !== undefined) query.append("featured", String(params.featured));
      const qs = query.toString();
      return request<Product[]>(qs ? `/products?${qs}` : "/products");
    },
    get: (slug: string) => request<Product>(`/products/${slug}`),
    create: (payload: any) => request<Product>("/products", { method: "POST", body: JSON.stringify(payload) }),
    update: (id: string, payload: any) => request<Product>(`/products/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
    delete: (id: string) => request<void>(`/products/${id}`, { method: "DELETE" }),
    
    // Categories
    listCategories: () => request<Category[]>("/categories"),
    createCategory: (payload: any) => request<Category>("/categories", { method: "POST", body: JSON.stringify(payload) }),
    createCustomRequest: (payload: { description: string; color_palette: string | null }) => 
      request("/products/custom-requests", { method: "POST", body: JSON.stringify(payload) }),
    uploadImage: (file: File) => {
      const fd = new FormData();
      fd.append("file", file);
      return request<{ url: string }>("/products/upload-image", { method: "POST", body: fd }, true);
    },
    getReviews: (productId: string) => request<any[]>(`/products/${productId}/reviews`),
    addReview: (productId: string, payload: { rating: number; comment: string }) => 
      request(`/products/${productId}/reviews`, { method: "POST", body: JSON.stringify(payload) }),
  },

  // Cart
  cart: {
    get: () => request<Cart>("/cart"),
    addItem: (payload: { product_id: string; variant_id?: string | null; quantity: number; gift_wrap?: boolean; note?: string | null }) => 
      request<Cart>("/cart/items", { method: "POST", body: JSON.stringify(payload) }),
    updateItem: (itemId: string, payload: { quantity?: number; gift_wrap?: boolean; note?: string | null }) => 
      request<Cart>(`/cart/items/${itemId}`, { method: "PATCH", body: JSON.stringify(payload) }),
    removeItem: (itemId: string) => request<Cart>(`/cart/items/${itemId}`, { method: "DELETE" }),
    getQuote: (couponCode?: string | null) => 
      request<CartQuote>("/cart/quote", { method: "POST", body: JSON.stringify({ coupon_code: couponCode || null }) }),
    merge: (guestSessionToken: string) => 
      request<Cart>("/cart/merge", { method: "POST", body: JSON.stringify({ guest_session_token: guestSessionToken }) }),
  },

  // Coupons
  coupons: {
    validate: (code: string, subtotal: number) => 
      request<CouponValidation>("/coupons/validate", { method: "POST", body: JSON.stringify({ code, subtotal }) }),
    adminList: () => request<Coupon[]>("/admin/coupons"),
    adminCreate: (payload: any) => request<Coupon>("/admin/coupons", { method: "POST", body: JSON.stringify(payload) }),
    adminUpdate: (id: string, payload: any) => request<Coupon>(`/admin/coupons/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
  },

  // Orders
  orders: {
    create: (payload: { shipping_address: ShippingAddress; coupon_code?: string | null; delivery_slot?: string | null }) => 
      request<Order>("/orders", { method: "POST", body: JSON.stringify(payload) }),
    verifyPayment: (payload: { order_id: string; razorpay_order_id: string; razorpay_payment_id: string; razorpay_signature: string }) => 
      request<Order>("/orders/verify-payment", { method: "POST", body: JSON.stringify(payload) }),
    cancel: (id: string) => request<Order>(`/orders/${id}/cancel`, { method: "POST" }),
    list: () => request<Order[]>("/orders"),
    get: (id: string) => request<Order>(`/orders/${id}`),
    
    // Admin orders
    adminListAll: (page = 1, limit = 20, status?: string) => {
      const q = new URLSearchParams({ page: String(page), limit: String(limit) });
      if (status) q.append("status_filter", status);
      return request<Order[]>(`/orders/admin/all?${q.toString()}`);
    },
    adminGetStats: () => request<{ total_sales: number; total_orders: number; average_order_value: number }>("/orders/admin/stats"),
    adminUpdateStatus: (id: string, status: string) => 
      request<Order>(`/orders/admin/${id}/status?new_status=${status}`, { method: "PATCH" }),
  },

  // AI Features
  ai: {
    search: (query: string) => request<any>(`/ai/search?q=${encodeURIComponent(query)}`),
    chat: (messages: { role: string; content: string }[]) => 
      request<{ reply: string; recommended_product_ids?: string[] }>("/ai/chat", { method: "POST", body: JSON.stringify({ messages }) }),
    
    colorMatch: async (imageFile: File) => {
      const formData = new FormData();
      formData.append("file", imageFile);
      return request<any>("/ai/color-match", { method: "POST", body: formData }, true);
    },
    
    describeProduct: async (imageFile: File) => {
      const formData = new FormData();
      formData.append("file", imageFile);
      return request<any>("/ai/describe-product", { method: "POST", body: formData }, true);
    },
    
    instagramCaption: (productId: string, style = "trendy") => {
      const formData = new FormData();
      formData.append("product_id", productId);
      formData.append("style", style);
      return request<any>("/ai/instagram-caption", { method: "POST", body: formData }, true);
    },
    
    summarizeReviews: (productId: string) => 
      request<any>(`/ai/summarize-reviews?product_id=${productId}`, { method: "POST" }),
      
    getChatHistory: () => request<any[]>("/ai/chat/history"),
    clearChatHistory: () => request<void>("/ai/chat/history", { method: "DELETE" }),
      
    faq: (question: string) => {
      const formData = new FormData();
      formData.append("question", question);
      return request<any>("/ai/faq", { method: "POST", body: formData }, true);
    }
  },

  // Admin Portal Services
  admin: {
    getCustomers: (q?: string) => {
      const params = q ? `?q=${encodeURIComponent(q)}` : "";
      return request<any[]>(`/admin/customers${params}`);
    },
    getAnalytics: () => request<any>("/admin/analytics"),
    getInventory: () => request<any>("/admin/inventory"),
    getReviews: () => request<any[]>("/admin/reviews"),
    moderateReview: (reviewId: string, payload: { is_approved?: boolean; is_flagged?: boolean }) =>
      request<any>(`/admin/reviews/${reviewId}/moderate`, { method: "PATCH", body: JSON.stringify(payload) }),
    getSettings: () => request<Record<string, any>>("/admin/settings"),
    updateSetting: (key: string, value: any, description?: string) =>
      request<any>("/admin/settings", { method: "PUT", body: JSON.stringify({ key, value, description }) }),
    getAuditLogs: (limit = 50, offset = 0) =>
      request<any[]>(`/admin/audit-logs?limit=${limit}&offset=${offset}`),
  }
};
