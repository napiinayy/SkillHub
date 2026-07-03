from django.utils.html import escape

from .models import Entry


def render_cv_html(entries, selected_achievement_ids, layout,
                   full_name="Your Name", contact=""):
    """Render a live HTML preview of the CV for the given selection."""
    grouped = {key: [] for key, _ in Entry.CATEGORY_CHOICES}
    for entry in entries:
        if entry.category in grouped:
            grouped[entry.category].append(entry)

    parts = ["<div class='cv-doc'>"]
    parts.append(f"<div class='cv-name'>{escape(full_name)}</div>")
    if contact:
        parts.append(f"<div class='cv-contact'>{escape(contact)}</div>")

    all_achievements = []
    for key, label in Entry.CATEGORY_CHOICES:
        items = grouped.get(key) or []
        if not items:
            continue
        parts.append(f"<div class='cv-section'><h3>{escape(label)}</h3>")
        for entry in items:
            org = f" \u00b7 {escape(entry.organization)}" if entry.organization else ""
            date_range = entry.date_range()
            date_html = (
                f"<span class='cv-date'>{escape(date_range)}</span>"
                if date_range else ""
            )
            parts.append("<div class='cv-item'>")
            parts.append(
                "<div class='cv-item-head'>"
                f"<span class='cv-role'>{escape(entry.name)}{org}</span>"
                f"{date_html}</div>"
            )
            if entry.description:
                parts.append(
                    f"<div class='cv-desc'>{escape(entry.description)}</div>"
                )
            achievements = [
                a for a in entry.achievements.all()
                if a.id in selected_achievement_ids
            ]
            all_achievements.extend(achievements)
            if layout == "nested" and achievements:
                parts.append("<ul class='cv-ach'>")
                for ach in achievements:
                    parts.append(f"<li>{escape(ach.display())}</li>")
                parts.append("</ul>")
            parts.append("</div>")
        parts.append("</div>")

    if layout == "section" and all_achievements:
        parts.append(
            "<div class='cv-section'><h3>Achievements</h3><ul class='cv-ach'>"
        )
        for ach in all_achievements:
            parts.append(f"<li>{escape(ach.display())}</li>")
        parts.append("</ul></div>")

    parts.append("</div>")
    return "".join(parts)
