"""Processor configuration HTMX components."""

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse
from sqlmodel import Session, select
from app.database import get_session
from app.models import FeedProcessorConfig, Feed, ProcessorTemplate
from .base_component import BaseComponent

router = APIRouter(tags=["htmx-processor-config"])


class ProcessorConfigComponent(BaseComponent):
    """Component for processor configuration-related HTMX endpoints."""

    @staticmethod
    def get_processor_badge_color(processor_type: str) -> str:
        """Get badge color for processor type."""
        return {
            'universal': 'primary',
            'cointelegraph': 'warning',
            'heise': 'success',
            'custom': 'info'
        }.get(processor_type, 'secondary')

    @staticmethod
    def build_config_table_row(config: FeedProcessorConfig, feed: Feed) -> str:
        """Build HTML for a processor config table row."""
        feed_name = feed.title or feed.url[:50] + "..."
        status_badge = "success" if config.is_active else "secondary"
        status_text = "Active" if config.is_active else "Inactive"

        return f'''
        <tr>
            <td>
                <strong>{feed_name}</strong><br>
                <small class="text-muted">{feed.url[:60]}{'...' if len(feed.url) > 60 else ''}</small>
            </td>
            <td>
                <span class="badge bg-{ProcessorConfigComponent.get_processor_badge_color(config.processor_type.value)}">{config.processor_type.value}</span>
            </td>
            <td>
                <span class="badge bg-{status_badge}">{status_text}</span>
            </td>
            <td>
                <small>{ProcessorConfigComponent.format_date(config.created_at)}</small>
            </td>
            <td>
                <div class="btn-group btn-group-sm">
                    <button class="btn btn-outline-primary"
                            data-bs-toggle="modal"
                            data-bs-target="#editConfigModal"
                            hx-get="/htmx/processor-config-form/{config.id}"
                            hx-target="#edit-config-form">
                        <i class="bi bi-pencil"></i>
                    </button>
                    <button class="btn btn-outline-danger"
                            hx-delete="/api/processors/config/{config.id}"
                            hx-target="#feed-configurations"
                            hx-confirm="Really delete configuration?">
                        <i class="bi bi-trash"></i>
                    </button>
                </div>
            </td>
        </tr>
        '''

    @staticmethod
    def build_template_card(template: ProcessorTemplate) -> str:
        """Build HTML for a processor template card."""
        status_badge = "success" if template.is_active else "secondary"
        status_text = "Active" if template.is_active else "Inactive"
        builtin_badge = "warning" if template.is_builtin else "info"
        builtin_text = "Built-in" if template.is_builtin else "Custom"

        delete_button = "" if template.is_builtin else f'''
        <button class="btn btn-outline-danger"
                hx-delete="/api/processors/templates/{template.id}"
                hx-target="#processor-templates"
                hx-confirm="Really delete template?">
            <i class="bi bi-trash"></i>
        </button>
        '''

        return f'''
        <div class="col-md-6">
            <div class="card mb-3">
                <div class="card-body">
                    <div class="d-flex justify-content-between align-items-start mb-2">
                        <h5 class="card-title">{template.name}</h5>
                        <div>
                            <span class="badge bg-{status_badge} me-1">{status_text}</span>
                            <span class="badge bg-{builtin_badge}">{builtin_text}</span>
                        </div>
                    </div>
                    <p class="card-text">
                        <small class="text-muted">{template.description or 'No description'}</small>
                    </p>
                    <div class="mb-2">
                        <strong>Processors:</strong>
                        <code>{template.processor_type.value}</code>
                    </div>
                    <div class="mb-3">
                        <strong>Version:</strong>
                        <span class="badge bg-secondary">{template.version}</span>
                        <small class="text-muted ms-2">
                            Created {ProcessorConfigComponent.format_date(template.created_at)}
                        </small>
                    </div>
                    <div class="btn-group btn-group-sm">
                        <button class="btn btn-outline-primary"
                                data-bs-toggle="modal"
                                data-bs-target="#editTemplateModal"
                                hx-get="/htmx/processor-template-form/{template.id}"
                                hx-target="#edit-template-form">
                            <i class="bi bi-pencil"></i> Edit
                        </button>
                        <button class="btn btn-outline-success"
                                hx-post="/api/processors/templates/{template.id}/apply"
                                hx-target="#processor-templates">
                            <i class="bi bi-play-circle"></i> Apply
                        </button>
                        {delete_button}
                    </div>
                </div>
            </div>
        </div>
        '''


@router.get("/processor-configs", response_class=HTMLResponse)
def get_processor_configs(session: Session = Depends(get_session)):
    """Get processor configurations list."""
    configs = session.exec(
        select(FeedProcessorConfig, Feed)
        .join(Feed, FeedProcessorConfig.feed_id == Feed.id)
        .order_by(Feed.title)
    ).all()

    if not configs:
        return '''
        <div class="alert alert-info">
            <i class="bi bi-info-circle"></i>
            No processor configurations found.
            <a href="#" class="alert-link" data-bs-toggle="modal" data-bs-target="#addConfigModal">
                Add your first configuration
            </a>
        </div>
        '''

    rows = [ProcessorConfigComponent.build_config_table_row(config, feed) for config, feed in configs]

    return f'''
    <div class="table-responsive">
        <table class="table table-hover">
            <thead>
                <tr>
                    <th>Feed</th>
                    <th>Processor Type</th>
                    <th>Status</th>
                    <th>Created</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
                {''.join(rows)}
            </tbody>
        </table>
    </div>
    '''


@router.get("/processor-templates", response_class=HTMLResponse)
def get_processor_templates(session: Session = Depends(get_session)):
    """Get processor templates list."""
    templates = session.exec(
        select(ProcessorTemplate)
        .order_by(ProcessorTemplate.is_builtin.desc(), ProcessorTemplate.name)
    ).all()

    if not templates:
        return '''
        <div class="alert alert-info">
            <i class="bi bi-info-circle"></i>
            No processor templates found.
        </div>
        '''

    cards = [ProcessorConfigComponent.build_template_card(template) for template in templates]

    return f'''
    <div class="row">
        {''.join(cards)}
    </div>
    '''