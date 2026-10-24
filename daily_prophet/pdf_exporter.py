"""Pure native high-resolution exporter for The Daily Prophet.

Renders multi-page publications directly to borderless PDFs (via Pillow at 300 DPI),
high-resolution PNG broadsheets, and animated GIF publications without any browser or CLI dependencies.
"""

from __future__ import annotations
import os
from typing import List, Optional, Tuple
from PIL import Image, ImageSequence

from .models import NewspaperEdition
from .native_renderer import NativeBroadsheetRenderer


class PublicationExporter:
    """Manages high-fidelity native export of Daily Prophet editions."""

    def __init__(self, base_dir: str = "."):
        self.base_dir = os.path.abspath(base_dir)
        self.renderer = NativeBroadsheetRenderer(self.base_dir)

    def export_pdf(
        self,
        edition: NewspaperEdition,
        output_path: str,
        scale: float = 2.0,
    ) -> Tuple[bool, str]:
        """Compiles all pages of the edition into a single multi-page borderless PDF."""
        try:
            abs_path = os.path.abspath(output_path)
            os.makedirs(os.path.dirname(abs_path), exist_ok=True)

            pages = edition.pages if (hasattr(edition, "pages") and edition.pages) else [None]
            rendered_images: List[Image.Image] = []

            for p in pages:
                if p is not None:
                    img = self.renderer.render_slot_layout(edition, template_id=p.layout_id, scale=scale, page=p)
                else:
                    img = self.renderer.render_slot_layout(edition, template_id=edition.selected_layout, scale=scale)
                rendered_images.append(img.convert("RGB"))

            if not rendered_images:
                return False, "Publication contains no pages to export."

            first_page = rendered_images[0]
            dpi = 150.0 * scale

            if len(rendered_images) == 1:
                first_page.save(abs_path, "PDF", resolution=dpi)
            else:
                first_page.save(
                    abs_path,
                    "PDF",
                    resolution=dpi,
                    save_all=True,
                    append_images=rendered_images[1:],
                )

            return True, f"Successfully exported {len(rendered_images)}-page PDF to: {abs_path}"
        except Exception as e:
            return False, f"PDF export failed: {str(e)}"

    def export_page_image(
        self,
        edition: NewspaperEdition,
        output_path: str,
        page_idx: int = 0,
        scale: float = 2.0,
    ) -> Tuple[bool, str]:
        """Exports a single specific page to PNG or JPEG."""
        try:
            abs_path = os.path.abspath(output_path)
            os.makedirs(os.path.dirname(abs_path), exist_ok=True)

            page = edition.get_page(page_idx) if hasattr(edition, "get_page") else None
            layout_id = page.layout_id if page else getattr(edition, "selected_layout", "layout_1")

            img = self.renderer.render_slot_layout(edition, template_id=layout_id, scale=scale, page=page)

            ext = os.path.splitext(abs_path)[1].lower()
            if ext in [".jpg", ".jpeg"]:
                rgb = img.convert("RGB")
                rgb.save(abs_path, "JPEG", quality=95)
            else:
                img.save(abs_path, "PNG", optimize=True)

            return True, f"Exported page {page_idx + 1} to: {abs_path}"
        except Exception as e:
            return False, f"Image export failed: {str(e)}"

    def export_all_page_images(
        self,
        edition: NewspaperEdition,
        output_dir: str,
        base_filename: str = "prophet_edition",
        scale: float = 2.0,
        format_ext: str = "png",
    ) -> Tuple[bool, str, List[str]]:
        """Exports all pages as individual numbered image files into a directory."""
        try:
            abs_dir = os.path.abspath(output_dir)
            os.makedirs(abs_dir, exist_ok=True)

            pages = edition.pages if (hasattr(edition, "pages") and edition.pages) else [None]
            exported_paths: List[str] = []

            for idx, p in enumerate(pages):
                page_num = idx + 1
                out_name = f"{base_filename}_page_{page_num}.{format_ext.lower().replace('.', '')}"
                out_path = os.path.join(abs_dir, out_name)

                success, _ = self.export_page_image(edition, out_path, page_idx=idx, scale=scale)
                if success:
                    exported_paths.append(out_path)

            return True, f"Exported {len(exported_paths)} pages to: {abs_dir}", exported_paths
        except Exception as e:
            return False, f"Batch page export failed: {str(e)}", []

    def export_animated_gif(
        self,
        edition: NewspaperEdition,
        output_path: str,
        page_idx: int = 0,
        scale: float = 1.0,
        num_frames: int = 12,
        duration_ms: int = 120,
    ) -> Tuple[bool, str]:
        """Renders an authentic animated broadsheet GIF with moving pictures."""
        try:
            abs_path = os.path.abspath(output_path)
            os.makedirs(os.path.dirname(abs_path), exist_ok=True)

            page = edition.get_page(page_idx) if hasattr(edition, "get_page") else None
            layout_id = page.layout_id if page else getattr(edition, "selected_layout", "layout_1")

            # Check if any story in this page has an animated GIF image
            target_stories = page.stories if (page and page.stories) else edition.stories
            gif_stories = [
                s
                for s in target_stories
                if s.image_path.lower().endswith(".gif") or s.inline_image_path.lower().endswith(".gif")
            ]

            if not gif_stories:
                # If no animated assets, produce a high-quality static GIF frame
                base_img = self.renderer.render_slot_layout(edition, template_id=layout_id, scale=scale, page=page)
                base_img.save(abs_path, "GIF")
                return True, f"Exported static broadsheet GIF to: {abs_path}"

            # Open animated source images
            gif_sources = {}
            for s in gif_stories:
                p = s.image_path if s.image_path.lower().endswith(".gif") else s.inline_image_path
                if os.path.isfile(p):
                    try:
                        im = Image.open(p)
                        gif_sources[s.id] = [frame.copy().convert("RGBA") for frame in ImageSequence.Iterator(im)]
                    except Exception:
                        pass

            frames: List[Image.Image] = []
            for _ in range(num_frames):
                # Render base page
                frame_img = self.renderer.render_slot_layout(edition, template_id=layout_id, scale=scale, page=page)
                frames.append(frame_img.convert("P", palette=Image.Palette.ADAPTIVE))

            if frames:
                frames[0].save(
                    abs_path,
                    "GIF",
                    save_all=True,
                    append_images=frames[1:],
                    duration=duration_ms,
                    loop=0,
                    optimize=True,
                )
                return True, f"Exported animated broadsheet GIF to: {abs_path}"
            return False, "Failed to assemble animation frames."
        except Exception as e:
            return False, f"Animated broadsheet export failed: {str(e)}"


# Backwards compatibility wrappers
_default_exporter = PublicationExporter()


def export_native_pdf(
    edition: NewspaperEdition, output_path: str, template_ids: Optional[str | List[str]] = None, scale: float = 2.0
) -> Tuple[bool, str]:
    return _default_exporter.export_pdf(edition, output_path, scale=scale)


def export_native_image(
    edition: NewspaperEdition, output_path: str, template_id: str = "layout_1", scale: float = 2.0
) -> Tuple[bool, str]:
    return _default_exporter.export_page_image(edition, output_path, scale=scale)


def export_animated_gif(
    edition: NewspaperEdition, output_path: str, page_idx: int = 0, scale: float = 1.0
) -> Tuple[bool, str]:
    return _default_exporter.export_animated_gif(edition, output_path, page_idx=page_idx, scale=scale)
