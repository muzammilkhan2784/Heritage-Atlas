# UNESCO World Heritage Explorer
### (MongoDB, Flask, GridFS, GeoJSON, Geospatial Search)

Multilingual search platform enabling users to discover UNESCO World Heritage Sites through keyword, image, and location-based search.

- Implemented geospatial and regex-based search using MongoDB nearSphere queries and GeoJSON data
- Integrated GridFS image storage and translated site information into six languages

1.  Technology Stack

I used the following stack for my UNESCO World Heritage Sites project:

Backend
Flask (Python): For the web framework as it is lightweight, easy to integrate with MongoDB, and allows rapid development.
MongoDB: A NoSQL database ideal for storing semi-structured UNESCO site data including text, coordinates, and images.
GridFS: Used to store and retrieve site images efficiently inside MongoDB.
Pymongo: Python library to interact with MongoDB from Flask.
MongoDB Authentication: Configured a mongoapp user with readWrite privileges to ensure secure database access.

Frontend
HTML/CSS (with Jinja2 templating): For the frontend interface.

Tools & Utilities 
VSCode & GitHub Classroom: For code development and collaboration.
Ubuntu VM on RLES: Deployed and tested in a Linux virtual environment for compatibility.

I chose this stack because it is lightweight, scalable, integrates well with geospatial queries, and is beginner-friendly for rapid development.



2.  Process

I began by sourcing my dataset from Kaggle:
[ 🔗 UNESCO Heritage Sites 2021 – Kaggle] (https://www.kaggle.com/datasets/ramjasmaurya/unesco-heritage-sites2021/data)

After downloading the dataset, I cleansed it by removing unnecessary columns and standardized formats such as dates and coordinate fields. Once cleaned, the dataset was imported into MongoDB using mongoimport, and stored in a collection named Sites.
Since the dataset did not include any images, I used a Python script to automatically fetch the actual image files from Wikipedia using the site names. The script queried the Wikipedia API to obtain the primary image for each site, then downloaded the image content and saved it locally using the site's site_id as the filename. These images were stored in a dedicated folder, ready to be uploaded into MongoDB using GridFS.

I then used another Python script to:

Upload the images to MongoDB using GridFS

Link each site document to its corresponding image via image_id

Convert latitude and longitude fields into GeoJSON Point format

Create a 2dsphere index on the location field to enable geospatial queries


For entries where an image could not be found on Wikipedia, I used a default placeholder image, which was uploaded once to GridFS and linked to all sites missing an individual image.

After my initial submission, I found that the dataset was relatively small. To expand its variety and demonstrate multilingual capabilities, I duplicated the dataset and used another Python script to translate key fields (such as the name and description) into six different languages using the Google Translate API. These translated records were stored in a separate collection called sites_translated.

Finally, I merged the original collection and the translated entries into a unified collection named sites_merged, which now powers all multilingual, geospatial, and image-driven features in the final application.


Challenges encountered:

No Images in Original Dataset: The dataset did not include any images, so I had to build a separate process to fetch images from Wikipedia and link them to the correct records.

Difficulty Fetching Images: Not all sites had reliable or consistent image results on Wikipedia, which led to gaps that required fallback handling with a default image.

Translation Limitations: Translating multilingual content presented difficulties, including API rate limits, occasional inaccurate translations, and language-specific formatting issues.

Inconsistent Field Structures: Some fields across records were named or formatted inconsistently, requiring cleanup before import.




3. Volume

Here are the results of countDocuments() for my collections:

db.sites_merged.countDocuments()
5639

db.fs.files.countDocuments()
876

db.fs.chunks.countDocuments()
13777



4.  Variety

Here are some interesting searches that demonstrate variety:

Search for “temple” → Click on "Megalithic Temples of Maltar" to view multilingual descriptions and additional site details.

Geospatial Search: Enter coordinates 13.4125, 103.866667 with a radius of 100 km → Returns heritage sites located in Cambodia.

Search for “forest” → Displays natural heritage sites such as tropical rainforests, often with available images.

Language Toggle: Select any site and change the language dropdown → Instantly switches to translated versions while preserving metadata.

Search near Paris: Use coordinates 48.85, 2.35 with a 100 km radius → Filters and returns sites in and around the Paris region.



5. Bells and Whistles

Some standout features of my app:

a. Geospatial Search: Users can search for sites within a specific radius of a given location using latitude, longitude, and distance.

b. Multilingual Support: Content is displayed in multiple languages based on user selection.

c. GridFS Image Storage: Efficient and scalable way to store images alongside site metadata.

d. User Comments: Users can leave comments on each site page, and they persist across languages.

e. Default Image Handling: Displays a fallback image when no GridFS image is available.

f. Clean & Responsive UI: Styled using custom CSS for clarity and usability across devices.

g. Persistent Search Inputs: Form data is stored in session to retain search values across page refreshes.


Secure Access: Database is protected using a MongoDB user account with minimal required permissions.


This project combines multilingual content, geospatial logic, and image-based visualization into a single web platform. I'm proud of how smoothly Flask, MongoDB, and GridFS worked together to create a seamless, educational user experience.
