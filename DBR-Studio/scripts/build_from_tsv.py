import csv, json, os, re, subprocess
from datetime import datetime

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_FILE = os.path.join(ROOT, "data", "submissions.tsv")
OUT_FILE = os.path.join(ROOT, "posts", "posts.json")

APPROVED_ONLY = True  # Only include rows with Status == Approved

def to_iso(date_str: str) -> str:
    if not date_str.strip():
        return ""
    try:
        return datetime.fromisoformat(date_str).date().isoformat()
    except Exception:
        try:
            return datetime.strptime(date_str, "%m/%d/%Y %H:%M").date().isoformat()
        except Exception:
            return ""

def split_multi(s: str):
    if not s.strip():
        return []
    return [x.strip() for x in re.split(r"[,;\n\r]+", s) if x.strip()]

def build_embed(link: str):
    if not link.strip():
        return {"embed": "", "linkOut": ""}
    t = link.strip()
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

def main():
    if not os.path.exists(DATA_FILE):
        print(f"[ERROR] Missing TSV: {DATA_FILE}")
        return 1

    with open(DATA_FILE, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        rows = list(reader)

    posts = []
    published, skipped = 0, 0

    for i, row in enumerate(rows, start=2):  # +2 because header = 1
        status = row.get("Status", "").strip().lower()
        if APPROVED_ONLY and status != "approved":
            print(f"- Row {i}: SKIP (Status={status or 'blank'}) — title=\"{row.get('Post Title','')}\"")
            skipped += 1
            continue

        title   = row.get("Post Title", "").strip()
        summary = row.get("Post Caption/Summary", "").strip()
        nick    = row.get("Name/Nickname", "").strip() or row.get("Name", "").strip()
        typeRaw = row.get("Post Type", "").strip().lower()
        link    = row.get("Link", "").strip()
        files   = row.get("Upload Files!", "").strip()
        date    = to_iso(row.get("Start time", "") or row.get("Completion time", ""))

        tags = []
        if typeRaw == "music": tags.append("music")
        if typeRaw in ("photos","photo"): tags.append("photography")
        if typeRaw == "art": tags.append("art")
        if "forms.office.com" in link or link.strip().startswith("<iframe"): tags.append("poll")

        embed_info = build_embed(link)
        images = split_multi(files)

        post = {}
        if title: post["title"] = title
        if date: post["date"] = date
        if summary: post["summary"] = summary
        if tags: post["tags"] = tags
        if len(images) > 1: post["images"] = images
        elif len(images) == 1: post["image"] = images[0]
        if embed_info["embed"]: post["embed"] = embed_info["embed"]
        if not embed_info["embed"] and embed_info["linkOut"]: post["link"] = embed_info["linkOut"]
        if nick: post["caption"] = f"Submitted by {nick}"

        # Feedback
        parts = []
        parts.append("title" if title else "title?")
        parts.append("date" if date else "date?")
        if tags: parts.append("tags:" + "|".join(tags))
        if "image" in post: parts.append("1 image")
        if "images" in post: parts.append(f"{len(post['images'])} images")
        if "embed" in post: parts.append("embed")
        if "link" in post: parts.append("link")
        if not any(k in post for k in ["image","images","embed","link"]): parts.append("(no media)")
        if any("sharepoint" in str(u).lower() or "onedrive" in str(u).lower() for u in images):
            parts.append("⚠ SharePoint/OneDrive URL (not public)")

        print(f"+ Row {i}: " + " | ".join(parts))

        posts.append(post)
        published += 1

    posts.sort(key=lambda p: p.get("date",""), reverse=True)

    os.makedirs(os.path.dirname(OUT_FILE), exist_ok=True)
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(posts, f, indent=2)
    print("----")
    print(f"Wrote {len(posts)} posts → {OUT_FILE}")
    print(f"Published: {published} | Skipped: {skipped}")

    return 0

if __name__ == "__main__":
    raise SystemExit(main())
