#!/usr/bin/env python3
"""Generate the OSFT marketing site in Open Source Barware's page format."""
import json
from pathlib import Path
from i18n import I18N

LAB = Path(__file__).resolve().parent
V = "30"
JS = "11"
DEMO = "http://127.0.0.1:5054/"


def write_i18n():
    blob = "window.OSFT_I18N = " + json.dumps(I18N, ensure_ascii=False, indent=2) + ";\n"
    (LAB / "js/i18n.js").write_text(blob, encoding="utf-8")
    (LAB / f"js/i18n-v{JS}.js").write_text(blob, encoding="utf-8")
    site = (LAB / "js/site.js").read_text(encoding="utf-8")
    (LAB / f"js/site-v{JS}.js").write_text(site, encoding="utf-8")
    print("wrote js/i18n-v" + JS + ".js", len(I18N["en"]), "keys")


def rel(depth: int) -> str:
    return "" if depth == 0 else "../" * depth


def shell(depth, title, desc, current, body, extra_body_class="", title_key=""):
    r = rel(depth)
    title_attr = f' data-i18n="{title_key}"' if title_key else ""
    def nav_cls(key):
        return ' class="is-here"' if current == key else ""
    def cta_cls():
        extra = " is-here" if current == "download" else ""
        return f' class="nav-cta{extra}"'
    header = f'''  <header class="site-header">
    <div class="header-inner">
      <a class="brand" href="{r}">
        <img class="brand-truck" src="{r}img/header-truck.webp" width="220" height="160" alt="" />
        <span class="brand-copy">
          <span class="brand-name">Open Source Food Truckin'</span>
          <span class="brand-tag" data-i18n="brand_tag">The mobile kitchen inventory system, proudly part of the Open Source Barware family.</span>
        </span>
      </a>
      <nav class="nav" id="site-nav" aria-label="Primary">
        <a href="{r}"{nav_cls("home")} data-i18n="nav_home">Home</a>
        <a href="{r}the-process/"{nav_cls("process")}><span data-i18n="nav_process">The Process</span><small data-i18n="nav_process_s">Walk the truck</small></a>
        <a href="{r}about/"{nav_cls("about")}><span data-i18n="nav_about">About</span><small data-i18n="nav_about_s">The Truck Stop</small></a>
        <a href="{r}resources/"{nav_cls("resources")}><span data-i18n="nav_res">Resources</span><small data-i18n="nav_res_s">Mobile Menu</small></a>
        <a href="{r}inventory/dashboard/"{nav_cls("demo")}><span data-i18n="nav_demo">Live Demo</span><small data-i18n="nav_demo_s">The Lot</small></a>
        <a href="{r}download/"{cta_cls()} data-i18n="nav_dl">Download Program</a>
      </nav>
      <div class="header-end">
        <div class="lang" role="group" aria-label="Language">
          <button type="button" data-locale="en" class="is-on" aria-pressed="true">EN</button>
          <button type="button" data-locale="es" aria-pressed="false">ES</button>
        </div>
        <button type="button" class="nav-toggle" id="nav-toggle" aria-expanded="false" aria-controls="site-nav">
          <span></span><span></span><span></span>
          <span class="sr" data-i18n="menu">Menu</span>
        </button>
      </div>
    </div>
  </header>'''
    footer = f'''  <footer class="site-footer">
    <div class="wrap">
      <div class="foot-grid">
        <div class="foot-brand">
          <p data-i18n="foot_brand_1">Crafted for rolling kitchens. Given to the trade, no strings attached. Sister program to Open Source Barware — same house, a parking brake.</p>
          <p data-i18n="foot_brand_2">A Richard B. Jamison project. Free forever.</p>
        </div>
        <div class="foot-col">
          <h3 data-i18n="foot_nav">Navigate</h3>
          <a href="{r}" data-i18n="nav_home">Home</a>
          <a href="{r}the-process/" data-i18n="nav_process">The Process</a>
          <a href="{r}about/" data-i18n="nav_about">About</a>
          <a href="{r}manifesto/" data-i18n="nav_manifesto">Manifesto</a>
          <a href="{r}resources/" data-i18n="nav_res">Resources</a>
          <a href="{r}blog/" data-i18n="nav_blog">Blog</a>
          <a href="{r}download/" data-i18n="nav_dl">Download Program</a>
          <a href="{r}downloads/" data-i18n="nav_guide">Program Guide</a>
          <a href="{r}open-source-compliance/" data-i18n="nav_compliance">Compliance</a>
          <a href="{r}inventory/dashboard/" data-i18n="nav_demo">Live Demo</a>
          <a href="{r}changelog/" data-i18n="nav_notes">Release notes</a>
        </div>
        <div class="foot-col">
          <h3 data-i18n="foot_inv">Free Inventory</h3>
          <a href="{r}free-food-truck-inventory-software/" data-i18n="foot_seo_ft">Food Truck Inventory Software</a>
          <a href="{r}truck-inventory/" data-i18n="foot_seo_truck">Truck &amp; Cooler Inventory</a>
          <a href="{r}prep-inventory/" data-i18n="foot_seo_prep">Prep Inventory</a>
          <a href="{r}food-truck-inventory-software-comparison/" data-i18n="foot_seo_cmp">Compare Alternatives</a>
          <h3 style="margin-top:1.4rem" data-i18n="foot_workshop">Workshop</h3>
          <p data-i18n-html="foot_workshop_p">From <a href="https://intelligenthospitalitysystems.com/">Intelligent Hospitality Systems</a>. Also from us: <a href="https://www.reservationrelief.com/">Reservation Relief</a>, reservations on the website you already own.</p>
          <p data-i18n-html="foot_resonant">Web &amp; systems notes: <a href="https://resonantwebdesign.com/industries/restaurants-hospitality-web-design/" rel="noopener noreferrer">Resonant</a></p>
        </div>
      </div>
      <p class="foot-legal">© 2026 Open Source Food Truckin' — <span data-i18n="foot_legal">All the program is free and open source under GPLv3</span> · <a href="{r}open-source-compliance/" data-i18n="nav_license">License and source</a> · <a href="{r}privacy/" data-i18n="nav_privacy">Privacy</a> · <a href="{r}terms/" data-i18n="nav_terms">Terms</a></p>
    </div>
  </footer>'''
    bc = f' class="{extra_body_class}"' if extra_body_class else ""
    return f'''<!DOCTYPE html>
<html lang="en" translate="no">
<head>
  <meta charset="utf-8" />
  <meta name="google" content="notranslate" />
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />
  <meta name="theme-color" content="#1a120c" />
  <meta name="description" content="{desc}" />
  <meta property="og:type" content="website" />
  <meta property="og:site_name" content="Open Source Food Truckin'" />
  <meta property="og:title" content="{title}" />
  <meta property="og:description" content="{desc}" />
  <meta property="og:image" content="https://osfoodtrucking.com/img/og-card.jpg" />
  <meta property="og:image:width" content="1200" />
  <meta property="og:image:height" content="630" />
  <meta property="og:image:alt" content="Open Source Food Truckin' — a night food truck, 100% free and bilingual" />
  <meta name="twitter:card" content="summary_large_image" />
  <meta name="twitter:image" content="https://osfoodtrucking.com/img/og-card.jpg" />
  <title{title_attr}>{title}</title>
  <link rel="icon" href="{r}img/gear.svg" type="image/svg+xml" />
  <link rel="stylesheet" href="{r}fonts/fonts.css?v=2" />
  <link rel="stylesheet" href="{r}css/site.css?v={V}" />
  <script src="/js/i18n-v{JS}.js"></script>
  <script>
    (function () {{
      var lang = "en";
      try {{
        var q = /(?:^|[?&])lang=(en|es)(?:&|$)/.exec(location.search);
        if (q) lang = q[1];
        else {{
          var s = localStorage.getItem("osft_lang");
          if (s === "es" || s === "en") lang = s;
          else {{
            var m = document.cookie.match(/(?:^|;\\s*)osft_lang=(en|es)(?:;|$)/);
            if (m) lang = m[1];
          }}
        }}
      }} catch (e) {{}}
      document.documentElement.lang = lang;
      if (lang === "es") document.documentElement.classList.add("osft-i18n-wait");
      setTimeout(function () {{ document.documentElement.classList.remove("osft-i18n-wait"); }}, 2000);
    }})();
  </script>
</head>
<body{bc}>
  <a class="skip" href="#main" data-i18n="skip">Skip to content</a>
{header}
{body}
{footer if extra_body_class != "lot-page" else ""}
  <script>
    window.OFFER_TRACKER = {{
      siteId: "osft-landing",
      ga4Id: "",
      endpoint: "https://opensourcebarware.com/api/nexus-collect",
      clarityId: "",
      debug: false
    }};
  </script>
  <script src="/js/tracker.js?v=2" defer></script>
  <script src="/js/site-v{JS}.js"></script>
</body>
</html>
'''


def write(path, html):
    p = LAB / path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(html, encoding="utf-8")
    print("wrote", path)


def hero(r, img, alt, kicker, h1, lede, extra="", kicker_k="", h1_k="", lede_k=""):
    kattr = f' data-i18n="{kicker_k}"' if kicker_k else ""
    hattr = f' data-i18n-html="{h1_k}"' if h1_k else ""
    lattr = f' data-i18n="{lede_k}"' if lede_k else ""
    return f'''  <section class="page-hero" aria-label="Hero">
    <img class="page-hero-art" src="{r}img/{img}.webp" alt="{alt}" width="1600" height="900" />
    <div class="page-hero-shade" aria-hidden="true"></div>
    <div class="wrap">
      <p class="kicker"{kattr}>{kicker}</p>
      <h1 class="display"{hattr}>{h1}</h1>
      <p class="lede"{lattr}>{lede}</p>
      {extra}
    </div>
  </section>'''


def home():
    r = ""
    body = f'''  <section class="poster" aria-label="Hero">
    <video class="poster-art" autoplay muted loop playsinline preload="auto" poster="{r}img/hero-header-poster.jpg" width="1280" height="720" disablepictureinpicture aria-hidden="true">
      <source src="{r}video/hero-header.mp4" type="video/mp4" />
    </video>
    <div class="poster-shade" aria-hidden="true"></div>
    <div class="poster-right">
      <div class="poster-copy">
        <h1>
          <span data-i18n="hero_h1">The real truck problem,</span>
          <span data-i18n="hero_h2">solved on the go.</span>
        </h1>
        <p class="hero-lead" data-i18n="hero_p">Tame the chaos of a rolling kitchen. From the same house as Open Source Barware: track supplies, pull last night’s POS, cost every plate, and print a load list — festival lot or street corner.</p>
        <p class="hero-find" data-i18n="hero_find">Find this and the bar tools at OpenSourceBarware.com.</p>
        <div class="hero-actions">
          <a class="btn btn-gold" href="{r}download/" data-i18n="cta_app">Download Program</a>
          <a class="btn btn-teal" href="{r}the-process/" data-i18n="cta_menu">Learn this system</a>
          <a class="btn btn-teal" href="{r}about/" data-i18n="cta_story">Read our story</a>
        </div>
      </div>
      <div class="poster-notes">
        <article class="sticker">
          <img class="sticker-gauge" src="{r}img/gauge.webp" width="160" height="160" alt="" />
          <div>
            <p class="sticker-kicker" data-i18n="asphalt_kicker">Waste-o-meter</p>
            <h2 data-i18n="asphalt_h">Built on the asphalt</h2>
            <p data-i18n="asphalt_note">Same kitchen that made Open Source Barware. This one just has a parking brake.</p>
          </div>
        </article>
        <article class="launch-note">
          <img class="launch-globe" src="{r}img/globe.webp" width="180" height="180" alt="" />
          <div>
            <h2 data-i18n="launch_h">Global launch</h2>
            <p data-i18n="launch_p">Launching for the whole crew. Food Truckin' for the rolling kitchen, Barware for the well. Fully bilingual in English and Spanish.</p>
            <p class="launch-es" data-i18n="launch_es">¡Disponible en español! Completamente bilingüe.</p>
          </div>
        </article>
      </div>
    </div>
  </section>

  <section class="free-band" id="free">
    <div class="free-banner">
      <div class="free-copy">
        <h2 data-i18n="free_h">100% free &amp; bilingual</h2>
        <p data-i18n="free_p">Free and open source under GPLv3. Runs on your own computer. No subscription, ever. The whole crew can work in English or Spanish.</p>
      </div>
      <img class="free-pig" src="{r}img/seal.webp" width="140" height="140" alt="" />
      <img class="free-truck" src="{r}img/truck-small.webp" width="200" height="120" alt="" />
      <img class="free-stamp" src="{r}img/free-seal.webp" width="150" height="150" alt="100% free" />
    </div>
  </section>

  <section class="stats-strip" aria-label="At a glance">
    <div class="stat"><b>$0</b><span data-i18n="stat_cost">Cost</span></div>
    <div class="stat"><b>1</b><span data-i18n="stat_prog">Free program</span></div>
    <div class="stat"><b>3</b><span data-i18n="stat_steps">Easy steps</span><small data-i18n="stat_steps_s">Each week</small></div>
    <div class="stat"><b>100%</b><span data-i18n="stat_simple">Simple</span><small data-i18n="stat_simple_s">Add data. Get inventory.</small></div>
  </section>

  <main id="main">
    <section class="problem">
      <p class="kicker" style="justify-content:center" data-i18n="prob_k">The Problem</p>
      <h2 data-i18n="prob_h">Every truck operator knows the drill.</h2>
      <p data-i18n="prob_p1">End of the night. Generator still running. Count the cooler by flashlight. Guess the freezer. Scribble numbers on a ticket pad. Walk to the laptop in the cab. Type it into a spreadsheet someone made in 2019. Try to reconcile against last night’s Square or Toast export. Watch it never add up. Text the prep cook tomorrow’s load list. Repeat.</p>
      <p data-i18n="prob_p2">Brick-and-mortar restaurants have been sold $249-a-month inventory platforms and invoice scanners built for four walls. Trucks get the leftover: a clipboard, a group chat, and a hope that the ice cream doesn’t thaw before Saturday’s festival.</p>
      <p class="punch" data-i18n="prob_punch">AI changed everything. Now we can build this program for free. So we did.</p>
      <p class="kicker" style="justify-content:center;margin-top:2rem" data-i18n="prob_time">Get your time back</p>
    </section>

    <section class="workshop">
      <div class="wrap">
        <p class="kicker" data-i18n="work_k">The Workshop</p>
        <h2 class="display" data-i18n="work_h">Precision instruments for the rolling craft.</h2>
        <p class="lede" data-i18n="work_lede">One free program. The full workflow lives inside it — Home base, inventory sheets, reports, on the truck, all inputs, menu costing, stops and load lists.</p>
        <div class="instruments">
          <div class="instrument"><span class="num">01</span><h3 data-i18n="inst1_h">Smart inventory sheets</h3><p data-i18n="inst1_p">Count sheet, variance, order list, and product master — cooler, freezer, dry, prep — with PAR, pack size, vendor, and Spanish names.</p></div>
          <div class="instrument"><span class="num">02</span><h3 data-i18n="inst2_h">Variance vs. POS sales</h3><p data-i18n="inst2_p">What you should have used from Square, Toast, Clover, or any CSV, against what the counts say you used.</p></div>
          <div class="instrument"><span class="num">03</span><h3 data-i18n="inst3_h">Optional invoice photos</h3><p data-i18n="inst3_p">Type invoice lines yourself — or connect your own AI key to read paper invoice photos and PDFs. Off by default.</p></div>
          <div class="instrument"><span class="num">04</span><h3 data-i18n="inst4_h">380-product starter list</h3><p data-i18n="inst4_p">Common food-truck products with units and pack sizes. No prices stuffed in — you enter what you actually pay.</p></div>
        </div>
        <p style="margin-top:1rem"><a class="btn btn-gold" href="{r}download/" data-i18n="cta_app">Download Program</a></p>
        <p style="margin-top:1.2rem;color:var(--muted);font-size:.95rem" data-i18n-html="work_track">Tracking one part of the truck? <a href="{r}truck-inventory/">Truck &amp; cooler inventory</a> · <a href="{r}prep-inventory/">Prep inventory</a></p>
      </div>
    </section>

    <section class="quote-band">
      <blockquote data-i18n="quote">“If you help enough people get what they need, the universe will provide what you need.”</blockquote>
      <cite data-i18n="quote_cite">— The philosophy behind Open Source Barware, and this sister program</cite>
      <p class="kicker" style="justify-content:center;margin-top:2.4rem" data-i18n="start_k">Get Started</p>
      <h2 class="display" data-i18n="start_h">Open the program. Start tonight.</h2>
      <p class="lede" style="margin:0 auto 0;text-align:center;text-shadow:none;color:var(--muted)" data-i18n="start_lede">No signup. No email capture. No sales pitch. Download the program and get to work — or play in The Lot first.</p>
      <div class="cta-row">
        <a class="btn btn-gold" href="{r}download/" data-i18n="cta_app">Download Program</a>
        <a class="btn btn-teal" href="{r}inventory/dashboard/" data-i18n="cta_demo">Live Demo</a>
        <a class="btn btn-teal" href="{r}resources/" data-i18n="cta_res">Explore community resources</a>
      </div>
    </section>
  </main>'''
    write("index.html", shell(0, "Open Source Food Truckin' — Free Food Truck Inventory Built by Operators",
          "Free, open-source food-truck inventory that runs on your own laptop. Counts by zone, POS import, plate costing, load lists — no subscription, no account, no cloud lock-in.",
          "home", body, title_key="title_home"))


STEPS = [
    ("01", "Install It and Bookmark It",
     "Download the package and unzip it. Run the installer (Install.command on Mac, Install.bat on Windows, or python server.py). It opens one browser window at http://127.0.0.1:5053/. Bookmark that window — that bookmark is the software. Everything you build lives inside that one page.",
     "One install, one bookmark. Come back to the same place every night. Want to count from a phone? Start it with --lan on the truck’s Wi-Fi and open the address it prints."),
    ("02", "Meet the Guided Walkthrough",
     "The first time it opens, you land on the guided walkthrough — the caterpillar. Welcome, optional AI (off by default), or “Load sample taco truck” if you just want to look around. No account, no cloud, no AI required. It walks you through mapping the whole truck one calm step at a time.",
     "This is the caterpillar stage: patient, offline, focused on getting your truck understood. Later it becomes the butterfly — Home base with the full industrial toolkit."),
    ("03", "Name Your Truck",
     "Step 1 is Your truck: the name on the wrap, weekly / every two weeks / monthly cycle, units. If you run more than one truck later, you add them in Settings. For the first build you name this one plainly.",
     "The name shows on Home base and on printed load lists. You can rename it anytime."),
    ("04", "Lay Out the Sections",
     "Name the physical places you walk: cooler, freezer, dry, prep — plus extras you turn on (window, commissary, outside, line / make table, lowboy, cab). Two coolers in the truck means two sections in the system. This is the frame you pour everything else into.",
     "Count the rooms in the rolling kitchen, then name them. Real shelf names come after the first map."),
    ("05", "Walk Each Section and Say It Out Loud",
     "Stand in the truck and vocalize it the way you already walk it. Go section by section, shelf by shelf — say the location, then name what’s in it. Move the same route every time so the map matches the real box. Speak English, Spanish, or mix them. Typing always works if the generator is too loud for a mic.",
     "This first voice note is the seed. Everything the program builds grows out of this walk, so speak it in order.",
     True),
    ("06", "Bring the Invoices",
     "The walk also takes product invoices — PDF, photos, CSV, or typed lines. You do not have to finish invoices to continue; they merge with what you said on the next step. Photos of invoices need optional AI if you want them read; CSV and typed lines work locally.",
     "Invoice quantities in setup are not added to stock. The walk count is what’s on the truck. Receiving still happens later in All inputs."),
    ("07", "Reconcile — Spoken × Invoices",
     "Step 4 shows “Here’s what I registered” per section. Tap any row to edit name, section, count, unit, pack, cost, vendor. Merge, link or unlink an invoice line, add a missing product, or park something as commissary-only / not stocked / skip. Nothing saves until Confirm & continue.",
     "The program does the heavy lifting. The operator approves the truth."),
    ("08", "Review the First Map, Then Count",
     "Approve the map: rename, move, set PAR. Then the first live count, section by section — voice fills the numbers, you save. After that, Home base opens as the butterfly: metrics, jump-to cards, low-PAR alerts.",
     "Printable count sheets and the on-phone stepper follow the same walking order you spoke the first time."),
    ("09", "Lock It — Optional PIN",
     "Create an owner PIN if you want, or leave it open. People & access (admin / manager / crew, per-permission, truck lock) stay available in Settings. Crew can be limited to daily end-of-shift counts.",
     "Open until you create the first admin. Same pattern as Open Source Barware."),
    ("10", "You Have Full Control — and It's Open Source",
     "Inside Home base: inventory sheets, reports, on the truck, all inputs, menu & costing, stops & load lists, settings. Daily / weekly / monthly count types. Multiple trucks and transfers. Backups, restore, reset. Because it is open source, nothing is locked away.",
     "Change the sections, restructure the layout, own the whole thing. Complete access, no lock-in."),
]


def process():
    r = rel(1)
    steps_html = []
    for s in STEPS:
        n = s[0]
        extra = ""
        if len(s) > 4 and s[4]:
            extra = '''<div class="walk-ex"><span class="lbl" data-i18n="walk_lbl">How to say the walk — English or Spanish</span>
Cooler. Shelf one: 40 lb ice, horchata 5 gal, queso 4 lb<br>
Cuarto frío. Charola uno: hielo 40 lb, horchata 5 gal…<br>
Freezer: carne asada 10 lb, french fries one case<br>
Dry: tortillas 4 packs, salsa 12 oz cans<br>
Prep: pico, cilantro, limes, onions<br>
Window / make table: only what is on the line tonight</div>'''
        steps_html.append(f'''<article class="step"><span class="num">{n}</span><div>
          <h3 data-i18n="s{n}_h">{s[1]}</h3>
          <p data-i18n="s{n}_p">{s[2]}</p>
          <p class="note" data-i18n="s{n}_n">{s[3]}</p>
          {extra}
        </div></article>''')
    body = hero(r, "hero-process", "Inside a food truck at night, cooler open, a silhouette walking a count with a phone.",
                "The Kitchen Table Version",
                "One local program.<br>Simple to start. Industrial strength when needed.",
                "Install it, bookmark one page in the browser, and that page becomes your whole system. Starts as an easy guided walkthrough — walk or talk your inventory in (English, Spanish, or mixed). Grows into the most complete free food-truck inventory program we know how to ship.",
                kicker_k="proc_kicker", h1_k="proc_h1", lede_k="proc_lede") + f'''
  <main id="main">
    <section class="copy band-warm">
      <div class="wrap">
        <p class="kicker" data-i18n="proc_big_k">The Big Picture</p>
        <h2 class="display" data-i18n="proc_big_h">What you are actually using</h2>
        <p class="lede" data-i18n="proc_big_lede">One calm control panel that runs on your laptop. Starts simple for the average operator — walk or talk the truck in, easy and fast. Grows into the industrial-strength toolkit: voice, count types, POS, recipes, load lists, multi-truck, crew PINs.</p>
        <div class="blocks-3" style="margin-top:2rem">
          <article class="panel"><p class="tag" data-i18n="proc_tag_one">One Program</p><h3 data-i18n="proc_one_h">One browser-side program</h3><p data-i18n="proc_one_p">You open one place. It starts simple (walk or talk inventory in, English, Spanish, or mixed), then grows into the full system — zones, scales of pack size, and pinpoint counts built in.</p></article>
          <article class="panel"><p class="tag" data-i18n="proc_tag_change">The Changeover</p><h3 data-i18n="proc_change_h">Caterpillar to butterfly</h3><p data-i18n="proc_change_p">At first it feels like a guided checklist. After the truck is mapped, the same page opens into Home base: sheets, reports, inputs, menu, stops, settings.</p></article>
          <article class="panel"><p class="tag" data-i18n="proc_tag_spine">The Spine</p><h3 data-i18n="proc_spine_h">Your voice in, a built map out</h3><p data-i18n="proc_spine_p">You talk (or walk) the truck the way you already walk it. A parser on your laptop — no internet, no AI, no account — reads your words, lays out the map, and does the math.</p></article>
        </div>
        <div class="blocks-2" style="margin-top:1.4rem">
          <div class="panel">
            <p class="tag" data-i18n="proc_inside_k">Inside the Home Base</p>
            <div class="home-mods">
              <div><h4 data-i18n="proc_mod_home_h">Home base</h4><p data-i18n="proc_mod_home_p">Last count, current cycle, what’s below PAR, jump-to cards, sample taco truck.</p></div>
              <div><h4 data-i18n="proc_mod_sheets_h">Inventory sheets</h4><p data-i18n="proc_mod_sheets_p">Count sheet, variance, order list, product master — the workbook view.</p></div>
              <div><h4 data-i18n="proc_mod_truck_h">On the truck</h4><p data-i18n="proc_mod_truck_p">Zones, extra trucks, transfers, crew board. Cooler · freezer · dry · prep.</p></div>
              <div><h4 data-i18n="proc_mod_in_h">All inputs</h4><p data-i18n="proc_mod_in_p">POS sales, invoices &amp; receiving, input log. Square / Toast / Clover / any CSV.</p></div>
              <div><h4 data-i18n="proc_mod_menu_h">Menu &amp; costing</h4><p data-i18n="proc_mod_menu_p">Plate cost, food-cost %, margin. Recipe qty in the product’s own unit.</p></div>
              <div><h4 data-i18n="proc_mod_stops_h">Stops &amp; load lists</h4><p data-i18n="proc_mod_stops_p">Lunch lot, brewery, festival — PAR per stop type, printable load list for tomorrow.</p></div>
            </div>
          </div>
          <aside class="panel">
            <p class="tag" data-i18n="proc_gates_k">Checks and Gates</p>
            <h3 data-i18n="proc_gates_h">The system slows down where it should — then unlocks full power.</h3>
            <ul class="gates">
              <li><b>01</b> <span data-i18n="proc_g1">Everything runs on your laptop — no account, no cloud.</span></li>
              <li><b>02</b> <span data-i18n="proc_g2">Name every cooler, freezer, dry, prep, window, commissary space.</span></li>
              <li><b>03</b> <span data-i18n="proc_g3">Ask about unclear brands, pack sizes, duplicates, missing shelves.</span></li>
              <li><b>04</b> <span data-i18n="proc_g4">Review the first map before the first real inventory count.</span></li>
              <li><b>05</b> <span data-i18n="proc_g5">Match the weekly count, purchases, and POS report to the same date window.</span></li>
              <li><b>06</b> <span data-i18n="proc_g6">Add AI later — and only if you want invoice photos read for you.</span></li>
              <li><b>07</b> <span data-i18n="proc_g7">Layer in daily counts, barcode, POs, multi-truck, crew PINs as you grow.</span></li>
            </ul>
          </aside>
        </div>
      </div>
    </section>

    <section class="copy">
      <div class="wrap">
        <p class="kicker" data-i18n="proc_need_k">Before Setup</p>
        <h2 class="display" data-i18n="proc_need_h">What you need at the table</h2>
        <p class="lede" data-i18n="proc_need_lede">Nothing exotic. Just the pieces a real truck already has, gathered into one guided flow.</p>
        <div class="need-grid" style="margin-top:1.6rem">
          <article class="need-card"><strong data-i18n="proc_need1_h">A laptop</strong><p data-i18n="proc_need1_p">Python 3.10+ and a browser. Chrome, Edge, or Safari for voice. Typing works everywhere.</p></article>
          <article class="need-card"><strong data-i18n="proc_need2_h">A phone</strong><p data-i18n="proc_need2_p">Voice notes in English or Spanish — cooler, freezer, dry, prep — naming product as you go. Or count on the phone over Wi-Fi.</p></article>
          <article class="need-card"><strong data-i18n="proc_need3_h">A first truck walk</strong><p data-i18n="proc_need3_p">That one saved walk is the seed the built-in parser reads to build your whole truck.</p></article>
          <article class="need-card"><strong data-i18n="proc_need4_h">Invoices + POS</strong><p data-i18n="proc_need4_p">Type or paste invoice lines and pull the Square / Toast / Clover / CSV export once the first cycle is ready.</p></article>
          <article class="need-card"><strong data-i18n="proc_need5_h">A careful review</strong><p data-i18n="proc_need5_p">The first map gets checked and approved before the program becomes your home base.</p></article>
          <article class="need-card"><strong data-i18n="proc_need6_h">Optional: your own AI</strong><p data-i18n="proc_need6_p">Not required for anything. Add it only if you want invoice photos read instead of typing.</p></article>
        </div>
      </div>
    </section>

    <section class="copy band-warm">
      <div class="wrap prose">
        <p class="kicker" data-i18n="proc_first_k">First Setup</p>
        <h2 class="display" data-i18n="proc_first_h">How it goes from first walk to home base</h2>
        <p data-i18n="proc_first_p">The first setup is meant to feel like a guided conversation. Do one thing, check it, then move to the next. Starts simple — the full toolkit is already inside when you need it.</p>
        {''.join(steps_html)}
      </div>
    </section>

    <section class="copy">
      <div class="wrap">
        <p class="kicker" data-i18n="proc_ai_k">Optional AI</p>
        <h2 class="display" data-i18n="proc_ai_h">The whole program works without it.</h2>
        <p class="lede" data-i18n="proc_ai_lede">Connect ChatGPT, Claude, Grok, local Ollama, or any OpenAI-compatible endpoint only if you want invoice photos and PDFs read. Your key stays in data/config.json on this computer and is left out of backups. Skip it now, add it later in Settings, or never touch it.</p>
        <div class="rhythm" style="margin-top:2rem">
          <article class="panel"><p class="tag" data-i18n="proc_count_k">Count</p><h3 data-i18n="proc_count_h">Daily, weekly, monthly</h3><p data-i18n="proc_count_p">Daily end-of-shift is a partial watch list. Weekly is the full truck. Monthly adds an extras checklist. Partials never zero what they skip.</p></article>
          <article class="panel"><p class="tag" data-i18n="proc_add_k">Add</p><h3 data-i18n="proc_add_h">POS, invoices, notes</h3><p data-i18n="proc_add_p">Bring in sales, delivery notes, and manager context for the same period. Barcode and receiving built in. Optional invoice photos if you connect AI.</p></article>
          <article class="panel"><p class="tag" data-i18n="proc_read_k">Read</p><h3 data-i18n="proc_read_h">Home base story</h3><p data-i18n="proc_read_p">Usage, spend, variance, food cost %, what to buy grouped by vendor, tomorrow’s load list.</p></article>
        </div>
        <div class="cta-row">
          <a class="btn btn-gold" href="{r}download/" data-i18n="cta_app">Download Program</a>
          <a class="btn btn-teal" href="{r}inventory/dashboard/" data-i18n="cta_lot_play">Play in The Lot</a>
        </div>
      </div>
    </section>
  </main>'''
    write("the-process/index.html", shell(1, "How Free Food Truck Inventory Works (Voice Walk → Count) | Open Source Food Truckin'",
          "How free food-truck inventory software works: voice walk, zones, variance, POS, load lists — local-first, no subscription. Full Open Source Food Truckin' process.",
          "process", body, title_key="title_process"))


def about():
    r = rel(1)
    body = hero(r, "hero-about", "A teal food truck on wet cobblestones at night, parking brake in the foreground.",
                "The Truck Stop",
                "Built on the asphalt.",
                "Same kitchen that made Open Source Barware. This one just has a parking brake. No founder-chef myth. Operators, a generator, and a program that stays free.",
                kicker_k="about_kicker", h1_k="about_h1", lede_k="about_lede") + f'''
  <main id="main">
    <section class="copy">
      <div class="wrap prose">
        <p data-i18n="about_p1">Open Source Food Truckin' exists because the bar program could not pretend a rolling kitchen is a back bar with wheels. Coolers thaw. Festivals change the PAR. The POS is a tablet on the window ledge. The count happens between service and the drive back to the commissary.</p>
        <p data-i18n="about_p2">We built the sister program in the same house: local-first, GPLv3, English and Spanish, no account, no subscription. Version 1.3-beta is the public toolkit — voice walk, invoice reconcile, daily/weekly/monthly counts, Square/Toast/Clover CSV, plate costing, stop types, load lists, multi-truck, crew PINs.</p>
        <p data-i18n-html="about_p3">Find Food Truckin' next to the bar tools at <a href="https://opensourcebarware.com/">OpenSourceBarware.com</a>. The family also includes <a href="https://intelligenthospitalitysystems.com/">Intelligent Hospitality Systems</a> and <a href="https://www.reservationrelief.com/">Reservation Relief</a>.</p>
        <p data-i18n="about_p4">A Richard B. Jamison project. Free forever.</p>
        <div class="cta-row" style="justify-content:flex-start">
          <a class="btn btn-gold" href="{r}manifesto/" data-i18n="cta_manifesto">Read the manifesto</a>
          <a class="btn btn-teal" href="{r}the-process/" data-i18n="cta_menu">Learn this system</a>
        </div>
      </div>
    </section>
  </main>'''
    write("about/index.html", shell(1, "About Open Source Food Truckin' — Built for Rolling Kitchens",
          "Why we built free open-source food-truck inventory from real end-of-night count pressure — and released it under GPLv3.",
          "about", body, title_key="title_about"))


def resources():
    r = rel(1)
    cards = [
        ("National Food Truck Association", "https://www.nationalfoodtrucks.org/", "Association of food truck associations. Law, location, event management, and operator tutorials — the connective tissue between vendors and regional groups."),
        ("NSFVA", "https://www.nsfva.org/", "National Association for Street Food Vendors. Mentorship, live classes, and a community built for trucks, trailers, carts, and tents."),
        ("Off the Grid", "https://offthegrid.com/", "Bay Area street-food markets and creator support. Weekly lots, catering, and a bench of operators who already live this schedule."),
        ("Street Vendor Project", "https://streetvendor.org/", "Advocacy for street vendors. Policy, legal support, and a reminder that the lot is a workplace."),
        ("Restaurant Workers' Community Foundation", "https://www.restaurantworkerscf.org/", "Advocacy and crisis relief for restaurant and hospitality workers — including the people on the line in a truck."),
        ("ServSafe / National Restaurant Association", "https://www.servsafe.com/", "Food-handler and manager certification most health departments expect. Learn it once, carry it every stop."),
        ("SCORE", "https://www.score.org/", "Free mentoring for small businesses. Useful when the truck is also the corporation."),
        ("Open Source Barware", "https://opensourcebarware.com/", "Sister program. Free bar inventory from the same house — voice walk, variance, POS, no subscription."),
    ]
    grid = "".join(
        f'<article class="panel"><p class="tag" data-i18n="res_tag">Community</p><h3><a href="{u}" rel="noopener">{t}</a></h3><p data-i18n="res_c{i}">{d}</p></article>'
        for i, (t, u, d) in enumerate(cards, 1)
    )
    body = hero(r, "hero-resources", "A night market of food trucks, crews talking between service windows.",
                "The Community",
                "People first.<br>Program second.",
                "The organizations, educators, and support networks that make this industry worth fighting for. All free. All worth your time.",
                kicker_k="res_kicker", h1_k="res_h1", lede_k="res_lede") + f'''
  <main id="main">
    <section class="copy">
      <div class="wrap">
        <p class="kicker" data-i18n="res_org_k">Industry Organizations</p>
        <h2 class="display" data-i18n="res_org_h">Your guild. Your people.</h2>
        <p class="lede" data-i18n="res_org_lede">National and local groups advocating for mobile vendors, providing education, and building the professional network you deserve.</p>
        <div class="blocks-2" style="margin-top:1.6rem">{grid}</div>
      </div>
    </section>
    <section class="copy band-warm">
      <div class="wrap">
        <p class="kicker" data-i18n="res_in_k">Inside this program</p>
        <h2 class="display" data-i18n="res_in_h">Learn without paying.</h2>
        <div class="blocks-3" style="margin-top:1.4rem">
          <article class="panel"><h3><a href="{r}the-process/" data-i18n="nav_process">The Process</a></h3><p data-i18n="res_in1">Install → walk → reconcile → home base. The kitchen-table version of the whole system.</p></article>
          <article class="panel"><h3><a href="{r}downloads/" data-i18n="nav_guide">Program Guide</a></h3><p data-i18n="res_in2">What each instrument is, what it looks like, and how it fits the weekly rhythm.</p></article>
          <article class="panel"><h3><a href="{r}blog/" data-i18n="nav_blog">Operator notes</a></h3><p data-i18n="res_in3">Spreadsheets, POS files, load lists, food cost — practical writing, no upsell.</p></article>
        </div>
      </div>
    </section>
  </main>'''
    write("resources/index.html", shell(1, "Free Food Truck Resources & Free Inventory System — Open Source Food Truckin'",
          "Free food-truck operator resources and the open source inventory program. Associations, education, and the local-first toolkit.",
          "resources", body, title_key="title_res"))


def download():
    r = rel(1)
    body = hero(r, "hero-download", "A laptop on a stainless prep table inside a food truck at night, receipts and a load list beside it.",
                "Free program",
                "Download<br>the free program.",
                "Free, local food-truck inventory on your laptop. No subscription. No cloud tax. Version 1.3-beta is live — voice walk, Spanish, POS, plate costing, load lists, and the full toolkit.",
                extra='''<ul class="trust">
        <li data-i18n="dl_t1">v1.3-beta live</li>
        <li data-i18n="dl_t2">GPLv3 · free forever</li>
        <li data-i18n="dl_t3">Mac, Windows, Linux · Python 3.10+</li>
        <li data-i18n="dl_t4">Local-first · no account to run</li>
        <li><a href="../changelog/" data-i18n="dl_t5">Release notes</a></li>
        <li><a href="#program-downloads" data-i18n="dl_t6">Skip to installer ↓</a></li>
      </ul>''',
                kicker_k="dl_kicker", h1_k="dl_h1", lede_k="dl_lede") + f'''
  <main id="main">
    <section class="copy dl-zone" id="program-downloads">
      <div class="wrap dl-grid">
        <div class="dl-gate" id="get-program">
          <p class="kicker" data-i18n="dl_inst_k">Get the program</p>
          <h2 class="display" data-i18n="dl_inst_h">Drop your email. Grab your truck’s inventory.</h2>
          <p class="dl-why" data-i18n="dl_inst_p">Your email unlocks the download. We only write when a new build or a fix ships — no marketing, no selling your address.</p>
          <form class="dl-form" id="dl-form" novalidate>
            <label class="dl-label" for="dl-email" data-i18n="dl_email_l">Email</label>
            <input class="dl-input" id="dl-email" name="email" type="email" required autocomplete="email" inputmode="email" spellcheck="false" placeholder="you@yourtruck.com" />
            <input class="dl-hp" type="text" name="website" tabindex="-1" autocomplete="off" aria-hidden="true" />
            <div class="dl-os">
              <button class="btn btn-gold" type="submit" name="os" value="mac"><span class="dl-os-k" data-i18n="dl_mac_k">For Mac</span><span data-i18n="dl_mac">Download for Mac</span></button>
              <button class="btn btn-gold" type="submit" name="os" value="win"><span class="dl-os-k" data-i18n="dl_win_k">For Windows</span><span data-i18n="dl_win">Download for Windows</span></button>
            </div>
            <p class="dl-msg" id="dl-msg" role="status" aria-live="polite"></p>
          </form>
          <p class="fineprint"><span data-i18n="dl_fine">v1.3.0-beta · about 680 KB · GPLv3, source included · Linux: use the Mac zip and run ./install.sh · see</span> <a href="{r}open-source-compliance/" data-i18n="nav_license">license and source</a>.</p>
        </div>
        <figure class="marquee" aria-labelledby="dl-count-cap">
          <p class="marquee-top" data-i18n="dl_count_k">Trucks rolling</p>
          <p class="marquee-board" id="dl-count" aria-live="polite" aria-atomic="true"><span>–</span><span>–</span><span>–</span><span>–</span><span>–</span><span>–</span></p>
          <figcaption class="marquee-cap" id="dl-count-cap" data-i18n="dl_count_cap">downloads served — free, every one</figcaption>
        </figure>
      </div>
    </section>
    <section class="copy dl-howto" id="install-steps">
      <div class="wrap">
        <p class="kicker" data-i18n="dl_how_k">After it downloads</p>
        <h2 class="display" data-i18n="dl_how_h">Two minutes to your first count.</h2>
        <div class="dl-steps">
          <article class="panel" data-os="mac">
            <p class="tag" data-i18n="dl_mac_k">For Mac</p>
            <ol>
              <li data-i18n="dl_m1">Open the zip in Downloads. You get a folder.</li>
              <li data-i18n-html="dl_m2">Double-click <b>Install.command</b>.</li>
              <li data-i18n-html="dl_m3">Mac says it can’t verify it? Open <b>System Settings › Privacy &amp; Security</b>, click <b>Open Anyway</b>, then double-click again. <b>START-HERE-MAC.html</b> in the folder shows it step by step.</li>
              <li data-i18n="dl_m4">Asked to install developer tools? Click Install, then run Install.command again.</li>
              <li data-i18n-html="dl_m5">Your browser opens the program. Bookmark it — <b>that bookmark is the software</b>.</li>
            </ol>
          </article>
          <article class="panel" data-os="win">
            <p class="tag" data-i18n="dl_win_k">For Windows</p>
            <ol>
              <li data-i18n-html="dl_w1">Right-click the zip › <b>Extract All</b>. Open the folder.</li>
              <li data-i18n-html="dl_w2">Double-click <b>Install.bat</b>. “Windows protected your PC”? <b>More info › Run anyway</b>.</li>
              <li data-i18n-html="dl_w3">No Python yet? It opens python.org. Install it with <b>Add python.exe to PATH</b> checked, then run Install.bat again.</li>
              <li data-i18n-html="dl_w4">Your browser opens the program. Bookmark it — <b>that bookmark is the software</b>.</li>
            </ol>
          </article>
        </div>
        <p class="dl-after" data-i18n="dl_after">It starts by itself when the computer turns on, works offline, and keeps every count on your machine. Updating later: run the new installer — your data stays.</p>
        <div class="actions">
          <a class="btn btn-teal" href="{r}inventory/dashboard/" data-i18n="dl_try">Try it in The Lot first</a>
        </div>
      </div>
    </section>
    <section class="copy band-warm">
      <div class="wrap" style="text-align:center">
        <p data-i18n="dl_guide_ask">Want to understand what’s inside before you install?</p>
        <a class="btn btn-teal" href="{r}downloads/" data-i18n="cta_guide">Read the program guide</a>
      </div>
    </section>
  </main>
  <script src="{r}js/download.js?v=1" defer></script>'''
    write("download/index.html", shell(1, "Download Free Food Truck Inventory Program v1.3-beta | Open Source Food Truckin'",
          "Download Open Source Food Truckin' free for Mac or Windows. Local counts, Spanish-ready notes, POS inputs, load lists. No account needed to run it.",
          "download", body, title_key="title_dl"))


GUIDES = [
    ("01", "Inventory sheets", "Count · variance · order list · product master",
     "The workbook view for every product, zone, PAR, pack, vendor, and Spanish name.",
     "Inside the program this is Inventory sheets. Setup builds the first version from the approved truck map, then each cycle updates it with counts, invoices, and POS exports.",
     ["Tabs: Count sheet, Variance, Order list, Product master", "Rows by physical section: cooler, freezer, dry, prep, window, commissary", "Columns for product, unit, pack, PAR, opening, purchases, closing, cost, variance"],
     ["Walk the truck by voice during setup.", "The system turns that walk into the first map.", "After you audit and approve it, the sheets become the weekly source of truth."]),
    ("02", "Count types", "Daily · weekly · monthly",
     "Daily end-of-shift is a partial watch list. Weekly is the full truck. Monthly adds an extras checklist.",
     "You pick the type and business date when you start a count. Crew logins can be limited to daily. A partial count only updates what it covers — everything else keeps its last count.",
     ["Watch list by section, category, or picked products", "History shows type, scope, and who counted", "Weekly sales variance skips partials on purpose"],
     ["Set count types in Settings.", "Start a count, walk the scope, complete it.", "Read variance on the matching window."]),
    ("03", "Voice walk & count sheet", "Mic or type · big −/+ steppers",
     "Speak the shelf in English or Spanish, check what it heard, save. On the phone, the count sheet is large taps, one-hand friendly.",
     "The parser lives on your laptop. Firefox has no speech recognition — the typed box always works. Barcode scan needs Chrome.",
     ["How-to-speak examples on the walk screen", "Matched / which one? / not found review", "Sticky Start / Complete bar on phones"],
     ["Walk each section in order.", "Confirm heard lines.", "Save; jump to variance."]),
    ("04", "POS sales import", "Square · Toast · Clover · any CSV",
     "Upload a sales export. Format auto-detect, preview, then import. Generic column mapping for everything else.",
     "Live POS APIs are documented stubs only. CSV column names come from public vendor docs and should be tested against your real file. Variance uses date-only matching.",
     ["Preview before import", "Voids skipped on Toast where documented", "Clover exports with no dates: pick the sales date on import"],
     ["Export item sales from the POS.", "Preview the mapping.", "Import; theoretical usage = qty sold × recipe qty."]),
    ("05", "Invoices, receiving, optional photos", "Typed · CSV · PDF · photo",
     "Log deliveries, match products, update cost. Snap invoice photos. Optional AI reading uses your own key and is off by default.",
     "This is the only place AI ever enters the program. Skip it and type or paste — the local parser handles that on its own.",
     ["Photo button labeled as needing AI", "Type-or-paste sitting beside it as the default", "Confirm line items before they touch the numbers"],
     ["Optional: add your own AI key in Settings.", "Snap the Sysco / US Foods / local produce invoice.", "Confirm; without a key, type or paste."]),
    ("06", "Menu, stops, load lists", "Plate cost · PAR per stop · print tomorrow",
     "Cost every plate. Set pars for lunch lots, breweries, festivals. Print a load list before you roll.",
     "Recipe qty must be in the product’s own unit (e.g. 0.04 pack of tortillas per taco). No unit conversion yet. Load list assumes on-hand is what’s on the truck.",
     ["Food-cost % and margin per menu item", "Stop types with their own PAR", "Printable load list grouped for the next stop"],
     ["Build recipes from the catalog.", "Name the stop types you actually work.", "Print the list the night before."]),
]


def downloads_guide():
    r = rel(1)
    blocks = []
    for g in GUIDES:
        n = g[0]
        looks = "".join(f'<li data-i18n="g{n}_l{i}">{x}</li>' for i, x in enumerate(g[5], 1))
        proc = "".join(f'<li data-i18n="g{n}_pr{i}">{x}</li>' for i, x in enumerate(g[6], 1))
        blocks.append(f'''<article class="guide" id="g-{n}">
          <p class="fmt" data-i18n="g{n}_fmt">{n} · {g[2]}</p>
          <h2 data-i18n="g{n}_h">{g[1]}</h2>
          <p data-i18n="g{n}_p1">{g[3]}</p>
          <p data-i18n="g{n}_p2">{g[4]}</p>
          <div class="blocks-2">
            <div><p class="tag" data-i18n="looks">Looks like</p><ul>{looks}</ul></div>
            <div><p class="tag" data-i18n="process_lbl">Process</p><ul>{proc}</ul></div>
          </div>
        </article>''')
    body = hero(r, "hero-download", "Laptop and load list on a food-truck prep table.",
                "Program Guide",
                "How each instrument fits.",
                "Learn how each Open Source Food Truckin' feature lives inside the local program — the same teaching format as Open Source Barware’s program guide.",
                kicker_k="guide_kicker", h1_k="guide_h1", lede_k="guide_lede") + f'''
  <main id="main">
    <section class="copy">
      <div class="wrap">{''.join(blocks)}</div>
    </section>
    <section class="copy band-warm">
      <div class="wrap" style="text-align:center">
        <a class="btn btn-gold" href="{r}download/" data-i18n="cta_app">Download Program</a>
        <a class="btn btn-teal" href="{r}the-process/" data-i18n="cta_menu">Read The Process</a>
      </div>
    </section>
  </main>'''
    write("downloads/index.html", shell(1, "Program Guide — Open Source Food Truckin'",
          "Learn how each Open Source Food Truckin' inventory feature fits inside the local food-truck inventory program.",
          "downloads", body, title_key="title_guide"))


def manifesto():
    r = rel(1)
    body = f'''  <section class="copy" style="padding-top:4rem">
    <div class="wrap" style="text-align:center">
      <p class="kicker" style="justify-content:center" data-i18n="man_k">The Manifesto</p>
      <h1 class="display" data-i18n-html="man_h1">Counting the cooler shouldn’t<br>cost you a festival’s tips.</h1>
      <p class="lede" style="margin:0 auto;text-shadow:none" data-i18n="man_lede">This is the honest version of why Open Source Food Truckin' exists, who it’s for, and why the whole program — cooler, freezer, prep, and load list included — is free and stays free.</p>
    </div>
  </section>
  <main id="main">
    <section class="copy">
      <div class="wrap">
        <p class="kicker" data-i18n="man_bill_k">The Bill Nobody Talks About</p>
        <h2 class="display" data-i18n="man_bill_h">Inventory has been a paid problem for decades.</h2>
        <p class="lede" data-i18n="man_bill_lede">Somewhere along the way, an industry decided that counting your own product was worth charging you for. Trucks inherited restaurant invoices.</p>
        <div class="bill-grid" style="margin-top:1.6rem">
          <article class="panel"><p class="tag" data-i18n="man_plat_k">The Platform</p><p class="amount">$249+ / mo</p><p data-i18n="man_plat_p">Restaurant inventory SaaS (MarketMan Starter published around $249/mo in 2026) built for four walls, billed every month, forever.</p></article>
          <article class="panel"><p class="tag" data-i18n="man_pos_k">The POS add-on</p><p class="amount" data-i18n="man_pos_amt">Quote</p><p data-i18n="man_pos_p">Toast / xtraCHEF-class invoice tools that want your POS first and a sales call second. Trucks already pay for the tablet.</p></article>
          <article class="panel"><p class="tag" data-i18n="man_sheet_k">The Spreadsheet</p><p class="amount" data-i18n="man_sheet_amt">$0, until it isn’t</p><p data-i18n="man_sheet_p">A sheet that worked for twelve SKUs and broke the week you added a second stop type.</p></article>
        </div>
      </div>
    </section>
    <section class="copy band-warm">
      <div class="wrap prose">
        <h2 class="display" data-i18n="man_keep_h">Promises we actually keep</h2>
        <ul>
          <li data-i18n="man_li1">No investors to answer to, so no pressure to add a paywall later.</li>
          <li data-i18n="man_li2">No email capture on the download — the program does not need your address to work.</li>
          <li data-i18n="man_li3">No seat limits, no location tax, no “upgrade to Pro” hiding a count type you already need.</li>
          <li data-i18n="man_li4">Open source, so if we ever drifted from this, anyone could see it in the code and fork it.</li>
        </ul>
        <p data-i18n="man_close">A Richard B. Jamison project. Sister to Open Source Barware. Free forever.</p>
        <a class="btn btn-gold" href="{r}download/" data-i18n="cta_app">Download Program</a>
      </div>
    </section>
  </main>'''
    write("manifesto/index.html", shell(1, "The Open Source Food Truck Manifesto — Free Inventory System",
          "Why the best free food-truck inventory system exists: no subscriptions, full data ownership, built by operators tired of paying to count coolers.",
          "manifesto", body, title_key="title_man"))


def changelog():
    r = rel(1)
    body = f'''  <main id="main">
    <section class="copy">
      <div class="wrap prose">
        <p class="kicker" data-i18n="ch_k">Changelog</p>
        <h1 class="display" data-i18n-html="ch_h1"><span style="color:var(--gold)">v1.3-beta</span> public toolkit</h1>
        <p data-i18n="ch_p">Released October 24, 2026 · Version 1.3.0-beta · GPL-3.0-or-later · Free forever. Local-first Python program on Mac, Windows, and Linux — no subscription, no cloud account required.</p>
        <div class="actions">
          <a class="btn btn-gold" href="{r}download/" data-i18n="cta_app">Download Program</a>
          <a class="btn btn-teal" href="{r}inventory/dashboard/" data-i18n="cta_demo">Live Demo</a>
        </div>
        <h2 data-i18n="ch_h2">Count types</h2>
        <ul>
          <li data-i18n="ch_c1">Daily end-of-shift: partial watch list (sections, categories, or picked products)</li>
          <li data-i18n="ch_c2">Weekly: the full truck</li>
          <li data-i18n="ch_c3">Monthly in-depth: full truck plus extras checklist</li>
          <li data-i18n="ch_c4">Partials never zero what they skip; weekly sales variance skips them</li>
        </ul>
        <h2 data-i18n="ch_h3">Reconcile edits</h2>
        <ul>
          <li data-i18n="ch_r1">On setup step 4, tap any row: name, section, count, unit, pack, cost, vendor, delete, merge, link/unlink invoice line, add a missing product</li>
          <li data-i18n="ch_r2">Nothing saves until Confirm &amp; continue</li>
        </ul>
        <h2 data-i18n="ch_h4">From v1.2 / v1.1 / v1.0</h2>
        <ul>
          <li data-i18n="ch_v1">Voice walk in English or Spanish; invoices into setup; “Here’s what I registered”</li>
          <li data-i18n="ch_v2">People &amp; PIN logins, 380-product starter list, POs by vendor, multi-truck, crew board</li>
          <li data-i18n="ch_v3">POS CSV (Square / Toast / Clover / generic), menu costing, stop types, load lists</li>
          <li data-i18n="ch_v4">OSB-style sidebar: Home base · Inventory sheets · Reports · On the truck · All inputs · Menu · Stops · Settings</li>
        </ul>
        <p data-i18n="ch_full">Full notes live in the download as CHANGELOG.md and PARITY.md.</p>
      </div>
    </section>
  </main>'''
    write("changelog/index.html", shell(1, "Release Notes v1.3-beta — Open Source Food Truckin' Changelog",
          "Open Source Food Truckin' v1.3-beta release notes: count types, reconcile edits, voice walk, POS import, load lists. Free open source food-truck inventory.",
          "changelog", body, title_key="title_ch"))


def simple_legal(slug, title, kicker, h1, paras, current, prefix="", title_key=""):
    r = rel(1)
    inner = "".join(
        f'<p data-i18n="{prefix}_p{i}">{p}</p>' if prefix else f"<p>{p}</p>"
        for i, p in enumerate(paras, 1)
    )
    kattr = f' data-i18n="{prefix}_k"' if prefix else ""
    hattr = f' data-i18n="{prefix}_h1"' if prefix else ""
    body = f'''  <main id="main">
    <section class="copy">
      <div class="wrap prose">
        <p class="kicker"{kattr}>{kicker}</p>
        <h1 class="display"{hattr}>{h1}</h1>
        {inner}
      </div>
    </section>
  </main>'''
    write(f"{slug}/index.html", shell(1, title, paras[0][:160], current, body, title_key=title_key))


def category(slug, title, desc, kicker, h1, lede, why, tracked, current, img="hero-process", prefix="", title_key=""):
    r = rel(1)
    if prefix:
        why_h = "".join(
            f'<article class="panel"><h3 data-i18n="{prefix}_w{i}_h">{t}</h3><p data-i18n="{prefix}_w{i}_p">{b}</p></article>'
            for i, (t, b) in enumerate(why, 1)
        )
        tr_h = "".join(
            f'<div class="instrument"><span class="num">{n}</span><h3 data-i18n="{prefix}_t{i}_h">{t}</h3><p data-i18n="{prefix}_t{i}_p">{b}</p></div>'
            for i, (n, t, b) in enumerate(tracked, 1)
        )
        body = hero(r, img, "", kicker, h1, lede, kicker_k=f"{prefix}_k", h1_k=f"{prefix}_h", lede_k=f"{prefix}_lede")
    else:
        why_h = "".join(f'<article class="panel"><h3>{t}</h3><p>{b}</p></article>' for t, b in why)
        tr_h = "".join(f'<div class="instrument"><span class="num">{n}</span><h3>{t}</h3><p>{b}</p></div>' for n, t, b in tracked)
        body = hero(r, img, "", kicker, h1, lede)
    body += f'''
  <main id="main">
    <section class="copy">
      <div class="wrap">
        <p class="kicker" data-i18n="why_k">Why this slice is different</p>
        <div class="blocks-3">{why_h}</div>
        <p class="kicker" style="margin-top:2.4rem" data-i18n="tracks_k">What the program tracks</p>
        <div class="instruments">{tr_h}</div>
        <div class="cta-row" style="justify-content:flex-start;margin-top:2rem">
          <a class="btn btn-gold" href="{r}download/" data-i18n="cta_app">Download Program</a>
          <a class="btn btn-teal" href="{r}the-process/" data-i18n="cta_process">See The Process</a>
        </div>
      </div>
    </section>
  </main>'''
    write(f"{slug}/index.html", shell(1, title, desc, current, body, title_key=title_key))


def compare():
    r = rel(1)
    rows = [
        ("hi", "Open Source Food Truckin'", "Free (GPLv3)", "Local files you control", "CSV: Square / Toast / Clover / generic", "Sales vs counts, food cost %", "Multiple trucks + transfers", "Yes — runs on your machines", "None — open source"),
        ("", "MarketMan", "Paid SaaS — Starter published ~$249/mo (2026)", "Vendor cloud", "Cloud integrations", "Restaurant inventory + purchasing", "Cloud multi-location", "Cloud-first", "Account + vendor cloud"),
        ("", "xtraCHEF (Toast)", "Quote — no public price", "Vendor cloud", "Built around Toast", "Invoice / back-office", "Plan-dependent", "Cloud", "POS + subscription"),
        ("", "Square / Toast POS inventory", "Bundled with POS plans", "Vendor cloud", "Native POS", "Item stock, not a truck walk", "POS locations", "Needs the POS", "POS account"),
        ("", "Spreadsheet", "Free", "Your file, until versions drift", "Manual paste", "Whatever you build", "Copy the file", "Yes", "You, and whoever has the sheet"),
    ]
    row_keys = [
        ["", "cmp_osft_cost", "cmp_osft_data", "cmp_osft_pos", "cmp_osft_var", "cmp_osft_multi", "cmp_osft_off", "cmp_osft_lock"],
        ["", "cmp_mm_cost", "cmp_mm_data", "cmp_mm_pos", "cmp_mm_var", "cmp_mm_multi", "cmp_mm_off", "cmp_mm_lock"],
        ["", "cmp_xc_cost", "cmp_mm_data", "cmp_xc_pos", "cmp_xc_var", "cmp_xc_multi", "cmp_xc_off", "cmp_xc_lock"],
        ["", "cmp_pos_cost", "cmp_mm_data", "cmp_pos_pos", "cmp_pos_var", "cmp_pos_multi", "cmp_pos_off", "cmp_pos_lock"],
        ["", "cmp_sh_cost", "cmp_sh_data", "cmp_sh_pos", "cmp_sh_var", "cmp_sh_multi", "cmp_sh_off", "cmp_sh_lock"],
    ]
    tr = ""
    for row_i, (cls, *cells) in enumerate(rows):
        keys = row_keys[row_i]
        tds = []
        for i, c in enumerate(cells):
            attr = f' data-i18n="{keys[i]}"' if keys[i] else ""
            tds.append(f"<td{attr}>{c}</td>")
        tr += f'<tr class="{cls}">{"".join(tds)}</tr>'
    th_keys = ["cmp_th1", "cmp_th2", "cmp_th3", "cmp_th4", "cmp_th5", "cmp_th6", "cmp_th7", "cmp_th8"]
    th_en = ["Program", "Cost", "Data", "POS", "Variance", "Multi-truck", "Offline", "Lock-in"]
    thead = "".join(f'<th data-i18n="{k}">{t}</th>' for k, t in zip(th_keys, th_en))
    body = hero(r, "hero-about", "Food truck on cobblestones at night.",
                "Compared",
                "MarketMan vs xtraCHEF vs a spreadsheet vs this.",
                "Honest comparison on cost, data ownership, POS, and lock-in. MarketMan publishes a price. xtraCHEF quotes. Spreadsheets are free until they aren’t. This program is GPLv3.",
                kicker_k="cmp_k", h1_k="cmp_h1", lede_k="cmp_lede") + f'''
  <main id="main">
    <section class="copy">
      <div class="wrap" style="overflow-x:auto">
        <table class="compare">
          <thead><tr>{thead}</tr></thead>
          <tbody>{tr}</tbody>
        </table>
        <p style="margin-top:1.2rem;color:var(--muted);font-size:.9rem" data-i18n="cmp_note">MarketMan Starter/Growth/Enterprise figures as published on vendor pricing pages in 2026 (~$249 / $299 / from $449). xtraCHEF does not publish a current price. Confirm on the vendor site before you buy anything. This page is not a paid comparison.</p>
        <div class="cta-row" style="justify-content:flex-start">
          <a class="btn btn-gold" href="{r}download/" data-i18n="cta_app">Download Program</a>
          <a class="btn btn-teal" href="{r}inventory/dashboard/" data-i18n="cta_lot_play">Play in The Lot</a>
        </div>
      </div>
    </section>
  </main>'''
    write("food-truck-inventory-software-comparison/index.html", shell(1,
        "MarketMan vs xtraCHEF vs Open Source Food Truckin' — Compared (2026)",
        "Honest comparison of MarketMan, xtraCHEF, POS inventory and Open Source Food Truckin' on cost, free tiers, data ownership and lock-in.",
        "compare", body, title_key="title_cmp"))


POSTS = [
    ("best-free-food-truck-inventory", "Why Open Source Food Truckin' is the Best Free Food Truck Inventory System",
     "2026-10-24", "Comparison",
     "What “best” means when you’re the one counting the cooler at 1 a.m. with the generator still running.",
     """<p>Best, for a truck, is not a feature grid. It is whether you can finish the count before the ice cream weeps, whether tomorrow’s load list is real, and whether anyone is going to bill you next month for the privilege.</p>
<p>Paid restaurant platforms are built for four walls. They assume a walk-in you can stand in, a desk in the office, and a manager who is not also the driver. MarketMan publishes Starter around $249 a month. xtraCHEF wants a quote and a Toast conversation. Square and Toast will sell you item stock that is not a cooler walk.</p>
<p>A spreadsheet is honest until the second stop type. Then you have two pars, a festival, a lunch lot, and a file named FINAL-v7.</p>
<p>Open Source Food Truckin' is GPLv3, local, bilingual, and built for zones that move. Voice walk, daily/weekly/monthly counts, POS CSV, plate costing, load lists. Play it in The Lot, then run it on the laptop in the cab.</p>"""),
    ("free-inventory-system-guide", "Free Inventory System for Food Trucks: Setup in One Night",
     "2026-10-24", "Setup",
     "Map sections, walk or talk the truck, reconcile invoices, first count — the exact process used on a real rolling kitchen.",
     """<p>You need a laptop, a browser, and one quiet hour after service. Download the program. Bookmark localhost. Skip AI. Name the truck. Turn on the sections you actually have.</p>
<p>Walk cooler, freezer, dry, prep. Say the shelf, then the product, then the pack. English, Spanish, or mixed. If the generator is loud, type. Bring invoices as CSV or typed lines. Reconcile: here’s what I registered. Confirm. Set PAR. Do the first count.</p>
<p>Home base opens. That is the butterfly. Tomorrow you print a load list. Next week you import Square or Toast. The process page is the long version of this night.</p>"""),
    ("cooler-freezer-inventory", "Cooler and Freezer Inventory Is a Different Problem",
     "2026-10-24", "Guide",
     "Thaw, FIFO, and a door that opens onto a parking lot. Why liquor-style bottle math does not save a walk-in on wheels.",
     """<p>Liquor inventory (the sister program) counts tenths of a bottle that does not spoil on the drive home. A cooler does. Ice melts. Dairy dates out. Frozen cases become a puddle if the generator hiccups.</p>
<p>Open Source Food Truckin' treats cooler and freezer as first-class zones, not a category dump. Daily end-of-shift can be a watch list of the things that die overnight. Weekly is the full box. Variance against POS tells you whether the carne asada on the ticket matches the carne asada that left the freezer.</p>
<p>PAR on a cooler is a stop-type problem. Lunch lot is not festival. The load list is how you stop guessing at 6 a.m.</p>"""),
    ("food-truck-inventory-spreadsheet", "The Food Truck Inventory Spreadsheet Problem",
     "2026-10-24", "Guide",
     "Almost every truck starts with a sheet, and for a while it is the right call. Where it breaks — stop types, date windows, version drift — and how to fix it.",
     """<p>A sheet is the right first tool. Twelve SKUs, one window, one PAR. Then you add a brewery night, a second truck, a Spanish-speaking prep cook, and a Toast export that does not match the row names.</p>
<p>The break is always the same: two people edit two copies, the date window on the POS file is not the date window on the count, and nobody knows whether tortillas are packs or cases.</p>
<p>This program still has a spreadsheet brain. It just refuses to be a file that lives in three inboxes. Voice builds the first map. Counts, invoices, and POS feed the same products. Export CSV when you want a sheet. Keep the truth in the program.</p>"""),
    ("pos-integration-toast-square-clover", "POS Integration in a Free Inventory System — Square, Toast, Clover, CSV",
     "2026-10-24", "Operations",
     "Structured imports that turn last night’s tickets into theoretical usage, without a live API tax.",
     """<p>Live POS APIs are a sales department. A truck already has an export. Open Source Food Truckin' takes Square Item Sales, Toast Item Selection Details, Clover Item Sales, or any CSV with item and qty columns. Preview first. Then import.</p>
<p>Column names are from public vendor docs and should be checked against your real file. Clover sometimes ships without dates — pick the sales date on import. Toast voids are skipped where documented. Live API adapters are stubs, on purpose: this program runs on your laptop.</p>
<p>Theoretical usage = qty sold × recipe qty, in the product’s own unit. That number only means something next to a count. That is the whole point of All inputs.</p>"""),
    ("variance-from-sales", "Variance Tracking That Actually Works on a Truck",
     "2026-10-24", "Operations",
     "Counted usage vs theoretical from the POS, with daily partials that do not wreck the weekly story.",
     """<p>Counted usage = start count + received − end count. Theoretical = sum of qty sold × recipe qty. The gap is variance. On a truck, a daily partial count is a snapshot of a watch list — it must not zero the freezer you did not open.</p>
<p>v1.3 count types exist for this. Daily end-of-shift updates only its scope. Weekly sales variance skips those partials. A product counted only on a daily list uses its own last count.</p>
<p>Timing matters. A before-service count sits before that day’s sales. An end-of-shift count sits after. POS files carry dates, not times. Pick the timing per count type. Then read the money report: food cost %, category vs target, stock value.</p>"""),
    ("load-list-and-stop-types", "Load Lists and Stop Types: Lunch Lot Is Not a Festival",
     "2026-10-24", "Operations",
     "PAR that changes with the parking space. Print tomorrow’s list before you roll.",
     """<p>Brick-and-mortar PAR assumes the room does not move. A truck’s PAR is the next stop. Lunch office park wants half the salsa and none of the funnel-cake sugar. Saturday festival wants the opposite, plus extra ice.</p>
<p>Stop types in this program hold their own PAR. You name the stops you actually work. The load list is on-hand versus that PAR, printable, grouped so the commissary run is one piece of paper.</p>
<p>It assumes on-hand is what’s on the truck. Commissary-to-truck transfer is a separate motion (multi-truck transfers exist; treat commissary as a truck if that’s how you run). Print the list the night before. That is the feature restaurants never had to invent.</p>"""),
    ("recipe-costing-food-cost", "Plate Costing and Food Cost % Without a $249 Platform",
     "2026-10-24", "Operations",
     "Cost per plate, margin, and food cost from the same catalog you count. Recipe qty in the product’s own unit.",
     """<p>A taco is not a mystery. It is tortillas × carne × salsa × lime, in the units you stock. This program costs the plate from last received cost (not weighted average yet) and shows food-cost % and margin.</p>
<p>The constraint is honest: no unit conversion. If you buy by the case and recipe by the pound, match the units or the variance will lie. That is in KNOWN-GAPS.md. We would rather show you the seam than hide it behind a paywall.</p>
<p>Money report needs sales plus two counts before food cost % lights up. That is the same discipline as Open Source Barware: add data, get inventory. No dashboard theater.</p>"""),
]


BLOG_CAT = {
    "Comparison": "blog_cat_cmp",
    "Setup": "blog_cat_setup",
    "Guide": "blog_cat_guide",
    "Operations": "blog_cat_ops",
}


def blog():
    r = rel(1)
    items = []
    for i, (slug, title, date, cat, excerpt, _) in enumerate(POSTS, 1):
        k = f"b{i}"
        cat_k = BLOG_CAT.get(cat, "")
        cat_attr = f' data-i18n="{cat_k}"' if cat_k else ""
        items.append(f'''<article>
          <p class="meta">{date} · <span{cat_attr}>{cat}</span></p>
          <h2><a href="{r}blog/{slug}/" data-i18n="{k}_t">{title}</a></h2>
          <p data-i18n="{k}_x">{excerpt}</p>
          <p><a href="{r}blog/{slug}/" data-i18n="read_more">Read more →</a></p>
        </article>''')
    body = f'''  <main id="main">
    <section class="copy">
      <div class="wrap prose">
        <p class="kicker" data-i18n="blog_k">Operator Notes</p>
        <h1 class="display" data-i18n="blog_h1">Blog</h1>
        <p data-i18n="blog_lede">Practical notes on running inventory the way real trucks do it. Free tools, real workflows, no upsells.</p>
        <div class="blog-list">{''.join(items)}</div>
        <p class="fineprint" data-i18n="blog_more">More notes coming as we test and improve the program with the trade.</p>
      </div>
    </section>
  </main>'''
    write("blog/index.html", shell(1, "Blog — Open Source Food Truckin' | Free Inventory System Guides",
          "In-depth operator guides on free food-truck inventory systems, variance, POS integration, load lists, and why the best system stays free and open source.",
          "blog", body, title_key="title_blog"))
    for i, (slug, title, date, cat, excerpt, html) in enumerate(POSTS, 1):
        k = f"b{i}"
        r2 = rel(2)
        cat_k = BLOG_CAT.get(cat, "")
        cat_attr = f' data-i18n="{cat_k}"' if cat_k else ""
        body = f'''  <main id="main">
    <section class="copy">
      <div class="wrap prose">
        <p class="meta">{date} · <span{cat_attr}>{cat}</span></p>
        <h1 class="display" data-i18n="{k}_t">{title}</h1>
        <p class="lede" style="text-shadow:none" data-i18n="{k}_x">{excerpt}</p>
        <div data-i18n-html="{k}_html">{html}</div>
        <p><a href="{r2}blog/" data-i18n="cta_notes">← All notes</a> · <a href="{r2}download/" data-i18n="cta_app">Download Program</a></p>
      </div>
    </section>
  </main>'''
        write(f"blog/{slug}/index.html", shell(2, f"{title} — Open Source Food Truckin'", excerpt, "blog", body, title_key=f"{k}_t"))


def lot():
    r = rel(2)
    body = f'''  <div class="lot-banner">
    <div>
      <p class="kicker" style="margin:0 0 6px" data-i18n="lot_k">The Lot · Live Demo</p>
      <p><span data-i18n="lot_p">Playable sample taco truck — same program as the download. Click around Home base, count sheet, POS, menu, load lists. This is a sandbox on this computer, not your truck. Download to run it for real.</span> <a href="{r}download/" data-i18n="nav_dl">Download</a></p>
    </div>
    <a class="btn btn-gold" href="{DEMO}" target="_blank" rel="noopener" data-i18n="lot_open">Open The Lot in its own window</a>
  </div>
  <main id="main">
    <iframe class="lot-frame" title="Open Source Food Truckin' live demo" src="{DEMO}"></iframe>
  </main>'''
    write("inventory/dashboard/index.html", shell(2, "The Lot — Live Demo | Open Source Food Truckin'",
          "Enter The Lot. Play in the Open Source Food Truckin' sandbox with sample taco-truck data before you download and build your own truck.",
          "demo", body, extra_body_class="lot-page", title_key="title_lot"))
    write("inventory/index.html", shell(1, "The Lot — Live Demo | Open Source Food Truckin'",
          "Playable sample taco truck.",
          "demo",
          f'''  <main id="main" class="copy"><div class="wrap prose">
            <p class="kicker" data-i18n="lot_k">The Lot</p>
            <h1 class="display" data-i18n="lot_h1">Play in the sample taco truck.</h1>
            <p data-i18n="lot_enter_p">Same home base as the download — metrics, sheets, and load lists after you look around.</p>
            <a class="btn btn-gold" href="dashboard/" data-i18n="lot_enter">Enter The Lot</a>
          </div></main>''', title_key="title_lot"))


def compliance():
    r = rel(1)
    body = f'''  <main id="main">
    <section class="copy">
      <div class="wrap prose">
        <p class="kicker" data-i18n="gpl_k">GPL Compliance</p>
        <h1 class="display" data-i18n="gpl_h1">Open source means the source stays with the download.</h1>
        <p data-i18n="gpl_p">Open Source Food Truckin' is free software distributed under the GNU General Public License version 3 or later. The license, notices, and corresponding source are in the same tarball anyone downloads.</p>
        <ul>
          <li data-i18n="gpl_li1">Download packages include LICENSE.txt, README, CHANGELOG, PARITY, and the Python source.</li>
          <li data-i18n="gpl_li2">The corresponding source is the same archive, at no charge.</li>
          <li data-i18n="gpl_li3">Modified redistributions should keep license notices intact and mark meaningful changes with a date.</li>
          <li data-i18n="gpl_li4">Running a hosted website by itself does not require users to distribute private changes; conveying downloadable copies does.</li>
        </ul>
        <p><a class="btn btn-gold" href="{r}download/" data-i18n="gpl_btn">Get the download (license included)</a> <a class="btn btn-teal" href="{r}downloads/LICENSE.txt" data-i18n="gpl_read">Read the full GPLv3 text</a></p>
      </div>
    </section>
  </main>'''
    write("open-source-compliance/index.html", shell(1, "Open Source Compliance — Open Source Food Truckin'",
          "GPL license, source code, and download package notices for Open Source Food Truckin'.",
          "compliance", body, title_key="title_gpl"))


def main():
    write_i18n()
    home()
    process()
    about()
    resources()
    download()
    downloads_guide()
    manifesto()
    changelog()
    blog()
    lot()
    compliance()
    compare()
    category(
        "free-food-truck-inventory-software",
        "Free Food Truck Inventory Software | Open Source Food Truckin'",
        "Free, open-source food-truck inventory software. Voice walk, zone counts, POS import, plate costing, load lists. GPLv3, local-first, no subscription.",
        "Free software",
        "Free food truck inventory software.",
        "The exact-match page for operators searching the phrase. Local-first, GPLv3, bilingual. The program is the product — this page is the door.",
        [
            ("No subscription", "The download is the program. Nothing unlocks later behind a card."),
            ("Built for wheels", "Zones, stop types, and load lists — not a restaurant platform with the word truck taped on."),
            ("Same house as Barware", "If you already trust Open Source Barware, this is the rolling-kitchen sister."),
        ],
        [
            ("01", "Voice + zones", "Walk cooler, freezer, dry, prep. English or Spanish."),
            ("02", "POS + recipes", "Square, Toast, Clover, or any CSV. Plate cost from the same catalog."),
            ("03", "Count types", "Daily partial, weekly full, monthly in-depth."),
            ("04", "Load lists", "PAR per stop type. Print tomorrow before you roll."),
        ],
        "seo",
        "hero-process",
        prefix="cat_free",
        title_key="title_cat_free",
    )
    category(
        "truck-inventory",
        "Free Truck & Cooler Inventory Tracking | Open Source Food Truckin'",
        "Cooler, freezer, and on-truck inventory with PAR, variance, and load lists. Free and open source.",
        "On the truck",
        "Truck and cooler inventory, the way you walk it.",
        "Highest spoilage, highest panic. The rolling walk-in is the liquor room of this business — except it thaws.",
        [
            ("Highest spoilage", "Dairy, meat, and ice cream do not wait for month-end."),
            ("Door on a parking lot", "Every open cooler is a temperature story. Daily watch lists exist for this."),
            ("FIFO in a box", "Cases stacked for the next stop, not a pretty storeroom."),
        ],
        [
            ("01", "Zone-level PAR", "Cooler and freezer as places, not a category total."),
            ("02", "Daily partial counts", "Watch list of what dies overnight, without zeroing the rest."),
            ("03", "Variance vs tickets", "Carne on the POS versus carne that left the freezer."),
            ("04", "Load list", "What to put on the truck for the next stop type."),
        ],
        "truck",
        "hero-process",
        prefix="cat_truck",
        title_key="title_cat_truck",
    )
    category(
        "prep-inventory",
        "Free Prep Inventory for Food Trucks | Open Source Food Truckin'",
        "Prep, dry storage, and make-table inventory with recipes and food cost. Free and open source.",
        "Prep",
        "Prep inventory is a different clock.",
        "Pico does not live in the freezer. Dry goods do not thaw. The make table is a third physics.",
        [
            ("Short shelf life", "Salsas, herbs, citrus — counted as prep, not as dry."),
            ("Recipe link", "Prep is where plate costing becomes true or false."),
            ("Window vs commissary", "What is on the line tonight versus what stays at the commissary."),
        ],
        [
            ("01", "Prep as a zone", "First-class section, same walk as the cooler."),
            ("02", "Recipes", "Qty in the product’s own unit. Food-cost % from the same map."),
            ("03", "Make table / window", "Optional extra zones for the line."),
            ("04", "Commissary", "Park product as commissary-only at reconcile if it never rides."),
        ],
        "prep",
        "hero-download",
        prefix="cat_prep",
        title_key="title_cat_prep",
    )
    simple_legal("privacy", "Privacy Policy — Open Source Food Truckin'", "Privacy", "Privacy Policy", [
        "Last updated October 24, 2026. Open Source Food Truckin' is built to keep your truck data on your own machine. This page explains the limited information the website itself handles.",
        "The downloadable program runs on your own computer. Your counts, products, costs, and variance stay on your device unless you choose to share them. We do not receive that data. An optional AI key, if you add one, stays in data/config.json and is left out of backups.",
        "This local lab site may send anonymous journey events (page views, time on page, outbound clicks) to the Open Source Barware collector used across family sites, tagged siteId osft-landing. No account is created. No email is required to download.",
        "To ask a privacy question, use the contact path on OpenSourceBarware.com or Intelligent Hospitality Systems.",
    ], "privacy", prefix="priv", title_key="title_priv")
    simple_legal("terms", "Terms of Use — Open Source Food Truckin'", "Terms", "Terms of Use", [
        "Last updated October 24, 2026. The program is licensed under the GNU GPLv3 or later. The website is provided as-is to explain, demonstrate, and distribute that program.",
        "You are responsible for how you use counts, costs, and load lists in your business. The software is a tool, not a health-department filing, not tax advice, not a POS.",
        "The Live Demo (The Lot) is a sandbox with sample data. Do not put real vendor invoices or real PINs in the demo.",
        "Trademarks of Square, Toast, Clover, MarketMan, and others belong to them. Adapters use publicly documented export formats.",
    ], "terms", prefix="terms", title_key="title_terms")
    print("done")


if __name__ == "__main__":
    main()
