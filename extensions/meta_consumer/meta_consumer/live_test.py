"""One authorized synthetic validation: Voice, Spark, Wonder; no automatic retry."""
import argparse
from decimal import Decimal, ROUND_FLOOR
import json
import os
from pathlib import Path
import re
import wave

from .core import Budget, MetaProvider, Refused, SPARK, WONDER, VOICE, canonical, replay_advice
from .server import State

REQUEST = ("Prepare an expense summary. The total must equal the item amounts "
           "and stay under one hundred Singapore dollars.")
PRICING_URL = "https://dev.meta.ai/docs/pricing-rate-limits"
RATES = {SPARK: (Decimal('1.25'), Decimal('4.25')),
         WONDER: (Decimal('4'), Decimal('20'))}  # USD per million, Standard IDs.
VOICE_HOURLY = Decimal('0.18')
MAX_INPUT_BYTES = 16000
MAX_OUTPUT_TOKENS = 2048
MAX_AUDIO_SECONDS = 20


def planned_reservation():
    # A conservative planning allowance, not a vendor tokenizer or invoice.
    inference = sum((MAX_INPUT_BYTES * inp + MAX_OUTPUT_TOKENS * out)
                    / Decimal(1000000) for inp, out in RATES.values())
    voice = Decimal(MAX_AUDIO_SECONDS) * VOICE_HOURLY / Decimal(3600)
    return (inference + voice) * 4  # Extra margin; no search/tools are requested.


def reported_cost(records):
    cost = Decimal(0)
    for record in records:
        usage = record.get('usage')
        if not usage:
            return None
        if record['requested_model'] == VOICE:
            millis = usage.get('provider_audio_duration_ms')
            if type(millis) is not int or millis < 0:
                return None
            seconds = (Decimal(millis) / 1000).to_integral_value(rounding=ROUND_FLOOR)
            cost += seconds * VOICE_HOURLY / 3600
        else:
            inp, out = RATES[record['requested_model']]
            cost += (usage['prompt_tokens'] * inp + usage['completion_tokens'] * out) / 1000000
    return cost


class ThreeCallProvider(MetaProvider):
    def __init__(self, **kwargs):
        super().__init__(budget=Budget(max_calls=3, max_input_bytes=MAX_INPUT_BYTES,
            max_completion_tokens=MAX_OUTPUT_TOKENS, max_audio_seconds=MAX_AUDIO_SECONDS), **kwargs)
        self.attempted_models = set()

    def _call(self, path, payload, content_type, model, audio_seconds=0):
        if model not in (VOICE, SPARK, WONDER) or model in self.attempted_models:
            raise Refused('This authorization permits one attempt per selected model; no retry')
        self.attempted_models.add(model)
        return super()._call(path, payload, content_type, model, audio_seconds)


def read_key(path=None):
    if path is None:
        value = os.environ.get('MODEL_API_KEY', '')
    else:
        selected = Path(path)
        if selected.stat().st_size > 8192:
            raise Refused('Selected key file is too large')
        raw = selected.read_text().strip()
        match = re.search(r'^\s*(?:export\s+)?MODEL_API_KEY\s*=\s*(.*?)\s*$', raw, re.M)
        value = match.group(1).strip('"\'') if match else raw
    if not value or any(c.isspace() for c in value):
        raise Refused('Configure MODEL_API_KEY or select a file containing only that key')
    return value


def validate_audio(path):
    with wave.open(str(path), 'rb') as wav:
        if (wav.getnchannels(), wav.getsampwidth(), wav.getframerate(), wav.getcomptype()) != (1, 2, 16000, 'NONE'):
            raise Refused('Synthetic test audio must be mono PCM16 WAV at 16 kHz')
        seconds = wav.getnframes() / wav.getframerate()
        if not 0 < seconds <= MAX_AUDIO_SECONDS:
            raise Refused('Synthetic test audio must be at most twenty seconds')
    return seconds


def run(provider, audio, output, review_transcript):
    validate_audio(audio)
    if planned_reservation() >= Decimal('1'):
        raise Refused('Planned reservation exceeds the authorized US$1 test budget')
    # An existing directory is a consumed/partial run; never overwrite or auto-resume.
    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    def save(name, value):
        (output / name).write_bytes(canonical(value) + b'\n')
    live = provider.transport is None
    report = {'evidence_class': 'LIVE_META_SYNTHETIC' if live else 'OFFLINE_RUNNER_TEST',
        'authorized_budget_usd': '1.00', 'planned_reservation_usd': str(planned_reservation()),
        'pricing_source': PRICING_URL, 'pricing_checked': '2026-11-03',
        'per_model_attempt_limit': 1, 'automatic_retries': 0,
        'requested_models': [VOICE, SPARK, WONDER], 'acceptance': 'UNRESOLVED',
        'insurance_coverage': False, 'native_app_acceptance_tested': False,
        'microphone_tested': False, 'status': 'STARTED'}
    save('RESULT.json', report)
    try:
        state = State(); state.provider = provider
        draft = provider.transcribe(audio.read_bytes(), allow_upload=True)
        save('transcript.json', draft)
        # A synthetic operator review is not represented as consumer identity/consent.
        if review_transcript(draft['transcript'], REQUEST) is not True:
            raise Refused('Synthetic transcript review declined; no inference requested')
        state.draft = draft
        body = {'request': REQUEST, 'draft_sha256': draft['transcript_sha256'],
            'confirmed': True, 'requirements': ['Recorded total equals the item sum',
            'The item sum is at most one hundred Singapore dollars'],
            'artifact': json.dumps({'expenses': [{'id': 'train', 'amount_minor': 2000},
                {'id': 'hotel', 'amount_minor': 4000}], 'total_minor': 8000}),
            'cap_minor': 10000, 'risk': {}}
        initial = state.prepare(body); save('initial.json', initial)
        first = provider.audit(state.current, state.risk, allow_upload=True)
        save('spark-advice.json', first)
        if reported_cost(provider.history) is None or reported_cost(provider.history) >= Decimal('1'):
            raise Refused('Reported usage unavailable or test budget exhausted; stop')
        body['artifact'] = body['artifact'].replace('8000', '6000')
        body['risk'] = {'caller_floor': 'human', 'irreversible': True}
        corrected = state.prepare(body); save('corrected.json', corrected)
        second = provider.audit(state.current, state.risk, allow_upload=True)
        save('wonder-advice.json', second)
        try:
            replay_advice(first, state.current)
            stale = False
        except Refused:
            stale = True
        report.update(status='THREE_RESPONSES_VALIDATED',
            initial_total_failed=not initial['deterministic_checks'][0]['passed'],
            corrected_total_passed=corrected['deterministic_checks'][0]['passed'],
            stale_prior_advice_refused=stale, human_floor_preserved=second['human_review_required'],
            transcript_review='operator-reviewed synthetic fixture; not a consumer identity claim',
            audit_efficacy='Not established by one synthetic case')
        save('history.json', state.history)
    except (Refused, OSError, ValueError) as error:
        report.update(status='STOPPED', reason=str(error) if isinstance(error, Refused)
            else 'Local input/output failure; inspect this run before any further call')
    finally:
        cost = reported_cost(provider.history)
        report.update(provider_attempts=len(provider.history),
            live_meta_attempts=len(provider.history) if live else 0,
            computed_cost_from_reported_usage_usd=str(cost) if cost is not None else None,
            cost_is_provider_invoice=False)
        save('provider-records.json', provider.history)
        save('RESULT.json', report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--audio', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--key-file', type=Path)
    parser.add_argument('--execute', action='store_true', help='Use the explicitly authorized US$1 synthetic test')
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit('Fresh output directory required; existing run cannot be retried')
    if not args.execute:
        print(json.dumps({'network_calls': 0, 'audio_seconds': validate_audio(args.audio),
            'planned_reservation_usd': str(planned_reservation()), 'execute': False}, indent=2))
        return
    key = read_key(args.key_file)
    def review(transcript, expected):
        print(json.dumps({'actual_transcript': transcript, 'synthetic_expected': expected}), flush=True)
        try:
            return input('Compare the synthetic transcript. Type REVIEWED to use the predefined request: ').strip() == 'REVIEWED'
        except EOFError:
            return False
    result = run(ThreeCallProvider(live=True, api_key=key), args.audio, args.output, review)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
