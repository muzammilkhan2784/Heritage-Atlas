# Data provenance and third-party assets

## Historical site records

The portable dataset is a normalized export of the author's original ISTE 438 coursework MongoDB collection `WorldHeritageSites.sites_merged`. The coursework README identifies [UNESCO Heritage Sites 2021 on Kaggle, by Ramjas Maurya](https://www.kaggle.com/datasets/ramjasmaurya/unesco-heritage-sites2021) as its source. Site descriptions originate from the [UNESCO World Heritage Centre](https://whc.unesco.org/en/list/). UNESCO is not affiliated with or endorsing this application.

The export contains 1,155 unique internal site identifiers and 5,639 translation records, with inscription years from 1978 through 2021. Source provenance reflects the original coursework archive; there has been no record-by-record comparison against today's official list. Internal IDs are not official UNESCO inscription numbers.

The original scripts used machine translation to add six languages to English. These translations have incomplete coverage and have not been independently reviewed. Names, boundaries, country/territory labels, descriptions, and inscription status may differ from the current official source.

Normalization removes BSON object IDs, HTML tags, old public comments, and image references without attribution records. It validates finite WGS84 coordinates, standardizes field names and types, splits multi-region membership, treats source zero areas as unknown, rejects duplicate `(site_id, language)` records, and preserves Unicode content. The English categorization totals are 898 cultural, 218 natural, and 39 mixed sites. The manifest records transformations, counts, and the compressed dataset's SHA-256 checksum.

This repository does not assert that third-party descriptions, translated derivatives, or source datasets are in the public domain, nor does it grant a new blanket license over them. Consult the source's terms and [UNESCO's licensing information](https://whc.unesco.org/en/licenses/) before downstream reuse. Attribution in this educational portfolio is not a substitute for applicable source terms.

## Images

The original local GridFS archive contained 876 file records and roughly 3.5 GB of chunk data. It is not part of this repository and was not altered. The source image-gathering scripts did not preserve adequate author/license metadata for each image. The new import command requires attribution and a source page before attaching additional raster media.

`static/images/compass.svg`, `static/images/landscape.svg`, and the CSS globe/category artwork were created for the application. The landscape is a general illustration, not a photograph or representation of the selected heritage site. The unused legacy UNESCO logo image was removed from the application assets.

## Map and frontend libraries

- **Leaflet 1.9.4:** vendored under `static/vendor/leaflet/`, including its BSD-2-Clause license. [Project](https://leafletjs.com/) · [License](../static/vendor/leaflet/LICENSE).
- **OpenStreetMap:** map tiles are requested directly by the browser. Visible map attribution links to [OpenStreetMap copyright and contributors](https://www.openstreetmap.org/copyright). Tile requests disclose the browser's network address to the tile provider and require internet access. Follow the provider's usage policy for a publicly hosted deployment.
- **Axe-core 4.11.0:** development-only accessibility checks, installed through the npm lockfile with the package's upstream license.
- **Prettier 3.8.1:** development-only CSS/JavaScript formatting.

Native MongoDB Community binaries are downloaded on the user's machine from the official distribution and verified against pinned SHA-256 values from its release manifest. They are not redistributed in this Git repository; extracted distributions retain their upstream license notices.
