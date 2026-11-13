import { FormEvent, forwardRef, useEffect, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import { ArrowRight, ChevronDown, CircleAlert, Mic, Minus, Plus, Search, ShoppingBag, SlidersHorizontal, Sparkles, Trash2, X } from "lucide-react";
import { addCartItem, chat, getCart, getProduct, getVariants, imageUrl, removeCartItem, searchProducts, transcribe, updateCartItem } from "./api";
import type { Product, SearchFilters } from "./types";

const initialFilters: SearchFilters = { gender: "men", category: "pants", limit: 12 };
const money = (price: number, currency = "EUR") => new Intl.NumberFormat("en-IE", { style: "currency", currency }).format(price);
const palette = ["black", "navy", "grey", "brown", "beige", "green"];

const ProductImage = forwardRef<HTMLImageElement, { product: Product; className?: string }>(function ProductImage({ product, className = "" }, ref) {
  const [failed, setFailed] = useState(false);
  return failed || !imageUrl(product) ? <div className={`image-fallback ${className}`}>StyleSpeak</div> : <img ref={ref} className={className} src={imageUrl(product)} alt={product.name} onError={() => setFailed(true)} />;
});

function App() {
  const queryClient = useQueryClient();
  const reduced = useReducedMotion();
  const [filters, setFilters] = useState<SearchFilters>(initialFilters);
  const [draft, setDraft] = useState("Show black men's cargo pants under €100");
  const [shown, setShown] = useState<Product[]>([]);
  const [detail, setDetail] = useState<Product | null>(null);
  const [cartOpen, setCartOpen] = useState(false);
  const [filterOpen, setFilterOpen] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [flying, setFlying] = useState<{ url: string; start: DOMRect } | null>(null);
  const cartButton = useRef<HTMLButtonElement>(null);
  const fileInput = useRef<HTMLInputElement>(null);

  const results = useQuery({ queryKey: ["search", filters], queryFn: () => searchProducts(filters), staleTime: 30_000 });
  const cart = useQuery({ queryKey: ["cart"], queryFn: getCart });
  useEffect(() => { if (results.data) setShown(results.data.products); }, [results.data]);
  useEffect(() => { if (!flying || reduced) return; const timer = window.setTimeout(() => setFlying(null), 720); return () => window.clearTimeout(timer); }, [flying, reduced]);

  const invalidateCart = () => queryClient.invalidateQueries({ queryKey: ["cart"] });
  const add = useMutation({
    mutationFn: ({ product, size }: { product: Product; size: string | null }) => addCartItem(product.sku, size),
    onSuccess: (_, input) => { invalidateCart(); setNotice(`${input.product.name} added to your bag.`); setCartOpen(true); },
    onError: (error) => setNotice(error.message),
  });
  const speak = useMutation({
    mutationFn: (message: string) => chat(message),
    onSuccess: async (reply) => {
      setNotice(reply.message);
      if (reply.products.length) setShown(reply.products);
      if (reply.selected_sku) setDetail(await getProduct(reply.selected_sku));
      invalidateCart();
    },
    onError: (error) => setNotice(error.message),
  });

  const submitSearch = (event: FormEvent) => { event.preventDefault(); if (!draft.trim()) return; setFilters({ query: draft, limit: 12 }); };
  const addFromCard = (product: Product, image: HTMLImageElement | null) => {
    if (image && cartButton.current && !reduced) setFlying({ url: image.currentSrc, start: image.getBoundingClientRect() });
    add.mutate({ product, size: product.sizes[0] ?? null });
  };
  const requestVoice = async () => {
    try { fileInput.current?.click(); } catch { setNotice("Choose an audio file to transcribe."); }
  };
  const chooseAudio = async (file?: File) => {
    if (!file) return;
    try { const { transcript } = await transcribe(file); setDraft(transcript); setNotice("Transcript ready. Edit it, then search."); } catch (error) { setNotice(error instanceof Error ? error.message : "Voice transcription failed."); }
  };
  const visible = shown.length ? shown : results.data?.products ?? [];

  return <main>
    <header className="site-header">
      <a className="wordmark" href="#top" aria-label="StyleSpeak home"><span>Style</span>Speak<sup>AI</sup></a>
      <nav aria-label="Primary navigation"><a href="#shop">Shop</a><a href="#assistant">AI stylist</a><a href="#story">About</a></nav>
      <button ref={cartButton} className="bag-button" onClick={() => setCartOpen(true)} aria-label={`Open bag, ${cart.data?.item_count ?? 0} products`}><ShoppingBag /><span>Bag</span><b>{cart.data?.item_count ?? 0}</b></button>
    </header>

    <section id="top" className="hero">
      <div className="eyebrow"><Sparkles /> Local-first AI fashion assistant</div>
      <h1>Dress like<br /><em>yourself.</em></h1>
      <p>Tell StyleSpeak what you are after. It reads your brief, searches a real local catalog, and keeps every recommendation grounded in an actual product.</p>
      <form className="search-bar" onSubmit={submitSearch}>
        <Search aria-hidden="true" /><input value={draft} onChange={(e) => setDraft(e.target.value)} aria-label="Ask StyleSpeak" placeholder="Try ‘black cargo pants under €100’" />
        <button type="button" className="icon-button" onClick={requestVoice} aria-label="Choose voice recording"><Mic /></button>
        <button type="submit" className="search-submit" aria-label="Search"><ArrowRight /></button>
      </form>
      <input ref={fileInput} type="file" accept="audio/*" hidden onChange={(e) => chooseAudio(e.target.files?.[0])} />
      <div className="prompt-row"><span>Try an edit:</span>{["Black cargo pants", "Relaxed fit", "Under €100"].map((x) => <button key={x} onClick={() => { setDraft(x); setFilters({ query: x, limit: 12 }); }}>{x}</button>)}</div>
      <div className="hero-aside"><p>Built for thoughtful shopping</p><span>01 / 03</span></div>
    </section>

    <section id="assistant" className="assistant-panel">
      <div><span className="section-kicker">Your AI stylist</span><h2>Say it naturally.</h2><p>Follow up with “show cheaper ones”, “only slim-fit”, or “add the second one”. Product references resolve against the results you can see.</p></div>
      <form onSubmit={(e) => { e.preventDefault(); if (draft.trim()) speak.mutate(draft); }}><input value={draft} onChange={(e) => setDraft(e.target.value)} aria-label="Message the AI stylist" /><button disabled={speak.isPending}>{speak.isPending ? "Thinking" : "Ask stylist"}<ArrowRight /></button></form>
    </section>

    <section id="shop" className="catalog-section">
      <div className="catalog-title"><div><span className="section-kicker">Curated by your brief</span><h2>Find your next pair.</h2><p>{results.isFetching ? "Searching the catalogue..." : `${visible.length} verified matches`}</p></div><button className="filter-toggle" onClick={() => setFilterOpen(!filterOpen)}><SlidersHorizontal /> Filter <ChevronDown /></button></div>
      <AnimatePresence>{filterOpen && <motion.div className="filters" initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }}>
        <label>Colour<select value={filters.color ?? ""} onChange={(e) => setFilters((f) => ({ ...f, color: e.target.value || null }))}><option value="">Any colour</option>{palette.map((color) => <option key={color}>{color}</option>)}</select></label>
        <label>Maximum price<input type="number" min="0" placeholder="No limit" value={filters.max_price ?? ""} onChange={(e) => setFilters((f) => ({ ...f, max_price: e.target.value ? Number(e.target.value) : null }))} /></label>
        <label>Fit<select value={filters.subcategory ?? ""} onChange={(e) => setFilters((f) => ({ ...f, subcategory: e.target.value || null }))}><option value="">Any fit</option><option value="cargo">Cargo</option><option value="jeans">Jeans</option><option value="chinos">Chinos</option><option value="joggers">Joggers</option></select></label>
        <button onClick={() => setFilters(initialFilters)}>Reset filters</button>
      </motion.div>}</AnimatePresence>
      {results.error && <div className="error-state"><CircleAlert /> {results.error.message}</div>}
      <div className="product-grid">{results.isLoading ? Array.from({ length: 8 }).map((_, i) => <div className="skeleton" key={i} />) : visible.map((product, index) => <ProductCard product={product} key={product.sku} index={index} onOpen={setDetail} onAdd={addFromCard} />)}</div>
      {!results.isLoading && !visible.length && <div className="empty-state"><h3>No exact matches</h3><p>We did not widen your request. Try a different colour, fit, or budget.</p></div>}
    </section>

    <section id="story" className="values"><p className="section-kicker">Less noise. Better choices.</p><h2>Only recommendations that can explain themselves.</h2><div><p><b>Real records</b> Every card comes from the local dataset, not a generated product.</p><p><b>Hard filters first</b> Price, colour, category and gender constraints stay intact while ranking.</p><p><b>Your pace</b> No payment or stock claims. This is a private local shopping demo.</p></div></section>

    <AnimatePresence>{detail && <ProductDetail product={detail} close={() => setDetail(null)} add={(p, size) => add.mutate({ product: p, size })} />}</AnimatePresence>
    <AnimatePresence>{cartOpen && <CartDrawer close={() => setCartOpen(false)} />}</AnimatePresence>
    <AnimatePresence>{notice && <motion.div className="notice" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: 20 }} onClick={() => setNotice(null)}>{notice}<button aria-label="Dismiss"><X /></button></motion.div>}</AnimatePresence>
    {flying && <motion.img className="flying-product" src={flying.url} alt="" initial={{ left: flying.start.left, top: flying.start.top, width: flying.start.width, height: flying.start.height, opacity: 1 }} animate={{ left: (cartButton.current?.getBoundingClientRect().left ?? window.innerWidth - 50), top: (cartButton.current?.getBoundingClientRect().top ?? 24), width: 28, height: 28, opacity: 0.25 }} transition={{ duration: 0.68, ease: [0.2, 0.8, 0.2, 1] }} />}
  </main>;
}

function ProductCard({ product, index, onOpen, onAdd }: { product: Product; index: number; onOpen: (p: Product) => void; onAdd: (p: Product, image: HTMLImageElement | null) => void }) {
  const ref = useRef<HTMLImageElement>(null);
  return <motion.article className="product-card" initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: Math.min(index * 0.04, 0.3) }}><button className="product-image" onClick={() => onOpen(product)} aria-label={`View ${product.name}`}><ProductImage ref={ref} product={product} className="product-photo" /><span>{product.color ?? "catalogue edit"}</span></button><div className="product-copy"><div><p>{product.brand}</p><h3>{product.name}</h3></div><strong>{money(product.price, product.currency)}</strong></div><div className="product-actions"><button onClick={() => onOpen(product)}>View details</button><button onClick={() => onAdd(product, ref.current)} aria-label={`Add ${product.name} to bag`}><Plus /></button></div></motion.article>;
}

function ProductDetail({ product, close, add }: { product: Product; close: () => void; add: (p: Product, size: string | null) => void }) {
  const [size, setSize] = useState(product.sizes[0] ?? null);
  const variants = useQuery({ queryKey: ["variants", product.sku], queryFn: () => getVariants(product.sku) });
  return <motion.div className="overlay" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onMouseDown={close}><motion.section className="detail-modal" initial={{ y: 28 }} animate={{ y: 0 }} exit={{ y: 28 }} onMouseDown={(e) => e.stopPropagation()} role="dialog" aria-modal="true" aria-labelledby="detail-title"><button className="close" onClick={close} aria-label="Close product details"><X /></button><div className="detail-image"><ProductImage product={product} /></div><div className="detail-copy"><p className="section-kicker">{product.brand}</p><h2 id="detail-title">{product.name}</h2><strong>{money(product.price, product.currency)}</strong><p>{product.description || "A local catalogue item. Fit, colour, price and available sizes come from the ingested product record."}</p>{variants.data && variants.data.length > 1 && <div className="variant-row"><span>Available colourways</span>{variants.data.map((variant) => <button key={variant.sku} title={variant.color ?? "Variant"} className="colour-dot" style={{ background: variant.color ?? "#998" }} />)}</div>}<div className="size-row"><span>Select size</span><div>{product.sizes.map((item) => <button key={item} className={size === item ? "selected" : ""} onClick={() => setSize(item)}>{item}</button>)}</div></div><button className="primary-action" onClick={() => add(product, size)}>Add to bag <ShoppingBag /></button></div></motion.section></motion.div>;
}

function CartDrawer({ close }: { close: () => void }) {
  const queryClient = useQueryClient();
  const cart = useQuery({ queryKey: ["cart"], queryFn: getCart });
  const change = useMutation({ mutationFn: ({ sku, quantity }: { sku: string; quantity: number }) => quantity ? updateCartItem(sku, quantity) : removeCartItem(sku), onSuccess: () => queryClient.invalidateQueries({ queryKey: ["cart"] }) });
  return <motion.div className="drawer-overlay" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onMouseDown={close}><motion.aside className="cart-drawer" initial={{ x: "100%" }} animate={{ x: 0 }} exit={{ x: "100%" }} onMouseDown={(e) => e.stopPropagation()} aria-label="Shopping bag"><header><h2>Your bag</h2><button onClick={close} aria-label="Close bag"><X /></button></header>{cart.isLoading ? <p>Loading your bag...</p> : !cart.data?.items.length ? <div className="empty-bag"><ShoppingBag /><h3>Your bag is waiting.</h3><p>Add a product and it will stay here for this browser session.</p></div> : <><div className="cart-lines">{cart.data.items.map((line) => <article key={`${line.sku}-${line.size ?? "default"}`}><ProductImage product={line.product} /><div><p>{line.product.brand}</p><h3>{line.product.name}</h3><span>{line.size ? `Size ${line.size}` : "One size"}</span><strong>{money(line.line_total, line.product.currency)}</strong><div className="quantity"><button onClick={() => change.mutate({ sku: line.sku, quantity: line.quantity - 1 })}><Minus /></button><span>{line.quantity}</span><button onClick={() => change.mutate({ sku: line.sku, quantity: line.quantity + 1 })}><Plus /></button><button className="remove" onClick={() => change.mutate({ sku: line.sku, quantity: 0 })}><Trash2 /></button></div></div></article>)}</div><footer><p><span>Subtotal</span><strong>{money(cart.data.subtotal)}</strong></p><button className="primary-action">Demo checkout <ArrowRight /></button><small>No payment or live stock data is collected.</small></footer></>}</motion.aside></motion.div>;
}

export default App;
