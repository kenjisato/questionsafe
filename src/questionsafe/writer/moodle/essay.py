# Moodle-specific context for essay
from __future__ import annotations
from ...questions.essay import Essay
from ._build import ctx
from .utils import base_question, rt_text, rt_format


@ctx.register
def _(q: Essay):
    d = base_question(q)
    resp = q.response
    d.update(
        {
            "type": "essay",
            "responseformat": resp.format,
            "responserequired": bool(resp.input_required),
            "responsefieldlines": resp.input_lines,
            "minwordlimit": resp.input_min_words,
            "maxwordlimit": resp.input_max_words,
            "attachments": resp.attachments_count,
            "attachmentsrequired": bool(resp.attachments_required),
            "maxbytes": resp.attachments_maxbytes,
            "filetypeslist": ",".join(resp.attachments_filetypelist)
            if resp.attachments_filetypelist
            else "",
            "responsetemplate_text": rt_text(resp.template),
            "responsetemplate_format": rt_format(resp.template),
            "graderinfo_text": rt_text(q.graderinfo),
            "graderinfo_format": rt_format(q.graderinfo),
        }
    )
    return d
