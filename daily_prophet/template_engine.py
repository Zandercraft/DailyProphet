"""HTML and CSS template generation engine for The Daily Prophet with AI-generated assets."""
import os
import base64
import mimetypes
from typing import List, Dict, Optional
from .models import NewspaperEdition, Story, StoryPriority


def _image_to_base64_data_uri(image_path: str) -> str:
    """Converts a local image file to a base64 data URI for standalone portability."""
    if not image_path or not os.path.isfile(image_path):
        return ""
    mime_type, _ = mimetypes.guess_type(image_path)
    if not mime_type:
        ext = os.path.splitext(image_path)[1].lower()
        if ext in [".jpg", ".jpeg"]:
            mime_type = "image/jpeg"
        elif ext == ".png":
            mime_type = "image/png"
        elif ext == ".gif":
            mime_type = "image/gif"
        elif ext == ".webp":
            mime_type = "image/webp"
        else:
            mime_type = "image/png"

    try:
        with open(image_path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode("ascii")
        return f"data:{mime_type};base64,{encoded}"
    except Exception:
        return ""


def _format_paragraphs(text: str, drop_cap: bool = True) -> str:
    """Formats raw text into justified HTML paragraphs with optional drop-cap on first letter."""
    if not text:
        return ""
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if not paragraphs:
        paragraphs = [p.strip() for p in text.split("\n") if p.strip()]

    html_parts = []
    for idx, p in enumerate(paragraphs):
        clean_p = p.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        clean_p = clean_p.replace("★", '<span class="star-bullet">★</span>')
        clean_p = clean_p.replace("•", '<span class="dot-bullet">•</span>')
        clean_p = clean_p.replace("✦", '<span class="star-bullet">✦</span>')
        
        if idx == 0 and drop_cap and len(clean_p) > 1 and not clean_p.startswith("<span"):
            first_char = clean_p[0]
            rest_text = clean_p[1:]
            html_parts.append(f'<p class="first-para"><span class="drop-cap">{first_char}</span>{rest_text}</p>')
        else:
            html_parts.append(f"<p>{clean_p}</p>")
    return "\n".join(html_parts)


def generate_newspaper_html(edition: NewspaperEdition, embed_images: bool = True, export_mode: bool = False) -> str:
    """Generates the complete, authentic Daily Prophet broadsheet HTML."""
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

    # Pre-encode images for standalone portability
    image_uris: Dict[str, str] = {}
    inline_uris: Dict[str, str] = {}
    for story in edition.stories:
        if story.image_path:
            if embed_images:
                uri = _image_to_base64_data_uri(story.image_path)
                image_uris[story.id] = uri if uri else story.image_path
            else:
                image_uris[story.id] = story.image_path
        else:
            image_uris[story.id] = ""

        inline_path = getattr(story, "inline_image_path", "")
        if inline_path:
            if embed_images:
                i_uri = _image_to_base64_data_uri(inline_path)
                inline_uris[story.id] = i_uri if i_uri else inline_path
            else:
                inline_uris[story.id] = inline_path
        else:
            inline_uris[story.id] = ""

    # Check for authentic vintage newspaper background
    parchment_bg_path = os.path.join(base_dir, "assets", "templates", "pages", "layout_1.png")
    if not os.path.isfile(parchment_bg_path):
        parchment_bg_path = os.path.join(base_dir, "assets", "templates", "pages", "additional_layout_1.png")

    parchment_uri = _image_to_base64_data_uri(parchment_bg_path) if os.path.isfile(parchment_bg_path) else ""

    # Categorize stories by priority
    cover_stories = [s for s in edition.stories if s.priority == StoryPriority.COVER.value]
    major_stories = [s for s in edition.stories if s.priority == StoryPriority.MAJOR.value]
    column_stories = [s for s in edition.stories if s.priority == StoryPriority.COLUMN.value]
    snippet_stories = [s for s in edition.stories if s.priority == StoryPriority.SNIPPET.value]

    if not cover_stories and edition.stories:
        cover_stories = [edition.stories[0]]
        remaining = edition.stories[1:]
        major_stories = [s for s in remaining if s.priority == StoryPriority.MAJOR.value]
        column_stories = [s for s in remaining if s.priority == StoryPriority.COLUMN.value]
        snippet_stories = [s for s in remaining if s.priority == StoryPriority.SNIPPET.value]

    cover = cover_stories[0] if cover_stories else None
    major = major_stories[0] if major_stories else None

    theme_class = f"theme-{edition.theme}"
    motion_class = "magical-motion-enabled" if edition.magical_motion else ""
    export_class = "export-mode" if export_mode else ""

    # Background CSS
    bg_style = f"background-image: url('{parchment_uri}'); background-size: cover; background-position: center;" if parchment_uri else ""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{edition.paper_title} - {edition.edition_date}</title>
  
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Cinzel+Decorative:wght@700;900&family=Cinzel:wght@600;700;800;900&family=IM+Fell+English:ital@0;1&family=Libre+Baskerville:ital,wght@0,400;0,700;1,400&family=Playfair+Display+SC:wght@700;900&family=Playfair+Display:ital,wght@0,700;0,900;1,700&family=UnifrakturMaguntia&family=Alex+Brush&display=swap" rel="stylesheet">

  <style>
    *, *::before, *::after {{
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }}

    :root {{
      --bg-parchment: #e2d1af;
      --ink-black: #110e0b;
      --ink-dark: #2b231c;
      --ink-muted: #5e4f41;
      --border-dark: #221c16;
      --border-fine: #6b5c4b;
      --accent-red: #6e1919;
      --accent-gold: #9e7529;
      --font-headline: 'Playfair Display SC', 'Cinzel', Georgia, serif;
      --font-subheadline: 'Libre Baskerville', Georgia, serif;
      --font-body: 'IM Fell English', 'Libre Baskerville', Georgia, serif;
      --font-script: 'Alex Brush', cursive;
      --font-masthead: 'Cinzel Decorative', 'Cinzel', 'Playfair Display SC', Georgia, serif;
    }}

    body.theme-parchment {{
      --bg-parchment: #ede0c6;
    }}

    body.theme-classic_newsprint {{
      --bg-parchment: #f4f3ec;
      --ink-black: #0f0f0f;
      --border-dark: #0f0f0f;
      --border-fine: #555555;
    }}

    body.theme-clean_print {{
      --bg-parchment: #ffffff;
      --ink-black: #000000;
      --border-dark: #000000;
      --border-fine: #333333;
    }}

    body {{
      background-color: #271f18;
      color: var(--ink-black);
      font-family: var(--font-body);
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: 16px 10px;
      -webkit-font-smoothing: antialiased;
    }}

    body.export-mode {{
      padding: 0 !important;
      background: transparent !important;
    }}

    body.export-mode .prophet-toolbar {{
      display: none !important;
    }}

    .prophet-toolbar {{
      position: sticky;
      top: 10px;
      z-index: 1000;
      background: #1c1611;
      border: 1px solid #5a4938;
      box-shadow: 0 6px 18px rgba(0,0,0,0.5);
      padding: 8px 20px;
      border-radius: 30px;
      display: flex;
      gap: 14px;
      align-items: center;
      margin-bottom: 18px;
      font-family: system-ui, -apple-system, sans-serif;
      font-size: 13px;
      color: #dfd7cb;
    }}

    .prophet-toolbar button {{
      background: #382e24;
      color: #f7f1e5;
      border: 1px solid #776654;
      padding: 6px 14px;
      border-radius: 16px;
      cursor: pointer;
      font-size: 12px;
      font-weight: 600;
      display: flex;
      align-items: center;
      gap: 6px;
      transition: all 0.2s;
    }}

    .prophet-toolbar button:hover {{
      background: #5c4a37;
      border-color: #baa48b;
      transform: translateY(-1px);
    }}

    .inline-cutout-img {{
      max-width: 135px;
      max-height: 140px;
      display: inline-block;
      filter: drop-shadow(1px 2px 5px rgba(25, 18, 10, 0.3));
    }}
    .float-right {{
      float: right;
      margin: 4px 0 8px 12px;
      shape-outside: margin-box;
    }}
    .float-left {{
      float: left;
      margin: 4px 12px 8px 0;
      shape-outside: margin-box;
    }}

    /* BROADSHEET CONTAINER */
    .broadsheet-page {{
      width: 1024px;
      max-width: 1024px;
      background-color: var(--bg-parchment);
      {bg_style}
      box-shadow: 0 16px 45px rgba(0,0,0,0.7), inset 0 0 100px rgba(60, 35, 15, 0.35);
      border: 1px solid #3d2f21;
      padding: 18px 22px 24px 22px;
      position: relative;
      margin: 0 auto;
    }}

    .theme-clean_print .broadsheet-page {{
      background-image: none !important;
      background-color: #ffffff !important;
      box-shadow: none !important;
    }}

    .broadsheet-inner-border {{
      border: 3px double var(--border-dark);
      padding: 12px 14px;
      position: relative;
    }}

    .corner-decor {{
      position: absolute;
      width: 18px;
      height: 18px;
      font-size: 16px;
      line-height: 18px;
      text-align: center;
      color: var(--border-dark);
      font-weight: bold;
    }}
    .c-tl {{ top: 4px; left: 4px; }}
    .c-tr {{ top: 4px; right: 4px; }}
    .c-bl {{ bottom: 4px; left: 4px; }}
    .c-br {{ bottom: 4px; right: 4px; }}

    /* MASTHEAD BANNER */
    .ai-masthead-banner {{
      width: 100%;
      height: auto;
      display: block;
      border-bottom: 2px solid var(--border-dark);
      margin-bottom: 8px;
      box-shadow: 0 2px 6px rgba(0,0,0,0.15);
    }}

    .masthead-container {{
      display: grid;
      grid-template-columns: 140px 1fr 140px;
      gap: 12px;
      align-items: center;
      border-bottom: 2px solid var(--border-dark);
      padding-bottom: 8px;
      position: relative;
    }}

    .ear-frame {{
      border: 2px solid var(--border-dark);
      padding: 6px 4px;
      text-align: center;
      background: rgba(255, 255, 255, 0.25);
      font-family: var(--font-headline);
    }}

    .ear-title {{
      font-size: 11px;
      font-weight: 800;
      letter-spacing: 0.5px;
      text-transform: uppercase;
      line-height: 1.2;
    }}

    .ear-divider {{
      border: none;
      border-top: 1px solid var(--border-dark);
      margin: 4px auto;
      width: 80%;
      position: relative;
    }}

    .ear-divider::after {{
      content: "✦";
      position: absolute;
      top: -7px;
      left: 50%;
      transform: translateX(-50%);
      background: var(--bg-parchment);
      padding: 0 4px;
      font-size: 8px;
    }}

    .ear-date {{
      font-size: 10px;
      font-weight: 700;
      letter-spacing: 0.8px;
      text-transform: uppercase;
      line-height: 1.25;
    }}

    .masthead-center {{
      text-align: center;
      position: relative;
    }}

    .script-the {{
      font-family: var(--font-script);
      font-size: 38px;
      line-height: 18px;
      color: var(--ink-black);
      margin-bottom: -10px;
      display: block;
      font-weight: normal;
    }}

    .masthead-title {{
      font-family: var(--font-masthead);
      font-size: clamp(48px, 6.2vw, 68px);
      font-weight: 900;
      letter-spacing: 2.8px;
      line-height: 1.0;
      text-transform: uppercase;
      color: var(--ink-black);
      text-shadow: 1px 1px 0px rgba(255,255,255,0.7), 2px 2px 2px rgba(45,30,15,0.25);
      margin: 2px 0 6px 0;
    }}

    .masthead-slogan {{
      font-family: var(--font-headline);
      font-size: 11px;
      font-weight: 800;
      letter-spacing: 1.5px;
      text-transform: uppercase;
      color: var(--ink-dark);
      margin-bottom: 6px;
    }}

    .topic-ticker-bar {{
      border-top: 1px solid var(--border-dark);
      padding-top: 5px;
      font-family: var(--font-headline);
      font-size: 11px;
      font-weight: 700;
      letter-spacing: 1.2px;
      text-transform: uppercase;
      color: var(--ink-dark);
      display: flex;
      justify-content: center;
      gap: 10px;
    }}

    .breaking-banner {{
      background: var(--accent-red);
      color: #ffffff;
      padding: 5px 10px;
      font-family: var(--font-headline);
      font-weight: 900;
      font-size: 12px;
      letter-spacing: 1.5px;
      text-align: center;
      text-transform: uppercase;
      margin: 10px 0;
      border: 1px solid var(--border-dark);
    }}

    /* TOP SPREAD */
    .top-spread-container {{
      display: grid;
      grid-template-columns: 1fr 310px;
      gap: 16px;
      border-bottom: 2px solid var(--border-dark);
      padding: 12px 0 14px 0;
      margin-bottom: 12px;
    }}

    .cover-story-block {{
      border-right: 1px solid var(--border-dark);
      padding-right: 16px;
    }}

    .cover-headline {{
      font-family: var(--font-headline);
      font-size: 31px;
      font-weight: 900;
      line-height: 1.05;
      letter-spacing: -0.2px;
      text-transform: uppercase;
      color: var(--ink-black);
      margin-bottom: 6px;
    }}

    .cover-subheadline {{
      font-family: var(--font-subheadline);
      font-size: 13.5px;
      font-style: italic;
      font-weight: 700;
      color: var(--ink-dark);
      margin-bottom: 10px;
      line-height: 1.25;
    }}

    .cover-content-layout {{
      display: grid;
      grid-template-columns: 1fr 1.25fr;
      gap: 14px;
      align-items: start;
    }}

    .photo-frame {{
      border: 2px solid var(--border-dark);
      padding: 4px;
      background: rgba(0, 0, 0, 0.05);
      position: relative;
      box-shadow: 2px 3px 8px rgba(0,0,0,0.22);
    }}

    .photo-frame img {{
      width: 100%;
      height: auto;
      display: block;
      filter: contrast(106%) brightness(98%);
      border: 1px solid #635342;
    }}

    .magical-motion-enabled .photo-frame img {{
      animation: magicalPortraitBreath 8s ease-in-out infinite alternate;
    }}

    @keyframes magicalPortraitBreath {{
      0% {{
        transform: scale(1.0) translate(0, 0);
        filter: contrast(106%) brightness(98%);
      }}
      50% {{
        transform: scale(1.02) translate(1px, -2px);
        filter: contrast(112%) brightness(102%);
      }}
      100% {{
        transform: scale(1.01) translate(-1px, 1px);
        filter: contrast(108%) brightness(96%);
      }}
    }}

    .photo-caption {{
      font-family: var(--font-subheadline);
      font-size: 10.5px;
      font-style: italic;
      color: var(--ink-muted);
      line-height: 1.3;
      margin-top: 4px;
      text-align: center;
    }}

    .article-body {{
      font-size: 12px;
      line-height: 1.45;
      text-align: justify;
      text-justify: inter-word;
      hyphens: auto;
      color: var(--ink-black);
    }}

    .article-body p {{
      margin-bottom: 8px;
      text-indent: 12px;
    }}

    .article-body p.first-para {{
      text-indent: 0;
    }}

    .drop-cap {{
      float: left;
      font-family: var(--font-headline);
      font-size: 44px;
      line-height: 36px;
      padding-top: 2px;
      padding-right: 6px;
      font-weight: 900;
      color: var(--ink-black);
    }}

    .feature-card {{
      display: flex;
      flex-direction: column;
    }}

    .feature-headline {{
      font-family: var(--font-headline);
      font-size: 15px;
      font-weight: 900;
      text-transform: uppercase;
      text-align: center;
      background: var(--border-dark);
      color: #f7efdc;
      padding: 4px 6px;
      letter-spacing: 1px;
      margin-bottom: 6px;
    }}

    .feature-subheadline {{
      font-family: var(--font-headline);
      font-size: 10.5px;
      font-weight: 700;
      text-transform: uppercase;
      text-align: center;
      color: var(--ink-dark);
      margin-bottom: 8px;
    }}

    .speech-quote-box {{
      border: 1px solid var(--border-fine);
      background: rgba(255, 255, 255, 0.45);
      padding: 8px 10px;
      margin-top: 8px;
      position: relative;
      font-family: var(--font-subheadline);
      font-style: italic;
      font-size: 11px;
      line-height: 1.35;
      border-radius: 4px;
      color: var(--ink-dark);
    }}

    /* MIDDLE ROW: 3-COLUMN */
    .middle-columns-grid {{
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 16px;
      border-bottom: 2px solid var(--border-dark);
      padding-bottom: 12px;
      margin-bottom: 12px;
    }}

    .news-column {{
      border-right: 1px solid var(--border-dark);
      padding-right: 14px;
      display: flex;
      flex-direction: column;
    }}

    .news-column:last-child {{
      border-right: none;
      padding-right: 0;
    }}

    .col-headline {{
      font-family: var(--font-headline);
      font-size: 16px;
      font-weight: 900;
      line-height: 1.15;
      text-transform: uppercase;
      color: var(--ink-black);
      margin-bottom: 4px;
    }}

    .col-subheadline {{
      font-family: var(--font-subheadline);
      font-size: 11.5px;
      font-style: italic;
      font-weight: 700;
      color: var(--ink-muted);
      margin-bottom: 8px;
      line-height: 1.25;
    }}

    .story-divider-line {{
      border: none;
      border-top: 1px dashed var(--border-fine);
      margin: 10px 0;
    }}

    /* BOTTOM ROW: LORE & NOTICES */
    .bottom-lore-grid {{
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 16px;
      border-bottom: 2px solid var(--border-dark);
      padding-bottom: 10px;
      margin-bottom: 10px;
    }}

    .lore-box {{
      border-right: 1px solid var(--border-dark);
      padding-right: 14px;
      font-size: 11.5px;
      line-height: 1.4;
    }}

    .lore-box:last-child {{
      border-right: none;
      padding-right: 0;
    }}

    .lore-box-title {{
      font-family: var(--font-headline);
      font-size: 13.5px;
      font-weight: 900;
      text-transform: uppercase;
      letter-spacing: 0.8px;
      border-bottom: 1px solid var(--border-dark);
      padding-bottom: 4px;
      margin-bottom: 8px;
      color: var(--ink-black);
    }}

    .star-bullet {{
      color: var(--accent-red);
      font-weight: bold;
      margin-right: 2px;
    }}

    .dot-bullet {{
      color: var(--accent-gold);
      font-weight: bold;
    }}

    .broadsheet-footer {{
      text-align: center;
      font-family: var(--font-headline);
      font-size: 12px;
      font-weight: 800;
      letter-spacing: 2.5px;
      text-transform: uppercase;
      color: var(--ink-dark);
      padding-top: 4px;
      display: flex;
      justify-content: center;
      align-items: center;
      gap: 12px;
    }}

    @media print {{
      * {{
        -webkit-print-color-adjust: exact !important;
        print-color-adjust: exact !important;
      }}
      @page {{
        size: auto;
        margin: 6mm;
      }}
      body {{
        background: transparent !important;
        padding: 0 !important;
      }}
      .prophet-toolbar {{
        display: none !important;
      }}
      .broadsheet-page {{
        box-shadow: none !important;
        border: none !important;
        width: 100% !important;
        max-width: 100% !important;
        padding: 8px !important;
      }}
      .magical-motion-enabled .photo-frame img {{
        animation: none !important;
      }}
    }}
  </style>
</head>
<body class="{theme_class} {motion_class} {export_class}" id="newspaper-body">

  <!-- INTERACTIVE CONTROLS TOOLBAR (AUTOMATICALLY HIDDEN ON EXPORT / PRINT) -->
  <div class="prophet-toolbar">
    <button onclick="window.print()">🖨️ Print Broadsheet</button>
    <button onclick="toggleParchmentTheme()">📜 Toggle Parchment / Clean White</button>
    <button onclick="toggleMotion()">🪄 Toggle Magic Photo Motion</button>
  </div>

  <div class="broadsheet-page">
    <div class="broadsheet-inner-border">
      <!-- CORNER FLOURISHES -->
      <div class="corner-decor c-tl">❖</div>
      <div class="corner-decor c-tr">❖</div>
      <div class="corner-decor c-bl">❖</div>
      <div class="corner-decor c-br">❖</div>

      <!-- MASTHEAD HEADER -->
      <header class="masthead-container">
        <div class="ear-frame">
          <div class="ear-title">{edition.edition_day}</div>
          <div class="ear-divider"></div>
          <div class="ear-date">{edition.edition_date}<br><span style="font-size: 9px; color: var(--ink-muted);">{edition.issue_number}</span></div>
        </div>

        <div class="masthead-center">
          <span class="script-the">The</span>
          <h1 class="masthead-title">{edition.paper_title}</h1>
          <div class="masthead-slogan">✦ {edition.tagline} ✦</div>
          <div class="topic-ticker-bar">{edition.topic_bar}</div>
        </div>

        <div class="ear-frame">
          <div class="ear-title" style="color: var(--accent-red);">PRICE: {edition.price}</div>
          <div class="ear-divider"></div>
          <div class="ear-date" style="font-size: 9.5px;">CASTLE WEATHER<br><span style="font-style: italic; font-weight: normal; font-size: 8.5px;">{edition.weather[:28]}</span></div>
        </div>
      </header>

      {f'<div class="breaking-banner">{edition.breaking_banner}</div>' if edition.breaking_banner else ''}

      <!-- TOP SPREAD: COVER STORY (LEFT) & MAJOR FEATURE (RIGHT) -->
      <section class="top-spread-container">
        <!-- COVER STORY -->
        <article class="cover-story-block">
          {f'<h2 class="cover-headline">{cover.headline}</h2>' if cover else ''}
          {f'<div class="cover-subheadline">{cover.subheadline}</div>' if cover and cover.subheadline else ''}

          <div class="cover-content-layout">
            <div class="article-body">
              {f'<img src="{inline_uris[cover.id]}" class="inline-cutout-img float-{cover.inline_image_align}" alt="{cover.headline}">' if cover and inline_uris.get(cover.id) else ''}
              {_format_paragraphs(cover.body, drop_cap=True) if cover else ''}
            </div>
            <div>
              {f'''
              <div class="photo-frame">
                <img src="{image_uris.get(cover.id, "")}" alt="{cover.headline}">
              </div>
              <div class="photo-caption">{cover.image_caption}</div>
              ''' if cover and image_uris.get(cover.id) else ''}
              {f'<div class="speech-quote-box">{cover.pull_quote}</div>' if cover and cover.pull_quote else ''}
            </div>
          </div>
        </article>

        <!-- MAJOR FEATURE (UPPER RIGHT) -->
        <aside class="feature-card">
          {f'''
          <div class="feature-headline">{major.headline}</div>
          {f'<div class="feature-subheadline">{major.subheadline}</div>' if major.subheadline else ''}
          {f'<div class="photo-frame"><img src="{image_uris.get(major.id, "")}" alt="{major.headline}"></div>' if image_uris.get(major.id) else ''}
          {f'<div class="photo-caption">{major.image_caption}</div>' if major.image_caption else ''}
          <div class="article-body" style="font-size: 11.5px; margin-top: 6px;">
            {_format_paragraphs(major.body, drop_cap=False)}
          </div>
          {f'<div class="speech-quote-box">{major.pull_quote}</div>' if major.pull_quote else ''}
          ''' if major else ''}
        </aside>
      </section>

      <!-- MIDDLE ROW: 3-COLUMN NEWSPAPER STORIES -->
      <section class="middle-columns-grid">
"""

    col1_stories = []
    col2_stories = []
    col3_stories = []

    for i, s in enumerate(column_stories):
        if i % 3 == 0:
            col1_stories.append(s)
        elif i % 3 == 1:
            col2_stories.append(s)
        else:
            col3_stories.append(s)

    columns = [col1_stories, col2_stories, col3_stories]
    for col_items in columns:
        html += '<div class="news-column">\n'
        for idx, story in enumerate(col_items):
            if idx > 0:
                html += '<hr class="story-divider-line">\n'
            story_img = image_uris.get(story.id, "")
            img_html = ""
            if story_img:
                img_html = f'''
                <div class="photo-frame" style="margin-bottom: 6px;">
                  <img src="{story_img}" alt="{story.headline}">
                </div>
                {f'<div class="photo-caption">{story.image_caption}</div>' if story.image_caption else ''}
                '''
            quote_html = f'<div class="speech-quote-box">{story.pull_quote}</div>' if story.pull_quote else ''
            formatted_body = _format_paragraphs(story.body, drop_cap=False)

            inline_cutout_html = f'<img src="{inline_uris[story.id]}" class="inline-cutout-img float-{story.inline_image_align}" alt="{story.headline}">' if inline_uris.get(story.id) else ''
            html += f"""
            <article>
              <h3 class="col-headline">{story.headline}</h3>
              {f'<div class="col-subheadline">{story.subheadline}</div>' if story.subheadline else ''}
              {img_html}
              <div class="article-body">
                {inline_cutout_html}
                {formatted_body}
              </div>
              {quote_html}
            </article>
            """
        html += '</div><!-- /.news-column -->\n'

    html += """
      </section><!-- /.middle-columns-grid -->

      <!-- BOTTOM ROW: LORE, NOTICES & WISDOM TRILOGY -->
      <section class="bottom-lore-grid">
"""

    if snippet_stories:
        for snip in snippet_stories:
            snip_img = image_uris.get(snip.id, "")
            img_html = ""
            if snip_img:
                img_html = f'''
                <div style="text-align: center; margin: 4px 0;">
                  <img src="{snip_img}" alt="{snip.headline}" style="max-height: 95px; max-width: 100%; border: 1px solid var(--border-fine);">
                </div>
                '''
            formatted_body = _format_paragraphs(snip.body, drop_cap=False)

            html += f"""
            <div class="lore-box">
              <div class="lore-box-title">{snip.headline}</div>
              {f'<div style="font-size: 11px; font-style: italic; color: var(--ink-muted); margin-bottom: 4px;">{snip.subheadline}</div>' if snip.subheadline else ''}
              {img_html}
              <div class="article-body" style="font-size: 11px;">
                {formatted_body}
              </div>
            </div>
            """
    else:
        # Authentic 3-box lore grid
        html += f"""
        <div class="lore-box">
          <div class="lore-box-title">{edition.lore_title_1}</div>
          <div class="article-body" style="font-size: 11px;">
            <p>{edition.lore_body_1}</p>
          </div>
        </div>

        <div class="lore-box">
          <div class="lore-box-title">{edition.lore_title_2}</div>
          <div class="article-body" style="font-size: 11px;">
            <p>{edition.lore_body_2}</p>
          </div>
        </div>

        <div class="lore-box">
          <div class="lore-box-title" style="color: var(--accent-red);">WORDS OF WISDOM</div>
          <div class="article-body" style="font-size: 11px; font-style: italic;">
            <p>"{edition.quote_text}"</p>
            <p style="font-style: normal; font-weight: bold; margin-top: 6px; color: var(--ink-muted);">— {edition.quote_author.upper()}</p>
          </div>
        </div>
        """

    html += f"""
      </section><!-- /.bottom-lore-grid -->

      <!-- BROADSHEET FOOTER -->
      <footer class="broadsheet-footer">
        <span>❖ ─── ✦</span>
        <span>{edition.footer_slogan}</span>
        <span>✦ ─── ❖</span>
      </footer>

    </div><!-- /.broadsheet-inner-frame -->
  </div><!-- /.broadsheet-page -->

  <script>
    function toggleParchmentTheme() {{
      const body = document.getElementById('newspaper-body');
      if (body.classList.contains('theme-original_prophet') || body.classList.contains('theme-parchment')) {{
        body.classList.remove('theme-original_prophet');
        body.classList.remove('theme-parchment');
        body.classList.add('theme-clean_print');
      }} else {{
        body.classList.remove('theme-clean_print');
        body.classList.add('theme-original_prophet');
      }}
    }}

    function toggleMotion() {{
      const body = document.getElementById('newspaper-body');
      body.classList.toggle('magical-motion-enabled');
    }}
  </script>
</body>
</html>
"""
    return html
