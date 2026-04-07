import cloudinary.uploader
from fastapi import UploadFile, HTTPException, status
from app.utils.constants import (
    MAX_IMAGE_SIZE_MB, MAX_VIDEO_SIZE_MB,
    ALLOWED_IMAGE_TYPES, ALLOWED_VIDEO_TYPES, MAX_MEDIA_PER_THREAD
)

MB = 1024 * 1024


async def upload_media(files: list[UploadFile]) -> list[str]:
    """
    Validates and uploads media files to Cloudinary.
    Returns list of secure_urls.
    Raises HTTPException for invalid files.
    """
    if len(files) > MAX_MEDIA_PER_THREAD:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
            f'Max {MAX_MEDIA_PER_THREAD} media files per thread')

    urls = []
    for file in files:
        content = await file.read()
        size_mb = len(content) / MB
        ct = file.content_type or ''

        if ct in ALLOWED_IMAGE_TYPES:
            if size_mb > MAX_IMAGE_SIZE_MB:
                raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    f'Image too large (max {MAX_IMAGE_SIZE_MB}MB)')
            resource_type = 'image'
        elif ct in ALLOWED_VIDEO_TYPES:
            if size_mb > MAX_VIDEO_SIZE_MB:
                raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    f'Video too large (max {MAX_VIDEO_SIZE_MB}MB)')
            resource_type = 'video'
        else:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                f'Invalid media type: {ct}')

        result = cloudinary.uploader.upload(
            content,
            resource_type=resource_type,
            folder='threadix/threads'
        )
        urls.append(result['secure_url'])
        await file.seek(0)  # reset for potential re-reads

    return urls
