import os


def write_index_html(output_dir: str) -> None:
    """Generate an HTML index file displaying all PNG images in the output directory.

    Args:
        output_dir: Directory containing the PNG images and where index.html will be written
    """
    images = sorted(
        f for f in os.listdir(output_dir) if os.path.isfile(os.path.join(output_dir, f)) and f.lower().endswith(".png")
    )

    html_lines = [
        "<!DOCTYPE html>",
        "<html lang='en'>",
        "<head>",
        "  <meta charset='UTF-8'>",
        "  <meta name='viewport' content='width=device-width, initial-scale=1.0'>",
        "  <title>SolarControl Plots</title>",
        "  <style>",
        "    body { font-family: Arial, sans-serif; margin: 1rem; background: #f9f9f9; color: #222; }",
        "    h1 { margin-bottom: 0.5rem; }",
        "    section { margin-bottom: 2rem; padding: 1rem; background: #fff; border: 1px solid #ddd; border-radius: 8px; }",
        "    img { display: block; max-width: 100%; height: auto; margin-top: 0.5rem; }",
        "  </style>",
        "</head>",
        "<body>",
        "  <h1>SolarControl Plots</h1>",
        "  <p>Browse the generated plot images below.</p>",
    ]

    for image in images:
        html_lines.extend([
            "  <section>",
            f"    <h2>{image}</h2>",
            f"    <img src=\"{image}\" alt=\"{image}\">",
            "  </section>",
        ])

    html_lines.extend(["</body>", "</html>"])

    with open(os.path.join(output_dir, "index.html"), "w", encoding="utf-8") as index_file:
        index_file.write("\n".join(html_lines))