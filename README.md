<p align="center">
  <img src="assets/logo.png" alt="The Daily Prophet Logo" width="190">
</p>

# The Daily Prophet - Broadsheet Generator & Layout Publisher

A modern, high-fidelity desktop publishing application in Python that generates authentic broadsheet newspaper layouts inspired by **The Daily Prophet** from Harry Potter.

Powered by a pure native rendering engine (Pillow) with borderless multi-page PDF export, animated broadsheet GIFs, an interactive real-time preview dock with dual-monitor support, and an in-place article composer.

---

## Key Features

- **Authentic Broadsheet Typography & Aesthetics**:
  - Classic period fonts (`Cinzel`, `Cinzel Decorative`, `Playfair Display`, `IM Fell English`, `UnifrakturMaguntia`).
  - Ornate engraved borders, decorative filigree rules, and ear boxes (Weather and Community dispatches).
  - Multi-column justified body text with elegant drop-caps and text-wrapping around cutout silhouettes.
  - Breaking news banner ribbons and pull-quote callouts.

- **Word-Inspired Three-Pane Workspace**:
  - **Left Pane (Story Navigator)**: Displays the active page's articles with instant reordering, deletion, and "Move to Page..." actions.
  - **Center Pane (Article Composer)**: Direct in-place writing—no modal dialogs required for routine authoring. Features 5 Wizarding Archetype presets, live slot auto-fit capacity meter, and an expandable styling drawer.
  - **Right Pane (Live Broadsheet Preview Dock)**: Interactive real-time canvas with zoom controls (`Fit to Screen`, `50%`, `75%`, `100%`, `150%`), page flip controls, and bi-directional slot highlighting.

- **Dual-Monitor Pop-Out Mode**:
  - Click **Pop Out** to detach the live broadsheet preview into an independent floating window for your secondary monitor.
  - The main editor window automatically expands across your screen for maximum writing comfort. Click **Dock** to restore it into the main workspace.

- **Bi-Directional Highlighting**:
  - Selecting an article in the story list or composer highlights its slot on the live sheet preview with a glowing parchment outline.
  - Clicking any slot directly on the live sheet preview immediately selects that article for editing.

- **Multi-Page Publication Engine**:
  - Full multi-page support with a horizontal page ribbon (`[Page 1: Front Page] [Page 2: Inside Feature] ... [ + Add Page ]`).
  - Each page can independently select its own layout template (Hero Cover, 3-Column Editorial, Classifieds & Notices, etc.).
  - Compile all pages into a unified 300 DPI borderless PDF.

- **One-Click Wizarding Archetypes & Lorem Ipsum**:
  - Presets for *Breaking Scandal / Alert*, *Ministry Official Decree*, *Rita Skeeter Exclusive*, *Quidditch Match Report*, and *Hogwarts Notice & Snippet*.
  - **Wizarding Lorem Ipsum**: Generates authentic Harry Potter newspaper copy (Diagon Alley potion shortages, cauldron regulations, owl post mist advisories) with one click for rapid layout prototyping.

- **Interactive Layout Slot Editor**:
  - Visual drag-and-drop bounding box editor for custom templates.
  - Shipped factory templates are protected against accidental deletion.
  - Portable, self-contained `.prophettemplate` archive packages.

- **Pure Native Exporters (Zero Browser / CLI Dependencies)**:
  - **Multi-Page PDF**: 300 DPI borderless print-ready document.
  - **High-Res Images**: Export active page or batch-export all pages as numbered PNGs.
  - **Animated Broadsheet GIFs**: Export moving pictures for authentic wizarding portraits.

---

## Quick Start

### 1. Installation

Ensure Python 3.10+ is installed, then clone the repository and install dependencies:

```powershell
pip install -r requirements.txt
```

### 2. Launching the Publisher

Run the application entry point:

```powershell
python main.py
```

Or using **Poe the Poet**:

```powershell
poe run
```

### 3. Developer Commands (Poe the Poet & Ruff)

Task automation is configured via `poethepoet` and `ruff`:

| Command                 | Action                                        |
|:------------------------|:----------------------------------------------|
| `poe run` / `poe start` | Launch The Daily Prophet desktop application  |
| `poe check`             | Run formatting check and linting in sequence  |
| `poe format`            | Auto-format Python code using Ruff            |
| `poe format-check`      | Check code formatting without writing changes |
| `poe lint`              | Lint codebase for issues using Ruff           |
| `poe lint-fix`          | Check and automatically fix safe lint issues  |
| `poe test`              | Run functional GUI smoke and regression tests |

### 4. Built-In Issue Presets

Use the top ribbon commands to load pre-configured editions immediately:
- **Hogwarts Issue**: The Hogwarts Community & Castle Dispatch edition with feature stories and student lore.
- **Azkaban Edition**: The famous *"MASS BREAKOUT FROM AZKABAN! (Sirius Black at Large)"* front-page broadsheet.

---

## Workflow Overview

```
[ Top Ribbon: Project & Sample Presets | Export Commands ]
[ Page Ribbon: Page 1 | Page 2 | ... | + Add Page | Layout Selector | Pop-Out Preview ]
-----------------------------------------------------------------------------------------
[ Story Navigator ]  |  [ Streamlined Composer ]         |  [ Live Preview Dock ]
- Active page stories |  - Headline, subheadline, author   |  - Real-time sheet rendering
- Add, Up, Down, Del |  - Archetype presets & Lorem Ipsum|  - Slot highlighting
- Move to Page...    |  - Auto-fit meter & Photo filters |  - Zoom (Fit, 50%-150%)
                     |  - Accordion styling drawer       |  - Page flip (< Prev, Next >)
```

1. **Navigate or Add Pages**: Switch between publication pages using the Page Ribbon. Assign different layout templates per page as desired.
2. **Select or Add a Story**: Click any story on the left pane, or click directly on the live sheet preview to select its slot.
3. **Compose & Customize**: Edit headline, body text, or author in the center composer. Notice the live sheet preview updates in real-time as you type.
4. **Export Your Publication**:
   - Click **Export PDF (Multi-Page)** to compile all edition pages into a high-resolution, borderless print-ready PDF.
   - Click **Export Images / GIF** to export either the active page or all pages (as PNGs or animated GIFs).

---

## Project Architecture

```
TheDailyProphet/
├── main.py                     # Application entry point
├── requirements.txt            # Python dependencies (Pillow, CustomTkinter, etc.)
├── docs/                       # Project roadmap & documentation
│   └── prophet_modernization_roadmap.md
├── assets/
│   ├── fonts/                  # Authentic wizarding font collection
│   ├── library/                # Character portraits and transparent cutouts
│   └── templates/installed/    # .prophettemplate packages
└── daily_prophet/
    ├── models.py               # NewspaperEdition, NewspaperPage & Story domain models
    ├── layout_models.py        # LayoutSlot, LayoutDefinition & SlotType models
    ├── native_renderer.py      # High-resolution Pillow broadsheet compositor
    ├── pdf_exporter.py         # Native Multi-Page PDF, Image & GIF exporter
    ├── template_package.py     # .prophettemplate archive packager & loader
    ├── versioning.py           # Format versioning & schema migration pipelines
    ├── sample_data.py          # Built-in Hogwarts & Azkaban issue editions
    └── gui/
        ├── main_window.py      # Main Word-inspired 3-pane publication workspace
        ├── story_composer.py   # In-place article composer with archetypes & auto-fit
        ├── preview_canvas.py   # Interactive live preview dock & dual-monitor window
        ├── layout_editor_window.py # Drag-and-drop slot layout editor
        ├── library_dialog.py   # Artwork & character cutout library
        ├── story_dialog.py     # Advanced story configuration dialog
        └── theme.py            # Centralized design tokens & vector IconManager
```

---

## License

This project is open-source and intended for educational, creative, and personal use. Harry Potter characters, names, and related indicia are trademarks of and © Warner Bros. Entertainment Inc.
