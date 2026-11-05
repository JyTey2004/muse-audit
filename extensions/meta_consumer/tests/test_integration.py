import copy
import io
import json
import threading
import unittest
import urllib.error
import urllib.request
import wave
from http.server import HTTPServer
from unittest.mock import patch

from meta_consumer.core import (Budget, MetaProvider, Refused, SPARK, WONDER,
    VOICE, bundle, canonical, confirm, digest, intake, replay_advice, route,
    strict_json, validate_bundle)
from meta_consumer.server import State, demo_checks, handler


RAW = '{"expenses":[{"id":"a","amount_minor":2000},{"id":"b","amount_minor":4000}],"total_minor":8000}'


def context():
    initial = intake("Make a budget under S$100.")
    approved = confirm(initial, initial["transcript"], initial["transcript_sha256"])
    return bundle(approved, ["Total matches items", "Stay under S$100"], RAW,
                  [{"id": "source1", "text": RAW, "basis": "recorded"}],
                  task_id="task-a", version="v1")


def advice(ctx):
    return {"task_id": ctx["task_id"], "version": ctx["version"],
            "bundle_sha256": ctx["bundle_sha256"], "suggested_tier": "standard",
            "findings": [{"requirement_id": r["id"], "assessment": "concern",
                          "explanation": "Synthetic provider fixture, not live model reasoning.",
                          "evidence_ids": ["source1"]} for r in ctx["requirements"]]}


class FakeMeta:
    def __init__(self, edit=None, usage=True, finish="stop"):
        self.calls = []
        self.edit = edit
        self.usage = usage
        self.finish = finish

    def __call__(self, path, raw, headers, timeout):
        self.calls.append((path, raw, headers, timeout))
        if path == "/asr/transcribe":
            return {"sessionId": "test-session", "transcript": "Make a budget under S$100.",
                    "audioDurationMs": 1000, "turns": []}
        request = strict_json(raw)
        ctx = strict_json(request["messages"][1]["content"])
        result = advice(ctx)
        # Server preview names its evidence differently; fixture uses the supplied IDs.
        for f in result["findings"]:
            f["evidence_ids"] = [ctx["evidence"][0]["id"]]
        if self.edit:
            self.edit(result)
        output = {"id": "test-response", "model": request["model"], "created": 0,
                  "choices": [{"finish_reason": self.finish, "message": {"content": json.dumps(result)}}]}
        if self.usage:
            output["usage"] = {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150}
        return output


def wav_bytes(rate=16000, channels=1, seconds=1):
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(channels); w.setsampwidth(2); w.setframerate(rate)
        w.writeframes(b"\0\0" * rate * channels * seconds)
    return buf.getvalue()


class CoreTests(unittest.TestCase):
    def test_no_confirmation_cannot_become_bundle(self):
        with self.assertRaises(Refused):
            bundle(intake("hi"), ["one"], RAW, [], task_id="x", version="v1")

    def test_stale_transcript_confirmation_and_tamper(self):
        d = intake("Keep cap 100")
        d["transcript"] = "Raise cap 1000"
        with self.assertRaises(Refused):
            confirm(d, "Raise cap 1000", d["transcript_sha256"])

    def test_edited_voice_retains_audio_and_original(self):
        fake = FakeMeta(); p = MetaProvider(transport=fake)
        d = p.transcribe(wav_bytes(), allow_upload=True)
        approved = confirm(d, "Make a budget under S$90.", d["transcript_sha256"])
        ctx = bundle(approved, ["Cap 90"], RAW, [{"id":"e", "text":RAW,"basis":"recorded"}],task_id="t",version="v1")
        validate_bundle(ctx)
        self.assertEqual(ctx["intake"]["audio_sha256"], digest(wav_bytes()))
        self.assertIn("100", ctx["intake"]["transcript"])
        self.assertIn("90", ctx["request"])

    def test_unconfigured_and_no_upload_consent_make_no_call(self):
        with patch("urllib.request.build_opener", side_effect=AssertionError("network forbidden")):
            with self.assertRaises(Refused):
                MetaProvider().audit(context(), {}, allow_upload=True)
        fake = FakeMeta(); p = MetaProvider(transport=fake)
        with self.assertRaises(Refused):
            p.audit(context(), {})
        self.assertEqual(fake.calls, [])

    def test_valid_advice_never_grants_acceptance(self):
        fake = FakeMeta(); p = MetaProvider(transport=fake)
        result = p.audit(context(), {}, allow_upload=True)
        self.assertEqual(result["acceptance"], "UNRESOLVED")
        self.assertFalse(result["insurance_coverage"])
        self.assertEqual(result["provider_record"]["mode"], "injected_test_transport")
        request = strict_json(fake.calls[0][1])
        self.assertEqual(request["model"], SPARK)
        self.assertTrue(request["response_format"]["json_schema"]["strict"])
        self.assertEqual(request["max_completion_tokens"], 2048)
        self.assertNotIn("Authorization", fake.calls[0][2])

    def test_wrong_task_version_digest_citations_and_forged_pass_refused(self):
        edits = [lambda r:r.update(task_id="other"), lambda r:r.update(version="v0"),
                 lambda r:r.update(bundle_sha256="f"*64),
                 lambda r:r["findings"][0].update(evidence_ids=["invented"]),
                 lambda r:r["findings"][0].update(assessment="PASS"),
                 lambda r:r["findings"].pop(),
                 lambda r:r["findings"].append(copy.deepcopy(r["findings"][0])),
                 lambda r:r.update(acceptance="APPROVED"),
                 lambda r:r["findings"][0].update(evidence_ids=[])]
        for edit in edits:
            with self.subTest(edit=edit):
                p = MetaProvider(transport=FakeMeta(edit))
                with self.assertRaises(Refused):
                    p.audit(context(), {}, allow_upload=True)
                self.assertEqual(p.history[-1]["state"], "INVALID_RESPONSE")

    def test_risk_floor_escalates_and_never_falls(self):
        p = MetaProvider(transport=FakeMeta())
        result = p.audit(context(), {"caller_floor":"human"}, allow_upload=True)
        self.assertEqual(result["review_tier"], "human")
        self.assertEqual(p.history[-1]["requested_model"], WONDER)
        self.assertTrue(result["human_review_required"])
        self.assertEqual(route(external_effect=True)["tier"], "human")
        self.assertEqual(route(irreversible=True)["tier"], "human")
        self.assertFalse(route(exposure_minor=100000)["policy_calibrated"])

    def test_model_can_raise_review(self):
        p = MetaProvider(transport=FakeMeta(lambda r:r.update(suggested_tier="human")))
        self.assertEqual(p.audit(context(), {}, allow_upload=True)["review_tier"], "human")

    def test_budgets_and_missing_usage_stop_further_inference(self):
        p = MetaProvider(budget=Budget(max_calls=1), transport=FakeMeta())
        p.audit(context(), {}, allow_upload=True)
        with self.assertRaises(Refused):
            p.audit(context(), {}, allow_upload=True)
        self.assertEqual(len(p.history), 1)
        p = MetaProvider(transport=FakeMeta(usage=False))
        with self.assertRaises(Refused):
            p.audit(context(), {}, allow_upload=True)
        with self.assertRaises(Refused):
            p.audit(context(), {}, allow_upload=True)
        self.assertEqual(len(p.history), 1)
        self.assertIsNone(p.history[-1]["usage"])

    def test_input_output_caps(self):
        p = MetaProvider(budget=Budget(max_input_bytes=10), transport=FakeMeta())
        with self.assertRaises(Refused):
            p.audit(context(), {}, allow_upload=True)
        self.assertEqual(p.history, [])
        p = MetaProvider(budget=Budget(max_completion_tokens=10), transport=FakeMeta())
        with self.assertRaises(Refused):
            p.audit(context(), {}, allow_upload=True)
        self.assertEqual(p.history[-1]["state"], "FAILED")

    def test_timeout_and_incomplete_finish_are_not_success(self):
        def timeout(*args):
            raise TimeoutError("sensitive transport detail should never leak")
        p = MetaProvider(transport=timeout)
        with self.assertRaises(Refused) as result:
            p.audit(context(), {}, allow_upload=True)
        self.assertNotIn("sensitive", str(result.exception))
        self.assertEqual(p.history[-1]["state"], "FAILED")
        p = MetaProvider(transport=FakeMeta(finish="length"))
        with self.assertRaises(Refused):
            p.audit(context(), {}, allow_upload=True)

    def test_wav_encoding_upload_permission_and_duration(self):
        fake = FakeMeta(); p = MetaProvider(transport=fake)
        for audio, consent in [(wav_bytes(), False),(b"fake", True),
                               (wav_bytes(rate=8000), True),(wav_bytes(channels=2), True),
                               (wav_bytes(seconds=61), True)]:
            with self.subTest(consent=consent, size=len(audio)):
                with self.assertRaises(Refused):
                    p.transcribe(audio, allow_upload=consent)
        self.assertEqual(fake.calls, [])
        d=p.transcribe(wav_bytes(), allow_upload=True)
        self.assertFalse(d["confirmed"])
        self.assertIn(b'name="request"', fake.calls[-1][1])
        self.assertIn(b'name="audio"', fake.calls[-1][1])
        self.assertIn(VOICE.encode(), fake.calls[-1][1])
        self.assertEqual(p.budget.audio_seconds, 1)

    def test_audio_budget_cannot_be_reset_by_another_upload(self):
        p=MetaProvider(budget=Budget(max_audio_seconds=1),transport=FakeMeta())
        p.transcribe(wav_bytes(),allow_upload=True)
        with self.assertRaises(Refused):
            p.transcribe(wav_bytes(),allow_upload=True)
        self.assertEqual(p.history[0]["state"], "RECEIVED")

    def test_strict_json(self):
        for raw in ['{"a":1,"a":2}', '{"x":NaN}', '{"x":Infinity}']:
            with self.assertRaises(Refused): strict_json(raw)

    def test_tampered_or_stale_replay_refused(self):
        ctx=context(); result=MetaProvider(transport=FakeMeta()).audit(ctx, {}, allow_upload=True)
        self.assertEqual(replay_advice(result, ctx)["acceptance"], "UNRESOLVED")
        changed=copy.deepcopy(ctx);changed["artifact"]="changed"
        with self.assertRaises(Refused): replay_advice(result, changed)
        forged=copy.deepcopy(result);forged["acceptance"]="PASS"
        with self.assertRaises(Refused): replay_advice(forged, ctx)

    def test_real_local_failure_correction_and_old_history(self):
        state=State(); state.draft=intake("Make a budget")
        body={"request":"Make a budget","draft_sha256":state.draft["transcript_sha256"],
              "confirmed":True,"requirements":["Total equals sum"],"artifact":RAW,"cap_minor":10000,"risk":{}}
        first=state.prepare(body)
        self.assertFalse(first["deterministic_checks"][0]["passed"])
        corrected=strict_json(RAW);corrected["total_minor"]=6000
        body["artifact"]=json.dumps(corrected)
        second=state.prepare(body)
        self.assertTrue(second["deterministic_checks"][0]["passed"])
        self.assertNotEqual(first["bundle"]["bundle_sha256"],second["bundle"]["bundle_sha256"])
        self.assertEqual(state.history[0]["checks"][0]["passed"], False)
        self.assertEqual(state.history[1]["state"], "STALE_AFTER_NEW_VERSION")


class HTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.state=State()
        cls.server=HTTPServer(("127.0.0.1",0),handler(cls.state))
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
        cls.origin=f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.server.server_close();cls.thread.join()

    def request(self,path,body=None,nonce=True,origin=None):
        headers={}
        if body is not None:
            headers={"Content-Type":"application/json"}
            if nonce:headers["X-Preview-Nonce"]=self.state.nonce
            if origin:headers["Origin"]=origin
        request=urllib.request.Request(self.origin+path,canonical(body) if body is not None else None,headers)
        try:
            with urllib.request.urlopen(request) as response:
                return response.status,response.read()
        except urllib.error.HTTPError as response:
            with response:
                return response.code,response.read()

    def test_offline_status_and_static_page(self):
        status,raw=self.request('/api/status')
        self.assertEqual(status,200)
        self.assertFalse(strict_json(raw)["live_configured"])
        self.assertIn(b'No purchases',self.request('/')[1])

    def test_cross_origin_and_missing_nonce_denied(self):
        self.assertEqual(self.request('/api/intake',{"request":"hello"},nonce=False)[0],403)
        self.assertEqual(self.request('/api/intake',{"request":"hello"},origin="https://other.invalid")[0],403)

    def test_http_confirmation_and_stale_model_scope(self):
        _,raw=self.request('/api/intake',{"request":"Make a budget"});d=strict_json(raw)
        body={"request":"Make a budget","draft_sha256":d["transcript_sha256"],"confirmed":False,
              "requirements":["Correct sum"],"artifact":RAW,"cap_minor":10000,"risk":{}}
        self.assertEqual(self.request('/api/prepare',body)[0],400)
        body['confirmed']=True
        status,raw=self.request('/api/prepare',body);self.assertEqual(status,200)
        self.assertEqual(self.request('/api/audit',{"bundle_sha256":"old","allow_upload":True})[0],400)
        self.assertEqual(self.request('/api/audit',{"bundle_sha256":strict_json(raw)['bundle']['bundle_sha256'],"allow_upload":True})[0],400)
        self.assertEqual(self.state.provider.history,[])


if __name__ == '__main__':
    unittest.main()
