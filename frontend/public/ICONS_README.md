# PWA Icon Placeholders

The following icon files need to be added to `frontend/public/`:

- `icon-192.png` - 192x192px PWA icon
- `icon-512.png` - 512x512px PWA icon

You can generate these using:
1. Online tools like https://realfavicongenerator.net/
2. Or create simple placeholders with ImageMagick:
   ```
   convert -size 192x192 -background "#4f46e5" -fill white -gravity center -font Arial-Bold -pointsize 72 label:"RC" icon-192.png
   convert -size 512x512 -background "#4f46e5" -fill white -gravity center -font Arial-Bold -pointsize 200 label:"RC" icon-512.png
   ```

Place these files in `frontend/public/` before deploying.
