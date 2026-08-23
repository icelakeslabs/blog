# Ice Lakes Labs — static blog

A static blog: a landing page plus one directory per post, each built from an
annotated plain-text draft. GitHub Pages hosts the whole thing — index, posts,
images and feed.

## Golden rule

**`src.txt` is the source of truth. Edit `src.txt`, never `post.md` or
`index.html`** — both are generated and are overwritten on every build.

## Prerequisites

    pandoc      (any 2.x or 3.x; needs pipe_tables, strikeout, header_attributes)
    python3     (stdlib only — no pip installs)
    exiftool    (strip-exif.sh)      Debian: libimage-exiftool-perl
    ImageMagick (redact.sh)          Debian: imagemagick

**Why 2.x still works:** pandoc 2.x rejects an identifier that starts with a
digit — it leaves the literal `{#1-foo}` in the heading text and invents its own
id, silently breaking every link to it. Sections here are numbered, so
`lib/convert.py:slug()` prefixes digit-leading slugs with `s`. Do not "simplify"
that away; it is what keeps the two pandoc majors producing the same anchors.
`postprocess.py` will warn about `unresolved anchors` if it ever regresses.

## Layout

    index.html          GENERATED landing page (list of posts)
    feed.xml            GENERATED RSS feed
    style.css           styling for the index AND every post
    build.sh            builds every post, then the index
    CNAME               your custom domain (one line, no protocol)
    lib/
      manifest.py       scans a post's images/, writes manifest.csv
      convert.py        src.txt -> post.md  (all markup rules live here)
      postprocess.py    TOC placement, back-link, anchor check
      audit.py          post.md -> review.txt
      index_gen.py      builds index.html and feed.xml from posts/
    posts/
      YYYY-MM-DD-slug/
        src.txt         the draft — THE ONLY FILE YOU EDIT BY HAND
        meta.txt        summary, tags, draft flag
        images/         this post's images, under their own names
        post.md         GENERATED
        index.html      GENERATED — the published page
        review.txt      GENERATED audit
        images-todo.txt GENERATED

## Build

    ./build.sh              # everything
    ./build.sh solar        # just posts whose directory name contains "solar"
    open index.html

Per post the pipeline is `manifest.py` → `convert.py` → `pandoc` →
`postprocess.py` → `audit.py`; then `index_gen.py` regenerates the landing
page and feed. `postprocess.py` moves the TOC below the title (pandoc puts it
above everything and nests the sections under the title's `<li>`), adds the
back-link, and warns about unresolved anchors or loose lists.

## Assumptions baked into this layout

Worth knowing before you commit to it — each is changeable, but not for free:

- **The repo root is the published site root.** Everything in the repo is
  fetchable, not just the HTML: `src.txt`, `README.md`, `lib/`, `post.md`,
  `review.txt` and `meta.txt` all get served. Your raw draft will live at
  `<domain>/posts/<dir>/src.txt`. On a free account the repo is public too, so
  that is two separate exposures of the same material.
- **`.nojekyll` is required.** GitHub Pages runs Jekyll by default, which
  skips paths beginning with `_` and can interfere with raw HTML. Do not
  delete it.
- **The draft must be named `src.txt`** — hardcoded in `lib/convert.py`.
- **The directory name is the permanent URL.** `posts/2026-08-19-solar-charging/`
  publishes at `/posts/2026-08-19-solar-charging/`. Renaming it later breaks
  every link anyone has shared.
- **Posts are exactly two levels deep**, because the pandoc call in `build.sh`
  hardcodes `--css=../../style.css`.
- **Images are per-post.** An image used in two posts is stored twice.
- **Generated files are committed.** Pages serves what is in the repo, so
  `index.html`, `feed.xml` and each post's `post.md` and `index.html` must be
  checked in. Expect noisy diffs on every build.

If the source exposure matters, the alternatives are: publish from a `docs/`
folder or a `gh-pages` branch containing only built output, or host on
Cloudflare Pages, which builds from a private repo on its free tier.

## Adding a post

The blog scales by adding folders under `posts/` — the machinery
(`build.sh`, `lib/`, `style.css`) is shared and never copied. Use the
scaffolder so you never hand-create a directory:

    ./new-post.sh "My Post Title"              # dated today
    ./new-post.sh "My Post Title" 2026-09-14   # explicit date

That creates `posts/YYYY-MM-DD-<slug>/` with a template `src.txt`, `meta.txt`
(`draft: true`), and an empty `images/`. Then:

1. Edit `src.txt` — line 1 is the title, line 3 the subtitle.
2. Drop figures in that post's `images/` and reference them with `=-=` markers.
3. **Strip photo metadata: `./strip-exif.sh <slug>`** — removes GPS/device/serial
   from any phone photos (they embed your home location). Run it whenever you add
   images, and always before publishing. Needs `exiftool` (`brew install exiftool`).
4. Fill in `meta.txt` (`summary`, `tags`); leave `draft: true` while writing.
5. `./build.sh <slug>` to build just that post (or `./build.sh` for all).
6. Set `draft: false` and rebuild when ready to list it.

Doing it by hand is equivalent: `mkdir -p posts/2026-09-14-my-slug/images`,
write `src.txt` and `meta.txt`, `./build.sh`. Either way, the date and URL slug
come from the directory name, so
`posts/2026-09-14-my-slug/` publishes at `/posts/2026-09-14-my-slug/`.
Set `draft: true` to build a post without listing it on the index or in the
feed — note it is still publicly reachable if someone knows the URL.

### meta.txt keys

| key | default | effect |
|---|---|---|
| `summary` | — | one-liner on the landing page and in the RSS `<description>` |
| `tags` | — | comma-separated |
| `draft` | `false` | `true` = built, but kept off the index and feed. **A missing `meta.txt` means the post is LIVE** — the flag is opt-in, so scaffold with `new-post.sh` rather than by hand. |
| `pin` | `false` | `true` = sorts above everything on the landing page regardless of date. Use for an evergreen intro. **Prefer this to forward-dating**: the date is baked into the URL and the permanent feed `guid`, so faking it to win the sort costs a stable link forever. |
| `toc` | `true` | `false` = no table of contents for that post. A short post with two headings gets noise, not navigation. |
| `subtitle` | line 3 of `src.txt` | overrides the default. Present-but-empty (`subtitle:`) means *no subtitle* — needed when line 3 is a real heading like `TL;DR`, which would otherwise be advertised as the subtitle. |

A post with no subtitle also changes where the TOC lands: `postprocess.py` puts
it after the title *and* subtitle when both exist, and falls back to just after
the `</h1>`. Either way it never renders above the title.

**Before publishing, set `SITE_URL` in `lib/index_gen.py`** to your real
domain, or the feed will contain example.com links. The build warns until you
do. `SITE_TITLE` and `SITE_TAGLINE` are alongside it.

## Markup conventions in src.txt

These are the author's own conventions, interpreted by `lib/convert.py`.
They apply to every post's `src.txt`.

### Structure

    Section heading         a line followed by a line of 4+ dashes
                            numbered sections get id="section-N"
    Sub-heading             a short standalone line (<60 chars) ending in
                            ":" or "-"  — the trailing character is stripped
    Lead-in sentence        a line ending in ":" that is followed by an
                            indented block or a "=-=" annotation stays PROSE,
                            keeping its colon — it is not promoted to a heading
    Code block              indent 4+ spaces
    Table                   indent, then a header row, then a rule line of
                            dash runs ("----   ----   ----"). Column positions
                            come from the dash runs. Wrapped cells continue on
                            following lines with a blank first column.
    Bullet list             "- ", "+ " or "* " at column 0; indented "  - "
                            items nest under the list above them
    Numbered list           "1." etc, indented or not

### Inline

    *word*                  bold
    /i text/i               italic
    /b text/b               bold
    /strikeout text/strikeout   strikethrough
    /m text/m               monospace, NO code-block background
    -Neurio-                strikethrough (explicit list in lib/convert.py: STRIKE)
    https://...             auto-linked, including inside prose parentheses

Only the tags listed above are recognised, so URL paths like `/vitals` and
`/tesla` are left alone. **If you invent a new convention, it will pass
through as literal text rather than erroring — add it to `inline()` first.**

### Annotations

    =-= <filename or description>       insert an image here
    =-= insert hyperlink to next TL;DR  link to the next TL;DR heading
    =-= insert hyperlink to section N   link to "#section-N"

Annotations may sit on their own line or trail prose on the same line.

## Images

Each post's images stay in its own `images/` under their own names — nothing renamed, nothing
duplicated. `lib/manifest.py` matches real files against the filename hint parsed
from each `=-=` annotation, ignoring case and extension, and writes
`images/manifest.csv`.

- Anything already in the `your_file` column is preserved; only blank rows are
  auto-filled.
- Entries whose file has vanished from `images/` are dropped, so the manifest
  can never point at a deleted file.
- Ten annotations name no file ("photo of Olimex", "July 1 screenshot") — fill
  those in by hand.
- IMG-02 and IMG-06 each mention two images but occupy one slot; IMG-22
  deliberately reuses IMG-20's file.

### Hand-editing images/manifest.csv

The file is part generated, part yours:

| column | who owns it |
|---|---|
| `slot`, `src_line`, `annotation`, `filename_hint` | regenerated from `src.txt` on every build — edits here are lost |
| `your_file` | **yours** — read and written back untouched |

So: edit only `your_file`. Do not add columns or rows; the row set comes from
the `=-=` annotations in `src.txt`.

A value naming a file that is not in `images/` is **kept, not deleted** — you
get a warning on the console and a line in `images-missing.txt`. That covers
typos and names entered before the file was copied in.

**When installing an updated copy of these scripts, do NOT overwrite your own
`images/manifest.csv`** — the one shipped alongside the scripts has an empty
`your_file` column.

Every build prints a count of unassigned slots and writes `images-todo.txt`.
Unassigned slots render with "UNASSIGNED" in the alt text.

## Before publishing images

The repo is public and **git history is permanent** — an image redacted in a
later commit is still fetchable in the earlier one. Clean images *before* the
commit that introduces them. There are two halves, and they need two tools.

**1. Metadata you cannot see** — `./strip-exif.sh [slug]`

Strips GPS, camera make/model, serial and timestamps; keeps Orientation so
photos don't rotate. Phone photos routinely carry the coordinates of wherever
they were taken. `build.sh` warns if any image still has such metadata, so a
forgotten run doesn't sail past silently.

**2. What is visible in the pixels** — your eyes, then `./redact.sh`

No tool can find this for you, and `grep` cannot see into an image. Open every
screenshot and look for device serials, app or site names (often a street
name), Wi-Fi SSIDs (wardriving databases map SSID to coordinates), other
hardware IDs, account emails, QR codes, and browser URL bars or hostnames.

```
./redact.sh posts/<slug>/images/<file> <x1,y1,x2,y2> [<x1,y1,x2,y2> ...]
```

It fills the region opaque and re-encodes, so the original pixels are gone
rather than covered, then re-strips metadata (image editors write fresh EXIF on
save). Look at the result afterward — a misplaced box hides nothing and the
exit code won't tell you.

Assume every identifier appears in **more than one** image, and scroll each
image to the bottom: in this repo's first post one serial appeared in four
screenshots, and two instances sat below the fold on pages whose title bars had
already been reviewed.

## review.txt

A superset audit of **every** code block and table in the finished page —
not just things the converter was unsure about. Each entry shows how it
currently renders, its section, its approximate `src.txt` line, and up to 10
lines of content.

IDs are md5 hashes of block content, not positions, so they are stable across
rebuilds. **Refer to entries by ID, never by ordinal position.** Two caveats:

- Editing a block changes its content, and therefore its ID.
- Byte-identical blocks get a `-2` suffix on the second occurrence.

All 14 entries of the solar-charging post have been reviewed and signed off.

## Verifying a build

    grep -c 'DR the next TL' index.html      # expect 9 nav links
    grep -c '<li><p>' index.html             # expect 0 (0 = tight lists)
    python3 - <<'EOF'
    import re, pathlib
    h = pathlib.Path('index.html').read_text()
    print('unresolved anchors:',
          [a for a in re.findall(r'href="#([^"]+)"', h) if f'id="{a}"' not in h])
    EOF

## Deploying to GitHub Pages

The whole blog lives in one repo — GitHub Pages sets a custom domain per
*repository*, not per page, so all posts share it.

1. `git init && git add . && git commit -m "blog"`
2. Create a **public** repo on GitHub and push.
3. Settings → Pages → Source: `main`, folder `/ (root)`.
4. Create a `CNAME` file at the repo root containing just your domain, e.g.
   `icelakeslabs.com` or `blog.icelakeslabs.com`.
5. In GoDaddy DNS:
   - apex (`icelakeslabs.com`): four `A` records to GitHub's Pages IPs
   - subdomain (`blog.icelakeslabs.com`): one `CNAME` to `<user>.github.io`
6. Wait for the cert, then tick "Enforce HTTPS".
7. Set `SITE_URL` in `lib/index_gen.py` to match, and rebuild.

Using the apex domain will replace your existing GoDaddy site, so a
subdomain is the safer choice unless you mean to move everything.

On a free GitHub account, Pages only works from a **public** repo — drafts,
images and full commit history become world-readable, including anything
revised out later. Cloudflare Pages allows private-repo deploys on its free
tier; same DNS approach, different target.

## Why not the GoDaddy blog editor

Tested directly. Its paste sanitiser keeps H2/H3, bold, italic, underline,
both strikethrough encodings, inline monospace, links, and lists — but drops
tables, superscript/subscript, horizontal rules, and blockquote styling.
Custom code sections render in an iframe with manual pixel height, no image
upload, and poor search indexing, which rules them out for a piece this long.
