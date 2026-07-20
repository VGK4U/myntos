#!/usr/bin/env bash
# Usage: bash scripts/update_catalog.sh /path/to/new-catalog.pdf
# Or run without argument to re-convert the existing PDF.

set -e
PDF_SRC="${1:-frontend/public/catalog/mnr-catalog.pdf}"
PAGES_DIR="frontend/public/catalog/pages"

if [ ! -f "$PDF_SRC" ]; then
  echo "ERROR: PDF not found at $PDF_SRC"
  echo "Usage: bash scripts/update_catalog.sh /path/to/new-catalog.pdf"
  exit 1
fi

# If a new file was given, copy it into place
if [ "$PDF_SRC" != "frontend/public/catalog/mnr-catalog.pdf" ]; then
  echo "Copying new PDF..."
  cp "$PDF_SRC" frontend/public/catalog/mnr-catalog.pdf
  cp "$PDF_SRC" backend/storage/catalog/mnr-catalog.pdf
  echo "PDF updated."
fi

echo "Converting pages to images..."
mkdir -p "$PAGES_DIR"
rm -f "$PAGES_DIR"/page-*.jpg

pdftoppm -jpeg -r 150 -scale-to-x 1200 \
  frontend/public/catalog/mnr-catalog.pdf \
  "$PAGES_DIR/page"

COUNT=$(ls "$PAGES_DIR"/page-*.jpg 2>/dev/null | wc -l)
echo ""
echo "Done. $COUNT pages generated in $PAGES_DIR"
echo ""
echo "Total size:"
du -sh "$PAGES_DIR"
echo ""
echo "Catalog is live — refresh the /catalog page to see the changes."
