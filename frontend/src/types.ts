export type Product = {
  sku: string;
  name: string;
  brand: string;
  category: string;
  subcategory?: string | null;
  gender?: string | null;
  color?: string | null;
  price: number;
  original_price?: number | null;
  currency: string;
  sizes: string[];
  image_url?: string | null;
  image_path?: string | null;
  description?: string | null;
};

export type SearchFilters = {
  query?: string;
  gender?: string | null;
  category?: string | null;
  subcategory?: string | null;
  color?: string | null;
  max_price?: number | null;
  min_price?: number | null;
  size?: string | null;
  limit?: number;
};

export type CartLine = { sku: string; size: string | null; quantity: number; product: Product; line_total: number };
export type Cart = { items: CartLine[]; item_count: number; subtotal: number };
export type ChatReply = { message: string; products: Product[]; selected_sku?: string | null; action?: string; cart_count?: number };
