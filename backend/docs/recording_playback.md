# Recording Playback

## Product Requirement

Teachers should be able to:

1. Watch saved classroom monitoring videos inside the system
2. Download the video if needed

## Implementation

Camera Monitoring records videos into:

```text
backend/app/static/recordings/
```

The system provides:

- Recording history table
- Watch page with HTML video player
- Download route

## Why Direct MP4 Link May Download

Some browsers or download managers treat direct `.mp4` links as downloadable files.  
A playback page solves this by embedding the MP4 inside a `<video controls>` element.
