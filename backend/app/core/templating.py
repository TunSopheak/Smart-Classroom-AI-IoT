from fastapi.templating import Jinja2Templates

from app.core.timezone import format_cambodia_datetime, format_cambodia_time


# One shared template engine so every page gets the same filters.
templates = Jinja2Templates(directory="app/templates")

# Convert naive UTC audit timestamps to Cambodia time for display:
#   {{ event.created_at|kh_datetime }}   {{ event.created_at|kh_time }}
templates.env.filters["kh_datetime"] = format_cambodia_datetime
templates.env.filters["kh_time"] = format_cambodia_time
