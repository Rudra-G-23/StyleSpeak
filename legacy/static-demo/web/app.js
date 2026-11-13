/* StyleSpeak storefront - local, explainable catalog assistant. */
(() => {
  "use strict";

  const CATALOG_URL = "./products.json";
  const BAG_KEY = "stylespeak.bag.v2";
  const THEME_KEY = "stylespeak.theme";
  const SWATCH = { black:"#2b2b2f",white:"#e7e3d7",grey:"#8b8b84",blue:"#40608c",navy:"#2b3a52",red:"#9c3a30",green:"#5b6350",yellow:"#c9a94e",orange:"#b96b3c",pink:"#c68f99",purple:"#6c5b84",brown:"#7b5a44",beige:"#c6b39a",burgundy:"#6d3540",teal:"#3f6d69",gold:"#b08d3f" };
  const COLORS = { black:["black","jet"],white:["white","off-white","ivory","ecru","cream"],grey:["grey","gray","charcoal","silver"],blue:["blue","denim","indigo"],navy:["navy","marine"],red:["red","scarlet"],green:["green","khaki","olive","sage"],yellow:["yellow","mustard"],orange:["orange","coral","rust"],pink:["pink","rose"],purple:["purple","lilac"],brown:["brown","chocolate","camel"],beige:["beige","sand","stone"],burgundy:["burgundy","bordeaux","wine"],teal:["teal","turquoise"],gold:["gold"] };
  const CATEGORIES = { Jackets:["jacket","jackets","bomber","windbreaker"],Coats:["coat","coats","parka","trench","overcoat"],Jeans:["jeans","denim"],Trousers:["trousers","trouser","pants","chino","joggers","cargo"],Shirts:["shirt","shirts","overshirt","blouse"],"T-Shirts & Polos":["t-shirt","tshirt","tee","polo"],Dresses:["dress","dresses","gown"],Sportswear:["sportswear","gym","running","training","workout"],Streetwear:["streetwear","hoodie","sweatshirt","sweater","jumper","fleece"] };
  const VIBES = { tailoring:["Shirts","Trousers","Coats"],tailored:["Shirts","Trousers","Coats"],formal:["Shirts","Trousers","Coats"],smart:["Shirts","Trousers","Coats"],office:["Shirts","Trousers"],work:["Shirts","Trousers"],wedding:["Dresses","Shirts","Coats"],party:["Dresses","T-Shirts & Polos"],summer:["Dresses","Shirts","T-Shirts & Polos"],winter:["Coats","Jackets","Streetwear"],outdoor:["Jackets","Coats"],lounge:["Streetwear","Sportswear"] };
  const STOP = new Set("a an the for with in of to and or on at is are as some any something anything stuff things piece pieces item items outfit look clothes clothing wardrobe me my mine i we you your need want wanting looking find show get please that this it its keep wear wearing buy add like love prefer maybe thanks have around about under below over above less than more most max maximum min minimum up budget euro euros eur cost costs price priced cheap affordable nice good great lovely new fresh really very just kind sort bit".split(" "));
  const $ = (selector, root=document) => root.querySelector(selector);
  const $$ = (selector, root=document) => [...root.querySelectorAll(selector)];
  const euro = new Intl.NumberFormat("de-DE", { style:"currency",currency:"EUR" });
  const state = { all:[],query:"",parsed:empty(),category:null,catList:null,sort:"featured",relaxNote:null,bag:loadBag(),selected:null,selectedSize:null,chat:[],recognition:null,voiceTarget:"search",searchIndex:null,indexBySku:new Map() };

  function empty() { return { colors:[],category:null,catList:null,gender:null,min:null,max:null,keywords:[],hits:{ color:{},cat:new Set(),price:new Set(),gender:new Set(),kw:new Set() } }; }
  function norm(value) { return String(value).toLowerCase().replace(/[^a-z0-9€]/g, ""); }
  function esc(value) { return String(value).replace(/[-/\\^$*+?.()|[\]{}]/g, "\\$&"); }
  function parseNumber(value) { return Math.round(parseFloat(String(value).replace(",", ".")) * 100) / 100; }
  function parseQuery(text) {
    const p = empty(), lower = " " + text.toLowerCase() + " ";
    if (!text.trim()) return p;
    const has = (term) => new RegExp("(?<![a-z])" + esc(term).replace(/-/g, "[- ]?") + "(?![a-z])", "i");
    for (const [colour, words] of Object.entries(COLORS)) for (const word of words) if (has(word).test(lower)) { if (!p.colors.includes(colour)) p.colors.push(colour); p.hits.color[norm(word)] = colour; }
    for (const [category, words] of Object.entries(CATEGORIES)) { if (p.category) break; for (const word of words) if (has(word).test(lower)) { p.category = category; p.hits.cat.add(norm(word)); break; } }
    for (const [word, categories] of Object.entries(VIBES)) if (has(word).test(lower)) { p.hits.cat.add(norm(word)); if (!p.category && !p.catList) p.catList = categories.slice(); }
    const recordPrice = (match) => match[0].split(/\s+/).forEach((word) => p.hits.price.add(norm(word)));
    let match;
    if ((match = lower.match(/between\s*[$€]?\s*(\d+(?:[.,]\d+)?)\s*(?:and|to|-|–)\s*[$€]?\s*(\d+(?:[.,]\d+)?)/))) { p.min=parseNumber(match[1]);p.max=parseNumber(match[2]);recordPrice(match); }
    if ((match = lower.match(/(?:under|below|less than|max(?:imum)?|up to|within|no more than|<)\s*[$€]?\s*(\d+(?:[.,]\d+)?)/))) { p.max=parseNumber(match[1]);recordPrice(match); }
    if ((match = lower.match(/(?:over|above|from|more than|at least|>)\s*[$€]?\s*(\d+(?:[.,]\d+)?)/))) { p.min=parseNumber(match[1]);recordPrice(match); }
    if (p.min===null && p.max===null && (match = lower.match(/[$€]\s*(\d+(?:[.,]\d+)?)|(\d+(?:[.,]\d+)?)\s*(?:[$€]|eur|euros?)/))) { p.max=parseNumber(match[1]||match[2]);recordPrice(match); }
    if (/(?<![a-z])(women|woman|womens|women's|ladies|female)(?![a-z])/i.test(lower)) { p.gender="women";["women","woman","womens","ladies","female"].forEach((word) => p.hits.gender.add(word)); }
    else if (/(?<![a-z])(men|man|mens|men's|male|guys)(?![a-z])/i.test(lower)) { p.gender="men";["men","man","mens","male","guys"].forEach((word) => p.hits.gender.add(word)); }
    const used = new Set([...Object.keys(p.hits.color),...p.hits.cat,...p.hits.price,...p.hits.gender]);
    for (const raw of text.toLowerCase().split(/[\s,.;/]+/)) { const word=norm(raw); if (word.length>=3 && !STOP.has(word) && !used.has(word) && !/^\d+$/.test(word) && !p.keywords.includes(word)) { p.keywords.push(word);p.hits.kw.add(word); } }
    return p;
  }
  function currentConstraints() { const p=state.parsed; return { category:state.category,catList:state.category?null:state.catList,colors:p.colors,gender:p.gender,min:p.min,max:p.max,keywords:p.keywords }; }
  function semanticMatch(product, c) { return (!c.category||product.category===c.category) && (!(!c.category&&c.catList?.length)||c.catList.includes(product.category)) && (!c.colors.length||c.colors.includes(product.color)) && (!c.gender||product.gender===c.gender) && (c.min===null||product.promotional_price>=c.min) && (c.max===null||product.promotional_price<=c.max); }
  function lexicalScore(product, words) { const name=(product.name+" "+product.type).toLowerCase(), broad=(product.brand+" "+product.category+" "+product.color+" "+product.gender).toLowerCase(); return words.reduce((score,word)=>score+(name.includes(word)?4:broad.includes(word)?1:0),0); }
  function tokens(text) { return String(text).toLowerCase().match(/[a-z0-9]+/g)||[]; }
  function rank(products,c) {
    const index=state.searchIndex;
    if(!index)return products.slice().sort((a,b)=>lexicalScore(b,c.keywords)-lexicalScore(a,c.keywords)||a.promotional_price-b.promotional_price);
    const terms=tokens(state.query).filter((term)=>index.idf[term]);
    const frequencies=terms.reduce((counts,term)=>{counts[term]=(counts[term]||0)+1;return counts;},{});
    const queryVector=Object.fromEntries(Object.entries(frequencies).map(([term,count])=>[term,(count/terms.length)*index.idf[term]]));
    const queryNorm=Math.sqrt(Object.values(queryVector).reduce((sum,weight)=>sum+weight*weight,0))||1;
    const k1=1.2,b=0.75;
    const scored=products.map((product)=>{
      const document=state.indexBySku.get(product.sku);
      if(!document)return {product,bm25:0,cosine:0};
      let dot=0,bm25=0;
      for(const term of Object.keys(queryVector)){
        dot+=(document.vector[term]||0)*queryVector[term];
        const tf=document.terms[term]||0;
        if(tf)bm25+=index.idf[term]*((tf*(k1+1))/(tf+k1*(1-b+b*(document.length/index.average_document_length))));
      }
      return {product,bm25,cosine:dot/(document.norm*queryNorm)};
    });
    const maxBm25=Math.max(1,...scored.map((item)=>item.bm25));
    return scored.sort((a,b)=>((b.bm25/maxBm25)*.55+b.cosine*.35+(b.product.discount_percentage?0.1:0))-((a.bm25/maxBm25)*.55+a.cosine*.35+(a.product.discount_percentage?0.1:0))||a.product.promotional_price-b.product.promotional_price).map((item)=>item.product);
  }
  function retrieveProducts(c=currentConstraints()) {
    const semantic=state.all.filter((product)=>semanticMatch(product,c));
    state.relaxNote=null;
    if (semantic.length) return rank(semantic,c);
    const relaxedPrice=state.all.filter((product)=>semanticMatch(product,{...c,min:null,max:null}));
    if(relaxedPrice.length){state.relaxNote="No item met that price exactly, so the stylist kept your gender and colour while widening the budget.";return rank(relaxedPrice,c);}
    const relaxedCut=state.all.filter((product)=>semanticMatch(product,{...c,category:null,catList:null,min:null,max:null}));
    if(relaxedCut.length){state.relaxNote="No item met every condition, so the stylist kept your gender and colour while widening the cut.";return rank(relaxedCut,c);}
    return [];
  }
  function sortProducts(products) { const list=products.slice(); if(state.sort==="price-asc")list.sort((a,b)=>a.promotional_price-b.promotional_price); else if(state.sort==="price-desc")list.sort((a,b)=>b.promotional_price-a.promotional_price); else if(state.sort==="discount")list.sort((a,b)=>b.discount_percentage-a.discount_percentage||a.promotional_price-b.promotional_price); else if(state.sort==="name")list.sort((a,b)=>a.name.localeCompare(b.name)); return list; }

  function loadBag() { try { return JSON.parse(localStorage.getItem(BAG_KEY)||"{}")||{}; } catch { return {}; } }
  function saveBag() { try { localStorage.setItem(BAG_KEY,JSON.stringify(state.bag)); } catch { /* Private mode does not persist. */ } }
  function bagLines() { return Object.entries(state.bag).map(([key,quantity])=>{const [sku,size]=key.split("::");return {key,size,quantity,product:state.all.find((product)=>product.sku===sku)};}).filter((line)=>line.product&&line.quantity>0); }
  const bagCount = () => bagLines().reduce((total,line)=>total+line.quantity,0);
  const bagSubtotal = () => bagLines().reduce((total,line)=>total+line.product.promotional_price*line.quantity,0);
  function setQuantity(key,quantity) { if(quantity<=0)delete state.bag[key];else state.bag[key]=Math.min(quantity,99);saveBag();render(); }
  function ink(hex) { const value=parseInt(hex.slice(1),16), lum=.2126*((value>>16)&255)+.7152*((value>>8)&255)+.0722*(value&255);return lum>142?"#18140f":"#f3efe6"; }
  const swatch = (colour) => SWATCH[colour]||"#8b8b84";
  const html = (value) => String(value).replace(/[&<>"]/g,(char)=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[char]));
  function price(product) { return product.discount_percentage ? euro.format(product.promotional_price)+"<span class=\"was\">"+euro.format(product.original_price)+"</span><span class=\"off\">−"+product.discount_percentage+"%</span>" : euro.format(product.promotional_price); }
  function productVisual(product,className) {
    const source=product.image_path||product.image_url;
    if(source)return "<img class=\""+className+"\" src=\""+html(source)+"\" alt=\""+html(product.name)+"\" loading=\"lazy\">";
    const hex=swatch(product.color);
    return "<div class=\"swatch\" data-cat=\""+product.category+"\" style=\"--sw:"+hex+";--sw-ink:"+ink(hex)+"\"><span class=\"type\">"+html(product.type)+"</span><span class=\"cname\">"+html(product.color)+"</span></div>";
  }
  function productCard(product) {
    const count=bagLines().filter((line)=>line.product.sku===product.sku).reduce((total,line)=>total+line.quantity,0);
    return "<article class=\"card\"><div class=\"product-media\">"+(product.discount_percentage?"<span class=\"cut\">−"+product.discount_percentage+"%</span>":"")+productVisual(product,"product-image")+"</div><div class=\"brand\">"+html(product.brand)+"</div><p class=\"name\">"+html(product.name)+"</p><div class=\"price\">"+price(product)+"</div><button class=\"add "+(count?"in":"")+"\" data-add=\""+product.sku+"\">"+(count?"In bag · "+count:"Choose size")+"</button></article>";
  }
  function lexHTML() { const p=state.parsed; return state.query.split(/(\s+)/).map((token)=>{if(/^\s+$/.test(token))return token;const word=norm(token);if(p.hits.color[word])return "<mark class=\"col\"><span class=\"dot\" style=\"background:"+swatch(p.hits.color[word])+"\"></span>"+html(token)+"</mark>";if(p.hits.cat.has(word)||p.hits.price.has(word)||p.hits.gender.has(word))return "<mark>"+html(token)+"</mark>";return p.hits.kw.has(word)?"<mark class=\"kw\">"+html(token)+"</mark>":html(token);}).join(""); }
  function chip(label,value,key) { return "<span class=\"bit\">"+label+" <span>"+html(value)+"</span><button data-clear=\""+key+"\" aria-label=\"remove "+label+"\">×</button></span>"; }
  function chips() { const p=state.parsed,b=[];if(state.category)b.push(chip("cut",state.category,"cut"));else if(state.catList)b.push(chip("occasion",state.catList.join(" / "),"cut"));if(p.colors.length)b.push(chip("colour",p.colors.join(" + "),"colour"));if(p.gender)b.push(chip("for",p.gender,"gender"));if(p.min!==null)b.push(chip("from",euro.format(p.min),"min"));if(p.max!==null)b.push(chip("max",euro.format(p.max),"max"));if(p.keywords.length)b.push(chip("words",p.keywords.join(" "),"words"));return b.length?b.join("")+"<button class=\"bit reset\" data-clear=\"all\">clear all ×</button>":""; }
  function renderCats() { const categories=[...new Set(state.all.map((product)=>product.category))].sort();$("#cats").innerHTML=["All",...categories].map((category)=>"<button data-cat-pick=\""+category+"\" aria-pressed=\""+(category==="All"?!state.category:state.category===category)+"\">"+category+"</button>").join(""); }
  function renderBag() {
    const lines=bagLines(); $("#bagcount").textContent=bagCount()?" · "+bagCount():"";
    $("#lines").innerHTML=lines.length?lines.map((line)=>"<div class=\"li\"><div class=\"mini\" style=\"--sw:"+swatch(line.product.color)+"\"></div><div><p class=\"lname\">"+html(line.product.name)+"</p><span class=\"lbrand\">"+html(line.product.brand)+" · "+html(line.size||"Size not selected")+"</span><div class=\"qty\"><button data-step=\"-1\" data-key=\""+line.key+"\" aria-label=\"one fewer\">−</button><span>"+line.quantity+"</span><button data-step=\"1\" data-key=\""+line.key+"\" aria-label=\"one more\">+</button></div></div><div class=\"right\"><span class=\"ltot\">"+euro.format(line.product.promotional_price*line.quantity)+"</span><button class=\"rm\" data-rm=\""+line.key+"\">remove</button></div></div>").join(""):"<div class=\"dempty\">Your bag is empty. Describe something up top and add it here.</div>";
    $("#subtotal").textContent=euro.format(bagSubtotal());
  }
  function render() {
    const results=sortProducts(retrieveProducts()), bits=chips(), read=$("#read");read.hidden=!state.query.trim()&&!bits;
    if(!read.hidden){$("#lex").innerHTML=lexHTML()||"no words the stylist could use";$("#bits").innerHTML=bits;$("#note").hidden=!state.relaxNote;$("#note").textContent=state.relaxNote||"";}
    $("#count").textContent=results.length===state.all.length?state.all.length+" pieces":results.length+" of "+state.all.length+" pieces";$("#sort").value=state.sort;
    $("#grid").innerHTML=results.length?results.map(productCard).join(""):"<div class=\"empty\"><p>No pieces on this rack.</p><p>Try <code>a winter coat</code> or lift the budget.</p></div>";
    renderCats();renderBag();
  }

  function runSearch(text) { state.query=text;state.parsed=parseQuery(text);state.category=state.parsed.category||null;state.catList=state.parsed.category?null:state.parsed.catList;render(); }
  let toastTimer;
  function toast(message) { const el=$("#toast");el.textContent=message;el.classList.add("show");clearTimeout(toastTimer);toastTimer=setTimeout(()=>el.classList.remove("show"),2600); }
  function openBag(open) { $("#drawer").classList.toggle("open",open);$("#scrim").classList.toggle("open",open);$("#drawer").setAttribute("aria-hidden",String(!open)); }
  function openDialog(id) { const dialog=$(id);if(!dialog.open)(id==="#stylist-modal"?dialog.show():dialog.showModal()); }
  function closeDialog(id) { const dialog=$(id);if(dialog.open)dialog.close();if(id==="#stylist-modal")document.body.classList.remove("stylist-open"); }
  function openVariant(sku) { state.selected=state.all.find((product)=>product.sku===sku);state.selectedSize=null;if(!state.selected)return;$("#variant-title").textContent=state.selected.name;$("#variant-product").innerHTML="<p class=\"variant-copy\">"+html(state.selected.brand)+" · "+euro.format(state.selected.promotional_price)+"</p>";$("#size-list").innerHTML=state.selected.sizes.map((size)=>"<button type=\"button\" data-size=\""+html(size)+"\" aria-pressed=\"false\">"+html(size)+"</button>").join("");$("#confirm-variant").disabled=true;openDialog("#variant-modal"); }
  function addSelected() { if(!state.selected||!state.selectedSize)return;const key=state.selected.sku+"::"+state.selectedSize;state.bag[key]=(state.bag[key]||0)+1;saveBag();closeDialog("#variant-modal");render();toast("Added · "+state.selected.name.split(" - ")[0]+" in "+state.selectedSize); }
  function reviewOrder() { const lines=bagLines();if(!lines.length){toast("Your bag is empty.");return;}$("#checkout-lines").innerHTML=lines.map((line)=>"<div><span>"+html(line.product.name)+" · "+html(line.size)+"</span><strong>"+line.quantity+" × "+euro.format(line.product.promotional_price)+"</strong></div>").join("");$("#checkout-total").textContent=euro.format(bagSubtotal());openDialog("#checkout-modal"); }
  function chatProduct(product) { return "<button class=\"chat-product\" data-add=\""+product.sku+"\"><img src=\""+html(product.image_path||product.image_url||"")+"\" alt=\"\" loading=\"lazy\"><span><b>"+html(product.brand)+"</b>"+html(product.name)+"<strong>"+euro.format(product.promotional_price)+"</strong></span></button>"; }
  function addChat(role,message,products=[]) { state.chat.push({role,message,products});$("#chat-log").innerHTML=state.chat.map((item)=>"<div class=\"chat "+item.role+"\"><span>"+(item.role==="user"?"You":"Stylist")+"</span><p>"+html(item.message)+"</p>"+(item.products||[]).map(chatProduct).join("")+"</div>").join("");$("#chat-log").scrollTop=$("#chat-log").scrollHeight;if(role==="assistant"&&$("#speak-back").checked)speak(message); }
  function reply(text) { if(/\b(bag|cart|checkout)\b/i.test(text)){openBag(true);return {message:"Your bag is open. You can adjust sizes and quantities there, then review the demo order.",products:[]};}const p=parseQuery(text);state.query=text;state.parsed=p;state.category=p.category||null;state.catList=p.category?null:p.catList;const results=retrieveProducts();render();if(!results.length)return {message:"I could not find that in this demo catalog without breaking your gender or colour request. Try a higher budget or a different colour.",products:[]};const names=results.slice(0,3).map((product)=>product.name.split(" - ")[0]);const note=state.relaxNote?" "+state.relaxNote:"";return {message:"I found "+(results.length===1?"one close match":results.length+" close matches")+". Start with "+names.join(", ")+". I blended catalogue meaning with keyword relevance."+note,products:results.slice(0,3)}; }
  function sendChat(text) { addChat("user",text);const response=reply(text);addChat("assistant",response.message,response.products); }
  function openStylist() { openDialog("#stylist-modal");document.body.classList.add("stylist-open");if(!state.chat.length)addChat("assistant","Tell me the occasion, colour, garment, or budget. I will search the local catalog and explain the matches.");setTimeout(()=>$("#chat-input").focus(),0); }
  function speak(message) { if(!("speechSynthesis" in window))return;window.speechSynthesis.cancel();const utterance=new SpeechSynthesisUtterance(message);utterance.lang="en-GB";utterance.rate=1;window.speechSynthesis.speak(utterance); }
  function setupVoice() {
    const Recognition=window.SpeechRecognition||window.webkitSpeechRecognition;
    if(!Recognition){$("#voice").disabled=true;$("#chat-voice").disabled=true;$("#voice-status").textContent="Voice input is not available in this browser. You can still type to the stylist.";return;}
    state.recognition=new Recognition();state.recognition.lang="en-GB";state.recognition.interimResults=false;state.recognition.maxAlternatives=1;
    state.recognition.onstart=()=>{$("#voice-status").textContent="Listening. Speak your request now.";["#voice","#chat-voice"].forEach((id)=>$(id).setAttribute("aria-pressed","true"));};
    state.recognition.onend=()=>["#voice","#chat-voice"].forEach((id)=>$(id).setAttribute("aria-pressed","false"));
    state.recognition.onerror=()=>{$("#voice-status").textContent="I could not hear that. Please try again or type your request.";};
    state.recognition.onresult=(event)=>{const text=event.results[0][0].transcript.trim();$("#voice-status").textContent="Heard: “"+text+"”";if(state.voiceTarget==="chat"){$("#chat-input").value=text;sendChat(text);}else{$("#q").value=text;runSearch(text);}};
  }
  function startVoice(target) { if(!state.recognition)return;state.voiceTarget=target;try{state.recognition.start();}catch{/* Recognition is already active. */} }
  function clearConstraint(key) { const p=state.parsed;if(key==="all"){$("#q").value="";runSearch("");return;}if(key==="cut"){state.category=null;state.catList=null;p.category=null;p.catList=null;}if(key==="colour")p.colors=[];if(key==="gender")p.gender=null;if(key==="min")p.min=null;if(key==="max")p.max=null;if(key==="words")p.keywords=[];render(); }
  function setupTheme() { const saved=localStorage.getItem(THEME_KEY);if(saved)document.documentElement.dataset.theme=saved;$("#theme").addEventListener("click",()=>{const next=document.documentElement.dataset.theme==="dark"?"light":"dark";document.documentElement.dataset.theme=next;localStorage.setItem(THEME_KEY,next);}); }
  function wire() {
    $("#ask").addEventListener("submit",(event)=>{event.preventDefault();runSearch($("#q").value);});$("#voice").addEventListener("click",()=>startVoice("search"));$("#chat-voice").addEventListener("click",()=>startVoice("chat"));
    $("#egs").addEventListener("click",(event)=>{const button=event.target.closest("button[data-eg]");if(button){$("#q").value=button.dataset.eg;runSearch(button.dataset.eg);}});
    $("#read").addEventListener("click",(event)=>{const button=event.target.closest("[data-clear]");if(button)clearConstraint(button.dataset.clear);});$("#cats").addEventListener("click",(event)=>{const button=event.target.closest("button[data-cat-pick]");if(!button)return;state.category=button.dataset.catPick==="All"?null:button.dataset.catPick;state.catList=null;render();});$("#sort").addEventListener("change",(event)=>{state.sort=event.target.value;render();});$("#grid").addEventListener("click",(event)=>{const button=event.target.closest("button[data-add]");if(button)openVariant(button.dataset.add);});
    $("#lines").addEventListener("click",(event)=>{const step=event.target.closest("button[data-step]"),remove=event.target.closest("button[data-rm]");if(step)setQuantity(step.dataset.key,(state.bag[step.dataset.key]||0)+Number(step.dataset.step));if(remove)setQuantity(remove.dataset.rm,0);});
    $("#openbag").addEventListener("click",()=>openBag(true));$("#closebag").addEventListener("click",()=>openBag(false));$("#scrim").addEventListener("click",()=>openBag(false));$("#clearbag").addEventListener("click",()=>{state.bag={};saveBag();render();});$("#pay").addEventListener("click",reviewOrder);
    $("#open-stylist").addEventListener("click",openStylist);$("#close-stylist").addEventListener("click",()=>closeDialog("#stylist-modal"));$("#chat-form").addEventListener("submit",(event)=>{event.preventDefault();const text=$("#chat-input").value.trim();if(!text)return;$("#chat-input").value="";sendChat(text);});$("#chat-log").addEventListener("click",(event)=>{const button=event.target.closest("button[data-add]");if(button)openVariant(button.dataset.add);});
    $("#close-variant").addEventListener("click",()=>closeDialog("#variant-modal"));$("#size-list").addEventListener("click",(event)=>{const button=event.target.closest("button[data-size]");if(!button)return;state.selectedSize=button.dataset.size;$$("#size-list button").forEach((item)=>item.setAttribute("aria-pressed",String(item===button)));$("#confirm-variant").disabled=false;});$("#confirm-variant").addEventListener("click",addSelected);
    $("#close-checkout").addEventListener("click",()=>closeDialog("#checkout-modal"));$("#place-order").addEventListener("click",()=>{const reference="SS-"+Math.floor(100000+Math.random()*900000);state.bag={};saveBag();closeDialog("#checkout-modal");openBag(false);render();toast("Demo order "+reference+" confirmed.");});
    document.addEventListener("keydown",(event)=>{if(event.key==="Escape")openBag(false);});$("#stylist-modal").addEventListener("close",()=>document.body.classList.remove("stylist-open"));$$("dialog").forEach((dialog)=>dialog.addEventListener("click",(event)=>{if(event.target===dialog)dialog.close();}));
  }
  async function boot() {
    let catalog=window.__CATALOG__;
    if(!catalog)try{const response=await fetch(CATALOG_URL,{cache:"no-cache"});if(!response.ok)throw new Error("catalog unavailable");catalog=await response.json();}catch{$("#grid").innerHTML="<div class=\"empty\"><p>Couldn't load the catalog.</p><p>Serve this folder over HTTP: <code>python3 -m http.server</code></p></div>";return;}
    let searchIndex=window.__SEARCH_INDEX__;
    if(!searchIndex)try{const response=await fetch("./search-index.json",{cache:"no-cache"});if(!response.ok)throw new Error("index unavailable");searchIndex=await response.json();}catch{searchIndex=null;}
    state.all=catalog.slice();state.searchIndex=searchIndex;state.indexBySku=new Map((searchIndex?.documents||[]).map((document)=>[document.sku,document]));$("#pcount").textContent=String(state.all.length);wire();setupTheme();setupVoice();$("#q").value="keep it under €120";runSearch($("#q").value);window.__StyleSpeak={parseQuery,retrieveProducts:(query)=>{const p=parseQuery(query);return retrieveProducts({category:p.category,catList:p.catList,colors:p.colors,gender:p.gender,min:p.min,max:p.max,keywords:p.keywords});}};
  }
  if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",boot);else boot();
})();
