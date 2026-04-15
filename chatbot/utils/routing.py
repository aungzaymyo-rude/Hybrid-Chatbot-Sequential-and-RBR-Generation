from __future__ import annotations

from typing import Callable

from .response import render_response


def handle_greeting(lang: str) -> str:
    return render_response('greeting', lang)


def handle_help(lang: str) -> str:
    return render_response('help', lang)


def handle_cbc_info(lang: str) -> str:
    return render_response('cbc_info', lang)


def handle_sample_collection(lang: str) -> str:
    return render_response('sample_collection', lang)


def handle_rbc_term(lang: str) -> str:
    return render_response('rbc_term', lang)


def handle_wbc_term(lang: str) -> str:
    return render_response('wbc_term', lang)


def handle_coag_test(lang: str) -> str:
    return render_response('coag_test', lang)


def handle_blood_smear(lang: str) -> str:
    return render_response('blood_smear', lang)


def handle_capability_query(lang: str) -> str:
    return render_response('capability_query', lang)


def handle_thanks(lang: str) -> str:
    return render_response('thanks', lang)


def handle_goodbye(lang: str) -> str:
    return render_response('goodbye', lang)


def handle_clarification(lang: str) -> str:
    return render_response('clarification', lang)


def handle_out_of_scope(lang: str) -> str:
    return render_response('out_of_scope', lang)


def handle_unsafe_medical_request(lang: str) -> str:
    return render_response('unsafe_medical_request', lang)


def handle_incomplete_query(lang: str) -> str:
    return render_response('incomplete_query', lang)


def handle_fallback(lang: str) -> str:
    return render_response('fallback', lang)


def handle_language_not_supported(lang: str) -> str:
    return render_response('language_not_supported', lang)


_INTENT_HANDLERS: dict[str, Callable[[str], str]] = {
    'greeting': handle_greeting,
    'help': handle_help,
    'cbc_info': handle_cbc_info,
    'sample_collection': handle_sample_collection,
    'rbc_term': handle_rbc_term,
    'wbc_term': handle_wbc_term,
    'coag_test': handle_coag_test,
    'blood_smear': handle_blood_smear,
    'capability_query': handle_capability_query,
    'thanks': handle_thanks,
    'goodbye': handle_goodbye,
    'clarification': handle_clarification,
    'out_of_scope': handle_out_of_scope,
    'unsafe_medical_request': handle_unsafe_medical_request,
    'incomplete_query': handle_incomplete_query,
    'fallback': handle_fallback,
    'language_not_supported': handle_language_not_supported,
}


def route_intent(intent: str, lang: str) -> str:
    handler = _INTENT_HANDLERS.get(intent, handle_fallback)
    return handler(lang)
