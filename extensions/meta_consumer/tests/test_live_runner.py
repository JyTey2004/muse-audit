import io
from pathlib import Path
import tempfile
import unittest
import urllib.error
from unittest.mock import patch
import wave

from meta_consumer.core import Refused, SPARK, VOICE, WONDER, strict_json
from meta_consumer.demo import fixture_transport
from meta_consumer.live_test import ThreeCallProvider, planned_reservation, run, read_key


class LiveRunnerTests(unittest.TestCase):
    def audio(self, root):
        path = root / 'synthetic.wav'
        with wave.open(str(path), 'wb') as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(16000)
            w.writeframes(b'\0\0' * 16000)
        return path

    def test_declined_transcript_stops_after_voice(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); provider = ThreeCallProvider(transport=fixture_transport)
            report = run(provider, self.audio(root), root/'run', lambda *_:False)
            self.assertEqual(report['status'], 'STOPPED')
            self.assertEqual(report['provider_attempts'], 1)
            self.assertEqual(report['live_meta_attempts'], 0)
            self.assertEqual(provider.history[0]['requested_model'], VOICE)

    def test_exactly_three_attempts_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); audio = self.audio(root)
            provider = ThreeCallProvider(transport=fixture_transport)
            report = run(provider, audio, root/'run', lambda *_:True)
            self.assertEqual(report['status'], 'THREE_RESPONSES_VALIDATED')
            self.assertEqual([r['requested_model'] for r in provider.history], [VOICE, SPARK, WONDER])
            self.assertTrue(report['stale_prior_advice_refused'])
            self.assertTrue(report['human_floor_preserved'])
            self.assertEqual(report['acceptance'], 'UNRESOLVED')
            self.assertLess(planned_reservation(), 1)
            with self.assertRaises(Refused):
                provider._call('/chat/completions', b'{}', 'application/json', WONDER)
            with self.assertRaises(FileExistsError):
                run(ThreeCallProvider(transport=fixture_transport), audio, root/'run', lambda *_:True)

    def test_provider_failure_does_not_retry_or_leak_response_body(self):
        body = io.BytesIO(b'private-provider-error-body')
        failure = urllib.error.HTTPError('https://api.meta.ai/v1/asr/transcribe', 401, 'Unauthorized', {}, body)
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); p = ThreeCallProvider(live=True, api_key='synthetic-test-key')
            with patch('urllib.request.OpenerDirector.open', side_effect=failure) as opened:
                report = run(p, self.audio(root), root/'run', lambda *_:True)
            self.assertEqual(opened.call_count, 1)
            self.assertEqual(report['status'], 'STOPPED')
            self.assertEqual(p.history[0]['http_status'], 401)
            self.assertTrue(body.closed)
            self.assertNotIn('private-provider-error-body', (root/'run'/'provider-records.json').read_text())

    def test_missing_usage_prevents_wonder(self):
        def transport(*args):
            result = fixture_transport(*args)
            result.pop('usage', None)
            return result
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); p = ThreeCallProvider(transport=transport)
            report = run(p, self.audio(root), root/'run', lambda *_:True)
            self.assertEqual(report['status'], 'STOPPED')
            self.assertEqual([r['requested_model'] for r in p.history], [VOICE, SPARK])
            self.assertIsNone(report['computed_cost_from_reported_usage_usd'])

    def test_key_file_parser_does_not_execute_shell(self):
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder)/'key.env'
            p.write_text('OTHER=unrelated\nMODEL_API_KEY="synthetic-key"\n')
            self.assertEqual(read_key(p), 'synthetic-key')
            p.write_text('MODEL_API_KEY="$(never execute this)"\n')
            with self.assertRaises(Refused):
                read_key(p)


if __name__ == '__main__':
    unittest.main()
