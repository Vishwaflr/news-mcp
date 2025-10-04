"""Base component with shared HTML builders and utilities for HTMX components."""

from typing import Dict, Any, Optional, List
from datetime import datetime
import re


class BaseComponent:
    """Base class for HTMX components with shared HTML builders."""

    @staticmethod
    def status_badge(status: str, size: str = "ms-2") -> str:
        """Generate a status badge HTML."""
        badge_classes = {
            "active": "success",
            "inactive": "warning",
            "error": "danger"
        }
        badge_class = badge_classes.get(status, "secondary")
        return f'<span class="badge bg-{badge_class} {size}">{status}</span>'

    @staticmethod
    def category_badges(categories: List[Any]) -> str:
        """Generate category badges HTML."""
        if not categories:
            return '<span class="badge bg-secondary ms-1">No Category</span>'

        badges = ""
        for category in categories:
            title_attr = f'title="{category.description}"' if hasattr(category, 'description') and category.description else ""
            badges += f'<span class="badge bg-primary ms-1" {title_attr}>{category.name}</span>'
        return badges

    @staticmethod
    def format_date(date: Optional[datetime], format_str: str = "%d.%m.%Y %H:%M") -> str:
        """Format datetime to string or return fallback."""
        if date:
            return date.strftime(format_str)
        return "Never"

    @staticmethod
    def clean_html_attr(text: str) -> str:
        """Clean text for use in HTML attributes - removes HTML tags and escapes quotes."""
        if not text:
            return ''
        # Remove all HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        # Replace HTML entities
        text = text.replace('&quot;', '"').replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&')
        # Escape quotes for HTML attributes
        text = text.replace('"', '&quot;')
        # Remove extra whitespace
        text = ' '.join(text.split())
        return text

    @staticmethod
    def truncate_text(text: str, max_length: int = 200) -> str:
        """Truncate text with ellipsis."""
        if not text:
            return ""
        return text[:max_length] + "..." if len(text) > max_length else text

    @staticmethod
    def alert_box(message: str, alert_type: str = "info", icon: str = None) -> str:
        """Generate Bootstrap alert box."""
        icon_html = f'<i class="bi bi-{icon}"></i> ' if icon else ""
        return f'<div class="alert alert-{alert_type}">{icon_html}{message}</div>'

    @staticmethod
    def button_group(buttons: List[Dict[str, Any]]) -> str:
        """Generate button group HTML."""
        html = '<div class="btn-group">'
        for btn in buttons:
            classes = btn.get('classes', 'btn btn-sm btn-outline-primary')
            attrs = btn.get('attrs', {})
            icon = btn.get('icon')
            text = btn.get('text', '')

            attr_str = ' '.join([f'{k}="{v}"' for k, v in attrs.items()])
            icon_html = f'<i class="bi bi-{icon}"></i>' if icon else ''

            html += f'<button class="{classes}" {attr_str}>{icon_html}{text}</button>'

        html += '</div>'
        return html

    @staticmethod
    def card_container(content: str, title: str = None, classes: str = "card mb-2") -> str:
        """Generate Bootstrap card container."""
        title_html = f'<h6 class="card-title mb-1">{title}</h6>' if title else ''
        return f'''
        <div class="{classes}">
            <div class="card-body">
                {title_html}
                {content}
            </div>
        </div>
        '''

    @staticmethod
    def load_button(entity_id: int, entity_type: str = "feed") -> str:
        """Generate load articles button."""
        return f'''
        <button class="btn btn-sm btn-success"
                hx-post="/htmx/{entity_type}-fetch-now/{entity_id}"
                hx-target="#fetch-status-{entity_id}"
                hx-swap="innerHTML"
                title="Load articles immediately">
            <i class="bi bi-download"></i> Load
        </button>'''

    @staticmethod
    def modal_button(target_endpoint: str, target_id: int, modal_id: str,
                     icon: str, classes: str = "btn btn-sm btn-outline-primary",
                     title: str = "") -> str:
        """Generate modal trigger button."""
        return f'''
        <button class="{classes}"
                hx-get="{target_endpoint}/{target_id}"
                hx-target="#{modal_id}-content"
                data-bs-toggle="modal"
                data-bs-target="#{modal_id}"
                title="{title}">
            <i class="bi bi-{icon}"></i>
        </button>'''

    @staticmethod
    def action_button(endpoint: str, method: str = "get", target: str = "",
                     swap: str = "innerHTML", icon: str = "",
                     classes: str = "btn btn-sm btn-outline-primary",
                     confirm: str = None, vals: str = None) -> str:
        """Generate HTMX action button."""
        attrs = [f'hx-{method}="{endpoint}"']

        if target:
            attrs.append(f'hx-target="{target}"')
        if swap != "innerHTML":
            attrs.append(f'hx-swap="{swap}"')
        if confirm:
            attrs.append(f'hx-confirm="{confirm}"')
        if vals:
            attrs.append(f'hx-vals=\'{vals}\'')

        attr_str = ' '.join(attrs)
        icon_html = f'<i class="bi bi-{icon}"></i>' if icon else ''

        return f'<button class="{classes}" {attr_str}>{icon_html}</button>'