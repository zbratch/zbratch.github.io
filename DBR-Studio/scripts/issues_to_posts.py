import os, re, json, glob, pathlib, requests, yaml
from datetime import datetime, timedelta, timezone

REPO = os.environ["GITHUB_REPO"]
TOKEN = os.environ["GITHUB_TOKEN"]
API = f"https://api.github.com/repos/{REPO}"

POSTS_DIR = pathlib.Path("_posts")
POSTS_DIR.mkdir(parents=True, exist_ok=True)

def excel_serial_to_dt(s):
    """Accept Excel serial like 45916.35 and return UTC datetime."""
    try:
        f = float(str(s))
    except Exception:
        return None
    base = datetime(1899, 12, 30, tzinfo=timezone.utc)  # Excel's "serial 0"
    days = int(f)
    seconds = round((f - days) * 86400)
    return base + timedelta(days=days, seconds=seconds)

def parse_date(any_val):
    if any_val is None or str(any_val).strip()=="":
        return datetime.now(timezone.utc)
    s = str(any_val).strip()
    # try ISO
    for fmt in ("%Y-%m-%dT%H:%M:%SZ","%Y-%m-%d %H:%M:%S","%Y-%m-%d"):
        try:
            dt = datetime.strptime(s, fmt).replace(tzinfo=timezone.utc)
            return dt
        except Exception:
            pass
    # try excel serial
    dt = excel_serial_to_dt(s)
    return dt or datetime.now(timezone.utc)

def slugify(title):
    s = re.sub(r"[^\w\s-]", "", title.lower())
    s = re.sub(r"[\s_-]+", "-", s).strip("-")
    return s or "post"

def split_frontmatter(body):
    m = re.search(r"(?s)^---\s*\n(.*?)\n---\s*\n?(.*)$", body)
    if not m:
        return None, body
    return m.group(1), m.group(2)

def load_issue_from_event():
    path = os.environ.get("GITHUB_EVENT_PATH")
    if not path or not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        evt = json.load(f)
    if "issue" in evt:
        return [evt["issue"]]
    return None

def fetch_issues():
    # Open issues only; we’ll consider ones that have front matter.
    out = []
    page = 1
    while True:
        r = requests.get(f"{API}/issues", params={"state":"open","per_page":100,"page":page},
                         headers={"Authorization": f"Bearer {TOKEN}",
                                  "Accept":"application/vnd.github+json"})
        r.raise_for_status()
        batch = r.json()
        out += batch
        if len(batch) < 100:
            break
        page += 1
    return out

def ensure_list_images(val):
    if isinstance(val, list):
        return [str(x).strip() for x in val if str(x).strip()]
    s = str(val or "").strip()
    return [s] if s else []

def find_existing_file(issue_number):
    pattern = str(POSTS_DIR / f"*-i{issue_number}.md")
    matches = glob.glob(pattern)
    return pathlib.Path(matches[0]) if matches else None

def write_post(issue, fm_dict, content):
    title = fm_dict.get("title") or issue["title"]
    dt = parse_date(fm_dict.get("date"))
    slug = slugify(title)
    images = ensure_list_images(fm_dict.get("images"))
    data = {
        "layout": "post",
        "title": title,
        "author": fm_dict.get("author",""),
        "category": fm_dict.get("category",""),
        "caption": fm_dict.get("caption",""),
        "link": fm_dict.get("link",""),
        "images": images,
        "date": dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "published": bool(fm_dict.get("published", True)),
        "issue_number": issue["number"],
    }

    # Keep one file per issue for idempotency
    path = find_existing_file(issue["number"])
    if not path:
        fname = f"{dt.strftime('%Y-%m-%d')}-{slug}-i{issue['number']}.md"
        path = POSTS_DIR / fname

    # Build file text
    front = yaml.safe_dump(data, sort_keys=False, allow_unicode=True).strip()
    text = f"---\n{front}\n---\n\n{content.strip()}\n"
    path.write_text(text, encoding="utf-8")
    print(f"Wrote {path}")

def process_issue(issue):
    body = issue.get("body") or ""
    fm_text, content = split_frontmatter(body)
    if not fm_text:
        print(f"Skipping issue #{issue['number']} (no YAML front matter).")
        return
    fm = yaml.safe_load(fm_text) or {}
    # Optional moderation: require label 'publish' OR published:true in YAML
    labels = {l["name"] for l in issue.get("labels", [])}
    published_flag = str(fm.get("published","true")).lower() == "true"
    if not (published_flag or "publish" in labels):
        # write/update but mark unpublished so it disappears from the site
        fm["published"] = False
    write_post(issue, fm, content)

def main():
    # If event includes an issue, do just that; else sweep all open issues.
    evt_issue = load_issue_from_event()
    issues = evt_issue or fetch_issues()
    for iss in issues:
        process_issue(iss)

if __name__ == "__main__":
    main()
