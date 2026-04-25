

import requests
from bs4 import BeautifulSoup


def decode_google_doc(url: str) -> None:
    
    response = requests.get(url)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    table = soup.find("table")
    if table is None:
        print("No table found in document.")
        return

    rows = table.find_all("tr")
    if len(rows) < 2:
        print("Table has no data rows.")
        return

    headers = [cell.get_text(strip=True).lower() for cell in rows[0].find_all(["td", "th"])]

    char_idx = x_idx = y_idx = None
    for i, h in enumerate(headers):
        if h in ("character", "char"):
            char_idx = i
        elif h == "x-coordinate" or h == "x coordinate" or h == "x":
            x_idx = i
        elif h == "y-coordinate" or h == "y coordinate" or h == "y":
            y_idx = i

    if char_idx is None:
        char_idx = 0
    if x_idx is None:
        x_idx = 1
    if y_idx is None:
        y_idx = 2

    cells_data = []
    max_x = 0
    max_y = 0

    for row in rows[1:]:
        cols = [cell.get_text(strip=True) for cell in row.find_all(["td", "th"])]
        if len(cols) <= max(char_idx, x_idx, y_idx):
            continue

        char = cols[char_idx]
        try:
            x = int(cols[x_idx])
            y = int(cols[y_idx])
        except ValueError:
            continue

        if not char:
            continue

        cells_data.append((char, x, y))
        max_x = max(max_x, x)
        max_y = max(max_y, y)

    grid = [[" "] * (max_x + 1) for _ in range(max_y + 1)]

    for char, x, y in cells_data:
        grid[y][x] = char

    for row in grid:
        print("".join(row))


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python decode_google_doc.py <google_doc_url>")
        sys.exit(1)

    decode_google_doc(sys.argv[1])
