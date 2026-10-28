"""Synthetic HTTP pilot data only; not a Muse/Meta/model run."""
import base64
import hashlib
from pathlib import Path
from muse_audit.native_connector.config import Config,Credential
TOKEN_A='synthetic-test-owner-a-credential-00000001'
TOKEN_B='synthetic-test-owner-b-credential-00000002'
TOKEN_R='synthetic-test-owner-a-readonly-00000003'
def config(root,**kwargs):
    def cred(owner,token,scopes):return Credential(owner,hashlib.sha256(token.encode()).hexdigest(),frozenset(scopes))
    return Config(Path(root).resolve(),(cred('owner-a',TOKEN_A,('review','intake','artifact','receipt')),cred('owner-b',TOKEN_B,('review','intake','artifact','receipt')),cred('owner-a',TOKEN_R,('review',))),**kwargs)
def body(request='Make a CSV for the picnic items, with item and amount columns, keeping the total at most 65.',total=65):
    source=b'item,amount\napples,12\nwater,8\n'
    return {'request':request,'requirements':[
      {'id':'columns','kind':'csv.columns','description':'Use item and amount columns','mode':'must_preserve','config':{'columns':['item','amount']}},
      {'id':'rows','kind':'csv.rows_exact','description':'Retain the supplied items and amounts','mode':'must_preserve','config':{'source_id':'items'}},
      {'id':'cap','kind':'csv.total_cap','description':'Keep the selected total within the cap','mode':'must_change','config':{'column':'amount','max_value':total}},
      {'id':'taste','kind':'semantic.claim','description':'Everyone will like the picnic choices','mode':'unknown','config':{}}],
      'sources':[{'id':'items','name':'items.csv','content_base64':base64.b64encode(source).decode()}],'artifact_name':'picnic.csv','artifact_kind':'csv','synthetic':True}
