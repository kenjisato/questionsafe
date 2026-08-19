# src/questionsafe/importers/markdown.py
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Tuple, Optional

import os
import re
import frontmatter
import warnings
import yaml

from .. import Q, Text
from ..base._question import Question
from ..base._answer import Answer
from ..base._mixins import MultiTryMixin, CombinedFeedbackMixin


# --- Coercion and common-applier helpers ------------------------------------

def _load_vars_from_cwd() -> dict:
    cfg_path = Path.cwd() / "questionsafe.yml"
    if not cfg_path.exists() or not cfg_path.is_file():
        return {}
    try:
        data = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
        if not isinstance(data, dict):
            return {}
        vars_block = data.get("variables", {})
        return dict(vars_block) if isinstance(vars_block, dict) else {}
    except Exception:
        return {}


def _expand_with_vars(s: str, vars_map: dict) -> str:
    if not isinstance(s, str):
        return s
    s2 = os.path.expanduser(s)
    pattern = re.compile(r"\$(?:([A-Za-z_][A-Za-z0-9_]*)|\{([^}]+)\})")

    def repl(m):
        key = m.group(1) or m.group(2)
        if key in vars_map:
            return str(vars_map[key])
        return os.environ.get(key, m.group(0))

    return pattern.sub(repl, s2)

def _coerce_text_like(val: Any, *, default_format: str = "markdown") -> Text | str | None:
    if val is None:
        return None
    if isinstance(val, Text):
        return val
    if isinstance(val, dict):
        return Text(str(val.get("text", "")), format=str(val.get("format", default_format)))
    return str(val)


def _apply_question_common(q: Any, meta: Dict[str, Any], body: str, *, default_format: str = "markdown") -> None:
    # questiontext from body (if non-empty)
    bt = (body or "").strip()
    if bt:
        fmt = str(meta.get("questiontext_format") or meta.get("format") or default_format)
        q.ask(Text(bt, format=fmt))
    # defaultgrade
    if "defaultgrade" in meta:
        try:
            q.set_defaultgrade(float(meta["defaultgrade"]))
        except Exception:
            pass
    # general feedback
    fb_meta = meta.get("feedback") or {}
    if isinstance(fb_meta, dict) and "general" in fb_meta:
        q.set_feedback_general(_coerce_text_like(fb_meta.get("general")))
    # tags
    tags_raw = meta.get("tags")
    if isinstance(tags_raw, (list, tuple)) and len(tags_raw) > 0:
        try:
            q.set_tags(*[str(t) for t in tags_raw])
        except Exception:
            pass
    # idnumber
    if "id" in meta and meta["id"] is not None:
        try:
            q.set_idnumber(str(meta["id"]))
        except Exception:
            pass

    # full-form answers (text-based question types): delegated to interface methods
    answers_meta = meta.get("answers")
    if isinstance(answers_meta, list) and answers_meta:
        try:
            from ..questions import SingleChoice as _SC, TrueFalse as _TF, MultiChoice as _MC, ShortAnswer as _SA
            # Only apply for text-answer based question types
            if isinstance(q, (_SC, _TF, _MC, _SA)):
                answers_list = _parse_text_answers(answers_meta)
                if answers_list:
                    q.set_answers(*answers_list)  # type: ignore[call-arg]
        except Exception:
            # Be forgiving; leave to validate() later
            pass

    # apply mixin-based configuration if supported
    _apply_multitry_common(q, meta)
    _apply_combined_feedback_common(q, meta)


def _apply_multitry_common(q: Any, meta: Dict[str, Any]) -> None:
    # Only apply when the object supports MultiTry and has_hints is enabled
    if not isinstance(q, MultiTryMixin):
        return
    if not getattr(q, "has_hints", False):
        # emit warning if hints/penalty provided but ignored
        if meta.get("hints") or (meta.get("hint_penalty") is not None):
            warnings.warn("Hints/penalty are not supported for this question type; ignoring.", UserWarning, stacklevel=2)
        return
    hints_meta = meta.get("hints", None)
    penalty = meta.get("hint_penalty", None)
    if hints_meta is None and penalty is None:
        return
    parsed: list[Any] = []
    if isinstance(hints_meta, (list, tuple)):
        for h in hints_meta:
            parsed.append(_coerce_text_like(h))
    try:
        if parsed and penalty is None:
            q.set_hints(*parsed)
        elif parsed and penalty is not None:
            q.set_hints(*parsed, penalty=float(penalty))
        elif penalty is not None:
            q.set_penalty(float(penalty))
    except Exception:
        pass


def _apply_combined_feedback_common(q: Any, meta: Dict[str, Any]) -> None:
    fb_meta = meta.get("feedback") or {}
    if not isinstance(fb_meta, dict):
        return
    keys_present = any(k in fb_meta for k in ("correct", "partiallycorrect", "incorrect"))
    # Only apply when the object supports CombinedFeedback and has_combined_feedback is enabled
    if not isinstance(q, CombinedFeedbackMixin) or not getattr(q, "has_combined_feedback", False):
        if keys_present:
            warnings.warn("Combined feedback is not supported for this question type; ignoring.", UserWarning, stacklevel=2)
        return
    # apply combined feedback
    kwargs: Dict[str, Any] = {}
    for key in ("correct", "partiallycorrect", "incorrect"):
        if key in fb_meta:
            kwargs[key] = _coerce_text_like(fb_meta.get(key))
    if not kwargs:
        return
    try:
        q.set_feedback_combined(**kwargs)  # type: ignore[arg-type]
    except Exception:
        if "correct" in kwargs:
            q.set_feedback_correct(kwargs["correct"])  # type: ignore[arg-type]
        if "partiallycorrect" in kwargs:
            q.set_feedback_partiallycorrect(kwargs["partiallycorrect"])  # type: ignore[arg-type]
        if "incorrect" in kwargs:
            q.set_feedback_incorrect(kwargs["incorrect"])  # type: ignore[arg-type]


def _parse_text_answers(answers_meta: Any) -> list:
    """Parse a list of text answers from front matter answers.

    Each item may be:
    - dict with keys: text, fraction, feedback (str or {text,format})
    - bare string (treated as fraction=0)
    Returns a list of Answer.from_text(...) (TextAnswer instances).
    """
    results: list = []
    if not isinstance(answers_meta, list):
        return results
    for item in answers_meta:
        if isinstance(item, dict):
            txt = str(item.get("text", "")).strip()
            if not txt:
                continue
            try:
                frac = float(item.get("fraction", 0.0))
            except Exception:
                frac = 0.0
            fb_val = _coerce_text_like(item.get("feedback"))
            results.append(Answer.from_text(txt, fraction=frac, feedback=fb_val))
        else:
            # fallback: treat as string
            txt = str(item)
            if txt.strip():
                results.append(Answer.from_text(txt, fraction=0.0))
    return results


def _merge_includes(self, meta: Dict[str, Any], *, include_warn: bool = False) -> None:
    inc = meta.get("include")
    if not inc:
        return
    includes = [inc] if isinstance(inc, (str, Path)) else list(inc)
    base_dir = self.answer_dir or self.path.parent
    merged: Dict[str, Any] = {}
    for item in includes:
        if isinstance(item, (str, Path)):
            item = _expand_with_vars(str(item), getattr(self, "_project_vars", {}))
        p = Path(item)
        if not p.is_absolute():
            p = base_dir / p
        if not p.exists() or not p.is_file():
            raise FileNotFoundError(f"Included file not found: {p}")
        ext = p.suffix.lower()
        data: Dict[str, Any] | Any
        if ext in {".yml", ".yaml"}:
            data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
            if not isinstance(data, dict):
                raise ValueError(f"Included YAML must be a mapping: {p}")
        elif ext in {".md", ".qmd", ".rmd", ".rmarkdown"}:
            post = frontmatter.load(p)
            data = dict(post.metadata or {})
            if not isinstance(data, dict):
                raise ValueError(f"Included Markdown front matter must be a mapping: {p}")
        else:
            # Default to YAML parsing for unknown extensions, for flexibility
            data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
            if not isinstance(data, dict):
                raise ValueError(f"Included file must parse to a mapping (YAML or front matter): {p}")
        for k, v in data.items():
            # Explicitly ignore nested includes to keep behavior single-level
            if k == "include":
                continue
            if k in meta:
                if meta[k] != v:
                    if include_warn:
                        warnings.warn(
                            f"Ignoring included value for key '{k}' from {p} (outer front matter has precedence)",
                            UserWarning,
                            stacklevel=2,
                        )
                continue
            if k in merged and merged[k] != v:
                if include_warn:
                    warnings.warn(
                        f"Conflicting values for key '{k}' among include files; keeping first value.",
                        UserWarning,
                        stacklevel=2,
                    )
                continue
            merged[k] = v
    for k, v in merged.items():
        if k not in meta:
            meta[k] = v


@dataclass
class Reader:
    """Read a single question from a Markdown file with YAML front matter.

    Usage
    - md = Reader("path/to/a_question.md")
    - q = md.read()  # -> a Question instance (e.g., Q.SingleChoice)

    Paths
    - answer_dir: base directory used when resolving 'include' files referenced by this document.
    - question_dir: base directory used when resolving cloze.file entries (embedded sub-questions).

    Supported types (initial): singlechoice
    """

    path: Path
    answer_dir: Optional[Path] = None
    question_dir: Optional[Path] = None

    def __init__(self, path: str | Path, *, answer_dir: str | Path | None = None, question_dir: str | Path | None = None):
        self.path = Path(path)
        self.answer_dir = Path(answer_dir) if answer_dir is not None else None
        self.question_dir = Path(question_dir) if question_dir is not None else None
        # Load project variables (from cwd)
        self._project_vars: Dict[str, Any] = _load_vars_from_cwd()

    # --- Public API ---
    def read(self, *, include_warn: bool = False, validate: bool = True) -> Question[Any]:
        post = frontmatter.load(self.path)
        meta: Dict[str, Any] = dict(post.metadata or {})
        body: str = post.content or ""

        # Merge includes before reading type
        _merge_includes(self, meta, include_warn=include_warn)

        # Optional wrapper: question: { type: ..., name: ..., ... }
        qwrap = meta.get("question")
        if isinstance(qwrap, dict):
            # Overlay with inner mapping, prefer inner keys
            # Keep merged includes at top-level unaffected
            inner = dict(qwrap)
            # Replace meta with inner keys overlaid on existing meta
            base = dict(meta)
            base.update(inner)
            meta = base

        qtype = str(meta.get("type", "")).strip().lower()
        if not qtype:
            raise ValueError("front matter must include 'type'")

        q: Question[Any]
        if qtype in {"singlechoice", "single", "sc"}:
            q = self._build_singlechoice(meta, body)
        elif qtype in {"truefalse", "tf"}:
            q = self._build_truefalse(meta, body)
        elif qtype in {"multichoice", "multiple", "multi", "mc"}:
            q = self._build_multichoice(meta, body)
        elif qtype in {"numerical", "num"}:
            q = self._build_numerical(meta, body)
        elif qtype in {"shortanswer", "short", "sa"}:
            q = self._build_shortanswer(meta, body)
        elif qtype in {"essay"}:
            q = self._build_essay(meta, body)
        elif qtype in {"description", "desc"}:
            q = self._build_description(meta, body)
        elif qtype in {"cloze"}:
            q = self._build_cloze(meta, body)
        else:
            raise NotImplementedError(f"Unsupported question type: {qtype}")

        if validate:
            q.validate()
        return q

    # --- Builders (designed to mirror model signatures as we expand) ---
    def _build_singlechoice(self, meta: Dict[str, Any], body: str) -> Q.SingleChoice:  # type: ignore[return-value]
        name = self._require_name(meta)
        # Detect conflict first (before applying common)
        if meta.get("answers") and meta.get("choices"):
            raise ValueError("Provide either 'answers' or 'choices', not both, for singlechoice")

        q = Q.SingleChoice(name)

        # Common properties and full-form answers (handled in _apply_question_common)
        _apply_question_common(q, meta, body)

        # If shorthand choices are provided (and no full-form answers), apply them
        if meta.get("choices") and not meta.get("answers"):
            ch = meta.get("choices")
            if isinstance(ch, list):
                parsed = self._choices_checkbox(ch)
                if parsed is not None:
                    checks, labels = parsed
                    correct = [lbl for lbl, c in zip(labels, checks) if c]
                    wrong = [lbl for lbl, c in zip(labels, checks) if not c]
                    if correct:
                        q.set_choices_correct(*correct)
                    else:
                        # No checked -> clear positives; let validate() decide
                        q.set_choices_correct()
                    if wrong:
                        q.set_choices_wrong(*wrong)
                else:
                    correct, wrong = self._choices(meta)
                    if len(correct) != 1:
                        raise ValueError(
                            "singlechoice expects exactly one correct choice; found "
                            f"{len(correct)}"
                        )
                    q.set_choice_correct(correct[0]).set_choices_wrong(*wrong)
            else:
                correct, wrong = self._choices(meta)
                if len(correct) != 1:
                    raise ValueError(
                        "singlechoice expects exactly one correct choice; found "
                        f"{len(correct)}"
                    )
                q.set_choice_correct(correct[0]).set_choices_wrong(*wrong)

        # choice_layout (new API)
        layout = meta.get("choice_layout") or {}
        if isinstance(layout, dict):
            try:
                q.set_choice_layout(
                    labels=str(layout["labels"]) if "labels" in layout else None,
                    shuffle=bool(layout["shuffle"]) if "shuffle" in layout else None,
                    single_choice=bool(layout["single_choice"]) if "single_choice" in layout else True,
                )
            except Exception:
                pass

        # mixin-based application is already handled in _apply_question_common
        return q

    def _build_multichoice(self, meta: Dict[str, Any], body: str) -> Q.MultiChoice:  # type: ignore[return-value]
        name = self._require_name(meta)
        # Detect conflict first (before applying common)
        if meta.get("answers") and meta.get("choices"):
            raise ValueError("Provide either 'answers' or 'choices', not both, for multichoice")

        q = Q.MultiChoice(name)

        # Common properties and full-form answers (handled in _apply_question_common)
        _apply_question_common(q, meta, body)

        # If shorthand choices are provided (and no full-form answers), apply them
        if meta.get("choices") and not meta.get("answers"):
            ch = meta.get("choices")
            if isinstance(ch, list):
                parsed = self._choices_checkbox(ch)
                if parsed is not None:
                    checks, labels = parsed
                    correct = [lbl for lbl, c in zip(labels, checks) if c]
                    wrong = [lbl for lbl, c in zip(labels, checks) if not c]
                    if correct:
                        q.set_choices_correct(*correct)
                    else:
                        # Clear positives explicitly if empty list
                        q.set_choices_correct()
                    if wrong:
                        q.set_choices_wrong(*wrong)
                else:
                    correct, wrong = self._choices(meta)
                    if correct:
                        q.set_choices_correct(*correct)
                    else:
                        # Explicitly clear positives if requested with empty correct list
                        q.set_choices_correct()
                    if wrong:
                        q.set_choices_wrong(*wrong)
            else:
                correct, wrong = self._choices(meta)
                if correct:
                    q.set_choices_correct(*correct)
                else:
                    # Explicitly clear positives if requested with empty correct list
                    q.set_choices_correct()
                if wrong:
                    q.set_choices_wrong(*wrong)

        # choice_layout (new API)
        layout = meta.get("choice_layout") or {}
        if isinstance(layout, dict):
            try:
                q.set_choice_layout(
                    labels=str(layout["labels"]) if "labels" in layout else None,
                    shuffle=bool(layout["shuffle"]) if "shuffle" in layout else None,
                    single_choice=bool(layout["single_choice"]) if "single_choice" in layout else False,
                )
            except Exception:
                pass

        # mixin-based application is already handled in _apply_question_common
        return q

    def _build_shortanswer(self, meta: Dict[str, Any], body: str) -> Q.ShortAnswer:  # type: ignore[return-value]
        name = self._require_name(meta)
        q = Q.ShortAnswer(name)

        # Common properties and full-form answers
        _apply_question_common(q, meta, body)

        # Case sensitivity (new API)
        if "case_sensitive" in meta:
            try:
                q.set_case_sensitive(bool(meta["case_sensitive"]))
            except Exception:
                pass

        # Shorthand 'answer' (single): scalar or mapping with text/feedback; fraction fixed to 100
        single_meta = meta.get("answer")
        answers_meta = meta.get("answers")
        if answers_meta is not None and single_meta is not None:
            raise ValueError("Provide either 'answers' or shorthand 'answer', not both, for shortanswer")

        if single_meta is not None and answers_meta is None:
            if isinstance(single_meta, dict):
                text = single_meta.get("text")
                if text is None:
                    # lenient: also accept 'value' for symmetry with Numerical
                    text = single_meta.get("value")
                if text is None:
                    return q
                fb = single_meta.get("feedback", None)
                q.add_answer(str(text), fraction=100.0, feedback=fb)
            else:
                q.add_answer(str(single_meta), fraction=100.0)

        return q

    def _build_essay(self, meta: Dict[str, Any], body: str) -> Q.Essay:  # type: ignore[return-value]
        name = self._require_name(meta)
        q = Q.Essay(name)
        _apply_question_common(q, meta, body)
        # response: textarea and attachments
        rmeta = meta.get("response") or {}
        if isinstance(rmeta, dict):
            tam = rmeta.get("textarea") or {}
            if isinstance(tam, dict):
                fmt = tam.get("format")
                if fmt is not None:
                    try:
                        q.set_response_format(str(fmt))
                    except Exception:
                        pass
                req = tam.get("required")
                if req is not None:
                    try:
                        q.set_input_required(bool(req))
                    except Exception:
                        pass
                lines = tam.get("lines")
                if lines is not None:
                    try:
                        q.set_input_lines(int(lines))
                    except Exception:
                        pass
                minw = tam.get("min_words")
                if minw is not None:
                    try:
                        q.set_input_words_min(int(minw))
                    except Exception:
                        pass
                maxw = tam.get("max_words")
                if maxw is not None:
                    try:
                        q.set_input_words_max(int(maxw))
                    except Exception:
                        pass
                tpl = tam.get("template")
                if tpl is not None:
                    # Accept str|Text|{path}
                    if isinstance(tpl, dict) and "path" in tpl:
                        p = _expand_with_vars(str(tpl.get("path") or ""), getattr(self, "_project_vars", {}))
                        q.set_response_template({"path": p})
                    else:
                        q.set_response_template(tpl)
            atm = rmeta.get("attachments") or {}
            if isinstance(atm, dict):
                count = atm.get("count")
                if count is not None:
                    try:
                        q.set_attachments_count(int(count))
                    except Exception:
                        pass
                req = atm.get("required")
                if req is not None:
                    try:
                        q.set_attachments_required(bool(req))
                    except Exception:
                        pass
                mb = atm.get("maxbytes")
                if mb is not None:
                    try:
                        q.set_attachments_maxbytes(int(mb))
                    except Exception:
                        pass
                ftl = atm.get("filetypelist")
                if isinstance(ftl, (list, tuple)):
                    try:
                        q.set_attachments_filetypes([str(x) for x in ftl])
                    except Exception:
                        pass
        # graderinfo can be str|TextLike|{path}; expand $VAR if present in str or dict path
        gi = meta.get("graderinfo")
        if gi is not None:
            if isinstance(gi, dict) and "path" in gi:
                p = _expand_with_vars(str(gi.get("path") or ""), getattr(self, "_project_vars", {}))
                q.set_graderinfo({"path": p})
            elif isinstance(gi, str):
                q.set_graderinfo(_expand_with_vars(gi, getattr(self, "_project_vars", {})))
            else:
                q.set_graderinfo(gi)
        return q

    def _build_description(self, meta: Dict[str, Any], body: str) -> Q.Description:  # type: ignore[return-value]
        name = self._require_name(meta)
        q = Q.Description(name)
        _apply_question_common(q, meta, body)
        return q

    def _build_cloze(self, meta: Dict[str, Any], body: str) -> Q.Cloze:  # type: ignore[return-value]
        # Build a Cloze and embed questions per 'cloze' mapping; body contains placeholders {{id}}
        name = self._require_name(meta)
        q = Q.Cloze(name)
        _apply_question_common(q, meta, body)

        # No mapping -> body may already contain raw CLOZE tokens; nothing else to do
        mapping = meta.get("cloze")
        if not mapping:
            return q

        # Base directory for resolving 'cloze.file' paths: question_dir or the cloze file's own directory
        base_dir = self.question_dir or self.path.parent

        def _coerce_options(val: object) -> dict:
            # Accept dict or list of 1-key dicts
            if isinstance(val, dict):
                return dict(val)
            if isinstance(val, list):
                merged: dict = {}
                for item in val:
                    if isinstance(item, dict):
                        merged.update(item)
                return merged
            # If scalar, treat as {'file': val}
            return {"file": val}

        def _resolve_path(p: str) -> Path:
            from pathlib import Path as _Path
            pp = _Path(p)
            if not pp.is_absolute():
                pp = _Path(base_dir) / pp
            return pp

        # Iterate identifiers
        if isinstance(mapping, dict):
            for ident, entry in mapping.items():
                opts = _coerce_options(entry)
                f = opts.get("file")
                if not f:
                    continue
                f_str = _expand_with_vars(str(f), getattr(self, "_project_vars", {}))
                path = _resolve_path(str(f_str))
                # Embedded fragments need not satisfy standalone-question rules
                # (e.g., empty questiontext); embed_question prechecks what matters.
                sub = Reader(path).read(validate=False)
                # Use provided name as identifier
                sub.set_name(str(ident))
                orientation = opts.get("orientation")
                weight = int(opts.get("weight", 1))
                q.embed_question(sub, orientation=orientation, weight=weight)
        return q

    def _build_numerical(self, meta: Dict[str, Any], body: str) -> Q.Numerical:  # type: ignore[return-value]
        from decimal import Decimal, ROUND_HALF_EVEN

        name = self._require_name(meta)
        q = Q.Numerical(name)

        # Common props (questiontext, hints, tags, etc.)
        _apply_question_common(q, meta, body)

        # Shorthand single-answer form is supported via 'answer'
        answers_meta = meta.get("answers")
        single_meta = meta.get("answer")
        if answers_meta is not None and single_meta is not None:
            raise ValueError("Provide either 'answers' or shorthand 'answer', not both, for numerical")

        PREC = Decimal("1e-15")
        # Full-form list of answers; the numeric value key is 'answer' (matches docs,
        # authoring templates, and Numerical.add_answer's parameter name)
        if isinstance(answers_meta, list) and answers_meta:
            for item in answers_meta:
                if not isinstance(item, dict):
                    continue
                if "answer" not in item:
                    raise ValueError("Each item in 'answers' must have an 'answer' key for numerical")
                val = float(Decimal(str(item.get("answer"))).quantize(PREC, rounding=ROUND_HALF_EVEN))
                tol_raw = item.get("tolerance", None)
                tol: float | None
                if tol_raw is None:
                    tol = None
                else:
                    tol = float(Decimal(str(tol_raw)).quantize(PREC, rounding=ROUND_HALF_EVEN))
                fr = float(item.get("fraction", 100.0))
                fb = item.get("feedback", None)
                q.add_answer(val, tolerance=tol, fraction=fr, feedback=fb)
        # Shorthand 'answer': a single scalar with fraction=100; tolerance/feedback
        # require the full-form 'answers' list
        elif single_meta is not None and answers_meta is None:
            if isinstance(single_meta, dict):
                raise ValueError(
                    "Shorthand 'answer' must be a scalar; use 'answers' for tolerance/feedback"
                )
            val = float(Decimal(str(single_meta)).quantize(PREC, rounding=ROUND_HALF_EVEN))
            q.add_answer(val, fraction=100.0)

        return q

    def _build_truefalse(self, meta: Dict[str, Any], body: str) -> Q.TrueFalse:  # type: ignore[return-value]
        name = self._require_name(meta)
        # Conflict: full-form answers vs shorthand answer
        if meta.get("answers") is not None and meta.get("answer") is not None:
            raise ValueError("Provide either 'answers' or shorthand 'answer', not both, for truefalse")

        q = Q.TrueFalse(name)

        # Common properties and full-form answers (handled in _apply_question_common)
        _apply_question_common(q, meta, body)

        # Shorthand answer: true|false (accept bool and common string aliases)
        if meta.get("answer") is not None and meta.get("answers") is None:
            ans = meta.get("answer")
            if isinstance(ans, bool):
                is_true = ans
            else:
                s = str(ans).strip().lower()
                if s in {"true", "t", "yes", "y", "1"}:
                    is_true = True
                elif s in {"false", "f", "no", "n", "0"}:
                    is_true = False
                else:
                    raise ValueError("truefalse 'answer' must be true or false")
            if is_true:
                q.set_correct_if_true()
            else:
                q.set_correct_if_false()
        # Checkbox choices shorthand
        ch = meta.get("choices")
        if ch is not None and meta.get("answers") is None:
            if isinstance(ch, list):
                parsed = self._choices_checkbox(ch)
                if parsed is not None:
                    checks, labels = parsed
                    correct = [lbl for lbl, c in zip(labels, checks) if c]
                    wrong = [lbl for lbl, c in zip(labels, checks) if not c]
                    if correct:
                        q.set_choices_correct(*correct)
                    else:
                        q.set_choices_correct()
                    if wrong:
                        q.set_choices_wrong(*wrong)

        # mixin-based application is already handled in _apply_question_common
        return q

    # --- helpers ---
    @staticmethod
    def _require_name(meta: Dict[str, Any]) -> str:
        name = meta.get("name")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("front matter must include 'name' as a non-empty string")
        return name

    @staticmethod
    def _choices_checkbox(choices_list: list) -> Tuple[list[bool], list[str]] | None:
        """Parse checkbox-style choices: ['(x) A', '( ) B'] -> (checks, labels) or None if not all match.

        Accepts (x) or (o) as checked (case-insensitive), and ( ) as unchecked.
        """
        import re
        checks: list[bool] = []
        labels: list[str] = []
        pat = re.compile(r"^\s*\((x|X|o|O| )\)\s+(.+?)\s*$")
        for item in choices_list:
            s = str(item)
            m = pat.match(s)
            if not m:
                return None
            checks.append(m.group(1).lower() in {"x", "o"})
            labels.append(m.group(2))
        return checks, labels

    @staticmethod
    def _choices(meta: Dict[str, Any]) -> Tuple[Tuple[str, ...], Tuple[str, ...]]:
        choices = meta.get("choices") or {}
        if not isinstance(choices, dict):
            raise ValueError("front matter 'choices' must be a mapping if provided")
        correct_raw = choices.get("correct") or []
        wrong_raw = choices.get("wrong") or []
        if not isinstance(correct_raw, (list, tuple)) or not all(
            isinstance(x, (str, int, float)) for x in correct_raw
        ):
            raise ValueError("choices.correct must be a list of strings")
        if not isinstance(wrong_raw, (list, tuple)) or not all(
            isinstance(x, (str, int, float)) for x in wrong_raw
        ):
            raise ValueError("choices.wrong must be a list of strings")
        corr = tuple(str(x) for x in correct_raw)
        wrong = tuple(str(x) for x in wrong_raw)
        return corr, wrong
