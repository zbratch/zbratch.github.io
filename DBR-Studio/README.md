
# DBR Studio — GitHub Pages Starter

A lightweight static site for music, photography, and art. No build tools required.

## Quick Start
1. Create a new GitHub repo (public) named `dbr-studio` (or your choice).
2. Upload this folder's contents to the repo root.
3. In repo Settings → Pages → Build and deployment → Source: `Deploy from a branch`. Choose `main` and `/ (root)`.
4. Visit the Pages URL shown in Settings.

## Structure
```
/
  index.html
  music.html
  photography.html
  art.html
  about.html
  CONTRIBUTING.html
  assets/
    styles.css
    script.js
  posts/
    posts.json
  photos/   (optional local images if you prefer)
```

## Posting Content
- Edit `posts/posts.json`. Example entry:
```json
{
  "title": "Boat Playlist",
  "date": "2025-09-08",
  "summary": "Community-sourced playlist: songs for life on the water.",
  "tags": ["music","playlist"],
  "embed": "<iframe ...></iframe>"
}
```
- Supported optional fields: `image`, `caption`, `embed`, `link`.

### Tags you might use
- `music`, `playlist`, `poll`, `photography`, `favorite-photo`, `art`, `announcement`

## Playlists
Embed YouTube/Spotify iframes directly in a post's `embed` field.

## Pic of the Day
Add a post with tag `photography` (or create a special tag like `pod`) and a single image. The Photography page renders the latest posts and can be filtered by tag.

## Polls
The demo poll stores your vote in `localStorage` (device-only). For real voting, use:
- **GitHub Discussions**: create a discussion and let people react/comment.
- **Google Forms**: link to a form; results collected in Google Sheets.
- **StrawPoll** or similar service.

## Submissions via GitHub
Set up **Issue Templates** for Music/Art/Photography:
- Users open an Issue, paste links (YouTube, SoundCloud, etc.) or upload images.
- Maintainers curate and add entries to `posts.json`.

## Content Guidelines
Keep content appropriate and non-polarizing for a broad audience. Avoid political, religious, adult content, and personal family info.

## Going Further (Optional)
- Migrate to **Jekyll** collections for real blog posts and archive pages.
- Add a `/data/` folder with multiple JSON files per section.
- Use a privacy-friendly image CDN or store images in `/photos`.
- Add search (client-side Fuse.js) and RSS (manual JSON feed).
