# Site images

This directory contains one image for each of the 1,155 sites in the historical dataset. These files are seed assets: the application serves them from MongoDB GridFS after import.

`catalog.json` records source pages, author/copyright credits, individual licenses, image dimensions, transformation notes, and SHA-256 hashes. Each image retains its own source terms. `manifest.json` summarizes coverage and the catalog checksum. Some properties are illustrated by a representative component or aerial/satellite image.

Most files are resized Wikimedia Commons images. `site_1097.jpg` and `site_1100.jpg` are unchanged original UNESCO nomination images with attribution/no-derivatives conditions; no resized file or crop is generated for them. The full GFDL-1.2 license for the three applicable images is included under `licenses/`.

See [data sources](../../docs/DATA_SOURCES.md) for the collection process and attribution notes.
