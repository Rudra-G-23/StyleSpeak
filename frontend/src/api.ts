import type { Cart, ChatReply, Product, SearchFilters } from "./types";

const API_BASE = (import.meta.env.VITE_API_URL ?? "http://localhost:8000").replace(/\/$/, "");
const SESSION_KEY = "stylespeak.session";

export const sessionId = (): string => {
  const existing = localStorage.getItem(SESSION_KEY);
  if (existing) return existing;
  const created = crypto.randomUUID();
  localStorage.setItem(SESSION_KEY, created);
  return created;
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", "X-StyleSpeak-Session": sessionId(), ...init?.headers },
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    throw new Error(payload?.detail ?? `Request failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}

export const imageUrl = (product: Product) => {
  const value = product.image_url ?? product.image_path;
  if (!value) return "";
  return value.startsWith("http") ? value : `${API_BASE}${value.startsWith("/") ? "" : "/"}${value}`;
};

export const searchProducts = (filters: SearchFilters) =>
  request<{ products: Product[]; interpreted_filters: SearchFilters }>("/api/search", {
    method: "POST",
    body: JSON.stringify({
      query: filters.query ?? "",
      filters: {
        gender: filters.gender,
        category: filters.category,
        subcategory: filters.subcategory,
        color: filters.color,
        max_price: filters.max_price,
        min_price: filters.min_price,
        size: filters.size,
      },
      limit: filters.limit ?? 12,
    }),
  });
export const getProduct = (sku: string) => request<Product>(`/api/products/${encodeURIComponent(sku)}`);
export const getVariants = (sku: string) => request<Product[]>(`/api/products/${encodeURIComponent(sku)}/variants`);
export const getCart = () => request<Cart>("/api/cart");
export const addCartItem = (sku: string, size: string | null) =>
  request<Cart>("/api/cart/items", { method: "POST", body: JSON.stringify({ sku, size, quantity: 1 }) });
export const updateCartItem = (sku: string, quantity: number) =>
  request<Cart>(`/api/cart/items/${encodeURIComponent(sku)}`, { method: "PATCH", body: JSON.stringify({ quantity }) });
export const removeCartItem = (sku: string) => request<Cart>(`/api/cart/items/${encodeURIComponent(sku)}`, { method: "DELETE" });
export const chat = (message: string) =>
  request<ChatReply>("/api/chat", { method: "POST", body: JSON.stringify({ message }) });
export async function transcribe(audio: Blob): Promise<{ transcript: string }> {
  const form = new FormData();
  form.append("audio", audio, "voice.webm");
  const response = await fetch(`${API_BASE}/api/voice/transcribe`, { method: "POST", headers: { "X-StyleSpeak-Session": sessionId() }, body: form });
  if (!response.ok) throw new Error("Voice transcription was unavailable. Try typing your request instead.");
  return response.json() as Promise<{ transcript: string }>;
}
