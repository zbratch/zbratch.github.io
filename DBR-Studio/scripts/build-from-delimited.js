// Build posts/posts.json from data/submissions.(tsv|csv)
// Matches headers exactly as provided (case-insensitive), incl. "Post Caption/Summary" and "Upload Files!".

const fs = require('fs');
const path = require('path');

// ====== CONFIG ======
const ROOT = path.join(__dirname, '..');
const DATA_DIR = path.join(ROOT, 'data');
const FILE_CANDIDATES = ['submissions.tsv', 'submissions.csv']; // try TSV first
const OUT_FILE = path.join(ROOT, 'posts', 'posts.json');
const APPROVED_ONLY = true; // set false to include Pending for testing
// ====================

function readFirstExisting(baseDir, names) {
  for (const n of names) {
    const p = path.join(baseDir, n);
    if (fs.existsSync(p)) return p;
  }
  return null;
}

function parseDelimited(text) {
  // Detect delimiter from first non-empty line
  const lines = text.split(/\r?\n/);
  const first = lines.find(l => l.trim() !== '') || '';
  const delim = first.includes('\t') ? '\t' : ',';
  return parseWithDelimiter(text, delim);
}

function parseWithDelimiter(text, delim) {
  // CSV/TSV with quotes
  const rows = [];
  let field = '', row = [], inQuotes = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (inQuotes) {
      if (c === '"') {
        if (text[i + 1] === '"') { field += '"'; i++; }
        else inQuotes = false;
      } else field += c;
    } else {
      if (c === '"') inQuotes = true;
      else if (c === delim) { row.push(field); field = ''; }
      else if (c === '\n')  { row.push(field); rows.push(row); row = []; field = ''; }
      else if (c === '\r')  { /* ignore */ }
      else field += c;
    }
  }
  row.push(field);
  if (row.length && !(row.length === 1 && row[0] === '')) rows.push(row);
  return rows;
}

// Normalize a header to a lookup key (lowercase, strip non-alphanum)
function norm(h) { return String(h || '').toLowerCase().replace(/[^a-z0-9]/g, ''); }
function toISO(d) { if (!d) return ''; const dt = new Date(d); return isNaN(dt) ? '' : dt.toISOString().slice(0,10); }
function splitMulti(s) { if (!s) return []; return s.split(/[,;\n\r]+/g).map(x=>x.trim()).filter(Boolean); }
function withProtocol(u) { if (!u) return ''; return /^https?:\/\//i.test(u) ? u : 'https://' + u; }

function buildEmbed(link) {
  if (!link) return { embed: '', linkOut: '' };
  const t = link.trim();
  if (t.startsWith('<iframe')) return { embed: t, linkOut: '' };
  if (/forms\.office\.com/i.test(t)) {
    const url = withProtocol(t);
    const add = /embed=true/i.test(url) ? '' : (url.includes('?') ? '&embed=true' : '?embed=true');
    return { embed: `<iframe src="${url}${add}" width="640" height="480" frameborder="0" style="border:none; max-width:100%; height:520px" allowfullscreen></iframe>`, linkOut: '' };
  }
  if (/youtube\.com|youtu\.be|spotify\.com/i.test(t)) {
    return { embed: `<iframe src="${t}" frameborder="0" allowfullscreen></iframe>`, linkOut: '' };
  }
  return { embed: '', linkOut: t };
}

function main() {
  const dataFile = readFirstExisting(DATA_DIR, FILE_CANDIDATES);
  if (!dataFile) {
    console.error('No data file found:', FILE_CANDIDATES.join(' or '), 'under', DATA_DIR);
    process.exit(1);
  }
  const text = fs.readFileSync(dataFile, 'utf8');
  const rows = parseDelimited(text);
  if (rows.length < 2) {
    fs.mkdirSync(path.dirname(OUT_FILE), { recursive: true });
    fs.writeFileSync(OUT_FILE, '[]\n');
    console.log('No data rows; wrote empty posts.json');
    return;
  }

  const header = rows.shift();
  const map = Object.fromEntries(header.map(h => [norm(h), h]));

  // Expected headers from your example:
  // Id | Start time | Completion time | Email | Name | Name/Nickname |
  // Post Type | Post Title | Post Caption/Summary | Link | Upload Files! | Status
  const h = {
    id:                map[norm('Id')],
    starttime:         map[norm('Start time')],
    completiontime:    map[norm('Completion time')],
    email:             map[norm('Email')],
    name:              map[norm('Name')],
    namenickname:      map[norm('Name/Nickname')],
    posttype:          map[norm('Post Type')],
    posttitle:         map[norm('Post Title')],
    postcaptionsummary:map[norm('Post Caption/Summary')],
    link:              map[norm('Link')],
    uploadfiles:       map[norm('Upload Files!')],
    status:            map[norm('Status')]
  };

  // Build an index lookup once
  const idx = Object.fromEntries(Object.entries(h).map(([k, hdr]) => [k, hdr ? header.indexOf(hdr) : -1]));

  const posts = rows
    .filter(r => {
      if (!APPROVED_ONLY) return true;
      if (idx.status < 0) return false; // no status column: publish nothing when APPROVED_ONLY
      const v = String(r[idx.status] || '').toLowerCase();
      return v === 'approved';
    })
    .map(r => {
      const title   = (idx.posttitle >= 0 ? r[idx.posttitle] : '').trim();
      const summary = (idx.postcaptionsummary >= 0 ? r[idx.postcaptionsummary] : '').trim();
      const nick    = ((idx.namenickname >= 0 ? r[idx.namenickname] : '') || (idx.name >= 0 ? r[idx.name] : '')).trim();
      const typeRaw = (idx.posttype >= 0 ? r[idx.posttype] : '').trim().toLowerCase();
      const link    = (idx.link >= 0 ? r[idx.link] : '').trim();
      const files   = (idx.uploadfiles >= 0 ? r[idx.uploadfiles] : '').trim();
      const date    = toISO(((idx.starttime >= 0 ? r[idx.starttime] : '') || (idx.completiontime >= 0 ? r[idx.completiontime] : '')).trim());

      const tags = [];
      if (typeRaw === 'music') tags.push('music');
      if (typeRaw === 'photos' || typeRaw === 'photo') tags.push('photography');
      if (typeRaw === 'art') tags.push('art');
      if (/forms\.office\.com/i.test(link) || /^\s*<iframe/i.test(link)) tags.push('poll');

      const { embed, linkOut } = buildEmbed(link);
      const images = splitMulti(files);

      const obj = {};
      if (title)   obj.title = title;
      if (date)    obj.date  = date;
      if (summary) obj.summary = summary;
      if (tags.length) obj.tags = tags;
      if (images.length > 1) obj.images = images;
      else if (images.length === 1) obj.image = images[0];
      if (embed) obj.embed = embed;
      if (!embed && linkOut) obj.link = linkOut;
      if (nick) obj.caption = `Submitted by ${nick}`;
      return obj;
    })
    .filter(p => Object.keys(p).length > 0)
    .sort((a,b) => new Date(b.date || 0) - new Date(a.date || 0));

  fs.mkdirSync(path.dirname(OUT_FILE), { recursive: true });
  fs.writeFileSync(OUT_FILE, JSON.stringify(posts, null, 2) + '\n');
  console.log(`Built ${posts.length} posts → ${path.relative(process.cwd(), OUT_FILE)}`);
}

main();
