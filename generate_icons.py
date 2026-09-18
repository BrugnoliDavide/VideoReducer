"""Generate Video Reducer icons: a film strip shrinking from large to small."""
import base64
import io
import math
from PIL import Image, ImageDraw


def draw_film_strip(draw, x, y, w, h, color, hole_color):
    draw.rounded_rectangle([x, y, x + w, y + h], radius=2, fill=color)
    hole_w = max(2, int(w * 0.18))
    hole_h = max(2, int(h * 0.08))
    margin_x = max(1, int(w * 0.08))
    num_holes = max(2, int(h / (hole_h * 2.5)))
    spacing = h / (num_holes + 1)
    for side_x in [x + margin_x, x + w - margin_x - hole_w]:
        for i in range(1, num_holes + 1):
            hy = y + spacing * i - hole_h / 2
            draw.rounded_rectangle(
                [side_x, hy, side_x + hole_w, hy + hole_h],
                radius=1, fill=hole_color,
            )


def draw_arrow(draw, x1, y, x2, color, thickness=2):
    draw.line([(x1, y), (x2, y)], fill=color, width=thickness)
    arrow_size = max(3, thickness * 2)
    draw.polygon([
        (x2, y),
        (x2 - arrow_size, y - arrow_size),
        (x2 - arrow_size, y + arrow_size),
    ], fill=color)


def create_icon(size):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    pad = int(size * 0.06)

    big_w = int(size * 0.32)
    big_h = int(size * 0.80)
    big_x = pad
    big_y = (size - big_h) // 2

    small_w = int(size * 0.22)
    small_h = int(size * 0.55)
    small_x = size - pad - small_w
    small_y = (size - small_h) // 2

    film_dark = (55, 65, 81)
    film_light = (34, 197, 94)
    hole_bg = (200, 210, 220)
    hole_green = (187, 247, 208)
    arrow_color = (99, 102, 241)

    draw_film_strip(draw, big_x, big_y, big_w, big_h, film_dark, hole_bg)

    frame_margin = int(big_w * 0.25)
    frame_x = big_x + frame_margin
    frame_w = big_w - frame_margin * 2
    frame_h = int(big_h * 0.22)
    spacing = big_h / 3.5
    for i in range(3):
        fy = big_y + spacing * (i + 0.5)
        draw.rectangle(
            [frame_x, fy, frame_x + frame_w, fy + frame_h],
            fill=(148, 163, 184),
        )

    draw_film_strip(draw, small_x, small_y, small_w, small_h, film_light, hole_green)

    sm_frame_margin = int(small_w * 0.25)
    sm_frame_x = small_x + sm_frame_margin
    sm_frame_w = small_w - sm_frame_margin * 2
    sm_frame_h = int(small_h * 0.22)
    sm_spacing = small_h / 3.5
    for i in range(3):
        fy = small_y + sm_spacing * (i + 0.5)
        draw.rectangle(
            [sm_frame_x, fy, sm_frame_x + sm_frame_w, fy + sm_frame_h],
            fill=(74, 222, 128),
        )

    arrow_y = size // 2
    arrow_x1 = big_x + big_w + int(size * 0.04)
    arrow_x2 = small_x - int(size * 0.04)
    thickness = max(2, size // 32)
    draw_arrow(draw, arrow_x1, arrow_y, arrow_x2, arrow_color, thickness)

    chevron_size = max(4, size // 12)
    cx = (arrow_x1 + arrow_x2) // 2
    cy = arrow_y
    for offset in [-chevron_size // 2, chevron_size // 2]:
        px = cx + offset
        draw.line([(px, cy - chevron_size), (px + chevron_size // 2, cy)],
                  fill=arrow_color, width=max(1, thickness - 1))
        draw.line([(px + chevron_size // 2, cy), (px, cy + chevron_size)],
                  fill=arrow_color, width=max(1, thickness - 1))

    return img


def main():
    sizes = [16, 32, 48, 64, 128, 256]
    imgs = [create_icon(s) for s in sizes]

    imgs[5].save(
        "icon.ico",
        format="ICO",
        sizes=[(s, s) for s in sizes],
        append_images=imgs[:-1],
    )
    print("Salvato: icon.ico")

    png256 = create_icon(256)
    png256.save("icon.png", format="PNG")
    print("Salvato: icon.png")

    buf = io.BytesIO()
    png64 = create_icon(64)
    png64.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")

    lines = [b64[i:i+76] for i in range(0, len(b64), 76)]
    b64_formatted = "\n".join(f'    "{line}"' for line in lines)

    with open("video_reducer/icon_data.py", "w", encoding="utf-8") as f:
        f.write('ICON_BASE64 = (\n')
        f.write(b64_formatted)
        f.write('\n)\n')
    print("Salvato: video_reducer/icon_data.py")


if __name__ == "__main__":
    main()
