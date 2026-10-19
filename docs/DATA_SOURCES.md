# Data provenance and third-party assets

## Historical site records

The portable dataset is a normalized export of the author's original ISTE 438 coursework MongoDB collection `WorldHeritageSites.sites_merged`. The coursework README identifies [UNESCO Heritage Sites 2021 on Kaggle, by Ramjas Maurya](https://www.kaggle.com/datasets/ramjasmaurya/unesco-heritage-sites2021) as its source. Site descriptions originate from the [UNESCO World Heritage Centre](https://whc.unesco.org/en/list/). UNESCO is not affiliated with or endorsing this application.

The export contains 1,155 unique internal site identifiers and 5,639 translation records, with inscription years from 1978 through 2021. Source provenance reflects the original coursework archive; there has been no record-by-record comparison against today's official list. Internal IDs are not official UNESCO inscription numbers.

The original scripts used machine translation to add six languages to English. These translations have incomplete coverage and have not been independently reviewed. Names, boundaries, country/territory labels, descriptions, and inscription status may differ from the current official source.

Normalization removes BSON object IDs, HTML tags, old public comments, and image references without attribution records. It validates finite WGS84 coordinates, standardizes field names and types, splits multi-region membership, treats source zero areas as unknown, rejects duplicate `(site_id, language)` records, and preserves Unicode content. The English categorization totals are 898 cultural, 218 natural, and 39 mixed sites. The manifest records transformations, counts, and the compressed dataset's SHA-256 checksum.

This repository does not assert that third-party descriptions, translated derivatives, or source datasets are in the public domain, nor does it grant a new blanket license over them. Consult the source's terms and [UNESCO's licensing information](https://whc.unesco.org/en/licenses/) before downstream reuse. Attribution in this educational portfolio is not a substitute for applicable source terms.

## Images

Every site has a bundled image in `data/photos/`. The original local GridFS archive and 875 saved coursework photos were inspected as references and remain untouched. The new collection uses 1,153 Wikimedia Commons images plus two original UNESCO nomination images. Some natural sites use aerial or satellite photography, and serial heritage properties may show a representative component.

Site associations were established by exact normalized UNESCO names for 1,141 records and reviewed inscription IDs for 14 changed, truncated, or delisted names. Commons files were associated through Wikidata UNESCO inscription identifiers and reviewed component/page matches. `catalog.json` records each file's site ID, official inscription ID, author credit, source, license, changes, dimensions, and SHA-256. `sources.json` and `attribution-overrides.json` retain the collection plan and credits recovered from older source pages.

Commons images are resized to at most 1,200 × 900 and stored as WebP. Search thumbnails are generated in GridFS. Each image retains its own source license; the collection does not apply a new blanket license. The three GFDL-1.2 images include the full license text under `data/photos/licenses/`. Seventeen legacy Commons pages do not name a photographer in their structured metadata or file descriptions; their captions explicitly direct readers to the source page rather than inventing an author.

The images for [Burkina Faso's metallurgy sites](https://whc.unesco.org/en/documents/166675) and the [Yellow Sea bird sanctuaries](https://whc.unesco.org/en/documents/166354) are original JPEG files from the UNESCO nomination records. Their published conditions specify attribution and no derivatives. These two files are retained byte-for-byte, including for thumbnail requests, and are displayed without cropping. The captions include the named author/copyright holder and link to the source and [published terms](https://whc.unesco.org/en/licenses/13).

The old CSS globe and category illustrations were removed when the original blue coursework design was restored. A neutral landscape illustration remains only as a defensive fallback for a missing or deleted media file; all bundled sites have an actual image.

## Map and frontend libraries

- **Leaflet 1.9.4:** vendored under `static/vendor/leaflet/`, including its BSD-2-Clause license. [Project](https://leafletjs.com/) · [License](../static/vendor/leaflet/LICENSE).
- **OpenStreetMap:** map tiles are requested directly by the browser. Visible map attribution links to [OpenStreetMap copyright and contributors](https://www.openstreetmap.org/copyright). Tile requests disclose the browser's network address to the tile provider and require internet access. Follow the provider's usage policy for a publicly hosted deployment.
- **Axe-core 4.11.0:** development-only accessibility checks, installed through the npm lockfile with the package's upstream license.
- **Prettier 3.8.1:** development-only CSS/JavaScript formatting.

Native MongoDB Community binaries are downloaded on the user's machine from the official distribution and verified against pinned SHA-256 values from its release manifest. They are not redistributed in this Git repository; extracted distributions retain their upstream license notices.
