/* =========================================================================
   StyleSpeak storefront - vanilla JS, no build step, no framework.
   Reads the demo catalog (window.__CATALOG__ when inlined, otherwise
   ./products.json). The "stylist" turns a sentence into colour / cut /
   budget filters and shows its reading back to you, marked in yellow.
   ========================================================================= */
(() => {
  "use strict";

  const CATALOG_URL = "./products.json";
  const BAG_KEY = "stylespeak.bag";

  // Canonical colour -> a muted fabric tone that holds on paper and on ink.
  const SWATCH = {
    black: "#2b2b2f", white: "#e7e3d7", grey: "#8b8b84", blue: "#40608c", navy: "#2b3a52",
    red: "#9c3a30", green: "#5b6350", yellow: "#c9a94e", orange: "#b96b3c", pink: "#c68f99",
    purple: "#6c5b84", brown: "#7b5a44", beige: "#c6b39a", burgundy: "#6d3540", teal: "#3f6d69",
    gold: "#b08d3f",
  };

  const COLOR_WORDS = {
    black: ["black", "jet"],
    white: ["white", "off-white", "ivory", "ecru", "cream", "chalk"],
    grey: ["grey", "gray", "charcoal", "anthracite", "graphite", "silver"],
    blue: ["blue", "denim", "indigo", "cobalt", "petrol"],
    navy: ["navy", "marine"],
    red: ["red", "scarlet", "cherry"],
    green: ["green", "khaki", "olive", "sage", "forest", "emerald", "thyme"],
    yellow: ["yellow", "mustard", "ochre", "lemon"],
    orange: ["orange", "coral", "rust", "terracotta", "amber"],
    pink: ["pink", "rose", "fuchsia", "blush", "magenta"],
    purple: ["purple", "lilac", "lavender", "mauve", "violet", "plum"],
    brown: ["brown", "chocolate", "mocha", "tan", "cognac", "camel"],
    beige: ["beige", "sand", "stone", "taupe", "nude", "oat"],
    burgundy: ["burgundy", "bordeaux", "wine", "maroon", "berry", "port"],
    teal: ["teal", "turquoise"],
    gold: ["gold"],
  };

  const CATEGORY_WORDS = {
    Jackets: ["jacket", "jackets", "bomber", "windbreaker", "anorak"],
    Coats: ["coat", "coats", "parka", "trench", "trenchcoat", "overcoat"],
    Jeans: ["jeans", "denim"],
    Trousers: ["trousers", "trouser", "pants", "chino", "chinos", "joggers", "leggings", "cargo"],
    Shirts: ["shirt", "shirts", "overshirt", "blouse"],
    "T-Shirts & Polos": ["t-shirt", "tshirt", "tee", "tees", "polo", "polos"],
    Dresses: ["dress", "dresses", "gown", "frock"],
    Sportswear: ["sportswear", "gym", "running", "training", "workout", "athletic", "sport"],
    Streetwear: ["streetwear", "hoodie", "hoodies", "hoody", "sweatshirt", "sweater", "jumper", "crewneck", "fleece"],
  };

  // Occasion / vibe words steer toward a set of categories without a literal match.
  const VIBE = {
    tailoring: ["Shirts", "Trousers", "Coats"],
    tailored: ["Shirts", "Trousers", "Coats"],
    formal: ["Shirts", "Trousers", "Coats"],
    smart: ["Shirts", "Trousers", "Coats"],
    office: ["Shirts", "Trousers"],
    work: ["Shirts", "Trousers"],
    wedding: ["Dresses", "Shirts", "Coats"],
    party: ["Dresses", "T-Shirts & Polos"],
    summer: ["Dresses", "Shirts", "T-Shirts & Polos"],
    winter: ["Coats", "Jackets", "Streetwear"],
    outdoor: ["Jackets", "Coats"],
    lounge: ["Streetwear", "Sportswear"],
  };

  const STOP = new Set(
    ("a an the for with in of to and or on at is are as some any something anything stuff things " +
      "piece pieces item items outfit look clothes clothing wardrobe me my mine i we you your need " +
      "want wanting looking find show get please that this it its keep keeps wear wearing buy add " +
      "like love loves prefer maybe perhaps thanks got have has around about under below over above " +
      "less than more most max maximum min minimum up budget euro euros eur cost costs price priced " +
      "cheap affordable nice good great lovely new fresh really very just kind sort bit").split(" "),
  );

  const $ = (sel, root = document) => root.querySelector(sel);
  const esc = (s) => String(s).replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const norm = (w) => w.toLowerCase().replace(/[^a-z0-9€]/g, "");
  const euro = new Intl.NumberFormat("de-DE", { style: "currency", currency: "EUR" });

  const state = {
    all: [],
    query: "",
    parsed: emptyParse(),
    category: null, // single manual/parsed category
    catList: null, // vibe-derived category set
    sort: "featured",
    relaxNote: null,
    bag: loadBag(),
  };

  function emptyParse() {
    return { colors: [], category: null, catList: null, gender: null, min: null, max: null,
      keywords: [], hits: { color: {}, cat: new Set(), price: new Set(), gender: new Set(), kw: new Set() } };
  }

  /* --------------------------------------------------------------------- */
  /* Stylist: sentence -> constraints, plus a per-word role map for marks  */
  /* --------------------------------------------------------------------- */
  function parseQuery(text) {
    const p = emptyParse();
    const low = " " + text.toLowerCase() + " ";
    if (!text.trim()) return p;

    const wb = (syn) => new RegExp("(?<![a-z])" + esc(syn).replace(/-/g, "[- ]?") + "(?![a-z])", "i");

    // colours (all that appear)
    for (const [canon, syns] of Object.entries(COLOR_WORDS)) {
      for (const syn of syns) {
        if (wb(syn).test(low)) {
          if (!p.colors.includes(canon)) p.colors.push(canon);
          p.hits.color[norm(syn)] = canon;
        }
      }
    }

    // first explicit garment category wins
    for (const [canon, syns] of Object.entries(CATEGORY_WORDS)) {
      if (p.category) break;
      for (const syn of syns) {
        if (wb(syn).test(low)) {
          p.category = canon;
          p.hits.cat.add(norm(syn));
          break;
        }
      }
    }

    // vibe / occasion -> category set (only if no explicit category)
    for (const [word, cats] of Object.entries(VIBE)) {
      if (wb(word).test(low)) {
        p.hits.cat.add(norm(word));
        if (!p.category && !p.catList) p.catList = cats.slice();
      }
    }

    // budget
    const priceHit = (m) => m[0].split(/\s+/).forEach((w) => w && p.hits.price.add(norm(w)));
    let m;
    if ((m = low.match(/between\s*€?\s*(\d+(?:[.,]\d+)?)\s*(?:and|to|-|–)\s*€?\s*(\d+(?:[.,]\d+)?)/))) {
      p.min = num(m[1]); p.max = num(m[2]); priceHit(m);
    }
    if ((m = low.match(/(?:under|below|less than|max(?:imum)?|up to|within|no more than|<)\s*€?\s*(\d+(?:[.,]\d+)?)/))) {
      p.max = num(m[1]); priceHit(m);
    }
    if ((m = low.match(/(?:over|above|from|more than|at least|>)\s*€?\s*(\d+(?:[.,]\d+)?)/))) {
      p.min = num(m[1]); priceHit(m);
    }
    if (p.max === null && p.min === null && (m = low.match(/€\s*(\d+(?:[.,]\d+)?)|(\d+(?:[.,]\d+)?)\s*(?:€|eur|euros?)/))) {
      p.max = num(m[1] || m[2]); priceHit(m);
    }

    // gender (test women/ladies before men so the "men" substring never wins)
    if (/(?<![a-z])(women|woman|womens|women's|ladies|female)(?![a-z])/i.test(low)) {
      p.gender = "women"; ["women", "woman", "womens", "ladies", "female"].forEach((w) => p.hits.gender.add(w));
    } else if (/(?<![a-z])(men|man|mens|men's|male|guys)(?![a-z])/i.test(low)) {
      p.gender = "men"; ["men", "man", "mens", "male", "guys"].forEach((w) => p.hits.gender.add(w));
    }

    // leftover meaningful words -> literal keyword filters (AND)
    const consumed = new Set([
      ...Object.keys(p.hits.color), ...p.hits.cat, ...p.hits.price, ...p.hits.gender,
    ]);
    for (const raw of text.toLowerCase().split(/[\s,.;/]+/)) {
      const w = norm(raw);
      if (w.length < 3 || STOP.has(w) || consumed.has(w) || /^\d+$/.test(w)) continue;
      if (!p.keywords.includes(w)) { p.keywords.push(w); p.hits.kw.add(w); }
    }
    return p;
  }

  function num(s) {
    return Math.round(parseFloat(String(s).replace(",", ".")) * 100) / 100;
  }

  /* --------------------------------------------------------------------- */
  /* Filtering + graceful relaxation                                       */
  /* --------------------------------------------------------------------- */
  function runFilter(opts) {
    const { category, catList, colors, gender, min, max, keywords } = opts;
    return state.all.filter((prod) => {
      if (category && prod.category !== category) return false;
      if (!category && catList && catList.length && !catList.includes(prod.category)) return false;
      if (colors.length && !colors.includes(prod.color)) return false;
      if (gender && gender !== "unisex" && prod.gender !== gender && prod.gender !== "unisex") return false;
      const price = prod.promotional_price;
      if (min !== null && price < min) return false;
      if (max !== null && price > max) return false;
      if (keywords.length) {
        const hay = (prod.name + " " + prod.type + " " + prod.category + " " + prod.brand).toLowerCase();
        if (!keywords.every((k) => hay.includes(k))) return false;
      }
      return true;
    });
  }

  function searchResults() {
    const p = state.parsed;
    const base = {
      category: state.category,
      catList: state.category ? null : state.catList,
      colors: p.colors,
      gender: p.gender,
      min: p.min,
      max: p.max,
      keywords: p.keywords,
    };
    state.relaxNote = null;
    let out = runFilter(base);
    if (out.length) return out;

    const steps = [];
    if (base.keywords.length) steps.push([{ ...base, keywords: [] }, `nothing matched "${base.keywords.join(" ")}" exactly`]);
    if (base.catList) steps.push([{ ...base, keywords: [], catList: null }, "widened the category"]);
    if (base.colors.length) steps.push([{ ...base, keywords: [], catList: null, colors: [] }, "dropped the colour"]);
    steps.push([{ ...base, keywords: [], catList: null, colors: [], min: null, max: null }, "ignored every constraint"]);

    for (const [relaxed, why] of steps) {
      out = runFilter(relaxed);
      if (out.length) {
        state.relaxNote = `Stylist ${why} - showing the closest rack.`;
        return out;
      }
    }
    return [];
  }

  function sortList(list) {
    const arr = list.slice();
    if (state.sort === "price-asc") arr.sort((a, b) => a.promotional_price - b.promotional_price);
    else if (state.sort === "price-desc") arr.sort((a, b) => b.promotional_price - a.promotional_price);
    else if (state.sort === "discount") {
      arr.sort((a, b) => b.discount_percentage - a.discount_percentage || a.promotional_price - b.promotional_price);
    } else if (state.sort === "name") arr.sort((a, b) => a.name.localeCompare(b.name));
    return arr;
  }

  /* --------------------------------------------------------------------- */
  /* Bag                                                                   */
  /* --------------------------------------------------------------------- */
  function loadBag() {
    try {
      return JSON.parse(localStorage.getItem(BAG_KEY) || "{}") || {};
    } catch {
      return {};
    }
  }
  function saveBag() {
    try {
      localStorage.setItem(BAG_KEY, JSON.stringify(state.bag));
    } catch {
      /* private mode - bag simply won't persist */
    }
  }
  const bagCount = () => Object.values(state.bag).reduce((n, q) => n + q, 0);
  function bagSubtotal() {
    return Object.entries(state.bag).reduce((sum, [sku, qty]) => {
      const prod = state.all.find((p) => p.sku === sku);
      return prod ? sum + prod.promotional_price * qty : sum;
    }, 0);
  }
  function setQty(sku, qty) {
    if (qty <= 0) delete state.bag[sku];
    else state.bag[sku] = Math.min(qty, 99);
    saveBag();
    render();
  }

  /* --------------------------------------------------------------------- */
  /* Rendering                                                             */
  /* --------------------------------------------------------------------- */
  function srgb(c) {
    c /= 255;
    return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
  }
  function inkFor(hex) {
    const n = parseInt(hex.slice(1), 16);
    const L = 0.2126 * srgb((n >> 16) & 255) + 0.7152 * srgb((n >> 8) & 255) + 0.0722 * srgb(n & 255);
    return L > 0.42 ? "#18140f" : "#f3efe6";
  }
  const swatchHex = (color) => SWATCH[color] || "#8b8b84";

  function priceHTML(prod) {
    if (prod.discount_percentage > 0) {
      return (
        `${euro.format(prod.promotional_price)}` +
        `<span class="was">${euro.format(prod.original_price)}</span>` +
        `<span class="off">−${prod.discount_percentage}%</span>`
      );
    }
    return euro.format(prod.promotional_price);
  }

  function cardHTML(prod) {
    const hex = swatchHex(prod.color);
    const ink = inkFor(hex);
    const cut = prod.discount_percentage > 0 ? `<span class="cut">−${prod.discount_percentage}%</span>` : "";
    const inBag = state.bag[prod.sku] || 0;
    return `
      <article class="card">
        <div class="swatch" data-cat="${prod.category}" style="--sw:${hex};--sw-ink:${ink}">
          ${cut}
          <span class="type">${escapeHTML(prod.type)}</span>
          <span class="cname">${escapeHTML(prod.color)}</span>
        </div>
        <div class="brand">${escapeHTML(prod.brand)}</div>
        <p class="name">${escapeHTML(prod.name)}</p>
        <div class="price">${priceHTML(prod)}</div>
        <button class="add ${inBag ? "in" : ""}" data-add="${prod.sku}">
          ${inBag ? `In bag · ${inBag}` : "Add"}
        </button>
      </article>`;
  }

  function escapeHTML(s) {
    return String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  }

  function lexHTML() {
    const p = state.parsed;
    if (!state.query.trim()) return "";
    return state.query
      .split(/(\s+)/)
      .map((tok) => {
        if (/^\s+$/.test(tok)) return tok;
        const w = norm(tok);
        if (p.hits.color[w]) {
          const dot = swatchHex(p.hits.color[w]);
          return `<mark class="col"><span class="dot" style="background:${dot}"></span>${escapeHTML(tok)}</mark>`;
        }
        if (p.hits.cat.has(w)) return `<mark>${escapeHTML(tok)}</mark>`;
        if (p.hits.price.has(w)) return `<mark>${escapeHTML(tok)}</mark>`;
        if (p.hits.gender.has(w)) return `<mark>${escapeHTML(tok)}</mark>`;
        if (p.hits.kw.has(w)) return `<mark class="kw">${escapeHTML(tok)}</mark>`;
        return escapeHTML(tok);
      })
      .join("");
  }

  function bitsHTML() {
    const p = state.parsed;
    const bits = [];
    if (state.category) bits.push(bit("cut", state.category, "cut"));
    else if (state.catList) bits.push(bit("cut", state.catList.join(" / "), "cut"));
    if (p.colors.length) bits.push(bit("colour", p.colors.join(" + "), "colour"));
    if (p.gender) bits.push(bit("for", p.gender, "gender"));
    if (p.min !== null) bits.push(bit("from", euro.format(p.min), "min"));
    if (p.max !== null) bits.push(bit("max", euro.format(p.max), "max"));
    if (!bits.length) return "";
    bits.push(`<button class="bit reset" data-clear="all">clear all ×</button>`);
    return bits.join("");

    function bit(label, value, key) {
      return `<span class="bit">${label} <span>${escapeHTML(value)}</span><button data-clear="${key}" aria-label="remove ${label}">×</button></span>`;
    }
  }

  function render() {
    const results = sortList(searchResults());

    // parse strip
    const read = $("#read");
    const bits = bitsHTML();
    if (!state.query.trim() && !bits) {
      read.hidden = true;
    } else {
      read.hidden = false;
      $("#lex").innerHTML = lexHTML() || "no words the stylist could use";
      $("#bits").innerHTML = bits;
      const note = $("#note");
      note.hidden = !state.relaxNote;
      note.textContent = state.relaxNote || "";
    }

    // controls
    const total = state.all.length;
    $("#count").textContent =
      results.length === total ? `${total} pieces` : `${results.length} of ${total} pieces`;
    renderCats();
    $("#sort").value = state.sort;

    // grid
    $("#grid").innerHTML = results.length
      ? results.map(cardHTML).join("")
      : `<div class="empty"><p>No pieces on this rack.</p><p>Try <code>a winter coat</code> or lift the budget.</p></div>`;

    renderBag();
  }

  function renderCats() {
    const cats = ["All", ...Object.keys(CATEGORY_WORDS)];
    $("#cats").innerHTML = cats
      .map((c) => {
        const on = c === "All" ? !state.category : state.category === c;
        return `<button data-cat-pick="${c}" aria-pressed="${on}">${c === "All" ? "All" : c}</button>`;
      })
      .join("");
  }

  function renderBag() {
    const count = bagCount();
    $("#bagcount").textContent = count ? ` · ${count}` : "";
    const entries = Object.entries(state.bag);
    const lines = $("#lines");
    if (!entries.length) {
      lines.innerHTML = `<div class="dempty">Your bag is empty. Describe something up top and add it here.</div>`;
    } else {
      lines.innerHTML = entries
        .map(([sku, qty]) => {
          const prod = state.all.find((p) => p.sku === sku);
          if (!prod) return "";
          const hex = swatchHex(prod.color);
          return `
            <div class="li">
              <div class="mini" style="--sw:${hex}"></div>
              <div>
                <p class="lname">${escapeHTML(prod.name)}</p>
                <span class="lbrand">${escapeHTML(prod.brand)}</span>
                <div class="qty">
                  <button data-step="-1" data-sku="${sku}" aria-label="one fewer">−</button>
                  <span>${qty}</span>
                  <button data-step="1" data-sku="${sku}" aria-label="one more">+</button>
                </div>
              </div>
              <div class="right">
                <span class="ltot">${euro.format(prod.promotional_price * qty)}</span>
                <button class="rm" data-rm="${sku}">remove</button>
              </div>
            </div>`;
        })
        .join("");
    }
    $("#subtotal").textContent = euro.format(bagSubtotal());
  }

  /* --------------------------------------------------------------------- */
  /* Events                                                                */
  /* --------------------------------------------------------------------- */
  function runSearch(text) {
    state.query = text;
    state.parsed = parseQuery(text);
    state.category = state.parsed.category || null;
    state.catList = state.parsed.category ? null : state.parsed.catList;
    render();
  }

  let toastTimer;
  function toast(msg) {
    const el = $("#toast");
    el.textContent = msg;
    el.classList.add("show");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => el.classList.remove("show"), 2200);
  }

  function openBag(open) {
    $("#drawer").classList.toggle("open", open);
    $("#scrim").classList.toggle("open", open);
    $("#drawer").setAttribute("aria-hidden", String(!open));
  }

  function wire() {
    $("#ask").addEventListener("submit", (e) => {
      e.preventDefault();
      runSearch($("#q").value);
    });

    $("#egs").addEventListener("click", (e) => {
      const b = e.target.closest("button[data-eg]");
      if (!b) return;
      $("#q").value = b.dataset.eg;
      runSearch(b.dataset.eg);
    });

    $("#read").addEventListener("click", (e) => {
      const b = e.target.closest("[data-clear]");
      if (!b) return;
      const k = b.dataset.clear;
      const p = state.parsed;
      if (k === "all") {
        $("#q").value = "";
        runSearch("");
        return;
      }
      if (k === "cut") { state.category = null; state.catList = null; p.category = null; p.catList = null; }
      if (k === "colour") p.colors = [];
      if (k === "gender") p.gender = null;
      if (k === "min") p.min = null;
      if (k === "max") p.max = null;
      render();
    });

    $("#cats").addEventListener("click", (e) => {
      const b = e.target.closest("button[data-cat-pick]");
      if (!b) return;
      const pick = b.dataset.catPick;
      state.category = pick === "All" ? null : pick;
      state.catList = null;
      render();
    });

    $("#sort").addEventListener("change", (e) => {
      state.sort = e.target.value;
      render();
    });

    $("#grid").addEventListener("click", (e) => {
      const b = e.target.closest("button[data-add]");
      if (!b) return;
      const sku = b.dataset.add;
      state.bag[sku] = (state.bag[sku] || 0) + 1;
      saveBag();
      render();
      const prod = state.all.find((p) => p.sku === sku);
      toast(`Added · ${prod ? prod.name.split(" - ")[0] : sku}`);
    });

    $("#lines").addEventListener("click", (e) => {
      const step = e.target.closest("button[data-step]");
      const rm = e.target.closest("button[data-rm]");
      if (step) setQty(step.dataset.sku, (state.bag[step.dataset.sku] || 0) + Number(step.dataset.step));
      if (rm) setQty(rm.dataset.rm, 0);
    });

    $("#openbag").addEventListener("click", () => openBag(true));
    $("#closebag").addEventListener("click", () => openBag(false));
    $("#scrim").addEventListener("click", () => openBag(false));
    $("#clearbag").addEventListener("click", () => {
      state.bag = {};
      saveBag();
      render();
    });
    $("#pay").addEventListener("click", () => toast("Demo storefront - checkout isn't wired up."));

    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") openBag(false);
    });
  }

  /* --------------------------------------------------------------------- */
  /* Boot                                                                  */
  /* --------------------------------------------------------------------- */
  async function boot() {
    let catalog = window.__CATALOG__;
    if (!catalog) {
      try {
        catalog = await (await fetch(CATALOG_URL, { cache: "no-cache" })).json();
      } catch {
        $("#grid").innerHTML =
          `<div class="empty"><p>Couldn't load the catalog.</p><p>Serve this folder over HTTP: <code>python3 -m http.server</code></p></div>`;
        return;
      }
    }
    state.all = catalog.slice();
    const pc = document.getElementById("pcount");
    if (pc) pc.textContent = String(state.all.length);
    wire();
    $("#q").value = "keep it under €120";
    runSearch($("#q").value);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
