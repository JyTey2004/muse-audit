"""A labelled, offline protocol fixture; never calls Meta or scores real models."""
import argparse
import io
import json
from pathlib import Path
import wave

from .core import MetaProvider, canonical, replay_advice, strict_json
from .server import State


def fixture_transport(path, payload, headers, timeout):
    if path == "/asr/transcribe":
        return {"sessionId":"OFFLINE-VOICE-FIXTURE", "audioDurationMs":1000,
                "transcript":"Prepare an expense summary under S$100.", "turns":[]}
    request = strict_json(payload)
    context = strict_json(request["messages"][1]["content"])
    advice = {"task_id":context["task_id"],"version":context["version"],
              "bundle_sha256":context["bundle_sha256"],"suggested_tier":"standard",
              "findings":[{"requirement_id":r["id"],"assessment":"uncertain",
                "explanation":"OFFLINE FIXTURE. No actual Meta inference or semantic judgment.",
                "evidence_ids":[]} for r in context["requirements"]]}
    return {"id":"OFFLINE-AUDIT-FIXTURE","model":request["model"],
            "choices":[{"finish_reason":"stop","message":{"content":json.dumps(advice)}}],
            "usage":{"prompt_tokens":100,"completion_tokens":50,"total_tokens":150}}


def run(output):
    output.mkdir(parents=True, exist_ok=False)
    state=State();state.provider=MetaProvider(transport=fixture_transport)
    audio=io.BytesIO()
    with wave.open(audio,"wb") as wav:
        wav.setnchannels(1);wav.setsampwidth(2);wav.setframerate(16000);wav.writeframes(b"\0\0"*16000)
    state.draft=state.provider.transcribe(audio.getvalue(),allow_upload=True)
    body={"request":state.draft["transcript"],"draft_sha256":state.draft["transcript_sha256"],
          "confirmed":True,"requirements":["Recorded total equals the item sum", "Item sum stays under S$100"],
          "artifact":json.dumps({"expenses":[{"id":"train","amount_minor":2000},{"id":"hotel","amount_minor":4000}],"total_minor":8000}),
          "cap_minor":10000,"risk":{}}
    initial=state.prepare(body)
    advisory=state.provider.audit(state.current,state.risk,allow_upload=True)
    artifact=strict_json(body["artifact"]);artifact["total_minor"]=6000;body["artifact"]=json.dumps(artifact)
    body["risk"]={"caller_floor":"human","external_effect":True,"outcome_observed":False}
    corrected=state.prepare(body)
    escalated=state.provider.audit(state.current,state.risk,allow_upload=True)
    stale_refused=False
    try:replay_advice(advisory,state.current)
    except ValueError:stale_refused=True
    result={"evidence_class":"OFFLINE_INJECTED_PROVIDER_FIXTURES", "live_meta_calls":0,
            "audio_fixture":"one second of silence; no speech recognition evaluated",
            "provider_usage":"manufactured fixture values; not real token or cost measurements",
            "initial_total_check_failed":not initial["deterministic_checks"][0]["passed"],
            "corrected_total_check_passed":corrected["deterministic_checks"][0]["passed"],
            "old_advice_refused_for_new_version":stale_refused,
            "human_floor_preserved":escalated["human_review_required"],
            "acceptance":escalated["acceptance"],"insurance_coverage":False,
            "models_exercised_as_protocol_fixtures":[r["requested_model"] for r in state.provider.history]}
    assert all(result[k] for k in ("initial_total_check_failed","corrected_total_check_passed",
                                  "old_advice_refused_for_new_version","human_floor_preserved"))
    for name,data in {"RESULT.json":result,"initial.json":initial,"advisory-fixture.json":advisory,
                      "corrected.json":corrected,"escalated-fixture.json":escalated,
                      "history.json":state.history,"provider-fixtures.json":state.provider.history}.items():
        (output/name).write_bytes(canonical(data)+b"\n")
    return result


def main():
    p=argparse.ArgumentParser();p.add_argument("--output",type=Path,required=True);args=p.parse_args()
    print(json.dumps(run(args.output),indent=2))


if __name__=="__main__":main()
