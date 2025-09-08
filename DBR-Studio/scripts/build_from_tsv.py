import csv, json, os, re, subprocess
from datetime import datetime
from urllib.parse import urlparse, unquote

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_FILE = os.path.join(ROOT, "data", "submissions.tsv")
OUT_FILE = os.path.join(ROOT, "posts", "posts.json")

APPROVED_ONLY = True  # Only include rows with Status == Approved

# ===== Image path rewrite config =====
# Where images live in the repo on disk:
REPO_PHOTOS_DIR = os.path.join(ROOT, "photos")
# How your site references them (web path):
REPO_WEB_BASE   = "/DBR-Studio/photos"
# Prefer /photos/{YYYY}/filename when a date is present
PREFER_YEAR_SUBFOLDER = False
# ====================================

def to_iso(date_str: str) -> str:
    s = (date_str or "").strip()
    if not s:
        return ""
    # Try ISO first, then common US m/d/Y H:M (Excel copy)
    for fmt in ("%Y-%m-%d", "%m/%d/%Y %H:%M", "%m/%d/%Y"):
        try:
            dt = datetime.strptime(s, fmt)
            return dt.date().isoformat()
        except Exception:
            pass
    # Fallback: let Python try parsing flexibly
    try:
        return datetime.fromisoformat(s).date().isoformat()
    except Exception:
        return ""

def split_multi(s: str):
    if not s or not s.strip():
        return []
    return [x.strip() for x in re.split(r"[,;\n\r]+", s) if x.strip()]

def build_embed(link: str):
    t = (link or "").strip()
    if not t:
        return {"embed": "", "linkOut": ""}
    if t.startswith("<iframe"):
        return {"embed": t, "linkOut": ""}
    if "forms.office.com" in t:
        url = t if t.startswith("http") else "https://" + t
        if "embed=true" not in url:
            url += "&embed=true" if "?" in url else "?embed=true"
        return {
            "embed": f'<iframe src="{url}" width="640" height="480" frameborder="0" style="border:none; max-width:100%; height:520px" allowfullscreen></iframe>',
            "linkOut": "",
        }
    if any(x in t for x in ["youtube.com", "youtu.be", "spotify.com"]):
        return {"embed": f'<iframe src="{t}" frameborder="0" allowfullscreen></iframe>', "linkOut": ""}
    return {"embed": "", "linkOut": t}

def extract_filename(url_or_path: str) -> str:
    """Return last path segment without query string; URL-decoded."""
    s = (url_or_path or "").strip()
    if not s:
        return ""
    # If it looks like HTML (iframe), nothing to do
    if s.startswith("<"):
        return ""
    # Strip query/hash
    if "?" in s: s = s.split("?", 1)[0]
    if "#" in s: s = s.split("#", 1)[0]
    # If it’s a URL, parse path; else treat as path already
    try:
        p = urlparse(s)
        path_part = p.path if p.scheme else s
    except Exception:
        path_part = s
    base = os.path.basename(path_part)
    return unquote(base)

def find_repo_photo_path(filename: str, year_hint: str | None) -> str | None:
    """Return repo web path like /dbr-studio/photos/2025/file.jpg if the file exists in repo."""
    if not filename:
        return None

    # Try year subfolder first, if configured and available
    if PREFER_YEAR_SUBFOLDER and year_hint:
        ydir = os.path.join(REPO_PHOTOS_DIR, year_hint)
        candidate = os.path.join(ydir, filename)
        if os.path.isfile(candidate):
            return f"{REPO_WEB_BASE}/{year_hint}/{filename}"

    # Try direct in photos root
    candidate = os.path.join(REPO_PHOTOS_DIR, filename)
    if os.path.isfile(candidate):
        return f"{REPO_WEB_BASE}/{filename}"

    # Walk the photos tree to find the first case-insensitive match
    lower_name = filename.lower()
    for root, _dirs, files in os.walk(REPO_PHOTOS_DIR):
        for f in files:
            if f.lower() == lower_name:
                rel = os.path.relpath(os.path.join(root, f), REPO_PHOTOS_DIR).replace("\\", "/")
                return f"{REPO_WEB_BASE}/{rel}"

    return None

def rewrite_images(values: list[str], iso_date: str) -> tuple[list[str], list[str]]:
    """Map incoming image values to repo paths if possible. Returns (rewritten, warnings)."""
    warnings = []
    year_hint = iso_date[:4] if (iso_date and len(iso_date) >= 4) else None
    out = []
    for v in values:
        # Already a repo path? keep as-is.
        if v.startswith(REPO_WEB_BASE) or v.startswith("/" + REPO_WEB_BASE.lstrip("/")):
            out.append(v)
            continue

        fn = extract_filename(v)
        mapped = find_repo_photo_path(fn, year_hint) if fn else None
        if mapped:
            out.append(mapped)
        else:
            out.append(v)  # keep original (may be SharePoint)
            if ("sharepoint" in v.lower() or "onedrive" in v.lower()):
                warnings.append(f"image not found in repo for '{fn or v}' (left SharePoint/OneDrive URL)")
            else:
                warnings.append(f"image not found in repo for '{fn or v}'")
    return out, warnings

def main():
    if not os.path.exists(DATA_FILE):
        print(f"[ERROR] Missing TSV: {DATA_FILE}")
        return 1

    import csv
    with open(DATA_FILE, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        rows = list(reader)

    APPROVED_VALUES = {"approved", "accept", "accepted", "yes", "ok", "publish", "published", "ready"}

    items = []      # will hold (row_index, iso_date, post_dict)
    published = 0
    skipped = 0

    for i, row in enumerate(rows, start=2):  # header is line 1
        status = (row.get("Status", "") or "").strip().lower()

        is_publish = (status in APPROVED_VALUES) or (not APPROVED_ONLY and status != "rejected")
        if not is_publish:
            print(f"- Row {i}: SKIP (Status={status or 'blank'}) — title=\"{row.get('Post Title','')}\"")
            skipped += 1
            continue

        title   = (row.get("Post Title", "") or "").strip()
        summary = (row.get("Post Caption/Summary", "") or "").strip()
        nick    = (row.get("Name/Nickname", "") or "").strip() or (row.get("Name", "") or "").strip()
        typeRaw = (row.get("Post Type", "") or "").strip().lower()
        link    = (row.get("Link", "") or "").strip()
        files   = (row.get("Upload Files!", "") or "").strip()
        date    = to_iso((row.get("Start time", "") or "") or (row.get("Completion time", "") or ""))

        tags = []
        if typeRaw == "music": tags.append("music")
        if typeRaw in ("photos", "photo"): tags.append("photography")
        if typeRaw == "art": tags.append("art")
        if "forms.office.com" in link or link.startswith("<iframe"): tags.append("poll")

        embed_info = build_embed(link)

        # Images: split then rewrite to repo paths if found
        raw_images = split_multi(files)
        rewritten_images, img_warnings = rewrite_images(raw_images, date)

        post = {}
        if title:   post["title"] = title
        if date:    post["date"] = date
        if summary: post["summary"] = summary
        if tags:    post["tags"] = tags
        if len(rewritten_images) > 1:
            post["images"] = rewritten_images
        elif len(rewritten_images) == 1:
            post["image"] = rewritten_images[0]
        if embed_info["embed"]:
            post["embed"] = embed_info["embed"]
        elif embed_info["linkOut"]:
            post["link"] = embed_info["linkOut"]
        if nick:
            post["caption"] = f"Submitted by {nick}"

        # Feedback
        parts = []
        parts.append("title" if title else "title?")
        parts.append("date" if date else "date?")
        if tags: parts.append("tags:" + "|".join(tags))
        if "image" in post: parts.append("1 image")
        if "images" in post: parts.append(f"{len(post['images'])} images")
        if "embed" in post: parts.append("embed")
        if "link" in post: parts.append("link")
        if not any(k in post for k in ["image", "images", "embed", "link"]): parts.append("(no media)")
        for w in img_warnings: parts.append("⚠ " + w)

        print(f"+ Row {i}: " + " | ".join(parts))

        items.append((i, post.get("date", ""), post))  # only append when we HAVE a post
        published += 1

    # Sort: newest first; undated at the bottom; stable on original row order
    # Key: (undated?, date_iso, row_index); we sort ascending, then reverse
    items.sort(key=lambda t: (t[1] == "", t[1], t[0]))
    items.reverse()

    final_posts = [p for (_i, _d, p) in items]

    os.makedirs(os.path.dirname(OUT_FILE), exist_ok=True)
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(final_posts, f, indent=2)

    print("----")
    print(f"Wrote {len(final_posts)} posts → {OUT_FILE}")
    print(f"Published: {published} | Skipped: {skipped}")
    return 0


# Sort: newest first by date; if equal/missing, keep original TSV order
def sort_key(item):
    d = item["_date"]
    # Convert to tuple for proper ordering: missing dates sort last
    return (d != "", d)  # True/False (so True > False), then ISO string
    posts.sort(key=lambda it: (it["_date"] == "", it["_date"], it["_row"]))  # oldest first
    posts.reverse()  # now newest first, preserving stable order among equals

    # Strip helpers back out
    final_posts = [it["post"] for it in posts]

    os.makedirs(os.path.dirname(OUT_FILE), exist_ok=True)
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(final_posts, f, indent=2)

    print("----")
    print(f"Wrote {len(final_posts)} posts → {OUT_FILE}")
    print(f"Published: {published} | Skipped: {skipped}")

    return 0

if __name__ == "__main__":
    raise SystemExit(main())
