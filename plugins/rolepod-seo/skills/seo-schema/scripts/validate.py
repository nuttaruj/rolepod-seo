#!/usr/bin/env python3
"""rolepod-seo — JSON-LD validator (Python stdlib only).

Usage:
  validate.py <file.json | file.html | https://url> [...]
  echo '{...}' | validate.py -

For each input: extract JSON-LD (raw JSON, or every
<script type="application/ld+json"> in HTML), parse it, walk the graph,
and check the rolepod minimum properties per type (the Required column of
references/schema-minimums.md — kept in lockstep by make test-static).
Exit 1 when any block fails to parse or any typed node misses a required
property. Prints one line per node.
"""
from __future__ import annotations

import json
import os
import re
import ssl
import sys
import urllib.request
from html.parser import HTMLParser

# type -> required properties; a tuple means "at least one of"
REQUIRED: dict[str, list] = {
    "Organization": ["name", "url", "logo"],
    "LocalBusiness": ["name", "address", "telephone"],
    "WebSite": ["name", "url"],
    "BreadcrumbList": ["itemListElement"],
    "Article": ["headline", "datePublished", "author.name", "image"],
    "Product": ["name", ("offers", "review", "aggregateRating")],
    "FAQPage": ["mainEntity"],
    "HowTo": ["name", "step"],
    "Person": ["name"],
    "Service": ["name", "provider"],
    "Event": ["name", "startDate", "location"],
    "VideoObject": ["name", "thumbnailUrl", "uploadDate"],
    "Review": ["itemReviewed", "author", "reviewRating"],
    "AggregateRating": ["ratingValue", ("reviewCount", "ratingCount")],
}
ALIASES = {
    "BlogPosting": "Article", "NewsArticle": "Article", "TechArticle": "Article",
    "Plumber": "LocalBusiness", "Dentist": "LocalBusiness", "Restaurant": "LocalBusiness",
    "Store": "LocalBusiness", "MedicalBusiness": "LocalBusiness", "LegalService": "LocalBusiness",
    "ProfessionalService": "LocalBusiness", "HomeAndConstructionBusiness": "LocalBusiness",
    "Corporation": "Organization", "NGO": "Organization", "EducationalOrganization": "Organization",
}
CA_BUNDLES = ("/etc/ssl/cert.pem", "/etc/ssl/certs/ca-certificates.crt", "/etc/pki/tls/certs/ca-bundle.crt",
              "/opt/homebrew/etc/openssl@3/cert.pem", "/usr/local/etc/openssl@3/cert.pem")


class _LD(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.blocks: list[str] = []
        self._buf: list[str] | None = None

    def handle_starttag(self, tag, attrs):
        a = {k: (v or "") for k, v in attrs}
        if tag == "script" and a.get("type", "").replace(" ", "").lower() == "application/ld+json":
            self._buf = []

    def handle_endtag(self, tag):
        if tag == "script" and self._buf is not None:
            self.blocks.append("".join(self._buf))
            self._buf = None

    def handle_data(self, data):
        if self._buf is not None:
            self._buf.append(data)


def read_source(src: str) -> str:
    if src == "-":
        return sys.stdin.read()
    if re.match(r"^https?://", src, re.I):
        ctx = ssl.create_default_context()
        for p in CA_BUNDLES:
            if os.path.exists(p):
                try:
                    ctx.load_verify_locations(p)
                except Exception:
                    pass
        req = urllib.request.Request(src, headers={"User-Agent": "Mozilla/5.0 (compatible; rolepod-seo/0.1)"})
        with urllib.request.urlopen(req, timeout=20, context=ctx) as r:
            return r.read(2_000_000).decode("utf-8", "replace")
    with open(src, encoding="utf-8") as f:
        return f.read()


def blocks_from(text: str) -> list[str]:
    stripped = text.lstrip()
    if stripped.startswith("{") or stripped.startswith("["):
        return [text]
    p = _LD()
    p.feed(text)
    p.close()
    return p.blocks


def get_path(node: dict, path: str):
    cur = node
    for part in path.split("."):
        if isinstance(cur, list):
            cur = cur[0] if cur else None
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def present(node: dict, req) -> bool:
    if isinstance(req, tuple):
        return any(present(node, r) for r in req)
    v = get_path(node, req)
    return v not in (None, "", [], {})


def label(req) -> str:
    return " / ".join(req) if isinstance(req, tuple) else req


def walk(data):
    stack = [data]
    while stack:
        x = stack.pop(0)
        if isinstance(x, dict):
            yield x
            stack.extend(v for v in x.values() if isinstance(v, (dict, list)))
        elif isinstance(x, list):
            stack.extend(x)


def check_block(raw: str, where: str) -> tuple[int, int]:
    ok = fail = 0
    try:
        data = json.loads(raw.strip())
    except json.JSONDecodeError as e:
        print(f"FAIL {where}: JSON-LD does not parse — {e.msg} at line {e.lineno} col {e.colno}")
        return 0, 1
    ctx = data.get("@context") if isinstance(data, dict) else None
    if isinstance(data, dict) and ctx is not None and "schema.org" not in json.dumps(ctx):
        print(f"WARN {where}: @context is {ctx!r}, expected schema.org")
    typed = 0
    for node in walk(data):
        t = node.get("@type")
        types = t if isinstance(t, list) else ([t] if t else [])
        for ty in types:
            key = ALIASES.get(str(ty), str(ty))
            if key not in REQUIRED:
                continue
            typed += 1
            missing = [label(r) for r in REQUIRED[key] if not present(node, r)]
            name = node.get("name") or node.get("headline") or node.get("@id") or ""
            if missing:
                fail += 1
                print(f"FAIL {where}: {ty} {name!r} missing {', '.join(missing)}")
            else:
                ok += 1
                print(f"ok   {where}: {ty} {name!r}")
    if typed == 0:
        print(f"WARN {where}: parsed, but no node of a known type (see references/schema-minimums.md)")
    return ok, fail


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    total_fail = 0
    for src in argv:
        try:
            text = read_source(src)
        except Exception as e:
            print(f"FAIL {src}: cannot read — {type(e).__name__}: {e}")
            total_fail += 1
            continue
        blocks = blocks_from(text)
        if not blocks:
            print(f"FAIL {src}: no JSON-LD found")
            total_fail += 1
            continue
        for i, raw in enumerate(blocks, 1):
            where = src if len(blocks) == 1 else f"{src}#{i}"
            _, f = check_block(raw, where)
            total_fail += f
    return 1 if total_fail else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
