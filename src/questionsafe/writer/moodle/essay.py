# Moodle-specific context for essay
from __future__ import annotations
from ...questions.essay import Essay
from ._build import ctx
from .utils import base_question, rt_text, rt_format


@ctx.register
def _(q: Essay):
    d = base_question(q)
    resp = q.response
    ta = resp.textarea
    at = resp.attachments
    d.update(
        {
            "type": "essay",
            "responseformat": ta.format,
            "responserequired": bool(ta.required),
            "responsefieldlines": ta.lines,
            "minwordlimit": ta.min_words,
            "maxwordlimit": ta.max_words,
            "attachments": at.count,
            "attachmentsrequired": bool(at.required),
            "maxbytes": at.maxbytes,
            "filetypeslist": ",".join(at.filetypelist) if at.filetypelist else "",
            "responsetemplate_text": rt_text(ta.template),
            "responsetemplate_format": rt_format(ta.template),
            "graderinfo_text": rt_text(q.graderinfo),
            "graderinfo_format": rt_format(q.graderinfo),
        }
    )
    return d
