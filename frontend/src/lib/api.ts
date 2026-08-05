// API Client for Kee Crochet AI Platform backend

let rawBaseUrl = process.env.NEXT_PUBLIC_API_URL || "https://kee-crochet-api.onrender.com/api";
if (rawBaseUrl.endsWith("/")) {
  rawBaseUrl = rawBaseUrl.slice(0, -1);
}
if (!rawBaseUrl.endsWith("/api")) {
  rawBaseUrl = `${rawBaseUrl}/api`;
}
const BASE_URL = rawBaseUrl;

async function getHeaders(multipart = false) {
  const headers: Record<string, string> = {};
  if (!multipart) {
    headers["Content-Type"] = "application/json";
  }
  
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("access_token");
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }
  }
  return headers;
}

async function request(endpoint: string, options: RequestInit = {}, multipart = false) {
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
    
    // Automatically attempt token refresh on 401 if a refresh token is available and we aren't calling auth routes
    if (response.status === 401 && !endpoint.includes("/auth/")) {
      const refreshToken = typeof window !== "undefined" ? localStorage.getItem("refresh_token") : null;
      if (refreshToken) {
        try {
          const refreshResp = await fetch(`${BASE_URL}/auth/refresh`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ refresh_token: refreshToken }),
          });
          if (refreshResp.ok) {
            const tokens = await refreshResp.json();
            localStorage.setItem("access_token", tokens.access_token);
            localStorage.setItem("refresh_token", tokens.refresh_token);
            
            // Retry the original request
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
            // Refresh token expired or rejected: log out
            localStorage.removeItem("access_token");
            localStorage.removeItem("refresh_token");
            window.dispatchEvent(new Event("unauthorized"));
          }
        } catch (refreshErr) {
          console.error("Auto-refresh token failed:", refreshErr);
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
      return null;
    }

    return response.json();
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
    register: (payload: any) => request("/auth/register", { method: "POST", body: JSON.stringify(payload) }),
    login: (payload: any) => request("/auth/login", { method: "POST", body: JSON.stringify(payload) }),
    requestOtp: (payload: any) => request("/auth/otp/request", { method: "POST", body: JSON.stringify(payload) }),
    verifyOtp: (payload: any) => request("/auth/otp/verify", { method: "POST", body: JSON.stringify(payload) }),
    googleLogin: (idToken: string) => request("/auth/google", { method: "POST", body: JSON.stringify({ id_token: idToken }) }),
    refresh: (refreshToken: string) => request("/auth/refresh", { method: "POST", body: JSON.stringify({ refresh_token: refreshToken }) }),
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
      return request(`/products?${query.toString()}`);
    },
    get: (slug: string) => request(`/products/${slug}`),
    create: (payload: any) => request("/products", { method: "POST", body: JSON.stringify(payload) }),
    update: (id: string, payload: any) => request(`/products/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
    delete: (id: string) => request(`/products/${id}`, { method: "DELETE" }),
    
    // Categories
    listCategories: () => request("/categories"),
    createCategory: (payload: any) => request("/categories", { method: "POST", body: JSON.stringify(payload) }),
    createCustomRequest: (payload: { description: string; color_palette: string | null }) => 
      request("/products/custom-requests", { method: "POST", body: JSON.stringify(payload) }),
    uploadImage: (file: File) => {
      const fd = new FormData();
      fd.append("file", file);
      return request("/products/upload-image", { method: "POST", body: fd }, true);
    },
    getReviews: (productId: string) => request(`/products/${productId}/reviews`),
    addReview: (productId: string, payload: any) => request(`/products/${productId}/reviews`, { method: "POST", body: JSON.stringify(payload) }),
  },

  // Cart
  cart: {
    get: () => request("/cart"),
    addItem: (payload: { product_id: string; variant_id?: string | null; quantity: number; gift_wrap?: boolean; note?: string | null }) => 
      request("/cart/items", { method: "POST", body: JSON.stringify(payload) }),
    updateItem: (itemId: string, payload: { quantity?: number; gift_wrap?: boolean; note?: string | null }) => 
      request(`/cart/items/${itemId}`, { method: "PATCH", body: JSON.stringify(payload) }),
    removeItem: (itemId: string) => request(`/cart/items/${itemId}`, { method: "DELETE" }),
  },

  // Orders
  orders: {
    create: (payload: { shipping_address: any; coupon_code?: string | null }) => 
      request("/orders", { method: "POST", body: JSON.stringify(payload) }),
    verifyPayment: (payload: { order_id: string; razorpay_order_id: string; razorpay_payment_id: string; razorpay_signature: string }) => 
      request("/orders/verify-payment", { method: "POST", body: JSON.stringify(payload) }),
    list: () => request("/orders"),
    get: (id: string) => request(`/orders/${id}`),
    
    // Admin orders
    adminListAll: () => request("/orders/admin/all"),
    adminGetStats: () => request("/orders/admin/stats"),
    adminUpdateStatus: (id: string, status: string) => 
      request(`/orders/admin/${id}/status?new_status=${status}`, { method: "PATCH" }),
  },

  // AI Features
  ai: {
    search: (query: string) => request(`/ai/search?q=${encodeURIComponent(query)}`),
    chat: (messages: { role: string; content: string }[]) => 
      request("/ai/chat", { method: "POST", body: JSON.stringify({ messages }) }),
    
    colorMatch: async (imageFile: File) => {
      const formData = new FormData();
      formData.append("file", imageFile);
      return request("/ai/color-match", { method: "POST", body: formData }, true);
    },
    
    describeProduct: async (imageFile: File) => {
      const formData = new FormData();
      formData.append("file", imageFile);
      return request("/ai/describe-product", { method: "POST", body: formData }, true);
    },
    
    instagramCaption: (productId: string, style = "trendy") => {
      const formData = new FormData();
      formData.append("product_id", productId);
      formData.append("style", style);
      return request("/ai/instagram-caption", { method: "POST", body: formData }, true);
    },
    
    summarizeReviews: (productId: string) => 
      request(`/ai/summarize-reviews?product_id=${productId}`, { method: "POST" }),
      
    getChatHistory: () => request("/ai/chat/history"),
    clearChatHistory: () => request("/ai/chat/history", { method: "DELETE" }),
      
    faq: (question: string) => {
      const formData = new FormData();
      formData.append("question", question);
      return request("/ai/faq", { method: "POST", body: formData }, true);
    }
  }
};
