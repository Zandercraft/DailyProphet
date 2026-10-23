# 🗞️ The Daily Prophet - Newspaper Generator

A clean, modern GUI application in Python that generates authentic, fully-templated broadsheet newspaper layouts inspired by **The Daily Prophet** from Harry Potter.

Simply input your stories, headlines, and accompanying photos with a priority rating (such as Cover Story hero, Major Feature, Side Column, or Notice/Brief), and the engine automatically calculates and styles an authentic Victorian/Edwardian wizarding broadsheet ready for preview, web sharing, or high-res printing to PDF!

---

## ✨ Features

- **🪄 Authentic Daily Prophet Aesthetic**:
  - Classic gothic/woodcut masthead typography (`Cinzel`, `Cinzel Decorative`, `Playfair Display`, `IM Fell English`, `Unifraktur`).
  - Ornate double-line borders, filigree corner ornaments (`❖`), and vintage ear boxes (Weather & Gringotts exchange rates).
  - Multi-column justified body text with elegant drop-caps.
  - Breaking news banner ribbon across the broadsheet.
  - Pull-quote callouts and vintage photo frames with corner tabs.

- **⭐ Intelligent Priority-Based Layout Engine**:
  - **🌟 Cover Story (Hero)**: Dominates the front page with a huge all-caps headline, author byline, prominent framed photo, pull-quote callout, and 2–3 column justified spread.
  - **📰 Major Feature**: Prominent secondary lead story with medium photo and dual-column format.
  - **📑 Side Column**: Traditional vertical news column with dividing rules.
  - **📜 Notice / Brief**: Framed announcement boxes for Ministry decrees, classifieds, or Quidditch scores (supports `ornate_box`, `parchment_scroll`, and `wanted_poster` styles).

- **🎬 Harry Potter Magical Moving Photo Effect**:
  - Subtle breathing/shimmer animation brings static portraits to life in the browser/preview!
  - Full support for animated GIFs (e.g., Azkaban prisoner photos, moving portraits).
  - Instant toggle button for magic motion.

- **🎨 Multi-Theme Support**:
  - **Aged Wizard Parchment**: Antique textured paper background with deep ink tones.
  - **Classic Newsprint**: Off-white vintage broadsheet texture.
  - **Ink-Friendly Clean Print**: Crisp white background optimized for home printers without toner waste.

- **📦 Standalone Portable HTML Export**:
  - All images are automatically converted and embedded directly as Base64 data URIs into a single, self-contained `.html` file. You can email or share it with anyone without missing files or broken images.

- **🖨️ 1-Click High-Res PDF Export**:
  - Automatically exports crisp, print-ready PDF broadsheets using Edge/Chromium headless printing.

---

## 🚀 Quick Start

### 1. Launch the Application
Run the launcher script:
```powershell
python main.py
```
*(Or run within the virtual environment: `.\.venv\Scripts\python main.py`)*

### 2. Instant Sample Edition
Click **🧙 Load Potter Sample** in the top bar to immediately populate the application with a complete, authentic Harry Potter edition:
- Cover Story: *"MASS BREAKOUT FROM AZKABAN! (Sirius Black at Large)"*
- Major Feature: *"TRIWIZARD TOURNAMENT REVIVED AT HOGWARTS"*
- Side Column: *"QUIDDITCH WORLD CUP: IRELAND TRIUMPHS"*
- Ministry Notice: *"MINISTRY OF MAGIC DIRECTIVE #84"*
- Classifieds: *"DIAGON ALLEY CLASSIFIEDS & NOTICES"*

### 3. Generate & Preview
- Click **🔮 Preview Broadsheet** to view the live layout in a dedicated desktop window.
- Click **🌐 Open in Browser** to view it in Microsoft Edge, Google Chrome, or Firefox.
- Click **🖨️ Export PDF** to generate a print-ready PDF file.
- Click **💾 Export HTML** to save a self-contained single-file HTML broadsheet.

---

## 🛠️ Adding Your Own Stories

1. In the **📰 Stories & Layout** tab, click **➕ Add Story** (or double-click any story in the list to edit).
2. Choose a **Story Priority**:
   - `Cover Story (Hero)`
   - `Major Feature`
   - `Side Column`
   - `Notice / Brief`
3. Enter your **Headline**, **Subheadline**, and **Author / Byline**.
4. (Optional) Click **Browse Image...** to attach any photo (PNG, JPG, GIF, WebP).
5. Enter your story body paragraphs and click **Save Story Article**.
6. Hit **🔮 Preview Broadsheet** to see your newspaper instantly laid out!

---

## 📂 Project Structure

```
TheDailyProphet/
├── main.py                     # Application entry point
├── requirements.txt            # Python dependencies
├── output/                     # Generated sample HTML and PDF
│   ├── daily_prophet_sample.html
│   └── daily_prophet_sample.pdf
├── assets/sample_images/       # Authentic vintage sample illustrations
│   ├── sirius_black_wanted.png
│   ├── triwizard_tournament.png
│   ├── golden_snitch.png
│   └── ministry_official_seal.png
└── daily_prophet/
    ├── models.py               # Story & NewspaperEdition data models
    ├── template_engine.py      # Broadsheet layout & HTML/CSS generator
    ├── sample_data.py          # Built-in Harry Potter sample edition
    ├── pdf_exporter.py         # Headless Chromium & Edge PDF exporter
    ├── asset_generator.py      # Vintage graphic generator using Pillow
    └── gui/
        ├── main_window.py      # CustomTkinter main interface
        ├── story_dialog.py     # Story editor & image selector
        └── preview_window.py   # Broadsheet preview launcher
```
