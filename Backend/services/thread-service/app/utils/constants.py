# Maximum nesting depth for comments (0 = top-level, 4 = deepest child)
MAX_COMMENT_DEPTH = 4

# Media upload constraints
MAX_IMAGE_SIZE_MB = 10
MAX_VIDEO_SIZE_MB = 100
MAX_MEDIA_PER_THREAD = 5
ALLOWED_IMAGE_TYPES = ['image/jpeg', 'image/png', 'image/webp', 'image/gif']
ALLOWED_VIDEO_TYPES = ['video/mp4', 'video/webm', 'video/quicktime']

# Pagination
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100

# Feed scoring weights
FEED_WEIGHT_VIEW    = 1
FEED_WEIGHT_LIKE    = 3
FEED_WEIGHT_COMMENT = 5

# Tag constraints
MAX_TAGS_PER_THREAD = 5
MAX_TAG_LENGTH = 30
TAG_REGEX = r'^[a-z0-9][a-z0-9\-]*[a-z0-9]$'

# Rate limiting
RATE_LIMIT_THREAD_CREATE  = '5/minute'
RATE_LIMIT_COMMENT_CREATE = '20/minute'
RATE_LIMIT_LIKE           = '60/minute'

# Seeded tags — created on first startup
SEEDED_TAGS = [
    'technology', 'programming', 'python', 'javascript', 'webdev',
    'gaming', 'music', 'art', 'science', 'news',
    'sports', 'movies', 'books', 'food', 'travel',
    'career', 'education', 'health', 'finance', 'general',
]
