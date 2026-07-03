from collections import OrderedDict

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.middleware.csrf import get_token
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils.html import escape

from . import google_export
from .cv_render import render_cv_html
from .docx_export import build_cv_document, docx_response
from .models import CVPreset, Entry


PAGE_CSS = """<style>
:root{
  --text:#2C2C2B; --muted:#7D7A75; --canvas:#FFFFFF; --soft:#F9F8F7;
  --surface:#F0EFED; --border:#E6E5E3; --blue:#2783DE; --blue-soft:#E5F2FC;
}
*{box-sizing:border-box;}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
  margin:0;background:var(--soft);color:var(--text);font-size:16px;line-height:1.5;}
a{color:var(--blue);}
.wrap{max-width:1040px;margin:0 auto;padding:32px 24px 64px;}
.header{display:flex;align-items:center;justify-content:space-between;gap:16px;flex-wrap:wrap;}
.header h1{font-size:28px;margin:0;letter-spacing:-0.01em;}
.sub{color:var(--muted);margin:4px 0 24px;}
.layout{display:grid;grid-template-columns:1fr 1fr;gap:24px;align-items:start;}
@media (max-width:860px){.layout{grid-template-columns:1fr;}}
.card{background:var(--canvas);border:1px solid var(--border);border-radius:12px;padding:20px;}
.card h2{font-size:12px;text-transform:uppercase;letter-spacing:0.07em;color:var(--muted);margin:0 0 14px;}
.cat-group{margin-bottom:14px;}
.cat-label{font-size:11px;font-weight:700;color:var(--muted);text-transform:uppercase;
  letter-spacing:0.06em;margin:10px 4px 4px;}
label.check{display:flex;gap:10px;align-items:flex-start;padding:8px 10px;border-radius:8px;cursor:pointer;}
label.check:hover{background:var(--soft);}
input[type=checkbox],input[type=radio]{margin-top:3px;accent-color:var(--blue);width:16px;height:16px;flex:none;}
.entry-title{font-weight:600;}
.entry-meta{color:var(--muted);font-size:14px;}
.achs{margin-left:24px;}
.achs label.check{padding:4px 8px;font-size:14px;}
.filters-row{display:flex;gap:12px;flex-wrap:wrap;align-items:flex-end;}
.inp{display:flex;flex-direction:column;gap:4px;font-size:12px;color:var(--muted);}
select,input[type=date],input[type=text]{font:inherit;padding:9px 10px;border:1px solid var(--border);
  border-radius:8px;background:var(--canvas);color:var(--text);}
.btn{font:inherit;font-weight:500;padding:10px 16px;border-radius:8px;border:1px solid var(--border);
  background:var(--canvas);color:var(--text);cursor:pointer;text-decoration:none;
  display:inline-flex;align-items:center;gap:6px;min-height:40px;}
.btn:hover{background:var(--soft);}
.btn-primary{background:var(--blue);border-color:var(--blue);color:#fff;}
.btn-primary:hover{background:#1f6fc0;}
.btn-ghost{background:transparent;}
.actions{display:flex;gap:10px;flex-wrap:wrap;margin-top:16px;}
.msg{padding:10px 14px;border-radius:8px;background:var(--blue-soft);color:#1a5aa0;margin-bottom:12px;font-size:14px;}
.msg.error{background:#FCE9E7;color:#a5352b;}
.hint{color:var(--muted);font-size:13px;margin-top:6px;}
.field{margin-bottom:16px;}
.empty{color:var(--muted);font-style:italic;}
.preview-card{grid-column:1 / -1;}
.cv-doc{background:#fff;border:1px solid var(--border);border-radius:8px;padding:32px 40px;
  max-width:720px;margin:0 auto;}
.cv-name{font-size:24px;font-weight:700;}
.cv-contact{color:var(--muted);font-size:14px;margin-bottom:8px;}
.cv-section{margin-top:20px;}
.cv-section h3{font-size:12px;text-transform:uppercase;letter-spacing:0.08em;color:var(--blue);
  border-bottom:2px solid var(--blue-soft);padding-bottom:4px;margin:0 0 10px;}
.cv-item{margin-bottom:12px;}
.cv-item-head{display:flex;justify-content:space-between;gap:12px;align-items:baseline;}
.cv-role{font-weight:600;}
.cv-date{color:var(--muted);font-size:13px;white-space:nowrap;}
.cv-desc{font-size:14px;margin-top:2px;}
.cv-ach{margin:6px 0 0;padding-left:20px;}
.cv-ach li{font-size:14px;margin:2px 0;}
</style>"""


def _filtered_entries(request):
    entries = Entry.objects.prefetch_related("achievements").all()
    category = request.GET.get("category")
    date_from = request.GET.get("date_from")
    date_to = request.GET.get("date_to")
    if category:
        entries = entries.filter(category=category)
    if date_from:
        entries = entries.filter(start_date__gte=date_from)
    if date_to:
        entries = entries.filter(start_date__lte=date_to)
    return entries


def _user_name(request):
    return request.user.get_full_name() or request.user.username


@login_required
def builder(request):
    if request.method == "POST":
        entry_ids = [int(x) for x in request.POST.getlist("entries")]
        ach_ids = [int(x) for x in request.POST.getlist("achievements")]
        layout = request.POST.get("layout", CVPreset.NESTED)
        action = request.POST.get("action")

        selected_entries = Entry.objects.prefetch_related("achievements").filter(
            id__in=entry_ids
        )

        if action == "save_preset":
            name = request.POST.get("preset_name", "").strip()
            if not name:
                messages.error(request, "Give the preset a name to save it.")
            else:
                preset, _ = CVPreset.objects.update_or_create(
                    name=name,
                    defaults={"achievement_layout": layout},
                )
                preset.entries.set(entry_ids)
                preset.achievements.set(ach_ids)
                messages.success(request, f'Saved preset "{name}".')
            return redirect("builder")

        if action == "gdoc":
            return _selection_to_gdoc(
                request, selected_entries, set(ach_ids), layout
            )

        if action == "preview":
            preview_html = render_cv_html(
                entries=selected_entries,
                selected_achievement_ids=set(ach_ids),
                layout=layout,
                full_name=_user_name(request),
                contact=request.user.email,
            )
            html = _render_builder_html(
                request,
                entries=list(_filtered_entries(request)),
                selected_category=request.GET.get("category", ""),
                date_from=request.GET.get("date_from", ""),
                date_to=request.GET.get("date_to", ""),
                checked_entries=set(entry_ids),
                checked_achievements=set(ach_ids),
                layout=layout,
                preview_html=preview_html,
            )
            return HttpResponse(html)

        # Default action: export .docx
        buffer = build_cv_document(
            entries=selected_entries,
            selected_achievement_ids=set(ach_ids),
            layout=layout,
            full_name=_user_name(request),
            contact=request.user.email,
        )
        return docx_response(buffer, filename="cv.docx")

    html = _render_builder_html(
        request,
        entries=list(_filtered_entries(request)),
        selected_category=request.GET.get("category", ""),
        date_from=request.GET.get("date_from", ""),
        date_to=request.GET.get("date_to", ""),
    )
    return HttpResponse(html)


@login_required
def load_preset(request, preset_id):
    preset = get_object_or_404(CVPreset, id=preset_id)
    entries = preset.entries.prefetch_related("achievements").all()
    ach_ids = set(preset.achievements.values_list("id", flat=True))
    buffer = build_cv_document(
        entries=entries,
        selected_achievement_ids=ach_ids,
        layout=preset.achievement_layout,
        full_name=_user_name(request),
        contact=request.user.email,
    )
    return docx_response(buffer, filename=f"{preset.name}.docx")


# --- Google Docs ------------------------------------------------------------

def _selection_to_gdoc(request, entries, ach_ids, layout, title="CV"):
    if not google_export.is_enabled():
        messages.error(request, "Google Docs export is not enabled.")
        return redirect("builder")
    if not google_export.has_credentials():
        return redirect("google_authorize")
    buffer = build_cv_document(
        entries=entries,
        selected_achievement_ids=ach_ids,
        layout=layout,
        full_name=_user_name(request),
        contact=request.user.email,
    )
    link = google_export.upload_docx_as_gdoc(buffer.getvalue(), title)
    if not link:
        return redirect("google_authorize")
    return redirect(link)


@login_required
def preset_to_gdoc(request, preset_id):
    preset = get_object_or_404(CVPreset, id=preset_id)
    entries = preset.entries.prefetch_related("achievements").all()
    ach_ids = set(preset.achievements.values_list("id", flat=True))
    return _selection_to_gdoc(
        request, entries, ach_ids, preset.achievement_layout, title=preset.name
    )


@login_required
def google_authorize(request):
    if not google_export.is_enabled():
        messages.error(request, "Google Docs export is not enabled.")
        return redirect("builder")
    redirect_uri = request.build_absolute_uri(reverse("google_callback"))
    flow = google_export.build_flow(redirect_uri)
    auth_url, state = flow.authorization_url(
        access_type="offline", include_granted_scopes="true", prompt="consent"
    )
    request.session["google_oauth_state"] = state
    # Persist the PKCE verifier so the callback (a separate request) can
    # complete the token exchange.
    request.session["google_code_verifier"] = flow.code_verifier
    return redirect(auth_url)


@login_required
def google_callback(request):
    redirect_uri = request.build_absolute_uri(reverse("google_callback"))
    flow = google_export.build_flow(redirect_uri)
    flow.code_verifier = request.session.get("google_code_verifier")
    flow.fetch_token(authorization_response=request.build_absolute_uri())
    google_export.store_credentials_from_flow(flow)
    messages.success(request, "Connected to Google Docs.")
    return redirect("builder")


# --- HTML rendering ---------------------------------------------------------

def _render_builder_html(request, *, entries, selected_category, date_from,
                         date_to, checked_entries=None,
                         checked_achievements=None, layout=None,
                         preview_html=None):
    def entry_checked(entry):
        return checked_entries is None or entry.id in checked_entries

    def ach_checked(ach):
        return checked_achievements is None or ach.id in checked_achievements

    out = []
    out.append("<!DOCTYPE html><html lang='en'><head><meta charset='utf-8'>")
    out.append("<meta name='viewport' content='width=device-width, initial-scale=1'>")
    out.append("<title>SkillHub \u00b7 CV Builder</title>")
    out.append(PAGE_CSS)
    out.append("</head><body><div class='wrap'>")
    out.append(
        "<div class='header'><h1>CV Builder</h1>"
        "<a class='btn btn-ghost' href='/admin/'>Manage skills</a></div>"
    )
    out.append(
        "<p class='sub'>Pick what to include, preview it live, then export a "
        ".docx or save it as a preset.</p>"
    )

    for message in messages.get_messages(request):
        css = "msg error" if message.level_tag == "error" else "msg"
        out.append(f"<div class='{css}'>{escape(str(message))}</div>")

    # Filter (GET form, separate from the selection form)
    options = ["<option value=''>All categories</option>"]
    for value, label in Entry.CATEGORY_CHOICES:
        selected = " selected" if value == selected_category else ""
        options.append(f"<option value='{value}'{selected}>{escape(label)}</option>")
    options_html = "".join(options)
    out.append("<form method='get' class='card' style='margin-bottom:24px'>")
    out.append("<h2>Filter</h2><div class='filters-row'>")
    out.append(
        f"<label class='inp'>Category<select name='category'>{options_html}</select></label>"
    )
    out.append(
        f"<label class='inp'>From<input type='date' name='date_from' value='{escape(date_from)}'></label>"
    )
    out.append(
        f"<label class='inp'>To<input type='date' name='date_to' value='{escape(date_to)}'></label>"
    )
    out.append("<button class='btn' type='submit'>Apply</button>")
    out.append(f"<a class='btn btn-ghost' href='{reverse('builder')}'>Reset</a>")
    out.append("</div></form>")

    # Selection form
    token = get_token(request)
    out.append("<form method='post'>")
    out.append(f"<input type='hidden' name='csrfmiddlewaretoken' value='{token}'>")
    out.append("<div class='layout'>")

    if preview_html:
        out.append("<div class='card preview-card'><h2>Preview</h2>")
        out.append(preview_html)
        out.append("</div>")

    # Entries card
    out.append("<div class='card'><h2>Entries</h2>")
    entries = list(entries)
    if not entries:
        out.append(
            "<p class='empty'>No entries yet. "
            "<a href='/admin/cv/entry/add/'>Add some in the admin.</a></p>"
        )
    else:
        by_cat = OrderedDict((key, []) for key, _ in Entry.CATEGORY_CHOICES)
        for entry in entries:
            by_cat.setdefault(entry.category, []).append(entry)
        for key, label in Entry.CATEGORY_CHOICES:
            items = by_cat.get(key) or []
            if not items:
                continue
            out.append(
                f"<div class='cat-group'><div class='cat-label'>{escape(label)}</div>"
            )
            for entry in items:
                ec = " checked" if entry_checked(entry) else ""
                meta = escape(entry.organization) if entry.organization else ""
                date_range = entry.date_range()
                if date_range:
                    date_txt = escape(date_range)
                    meta = f"{meta} \u00b7 {date_txt}" if meta else date_txt
                meta_html = (
                    f"<br><span class='entry-meta'>{meta}</span>" if meta else ""
                )
                out.append(
                    "<label class='check'>"
                    f"<input type='checkbox' name='entries' value='{entry.id}'{ec}>"
                    f"<span><span class='entry-title'>{escape(entry.name)}</span>"
                    f"{meta_html}</span></label>"
                )
                achievements = list(entry.achievements.all())
                if achievements:
                    out.append("<div class='achs'>")
                    for ach in achievements:
                        ac = " checked" if ach_checked(ach) else ""
                        out.append(
                            "<label class='check'>"
                            f"<input type='checkbox' name='achievements' value='{ach.id}'{ac}>"
                            f"<span>{escape(ach.display())}</span></label>"
                        )
                    out.append("</div>")
            out.append("</div>")
    out.append("</div>")

    # Options card
    out.append("<div class='card'><h2>Options</h2>")
    out.append(
        "<div class='field'><div class='cat-label' style='margin-left:0'>"
        "Achievement layout</div>"
    )
    for index, (value, label) in enumerate(CVPreset.LAYOUT_CHOICES):
        if layout is None:
            is_checked = index == 0
        else:
            is_checked = layout == value
        ck = " checked" if is_checked else ""
        out.append(
            "<label class='check'>"
            f"<input type='radio' name='layout' value='{value}'{ck}>"
            f"<span>{escape(label)}</span></label>"
        )
    out.append("</div>")

    out.append(
        "<div class='field'><div class='cat-label' style='margin-left:0'>"
        "Save as preset</div>"
    )
    out.append(
        "<input type='text' name='preset_name' placeholder='e.g. Research Lab' "
        "style='width:100%'>"
    )
    out.append(
        "<div class='hint'>Presets rebuild this exact CV in one click.</div></div>"
    )

    out.append("<div class='actions'>")
    out.append(
        "<button class='btn btn-primary' type='submit' name='action' value='preview'>Preview</button>"
    )
    out.append(
        "<button class='btn' type='submit' name='action' value='export'>Export .docx</button>"
    )
    out.append(
        "<button class='btn' type='submit' name='action' value='save_preset'>Save preset</button>"
    )
    if google_export.is_enabled():
        out.append(
            "<button class='btn' type='submit' name='action' value='gdoc'>Save to Google Docs</button>"
        )
    out.append("</div>")
    out.append("</div>")  # options card

    out.append("</div>")  # layout
    out.append("</form>")

    # Saved presets
    out.append("<div class='card' style='margin-top:24px'><h2>Saved presets</h2>")
    presets = list(CVPreset.objects.all())
    if not presets:
        out.append("<p class='empty'>No presets saved yet.</p>")
    else:
        for preset in presets:
            export_url = reverse("load_preset", args=[preset.id])
            gdoc_html = ""
            if google_export.is_enabled():
                gdoc_url = reverse("preset_to_gdoc", args=[preset.id])
                gdoc_html = (
                    f"<a class='btn btn-ghost' href='{gdoc_url}'>Google Docs</a>"
                )
            out.append(
                "<div style='display:flex;justify-content:space-between;"
                "align-items:center;gap:12px;padding:10px 0;"
                "border-bottom:1px solid var(--border)'>"
                f"<span><strong>{escape(preset.name)}</strong> "
                f"<span class='entry-meta'>\u00b7 {escape(preset.get_achievement_layout_display())}</span></span>"
                f"<span style='display:flex;gap:8px'>"
                f"<a class='btn' href='{export_url}'>.docx</a>{gdoc_html}</span>"
                "</div>"
            )
    out.append("</div>")

    out.append("</div></body></html>")
    return "".join(out)