#!/usr/bin/env python3
"""rolepod-seo — Tier A collector (plain fetch, Python stdlib only).

Fetches what an audit can see without a browser — HTML, robots.txt,
sitemap(s), llms.txt — and writes one row per page plus site-level facts,
so the auditing model reads a table instead of raw HTML.

Usage:
  collect.py BASE_URL [--mode quick|full] [--urls FILE] [--out DIR]
             [--max-pages N] [--timeout SEC] [--quiet]

Outputs (in --out, default .rolepod-seo/collect-<host>-<YYYYMMDD>/):
  pages.tsv     per-page facts, tab-separated (machine-readable)
  pages.md      the same rows as a markdown table (paste into the report)
  site.json     robots / sitemap / duplicates / redirects / host variants
  collect.json  pages + site in one document (feeds the JSON sidecar)

No JavaScript is executed. Rendered-DOM checks (JS-injected meta, JSON-LD
added at runtime, Core Web Vitals) belong to rolepod-uiproof.

Safety: private, loopback, link-local and cloud-metadata targets are refused
(also as redirect targets) unless --allow-private is given for a site you run
locally. DNS is resolved once per fetch; rebinding between resolve and connect
is not defended at this layer. Sitemap XML is size-capped and rejected when it
carries a DOCTYPE.
"""
from __future__ import annotations

import argparse
from collections import deque
import ipaddress
import socket
import datetime as dt
import json
import os
import re
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from html.parser import HTMLParser

VERSION = 1
UA = "Mozilla/5.0 (compatible; rolepod-seo/0.1; +https://github.com/nuttaruj/rolepod-seo)"
BOTS = ["Googlebot", "Bingbot", "GPTBot", "ClaudeBot", "PerplexityBot", "Google-Extended", "CCBot"]
SITEMAP_MAX_BYTES = 20 * 1024 * 1024
SITEMAP_MAX_URLS = 50_000
BLOCKED_HOSTS = {"localhost", "metadata.google.internal", "metadata", "instance-data", "169.254.169.254", "fd00:ec2::254"}
_ALLOW_PRIVATE = False


def is_safe_ip(ip_str: str) -> bool:
    """Public unicast only: rejects private, loopback, link-local, reserved, multicast, unspecified (IPv4-mapped IPv6 included)."""
    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError:
        return False
    return not (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast or ip.is_unspecified)


def unsafe_reason(url: str) -> str | None:
    """Why this URL must not be fetched, or None. Hostname blocklist, IP-literal check, then every resolved address."""
    if _ALLOW_PRIVATE:
        return None
    p = urllib.parse.urlsplit(url)
    if p.scheme.lower() not in ("http", "https"):
        return f"scheme {p.scheme!r} not allowed"
    host = (p.hostname or "").lower().rstrip(".")
    if not host:
        return "no hostname"
    if host in BLOCKED_HOSTS or host.endswith((".localhost", ".internal", ".local")):
        return f"blocked hostname {host}"
    try:
        ipaddress.ip_address(host)
        return None if is_safe_ip(host) else f"private or reserved address {host}"
    except ValueError:
        pass
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror:
        return f"{host} does not resolve"
    for info in infos:
        ip = info[4][0]
        if not is_safe_ip(ip):
            return f"{host} resolves to private address {ip}"
    return None

SKIP_RE = re.compile(
    r"(/wp-admin|/wp-login|/login|/signin|/sign-in|/register|/cart|/checkout|/account|/my-account"
    r"|/privacy|/terms|/cookie|/legal|/tag/|/tags/|/category/|/page/\d+|/feed|/author/|/search"
    r"|\?s=|/xmlrpc|/wp-json|/wp-content/)",
    re.I,
)
ASSET_RE = re.compile(r"\.(pdf|jpe?g|png|gif|svg|webp|avif|zip|mp4|mp3|css|js|xml|json|ico|woff2?|txt)($|\?)", re.I)
KEY_PAGES = [
    ("about", re.compile(r"/about|/company|/team|/who-we-are|/our-story", re.I)),
    ("services", re.compile(r"/service|/product|/solution|/what-we-do|/feature", re.I)),
    ("pricing", re.compile(r"/pric|/plans|/packages", re.I)),
    ("cases", re.compile(r"/case-stud|/cases?\b|/customers?\b|/portfolio|/our-work|/work\b|/testimonials?\b|/reviews?\b", re.I)),
    ("blog", re.compile(r"/blog|/news|/article|/insight|/resource|/guide|/learn", re.I)),
    ("contact", re.compile(r"/contact|/get-in-touch|/book|/quote|/demo", re.I)),
    ("faq", re.compile(r"/faqs?\b|/help\b|/support\b|/questions?\b", re.I)),
]
QUESTION_RE = re.compile(r"^(who|what|when|where|why|how|can|could|does|do|is|are|should|which|will)\b|\?\s*$", re.I)
SKIP_TAGS = ("script", "style", "noscript", "template", "svg")
# third-party script / stylesheet / iframe hosts → known analytics or tag providers (substring match on the host)
ANALYTICS_PROVIDERS = [
    ("googletagmanager.com", "google-tag-manager"), ("google-analytics.com", "google-analytics"), ("analytics.google.com", "google-analytics"),
    ("plausible.io", "plausible"), ("posthog.com", "posthog"), ("amplitude.com", "amplitude"), ("mixpanel.com", "mixpanel"),
    ("segment.com", "segment"), ("segment.io", "segment"), ("hotjar.com", "hotjar"), ("clarity.ms", "microsoft-clarity"),
    ("usefathom.com", "fathom"), ("umami.is", "umami"), ("heapanalytics.com", "heap"), ("heap.io", "heap"),
    ("rudderstack.com", "rudderstack"), ("intercom.io", "intercom"), ("matomo", "matomo"), ("pirsch.io", "pirsch"),
    ("simpleanalytics.com", "simple-analytics"), ("vercel-scripts.com", "vercel-analytics"), ("vercel-insights.com", "vercel-analytics"),
    ("goatcounter.com", "goatcounter"), ("newrelic.com", "new-relic"), ("nr-data.net", "new-relic"), ("fullstory.com", "fullstory"),
    ("logrocket.com", "logrocket"), ("facebook.net", "meta-pixel"), ("connect.facebook.net", "meta-pixel"), ("tiktok.com", "tiktok-pixel"),
    ("snap.licdn.com", "linkedin-insight"), ("ads-twitter.com", "x-pixel"), ("clickcease", "clickcease"), ("hs-scripts.com", "hubspot"),
    ("hubspot.com", "hubspot"), ("crazyegg.com", "crazyegg"), ("mouseflow.com", "mouseflow"), ("cookiebot.com", "cookiebot"),
    ("onetrust.com", "onetrust"), ("line-scdn.net", "line-tag"), ("googlesyndication.com", "adsense"), ("doubleclick.net", "google-ads"),
]
# ISO 639-1 language codes for hreflang validation (primary subtag only; region / script subtags are not checked)
ISO_639_1 = set("""aa ab ae af ak am an ar as av ay az ba be bg bh bi bm bn bo br bs ca ce ch co cr cs cu cv cy da de dv dz ee el en eo es et eu fa ff fi fj fo fr fy ga gd gl gn gu gv ha he hi ho hr ht hu hy hz ia id ie ig ii ik io is it iu ja jv ka kg ki kj kk kl km kn ko kr ks ku kv kw ky la lb lg li ln lo lt lu lv mg mh mi mk ml mn mr ms mt my na nb nd ne ng nl nn no nr nv ny oc oj om or os pa pi pl ps pt qu rm rn ro ru rw sa sc sd se sg si sk sl sm sn so sq sr ss st su sv sw ta te tg th ti tk tl tn to tr ts tt tw ty ug uk ur uz ve vi vo wa wo xh yi yo za zh zu""".split())


def valid_hreflang(code: str) -> bool:
    c = (code or "").strip().lower()
    if c == "x-default":
        return True
    primary = c.split("-")[0]
    return primary in ISO_639_1 or (len(primary) == 3 and primary.isalpha())  # ISO 639-2/3 three-letter codes are tolerated


# ---------------------------------------------------------------- helpers
def clean(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


def norm(url: str) -> str:
    """Normalise for comparisons: lower-case scheme+host, drop fragment, strip one trailing slash."""
    p = urllib.parse.urlsplit(url.strip())
    path = p.path or "/"
    if len(path) > 1 and path.endswith("/"):
        path = path[:-1]
    return urllib.parse.urlunsplit((p.scheme.lower(), p.netloc.lower(), path, p.query, ""))


def host_of(url: str) -> str:
    return urllib.parse.urlsplit(url).netloc.lower()


def same_origin(a: str, b: str) -> bool:
    return host_of(a) == host_of(b)


def is_local(host: str) -> bool:
    h = host.split(":")[0]
    return h in ("localhost", "127.0.0.1", "0.0.0.0", "::1") or re.match(r"^\d+\.\d+\.\d+\.\d+$", h) is not None


def path_of(url: str) -> str:
    p = urllib.parse.urlsplit(url)
    return (p.path or "/") + (("?" + p.query) if p.query else "")


_CTX: ssl.SSLContext | None = None
_INSECURE = False
CA_BUNDLES = (
    "/etc/ssl/cert.pem",                       # macOS system bundle
    "/etc/ssl/certs/ca-certificates.crt",      # Debian / Ubuntu / Alpine
    "/etc/pki/tls/certs/ca-bundle.crt",        # RHEL / Fedora
    "/opt/homebrew/etc/openssl@3/cert.pem",    # Homebrew (arm64)
    "/usr/local/etc/openssl@3/cert.pem",       # Homebrew (x86_64)
)


def ssl_context() -> ssl.SSLContext:
    """Default context plus every CA bundle we can find — python.org builds on
    macOS ship without one and fail every https fetch otherwise."""
    global _CTX
    if _CTX is not None:
        return _CTX
    ctx = ssl.create_default_context()
    try:
        import certifi  # type: ignore

        ctx.load_verify_locations(certifi.where())
    except Exception:
        pass
    for path in CA_BUNDLES:
        if os.path.exists(path):
            try:
                ctx.load_verify_locations(path)
            except Exception:
                pass
    if _INSECURE:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    _CTX = ctx
    return ctx


KEEP_HEADERS = {"strict-transport-security", "content-security-policy", "x-content-type-options", "x-robots-tag", "cache-control", "server"}


class _Redirects(urllib.request.HTTPRedirectHandler):
    def __init__(self):
        super().__init__()
        self.hops: list[tuple[int, str]] = []

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        self.hops.append((code, newurl))
        why = unsafe_reason(newurl)
        if why:
            raise urllib.error.URLError(f"refused redirect: {why}")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch(url: str, timeout: float, limit: int = 2_000_000) -> dict:
    rh = _Redirects()
    opener = urllib.request.build_opener(rh, urllib.request.HTTPSHandler(context=ssl_context()))
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": UA,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        },
    )
    out = {"url": url, "status": 0, "final_url": url, "hops": [], "content_type": "", "x_robots": "", "headers": {}, "body": b"", "error": ""}
    why = unsafe_reason(url)
    if why:
        out["error"] = f"refused: {why}"
        return out
    try:
        with opener.open(req, timeout=timeout) as r:
            out["status"] = r.status
            out["final_url"] = r.geturl()
            out["content_type"] = r.headers.get("Content-Type", "") or ""
            out["x_robots"] = r.headers.get("X-Robots-Tag", "") or ""
            out["headers"] = {k.lower(): v for k, v in r.headers.items() if k.lower() in KEEP_HEADERS}
            out["body"] = r.read(limit)
    except urllib.error.HTTPError as e:
        out["status"] = e.code
        out["final_url"] = e.geturl() if hasattr(e, "geturl") else url
        out["content_type"] = (e.headers.get("Content-Type", "") if e.headers else "") or ""
        if e.headers:
            out["headers"] = {k.lower(): v for k, v in e.headers.items() if k.lower() in KEEP_HEADERS}
        try:
            out["body"] = e.read(500_000)
        except Exception:
            pass
    except Exception as e:  # URLError, timeout, ssl
        out["error"] = f"{type(e).__name__}: {e}"[:200]
    out["hops"] = rh.hops
    return out


def head(url: str, timeout: float) -> dict:
    """Status-only probe for sitemap sweeps: HEAD, falling back to a tiny GET when HEAD is refused."""
    why = unsafe_reason(url)
    if why:
        return {"status": 0, "final_url": url, "hops": 0, "error": f"refused: {why}"}
    for method in ("HEAD", "GET"):
        rh = _Redirects()
        opener = urllib.request.build_opener(rh, urllib.request.HTTPSHandler(context=ssl_context()))
        req = urllib.request.Request(url, method=method, headers={"User-Agent": UA})
        try:
            with opener.open(req, timeout=timeout) as r:
                if method == "GET":
                    r.read(1024)
                return {"status": r.status, "final_url": r.geturl(), "hops": len(rh.hops), "error": ""}
        except urllib.error.HTTPError as e:
            if method == "HEAD" and e.code in (405, 403, 501):
                continue
            return {"status": e.code, "final_url": url, "hops": len(rh.hops), "error": ""}
        except Exception as e:
            return {"status": 0, "final_url": url, "hops": len(rh.hops), "error": f"{type(e).__name__}: {e}"[:120]}
    return {"status": 0, "final_url": url, "hops": 0, "error": "no response"}


def decode(body: bytes, content_type: str) -> str:
    """BOM → Content-Type charset → <meta charset> in the first 4 KB → utf-8 / cp1252 / latin-1."""
    if body.startswith(b"\xef\xbb\xbf"):
        return body[3:].decode("utf-8", "replace")
    if body.startswith((b"\xff\xfe", b"\xfe\xff")):
        return body.decode("utf-16", "replace")
    encs: list[str] = []
    m = re.search(r"charset=\"?([\w-]+)", content_type or "", re.I)
    if m:
        encs.append(m.group(1))
    m2 = re.search(rb"<meta[^>]+charset=[\"']?\s*([\w-]+)", body[:4096], re.I)
    if m2:
        encs.append(m2.group(1).decode("ascii", "ignore"))
    for enc in encs + ["utf-8", "cp1252", "latin-1"]:
        try:
            return body.decode(enc)
        except Exception:
            continue
    return body.decode("utf-8", "replace")


# ---------------------------------------------------------------- HTML facts
class Page(HTMLParser):
    def __init__(self, base: str):
        super().__init__(convert_charrefs=True)
        self.base = base
        self.title: str | None = None
        self.metas: dict[str, str] = {}
        self.canonical: str | None = None
        self.icon = False
        self.hreflang = 0
        self.hreflang_links: list[dict] = []
        self.third_party: set[str] = set()
        self.nav_links: list[tuple[str, int, str]] = []   # (url, list depth within the nav, region)
        self._nav_stack: list[str] = []                      # open tags while inside a nav-ish element
        self._nav_region = ""
        self._nav_ul = 0
        self._footer = 0
        self.lang = ""
        self.charset = False
        self.h: dict[int, list[str]] = {1: [], 2: [], 3: []}
        self.jsonld_raw: list[str] = []
        self.text: list[str] = []
        self.imgs = 0
        self.imgs_noalt = 0
        self.links_int = 0
        self.links_ext = 0
        self.internal: list[str] = []
        self.author_signals: set[str] = set()
        self.faq_signals: set[str] = set()
        self.contact: set[str] = set()
        self.dates: set[str] = set()
        self.details = 0
        self.tables = 0
        self.lists = 0
        self.mixed = 0
        self._skip = 0
        self._title_buf: list[str] | None = None
        self._h_buf: list[str] | None = None
        self._h_level = 0
        self._ld_buf: list[str] | None = None

    def handle_starttag(self, tag, attrs):
        a = {k: (v or "") for k, v in attrs}
        if tag == "html":
            self.lang = a.get("lang", "")
        if tag in ("script", "iframe") and a.get("src"):
            self._note_third_party(a["src"])
        cls_id = (a.get("class", "") + " " + a.get("id", "")).lower()
        if tag == "footer" or re.search(r"(^|[\s_-])footer([\s_-]|$)", cls_id):
            self._footer += 1
        if self._nav_stack:
            self._nav_stack.append(tag)
            if tag in ("ul", "ol"):
                self._nav_ul += 1
        elif tag == "nav" or tag == "header" or a.get("role", "").lower() == "navigation" or re.search(r"(^|[\s_-])(nav|navbar|menu|main-menu|primary-menu)([\s_-]|$)", cls_id):
            self._nav_stack.append(tag)
            self._nav_region = "footer" if self._footer else ("header" if tag == "header" else "nav")
            self._nav_ul = 0
        if tag in SKIP_TAGS:
            self._skip += 1
            if tag == "script" and a.get("type", "").replace(" ", "").lower() == "application/ld+json":
                self._ld_buf = []
            return
        if self._skip:
            return
        cls = a.get("class", "") + " " + a.get("id", "")
        if re.search(r"(^|[\s_-])(author|byline|written-by)([\s_-]|$)", cls, re.I):
            self.author_signals.add("class:author")
        if re.search(r"(^|[\s_-])faq", cls, re.I):
            self.faq_signals.add("class:faq")
        if tag == "title" and self.title is None:
            self._title_buf = []
        elif tag == "meta":
            name = (a.get("name") or a.get("property") or a.get("http-equiv") or "").lower()
            if a.get("charset"):
                self.charset = True
            if name:
                self.metas.setdefault(name, a.get("content", ""))
            if name == "author":
                self.author_signals.add("meta:author")
            if name in ("article:published_time", "article:modified_time", "date", "dc.date", "dcterms.date"):
                self.dates.add("meta:" + name)
        elif tag == "link":
            rel = a.get("rel", "").lower().split()
            href = a.get("href", "")
            if "stylesheet" in rel and href:
                self._note_third_party(href)
            if "canonical" in rel and self.canonical is None:
                self.canonical = href
            if "alternate" in rel and a.get("hreflang"):
                self.hreflang += 1
                self.hreflang_links.append({"lang": a["hreflang"].strip().lower(), "href": urllib.parse.urljoin(self.base, href)})
            if "author" in rel:
                self.author_signals.add("link:author")
            if "icon" in rel:
                self.icon = True
        elif tag in ("h1", "h2", "h3"):
            self._h_level = int(tag[1])
            self._h_buf = []
        elif tag == "img":
            self.imgs += 1
            if not a.get("alt", "").strip():
                self.imgs_noalt += 1
            if a.get("src", "").startswith("http://") and self.base.startswith("https://"):
                self.mixed += 1
        elif tag == "a":
            href = a.get("href", "")
            if href.startswith("tel:"):
                self.contact.add("tel")
            elif href.startswith("mailto:"):
                self.contact.add("mailto")
            elif href and not href.startswith(("#", "javascript:")):
                full = urllib.parse.urljoin(self.base, href)
                if full.startswith("http"):
                    if same_origin(full, self.base):
                        self.links_int += 1
                        self.internal.append(full)
                        if self._nav_stack:
                            self.nav_links.append((full, max(self._nav_ul, 1), self._nav_region))
                    else:
                        self.links_ext += 1
            if "author" in a.get("rel", "").lower().split():
                self.author_signals.add("a:rel-author")
        elif tag == "time":
            self.dates.add("time")
        elif tag == "address":
            self.contact.add("address")
        elif tag == "details":
            self.details += 1
        elif tag == "table":
            self.tables += 1
        elif tag in ("ul", "ol"):
            self.lists += 1

    def _note_third_party(self, src: str) -> None:
        full = urllib.parse.urljoin(self.base, src)
        if full.startswith("http") and not same_origin(full, self.base):
            self.third_party.add(host_of(full))

    def handle_endtag(self, tag):
        if self._nav_stack:
            # pop to the matching open tag; leaving the outermost element ends the nav context
            if tag in self._nav_stack:
                while self._nav_stack:
                    t = self._nav_stack.pop()
                    if t in ("ul", "ol"):
                        self._nav_ul = max(0, self._nav_ul - 1)
                    if t == tag:
                        break
        if tag == "footer" and self._footer:
            self._footer -= 1
        if tag in SKIP_TAGS:
            if tag == "script" and self._ld_buf is not None:
                self.jsonld_raw.append("".join(self._ld_buf))
                self._ld_buf = None
            if self._skip:
                self._skip -= 1
            return
        if self._skip:
            return
        if tag == "title" and self._title_buf is not None:
            self.title = clean(" ".join(self._title_buf))
            self._title_buf = None
        elif tag in ("h1", "h2", "h3") and self._h_buf is not None:
            txt = clean(" ".join(self._h_buf))
            self.h[self._h_level].append(txt)
            if re.search(r"\b(faq|frequently asked|common questions)\b", txt, re.I):
                self.faq_signals.add("heading:faq")
            self._h_buf = None

    def handle_data(self, data):
        if self._ld_buf is not None:
            self._ld_buf.append(data)
            return
        if self._skip:
            return
        if self._title_buf is not None:
            self._title_buf.append(data)
        if self._h_buf is not None:
            self._h_buf.append(data)
        self.text.append(data)


def ld_walk(blocks: list[str]):
    types: list[str] = []
    ok = bad = 0
    has_author = False
    for raw in blocks:
        try:
            data = json.loads(raw.strip())
        except Exception:
            bad += 1
            continue
        ok += 1
        queue = deque([data])
        while queue:
            x = queue.popleft()
            if isinstance(x, dict):
                t = x.get("@type")
                if isinstance(t, str):
                    types.append(t)
                elif isinstance(t, list):
                    types.extend(str(i) for i in t)
                if "author" in x:
                    has_author = True
                queue.extend(x.values())
            elif isinstance(x, list):
                queue.extend(x)
    seen: list[str] = []
    for t in types:
        if t not in seen:
            seen.append(t)
    return seen, ok, bad, has_author


def page_facts(url: str, res: dict) -> dict:
    row = {
        "url": url,
        "status": res["status"],
        "final_url": res["final_url"],
        "hops": len(res["hops"]),
        "redirect_chain": [f"{c} → {u}" for c, u in res["hops"]],
        "content_type": res["content_type"].split(";")[0].strip(),
        "error": res["error"],
        "_headers": res.get("headers", {}),
    }
    if res["error"] or res["status"] >= 400 or not res["body"] or "html" not in res["content_type"].lower():
        return row
    html = decode(res["body"], res["content_type"])
    p = Page(res["final_url"])
    try:
        p.feed(html)
        p.close()
    except Exception as e:  # keep the row; note the parser failure
        row["error"] = f"parse: {type(e).__name__}"
    words = len(" ".join(p.text).split())
    types, ld_ok, ld_bad, ld_author = ld_walk(p.jsonld_raw)
    desc = p.metas.get("description", "")
    robots = p.metas.get("robots", "")
    canon = p.canonical
    if canon:
        canon_abs = urllib.parse.urljoin(res["final_url"], canon)
        if norm(canon_abs) == norm(res["final_url"]):
            canonical_ok = "self"
        elif not same_origin(canon_abs, res["final_url"]):
            canonical_ok = "cross-domain"
        else:
            canonical_ok = "other"
    else:
        canon_abs = ""
        canonical_ok = "missing"
    q_headings = [h for h in p.h[2] + p.h[3] if QUESTION_RE.search(h)]
    if ld_author or "Person" in types:
        p.author_signals.add("ld:author")
    faq_visible = bool(p.faq_signals) or p.details >= 2
    row.update(
        {
            "generator": p.metas.get("generator", ""),
            "title": p.title or "",
            "title_len": len(p.title or ""),
            "description": desc,
            "description_len": len(desc),
            "h1_count": len(p.h[1]),
            "h1": p.h[1][0] if p.h[1] else "",
            "h1_all": p.h[1],
            "h2_count": len(p.h[2]),
            "h2": p.h[2][:12],
            "h3_count": len(p.h[3]),
            "canonical": canon_abs,
            "canonical_ok": canonical_ok,
            "robots_meta": robots,
            "x_robots": res["x_robots"],
            "noindex": ("noindex" in robots.lower()) or ("noindex" in res["x_robots"].lower()),
            "lang": p.lang,
            "charset": p.charset,
            "viewport": bool(p.metas.get("viewport")),
            "favicon": p.icon,
            "og": {
                "title": bool(p.metas.get("og:title")),
                "description": bool(p.metas.get("og:description")),
                "image": bool(p.metas.get("og:image")),
                "type": p.metas.get("og:type", ""),
            },
            "twitter_card": p.metas.get("twitter:card", ""),
            "hreflang_count": p.hreflang,
            "hreflang": p.hreflang_links,
            "third_party_hosts": sorted(p.third_party),
            "analytics": sorted({prov for h in p.third_party for needle, prov in ANALYTICS_PROVIDERS if needle in h}),
            "word_count": words,
            "images": p.imgs,
            "images_no_alt": p.imgs_noalt,
            "links_internal": p.links_int,
            "links_external": p.links_ext,
            "mixed_content": p.mixed,
            "schema_types": types,
            "jsonld_blocks": ld_ok,
            "jsonld_invalid": ld_bad,
            "author_signals": sorted(p.author_signals),
            "author_present": bool(p.author_signals),
            "faq_visible": faq_visible,
            "faq_schema": "FAQPage" in types,
            "question_headings": len(q_headings),
            "date_signals": sorted(p.dates),
            "date_visible": bool(p.dates),
            "contact_signals": sorted(p.contact),
            "tables": p.tables,
            "lists": p.lists,
            "_internal_links": p.internal,
            "_nav_links": p.nav_links,
            "_text": " ".join(p.text).lower(),
        }
    )
    return row


# ---------------------------------------------------------------- robots / sitemap
def parse_robots(text: str):
    groups: list[tuple[list[str], list[tuple[str, str]]]] = []
    cur = None
    sitemaps: list[str] = []
    for line in text.splitlines():
        line = line.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        k, v = [s.strip() for s in line.split(":", 1)]
        kl = k.lower()
        if kl == "user-agent":
            if cur is not None and cur[1]:
                groups.append(cur)
                cur = None
            if cur is None:
                cur = ([v.lower()], [])
            else:
                cur[0].append(v.lower())
        elif kl in ("allow", "disallow") and cur is not None:
            cur[1].append((kl, v))
        elif kl == "sitemap":
            sitemaps.append(v)
    if cur is not None:
        groups.append(cur)
    return groups, sitemaps


def robots_verdict(groups, ua: str) -> dict:
    u = ua.lower()
    rules = None
    via = "none"
    for agents, r in groups:
        if any(a != "*" and (a == u or a in u or u in a) for a in agents):
            rules, via = r, "specific"
            break
    if rules is None:
        for agents, r in groups:
            if "*" in agents:
                rules, via = r, "wildcard"
                break
    if rules is None:
        return {"verdict": "no-rules", "via": via, "disallow": []}
    dis = [p for k, p in rules if k == "disallow" and p]
    allow_root = any(k == "allow" and p == "/" for k, p in rules)
    if "/" in dis and not allow_root:
        v = "blocked-all"
    elif dis:
        v = "partial"
    else:
        v = "allowed"
    return {"verdict": v, "via": via, "disallow": dis[:20]}


def read_sitemaps(urls: list[str], timeout: float, log) -> dict:
    info = {"checked": [], "entries": [], "errors": [], "index_children": 0}
    queue = list(urls)
    seen = set()
    while queue and len(seen) < 25:
        u = queue.pop(0)
        if u in seen:
            continue
        seen.add(u)
        res = fetch(u, timeout, limit=SITEMAP_MAX_BYTES)
        info["checked"].append({"url": u, "status": res["status"], "error": res["error"]})
        if res["status"] != 200 or not res["body"]:
            continue
        if len(res["body"]) >= SITEMAP_MAX_BYTES:
            info["errors"].append(f"{u}: larger than {SITEMAP_MAX_BYTES // (1024 * 1024)} MiB, skipped")
            continue
        if b"<!doctype" in res["body"][:4096].lower():
            info["errors"].append(f"{u}: DOCTYPE is not allowed in sitemap XML, skipped")
            continue
        if len(info["entries"]) >= SITEMAP_MAX_URLS:
            info["errors"].append(f"{u}: URL cap {SITEMAP_MAX_URLS} reached, skipped")
            continue
        try:
            root = ET.fromstring(res["body"])
        except ET.ParseError as e:
            info["errors"].append(f"{u}: invalid XML ({e})")
            continue
        tag = root.tag.lower()
        ns = {"s": root.tag.split("}")[0].strip("{")} if "}" in root.tag else {}
        loc_path = "s:sitemap/s:loc" if ns else "sitemap/loc"
        url_path = "s:url" if ns else "url"
        if tag.endswith("sitemapindex"):
            for loc in root.findall(loc_path, ns):
                if loc.text:
                    queue.append(loc.text.strip())
                    info["index_children"] += 1
        else:
            for node in root.findall(url_path, ns):
                loc = node.find("s:loc" if ns else "loc", ns)
                lm = node.find("s:lastmod" if ns else "lastmod", ns)
                if loc is not None and loc.text:
                    info["entries"].append({"loc": loc.text.strip(), "lastmod": (lm.text or "").strip() if lm is not None else ""})
    log(f"sitemap: {len(info['entries'])} URLs from {len(info['checked'])} file(s)")
    return info


# ---------------------------------------------------------------- selection
QUICK_CAP = 40
L2_PER_SECTION = 2


def url_depth(url: str) -> int:
    return len([x for x in urllib.parse.urlsplit(url).path.split("/") if x])


def section_of(url: str) -> str:
    segs = [x for x in urllib.parse.urlsplit(url).path.split("/") if x]
    return "/" + segs[0] if len(segs) > 1 else "/"


def select_pages(base: str, home_row: dict, sitemap_entries: list[dict], mode: str, max_pages: int, per_section: int, everything: bool) -> tuple[list[tuple[str, str]], dict]:
    """Quick = home + the site's first-level URLs from the sitemap (its own map of the main sections) + the newest
    L2_PER_SECTION pages under each + menu links the sitemap missed. No sitemap → navigation markup, and the report
    says so. Full = Quick + footer links + a per-section sitemap sample (newest first) up to max_pages; --all lifts caps."""
    nav = home_row.get("_nav_links", [])
    home_links = home_row.get("_internal_links", [])
    seen = {norm(base)}
    picks: list[tuple[str, str]] = []

    def usable(u: str) -> str | None:
        u2 = urllib.parse.urlsplit(u)._replace(fragment="").geturl()
        if not same_origin(u2, base) or SKIP_RE.search(u2) or ASSET_RE.search(u2):
            return None
        return u2

    def add(u: str, why: str) -> bool:
        u2 = usable(u)
        if not u2:
            return False
        k = norm(u2)
        if k in seen:
            return False
        seen.add(k)
        picks.append((u2, why))
        return True

    entries = [e for e in sitemap_entries if usable(e["loc"])]
    l1 = l2 = 0
    if entries:
        source = "sitemap"
        for e in entries:  # sitemap order = the site's own priority order
            if url_depth(e["loc"]) == 1 and add(e["loc"], "sitemap-l1"):
                l1 += 1
        by_section: dict[str, list[dict]] = {}
        for e in entries:
            if url_depth(e["loc"]) == 2:
                by_section.setdefault(section_of(e["loc"]), []).append(e)
        for sec, es in by_section.items():
            taken = 0
            for e in sorted(es, key=lambda e: (e.get("lastmod") or ""), reverse=True):
                if taken >= L2_PER_SECTION:
                    break
                if add(e["loc"], "sitemap-l2"):
                    taken += 1
                    l2 += 1
    else:
        source = "nav"
    menu_main = sum(1 for u, lvl, reg in nav if reg in ("nav", "header") and lvl <= 1 and add(u, "menu"))
    menu_sub = sum(1 for u, lvl, reg in nav if reg in ("nav", "header") and lvl >= 2 and add(u, "submenu"))
    fallback = False
    if not entries and menu_main + menu_sub < 3:  # neither sitemap nor navigation markup: key-page patterns over the homepage links
        fallback = True
        source = "home-links"
        for _label, rx in KEY_PAGES:
            for u in sorted(home_links, key=lambda x: len(urllib.parse.urlsplit(x).path)):
                if rx.search(path_of(u)) and add(u, "key-page"):
                    break
    info = {"structure_source": source, "sitemap_l1": l1, "sitemap_l2": l2, "l2_per_section": L2_PER_SECTION,
            "menu_extra": menu_main, "submenu_extra": menu_sub, "menu_main": menu_main, "menu_sub": menu_sub, "nav_fallback": fallback, "quick_cap": QUICK_CAP}
    if mode == "quick" and not everything:
        info["quick_cap_hit"] = len(picks) > QUICK_CAP
        return [(base, "home")] + picks[:QUICK_CAP], info
    for u, lvl, reg in nav:
        if reg == "footer":
            add(u, "footer")
    for u in home_links:
        add(u, "home-link")
    # stratified sitemap sample: per section, newest lastmod first
    sections: dict[str, list[dict]] = {}
    for e in sitemap_entries:
        if same_origin(e["loc"], base):
            sections.setdefault(section_of(e["loc"]), []).append(e)
    sampled: dict[str, dict] = {}
    for sec, entries in sorted(sections.items(), key=lambda kv: -len(kv[1])):
        ordered = sorted(entries, key=lambda e: (e.get("lastmod") or ""), reverse=True)
        taken = 0
        for e in ordered:
            if not everything and taken >= per_section:
                break
            if add(e["loc"], "sitemap"):
                taken += 1
        already = sum(1 for e in entries if norm(e["loc"]) in seen)
        sampled[sec] = {"total": len(entries), "selected": already}
    cap = len(picks) if everything else max_pages - 1
    info.update({"sections": sampled, "sitemap_total": len(sitemap_entries), "cap": None if everything else max_pages, "cap_hit": len(picks) > cap})
    return [(base, "home")] + picks[:cap], info


def discover(base: str, home_links: list[str], sitemap_locs: list[str], mode: str, max_pages: int) -> list[str]:
    ordered: list[str] = []
    seen = {norm(base)}

    def add(u: str):
        u2 = urllib.parse.urlsplit(u)._replace(fragment="").geturl()
        if not same_origin(u2, base) or SKIP_RE.search(u2) or ASSET_RE.search(u2):
            return
        k = norm(u2)
        if k in seen:
            return
        seen.add(k)
        ordered.append(u2)

    def depth(u: str) -> int:
        return len([seg for seg in urllib.parse.urlsplit(u).path.split("/") if seg])

    # nav / footer links first (shallowest first), then the sitemap (shallowest first)
    for u in sorted(home_links, key=depth):
        add(u)
    for u in sorted(sitemap_locs, key=depth):
        add(u)
    if mode == "full":
        return [base] + ordered[: max_pages - 1]
    picked: list[str] = []
    for _label, rx in KEY_PAGES:
        for u in ordered:
            if rx.search(path_of(u)) and u not in picked:
                picked.append(u)
                break
        if len(picked) >= 6:
            break
    return [base] + picked[:6]


def page_role(url: str, base: str) -> str:
    if norm(url) == norm(base):
        return "home"
    p = path_of(url)
    for label, rx in KEY_PAGES:
        if rx.search(p):
            return {"about": "trust", "services": "money", "pricing": "money", "cases": "trust", "blog": "blog", "contact": "trust", "faq": "answer"}[label]
    return "other"


# ---------------------------------------------------------------- cross-page analysis
def link_graph(rows: list[dict], base: str) -> dict:
    """Inbound links and click depth among the fetched pages only."""
    keys = {norm(r["url"]): r for r in rows}
    out_edges: dict[str, set[str]] = {k: set() for k in keys}
    for k, r in keys.items():
        for l in r.get("_internal_links", []):
            t = norm(urllib.parse.urlsplit(l)._replace(fragment="").geturl())
            if t in keys and t != k:
                out_edges[k].add(t)
    inlinks: dict[str, set[str]] = {k: set() for k in keys}
    for src, targets in out_edges.items():
        for t in targets:
            inlinks[t].add(src)
    home = norm(base)
    depth: dict[str, int | None] = {k: None for k in keys}
    if home in keys:
        depth[home] = 0
        q = deque([home])
        while q:
            cur = q.popleft()
            for t in out_edges[cur]:
                if depth[t] is None:
                    depth[t] = depth[cur] + 1
                    q.append(t)
    for k, r in keys.items():
        r["inlinks"] = len(inlinks[k])
        r["depth"] = depth[k]
    return {
        "pages_in_graph": len(keys),
        "unreachable_from_home": [path_of(r["url"]) for k, r in keys.items() if depth[k] is None and k != home and r["status"] == 200],
        "low_inlinks": [path_of(r["url"]) for k, r in keys.items() if r["status"] == 200 and k != home and len(inlinks[k]) <= 1 and r.get("role") in ("money", "answer", "trust")],
    }


def near_duplicates(rows: list[dict], threshold: float = 0.7, k: int = 8) -> list[dict]:
    """Pairs of fetched pages whose word-shingle sets overlap ≥ threshold (Jaccard)."""
    sets = []
    for r in rows:
        words = r.get("_text", "").split()
        if len(words) < 100:
            continue
        sh = {hash(" ".join(words[i:i + k])) for i in range(len(words) - k + 1)}
        sets.append((r, sh))
    pairs = []
    for i in range(len(sets)):
        for j in range(i + 1, len(sets)):
            a, sa = sets[i]
            b, sb = sets[j]
            inter = len(sa & sb)
            if not inter:
                continue
            sim = inter / len(sa | sb)
            if sim >= threshold:
                pairs.append({"a": path_of(a["url"]), "b": path_of(b["url"]), "similarity": round(sim, 2)})
    return sorted(pairs, key=lambda x: -x["similarity"])[:50]


def hreflang_report(rows: list[dict]) -> dict:
    """Self-reference, x-default and reciprocity among the fetched pages that declare hreflang."""
    fetched = {norm(r["final_url"]): r for r in rows if r.get("status") == 200}
    fetched.update({norm(r["url"]): r for r in rows if r.get("status") == 200})
    declared = [r for r in rows if r.get("status") == 200 and r.get("hreflang")]
    missing_self, missing_xdefault, non_reciprocal, invalid_codes = [], [], [], []
    unchecked = 0
    for r in declared:
        me = norm(r["final_url"])
        path = path_of(r["url"])
        for h in r["hreflang"]:
            if not valid_hreflang(h["lang"]):
                invalid_codes.append({"page": path, "code": h["lang"], "href": path_of(h["href"])})
        alts = {norm(h["href"]): h["lang"] for h in r["hreflang"]}
        langs = {h["lang"] for h in r["hreflang"]}
        if me not in alts and norm(r["url"]) not in alts:
            missing_self.append(path)
        if "x-default" not in langs:
            missing_xdefault.append(path)
        for alt, lang in alts.items():
            if alt in (me, norm(r["url"])):
                continue
            other = fetched.get(alt)
            if other is None:
                unchecked += 1
                continue
            back = {norm(h["href"]) for h in other.get("hreflang", [])}
            if me not in back and norm(r["url"]) not in back:
                non_reciprocal.append({"page": path, "alternate": path_of(alt), "lang": lang})
    return {
        "pages_with_hreflang": len(declared),
        "missing_self": missing_self,
        "missing_x_default": missing_xdefault,
        "non_reciprocal": non_reciprocal,
        "invalid_codes": invalid_codes,
        "alternates_not_fetched": unchecked,
    }


SITE_TYPE_RULES = {
    "saas": {"paths": r"/pricing|/plans|/features|/integrations|/docs|/api\b|/sign-?up|/free-trial|/changelog", "text": ("free trial", "sign up", "start free", "per month", "per seat", "integrations")},
    "ecommerce": {"paths": r"/products?/|/collections?/|/cart|/checkout|/shop\b|/category/", "text": ("add to cart", "add to basket", "free shipping", "in stock", "checkout")},
    "local": {"paths": r"/contact|/locations?|/areas?-we-serve|/service-area|/book", "text": ("serving ", "service area", "areas we cover", "near you", "opening hours", "call us", "visit us")},
    "publisher": {"paths": r"/blog|/news|/articles?/|/topics?/|/authors?/|/magazine|/stories", "text": ("read more", "latest articles", "by ", "published", "editor")},
    "agency": {"paths": r"/case-stud|/portfolio|/our-work|/clients|/industries|/services", "text": ("case study", "our clients", "our work", "we help", "get a proposal", "book a call")},
}


def site_type(rows: list[dict], home_text: str) -> dict:
    """Weighted signals: distinct path sections (1 each, max 3), homepage phrases (1 each), schema (2), home NAP (3), authors (1)."""
    signals: dict[str, list[str]] = {t: [] for t in SITE_TYPE_RULES}
    points: dict[str, int] = {t: 0 for t in SITE_TYPE_RULES}
    paths = [path_of(r["url"]) for r in rows]
    for t, rule in SITE_TYPE_RULES.items():
        sections = sorted({"/" + p.strip("/").split("/")[0] for p in paths if re.search(rule["paths"], p, re.I)})
        if sections:
            signals[t].append(f"paths: {', '.join(sections[:4])}")
            points[t] += min(len(sections), 3)
        found = [w for w in rule["text"] if w in home_text]
        if found:
            signals[t].append(f"text: {', '.join(w.strip() for w in found[:4])}")
            points[t] += len(found)
    types_seen = {t for r in rows for t in r.get("schema_types", [])}
    if "Product" in types_seen:
        signals["ecommerce"].append("schema: Product"); points["ecommerce"] += 2
    if types_seen & {"LocalBusiness", "Plumber", "Dentist", "Restaurant", "Store", "ProfessionalService", "HomeAndConstructionBusiness"}:
        signals["local"].append("schema: LocalBusiness"); points["local"] += 2
    if types_seen & {"Article", "BlogPosting", "NewsArticle"}:
        signals["publisher"].append("schema: Article"); points["publisher"] += 2
    home = rows[0] if rows else {}
    if {"address", "tel"} <= set(home.get("contact_signals", [])):
        signals["local"].append("home: address + phone"); points["local"] += 3
    if sum(1 for r in rows if r.get("author_present")) >= 2:
        signals["publisher"].append("authors on ≥2 pages"); points["publisher"] += 1
    ranked = sorted(points.items(), key=lambda kv: -kv[1])
    (best, bp), (_, sp) = ranked[0], ranked[1]
    if bp == 0:
        return {"type": "unknown", "confidence": "none", "signals": {}}
    conf = "high" if bp >= sp + 2 else "low"
    return {"type": best, "confidence": conf, "points": points, "signals": {t: v for t, v in signals.items() if v}}


# ---------------------------------------------------------------- output
TSV_COLS = [
    "url", "role", "selected_by", "status", "hops", "title", "title_len", "description_len", "h1_count", "h1", "h2_count",
    "canonical_ok", "robots_meta", "lang", "word_count", "schema_types", "author_present", "faq_visible",
    "faq_schema", "question_headings", "images_no_alt", "og", "date_visible", "inlinks", "depth", "third_party", "error",
]


def cell(row: dict, col: str) -> str:
    if col == "third_party":
        return str(len(row.get("third_party_hosts", []))) if "third_party_hosts" in row else ""
    v = row.get(col, "")
    if col == "schema_types":
        return ",".join(v) if isinstance(v, list) else ""
    if col == "og":
        if not isinstance(v, dict):
            return ""
        return "".join(k[0] for k in ("title", "description", "image") if v.get(k)) or "-"
    if isinstance(v, bool):
        return "y" if v else "n"
    if isinstance(v, list):
        return ";".join(map(str, v))
    if v is None:
        return "-"
    return str(v).replace("\t", " ").replace("\n", " ")


def write_outputs(out: str, doc: dict):
    os.makedirs(out, exist_ok=True)
    rows = doc["pages"]
    with open(os.path.join(out, "pages.tsv"), "w", encoding="utf-8") as f:
        f.write("\t".join(TSV_COLS) + "\n")
        for r in rows:
            f.write("\t".join(cell(r, c) for c in TSV_COLS) + "\n")
    md_cols = ["path", "status", "title", "desc", "h1", "canonical", "robots", "words", "schema", "author", "faq", "q-h2/3", "in/depth"]
    lines = ["| " + " | ".join(md_cols) + " |", "|" + "---|" * len(md_cols)]
    for r in rows:
        t = r.get("title", "")
        tl = r.get("title_len", 0)
        dl = r.get("description_len", 0)
        h1c = r.get("h1_count", "")
        cells = [
                    path_of(r["url"]),
                    str(r["status"]) + (f" ({r['hops']} hop)" if r.get("hops") else "") + (f" {r['error']}" if r.get("error") else ""),
                    (t[:50] + ("…" if len(t) > 50 else "") + f" ({tl})") if t else ("—" if r["status"] else ""),
                    (str(dl) if dl else "missing") if "description_len" in r else "",
                    (f"{h1c}× " + (r.get("h1", "")[:40] or "")) if h1c != "" else "",
                    r.get("canonical_ok", ""),
                    r.get("robots_meta", "") or "—",
                    str(r.get("word_count", "")),
                    ",".join(r.get("schema_types", [])) or "—",
                    cell(r, "author_present"),
                    (cell(r, "faq_visible") + "/" + cell(r, "faq_schema")) if "faq_visible" in r else "",
                    str(r.get("question_headings", "")),
                    (f"{r.get('inlinks', 0)}/{'-' if r.get('depth') is None else r.get('depth')}") if r.get("status") == 200 else "",
                ]
        lines.append("| " + " | ".join(c.replace("|", "\\|") for c in cells) + " |")
    with open(os.path.join(out, "pages.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
        f.write("\nfaq = visible/schema · q-h2/3 = question-phrased H2/H3 · in/depth = inbound links from fetched pages / clicks from home (- = unreachable) · og = t/d/i for og:title / og:description / og:image present\n")
    with open(os.path.join(out, "site.json"), "w", encoding="utf-8") as f:
        json.dump(doc["site"], f, indent=2, ensure_ascii=False)
    with open(os.path.join(out, "collect.json"), "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=2, ensure_ascii=False)


# ---------------------------------------------------------------- main
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("base_url")
    ap.add_argument("--mode", choices=["quick", "full"], default="quick")
    ap.add_argument("--urls", help="file with one URL per line; overrides discovery")
    ap.add_argument("--out", help="output directory")
    ap.add_argument("--max-pages", type=int, default=150)
    ap.add_argument("--timeout", type=float, default=15.0)
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--fixed-time", help="ISO timestamp to stamp instead of now (tests)")
    ap.add_argument("--insecure", action="store_true", help="skip TLS verification (recorded in site.json; last resort)")
    ap.add_argument("--allow-private", action="store_true", help="allow private / loopback targets (a site you run locally)")
    ap.add_argument("--plan", action="store_true", help="fetch only home + robots + sitemap and print what Quick / Full / --all would fetch")
    ap.add_argument("--per-section", type=int, default=10, help="Full mode: sitemap URLs sampled per top-level section (newest first)")
    ap.add_argument("--all", action="store_true", help="fetch every discovered page (no section sampling, no cap)")
    ap.add_argument("--sitemap-status", action="store_true", help="also HEAD every sitemap URL that was not fetched: status, redirects (no parsing)")
    a = ap.parse_args(argv)
    global _INSECURE, _ALLOW_PRIVATE
    _INSECURE = a.insecure
    _ALLOW_PRIVATE = a.allow_private

    base = a.base_url if re.match(r"^https?://", a.base_url, re.I) else "https://" + a.base_url
    if not urllib.parse.urlsplit(base).path:
        base += "/"
    host = host_of(base)
    now = a.fixed_time or dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    out = a.out or os.path.join(".rolepod-seo", f"collect-{host.replace(':', '-')}-{now[:10].replace('-', '')}")

    def log(msg: str):
        if not a.quiet:
            print(msg, file=sys.stderr)

    log(f"rolepod-seo collect v{VERSION} — {base} ({a.mode})")

    # 1. home
    home = fetch(base, a.timeout)
    if home["error"].startswith("refused:"):
        print(f"{home['error']} — pass --allow-private only for a site you run locally", file=sys.stderr)
        return 2
    home_row = page_facts(base, home)
    if home["error"] or home["status"] >= 400:
        log(f"home: {home['status']} {home['error']}")

    # 2. robots + sitemap + llms.txt
    origin = urllib.parse.urlsplit(home["final_url"] if home["final_url"].startswith("http") else base)
    root = f"{origin.scheme}://{origin.netloc}/"
    rob = fetch(root + "robots.txt", a.timeout)
    groups, robot_sitemaps = ([], [])
    if rob["status"] == 200 and rob["body"]:
        groups, robot_sitemaps = parse_robots(decode(rob["body"], rob["content_type"]))
    robots_info = {
        "url": root + "robots.txt",
        "status": rob["status"],
        "error": rob["error"],
        "sitemaps_declared": robot_sitemaps,
        "agents": {ua: robots_verdict(groups, ua) for ua in BOTS},
        "wildcard": robots_verdict(groups, "*") if groups else {"verdict": "no-rules", "via": "none", "disallow": []},
        "blocks_assets": any(re.search(r"\.(css|js)\b|/wp-includes|/assets|/static|/_next", p, re.I) for _, r in groups for k, p in r if k == "disallow"),
    }
    sm_urls = [urllib.parse.urljoin(root, s) for s in robot_sitemaps] or [root + "sitemap.xml"]
    sitemap = read_sitemaps(sm_urls, a.timeout, log)
    if not sitemap["entries"] and not robot_sitemaps:
        alt = read_sitemaps([root + "sitemap_index.xml"], a.timeout, log)
        if alt["entries"]:
            sitemap = alt
    llms = fetch(root + "llms.txt", a.timeout, limit=50_000)
    llms_present = llms["status"] == 200 and b"<html" not in llms["body"][:2000].lower()

    # 3. page selection
    selection_info: dict = {}
    selected_by: dict[str, str] = {norm(base): "home"}
    if a.urls:
        with open(a.urls, encoding="utf-8") as f:
            urls = [l.strip() for l in f if l.strip() and not l.startswith("#")]
        if norm(base) not in {norm(u) for u in urls}:
            urls = [base] + urls
        for u in urls[1:]:
            selected_by[norm(u)] = "list"
        selection_info = {"source": "--urls", "count": len(urls)}
    else:
        picks, selection_info = select_pages(base, home_row, sitemap["entries"], a.mode, a.max_pages, a.per_section, a.all)
        urls = [u for u, _ in picks]
        for u, why in picks:
            selected_by[norm(u)] = why
        selection_info["source"] = "all" if a.all else a.mode
    if a.plan:
        quick_picks, qi = select_pages(base, home_row, sitemap["entries"], "quick", a.max_pages, a.per_section, False)
        full_picks, fi = select_pages(base, home_row, sitemap["entries"], "full", a.max_pages, a.per_section, False)
        all_picks, _ = select_pages(base, home_row, sitemap["entries"], "full", a.max_pages, a.per_section, True)
        plan = {
            "base_url": base, "sitemap_urls": len(sitemap["entries"]), "structure_source": qi["structure_source"],
            "sitemap_l1": qi["sitemap_l1"], "sitemap_l2": qi["sitemap_l2"], "menu_extra": qi["menu_extra"], "submenu_extra": qi["submenu_extra"],
            "menu_main": qi["menu_main"], "menu_sub": qi["menu_sub"], "nav_fallback": qi["nav_fallback"],
            "quick": {"pages": len(quick_picks), "est_seconds": round(len(quick_picks) * 0.6), "cap_hit": qi.get("quick_cap_hit", False)},
            "full": {"pages": len(full_picks), "est_seconds": round(len(full_picks) * 0.6), "sections": fi["sections"], "per_section": a.per_section},
            "all": {"pages": len(all_picks), "est_seconds": round(len(all_picks) * 0.6)},
        }
        print(json.dumps(plan, indent=2, ensure_ascii=False))
        log(f"plan: structure from {plan['structure_source']} · sitemap {plan['sitemap_urls']} (level-1 {plan['sitemap_l1']}, level-2 sampled {plan['sitemap_l2']}) · menu extra {plan['menu_extra']}+{plan['submenu_extra']} → quick {plan['quick']['pages']} pages (~{plan['quick']['est_seconds']}s), full {plan['full']['pages']} (~{plan['full']['est_seconds']}s), all {plan['all']['pages']} (~{plan['all']['est_seconds']}s)")
        return 0
    log(f"pages: {len(urls)} selected ({selection_info.get('source')}, structure from {selection_info.get('structure_source', '--urls')}; sitemap level-1 {selection_info.get('sitemap_l1', 0)} + level-2 {selection_info.get('sitemap_l2', 0)}, menu extra {selection_info.get('menu_extra', 0)}+{selection_info.get('submenu_extra', 0)})")

    # 4. fetch pages
    rows = [home_row]
    for u in urls[1:]:
        res = fetch(u, a.timeout)
        rows.append(page_facts(u, res))
        log(f"  {res['status'] or 'ERR':>4} {path_of(u)}")
    if a.mode == "full" and not a.urls:
        have = {norm(r["url"]) for r in rows}
        extra: list[str] = []
        for r in rows:
            for h in r.get("hreflang", []):
                u = h["href"]
                if same_origin(u, base) and norm(u) not in have and not SKIP_RE.search(u) and not ASSET_RE.search(u):
                    have.add(norm(u))
                    extra.append(u)
        for u in extra[:50]:
            res = fetch(u, a.timeout)
            rows.append(page_facts(u, res))
            log(f"  {res['status'] or 'ERR':>4} {path_of(u)}  (hreflang alternate)")
    for r in rows:
        r["role"] = page_role(r["url"], base)
        r["selected_by"] = selected_by.get(norm(r["url"]), "hreflang")
    sitemap_set = {norm(e["loc"]) for e in sitemap["entries"]}
    for r in rows:
        r["in_sitemap"] = norm(r["url"]) in sitemap_set

    # 5. site-level cross-page facts
    by_title: dict[str, list[str]] = {}
    by_desc: dict[str, list[str]] = {}
    for r in rows:
        if r.get("title"):
            by_title.setdefault(r["title"], []).append(path_of(r["url"]))
        if r.get("description"):
            by_desc.setdefault(r["description"], []).append(path_of(r["url"]))
    fetched_norm = {norm(r["url"]): r for r in rows}
    sitemap_not_ok = [e["loc"] for e in sitemap["entries"] if norm(e["loc"]) in fetched_norm and fetched_norm[norm(e["loc"])]["status"] != 200]
    sitemap_noindex = [e["loc"] for e in sitemap["entries"] if norm(e["loc"]) in fetched_norm and fetched_norm[norm(e["loc"])].get("noindex")]
    unchecked = [e["loc"] for e in sitemap["entries"] if norm(e["loc"]) not in fetched_norm]

    variants = {}
    if not is_local(host):
        h = origin.netloc
        alt_host = h[4:] if h.startswith("www.") else "www." + h
        for label, u in (("http", f"http://{h}/"), ("alt-host", f"{origin.scheme}://{alt_host}/")):
            v = fetch(u, a.timeout, limit=1000)
            variants[label] = {"url": u, "status": v["status"], "final_url": v["final_url"], "hops": len(v["hops"]), "error": v["error"]}
    else:
        variants = {"note": "not assessed (local host)"}

    body_l = home["body"][:400_000].lower()
    platform_signals = [name for name, needle in (
        ("wordpress", b"/wp-content/"), ("nextjs", b"/_next/"), ("nuxt", b"/_nuxt/"), ("gatsby", b"/gatsby"),
        ("shopify", b"cdn.shopify.com"), ("wix", b"wixstatic.com"), ("squarespace", b"squarespace"),
        ("webflow", b"webflow"), ("hubspot", b"hubspot"), ("framer", b"framerusercontent"),
        ("astro", b"astro-"), ("drupal", b"/sites/default/files"), ("joomla", b"/media/jui/"),
    ) if needle in body_l]
    platform_hints = {"generator": home_row.get("generator", ""), "signals": platform_signals}

    orphan_candidates = [path_of(e["loc"]) for e in sitemap["entries"] if norm(e["loc"]) not in {norm(u) for u in home_row.get("_internal_links", [])} and norm(e["loc"]) != norm(base)]

    site = {
        "base_url": base,
        "host": host,
        "final_home_url": home["final_url"],
        "home_status": home["status"],
        "https": home["final_url"].startswith("https://"),
        "tls_verify": not a.insecure,
        "platform_hints": platform_hints,
        "robots": robots_info,
        "sitemap": {
            "declared_in_robots": bool(robot_sitemaps),
            "files": sitemap["checked"],
            "url_count": len(sitemap["entries"]),
            "with_lastmod": sum(1 for e in sitemap["entries"] if e["lastmod"]),
            "errors": sitemap["errors"],
            "listed_but_not_200": sitemap_not_ok,
            "listed_but_noindex": sitemap_noindex,
            "not_fetched_count": len(unchecked),
            "not_linked_from_home": orphan_candidates[:50],
        },
        "llms_txt": {"url": root + "llms.txt", "present": llms_present, "status": llms["status"]},
        "host_variants": variants,
        "duplicates": {
            "titles": {t: p for t, p in by_title.items() if len(p) > 1},
            "descriptions": {d: p for d, p in by_desc.items() if len(p) > 1},
        },
        "redirect_chains": [{"url": r["url"], "chain": r["redirect_chain"]} for r in rows if r.get("hops", 0) >= 1],
        "failed_pages": [{"url": r["url"], "status": r["status"], "error": r["error"]} for r in rows if r["status"] != 200 or r["error"]],
        "pages_fetched": sum(1 for r in rows if r["status"] == 200),
        "pages_selected": len(rows),
    }
    sitemap_status = None
    if a.sitemap_status:
        fetched_keys = {norm(r["url"]) for r in rows}
        todo = [e["loc"] for e in sitemap["entries"] if norm(e["loc"]) not in fetched_keys][:5000]
        counts = {"checked": 0, "ok": 0, "redirect": 0, "not_found": 0, "error": 0}
        problems: list[dict] = []
        status_rows: list[str] = ["url\tstatus\tfinal_url\thops"]
        for u in todo:
            res = head(u, min(a.timeout, 10.0))
            counts["checked"] += 1
            kind = "error" if res["error"] else ("not_found" if res["status"] >= 400 else ("redirect" if res["hops"] else "ok"))
            counts[kind] += 1
            if kind != "ok":
                problems.append({"url": u, "status": res["status"], "final_url": res["final_url"], "hops": res["hops"], "error": res["error"]})
            status_rows.append(f"{u}\t{res['status']}\t{res['final_url']}\t{res['hops']}")
        os.makedirs(out, exist_ok=True)
        with open(os.path.join(out, "sitemap-status.tsv"), "w", encoding="utf-8") as f:
            f.write("\n".join(status_rows) + "\n")
        sitemap_status = {**counts, "problems": problems[:200], "file": "sitemap-status.tsv"}
        log(f"sitemap status: {counts}")
    graph = link_graph(rows, base)
    dups = near_duplicates(rows)
    stype = site_type(rows, home_row.get("_text", ""))
    hh = home_row.get("_headers", {})
    site["link_graph"] = graph
    site["near_duplicates"] = dups
    site["site_type"] = stype
    site["selection"] = selection_info
    site["sitemap_status"] = sitemap_status
    site["hreflang"] = hreflang_report(rows)
    tp_pages: dict[str, int] = {}
    for r in rows:
        for h in r.get("third_party_hosts", []):
            tp_pages[h] = tp_pages.get(h, 0) + 1
    site["third_party"] = {
        "hosts": dict(sorted(tp_pages.items(), key=lambda kv: (-kv[1], kv[0]))),
        "analytics": sorted({a for r in rows for a in r.get("analytics", [])}),
        "home_count": len(home_row.get("third_party_hosts", [])),
    }
    site["security"] = {
        "hsts": "strict-transport-security" in hh,
        "hsts_value": hh.get("strict-transport-security", ""),
        "csp": "content-security-policy" in hh,
        "x_content_type_options": hh.get("x-content-type-options", ""),
        "server": hh.get("server", ""),
    }
    for r in rows:
        r.pop("_internal_links", None)
        r.pop("_nav_links", None)
        r.pop("_text", None)
        r.pop("_headers", None)
    doc = {
        "tool": "rolepod-seo/collect",
        "version": VERSION,
        "collected_at": now,
        "base_url": base,
        "mode": a.mode,
        "pages": rows,
        "site": site,
    }
    write_outputs(out, doc)
    log(f"site type: {stype['type']} ({stype['confidence']}) · near-duplicates: {len(dups)} · unreachable from home: {len(graph['unreachable_from_home'])}")
    log(f"wrote {out}/pages.md, pages.tsv, site.json, collect.json — {site['pages_fetched']}/{site['pages_selected']} pages 200")
    print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
