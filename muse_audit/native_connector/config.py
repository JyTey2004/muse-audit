"""Launch-only configuration. Never issue a credential or accept owner/root from callers."""
from dataclasses import dataclass
import hashlib
import hmac
from pathlib import Path
import re
from urllib.parse import urlsplit
from ..io import read_json,digest

SCOPES={'review','intake','artifact','receipt'}
@dataclass(frozen=True)
class Credential:
    principal:str
    token_sha256:str
    scopes:frozenset
@dataclass(frozen=True)
class Config:
    store:Path
    credentials:tuple
    public_base_url:str|None=None
    origins:tuple=()
    requests_per_minute:int=120
    max_tasks_per_owner:int=100
    max_versions_per_task:int=20
    max_receipts_per_task:int=100
    def __post_init__(self):
        root=Path(self.store)
        if root.is_symlink() or root.resolve()!=root:raise ValueError('Launch store must be an absolute non-symlink path')
        if not self.credentials:raise ValueError('Existing credential bindings required; no credential is minted')
        seen=set()
        for c in self.credentials:
            if not re.fullmatch(r'[a-zA-Z0-9_-]{1,64}',c.principal):raise ValueError('Invalid configured principal')
            if not re.fullmatch('[a-f0-9]{64}',c.token_sha256) or c.token_sha256 in seen:raise ValueError('Unique SHA256 credential bindings required')
            if not c.scopes or not c.scopes<=SCOPES:raise ValueError('Invalid configured scopes')
            seen.add(c.token_sha256)
        if self.public_base_url:
            p=urlsplit(self.public_base_url)
            if p.scheme!='https' or not p.hostname or p.username or p.password or p.query or p.fragment or p.path not in ('','/') or p.port not in (None,443):raise ValueError('Reviewed base URL must be an HTTPS origin on 443')
        for origin in self.origins:
            p=urlsplit(origin)
            if p.scheme!='https' or not p.hostname or p.path not in ('','/') or p.username or p.password or p.query or p.fragment:raise ValueError('Exact HTTPS origins only')
        for name in ('requests_per_minute','max_tasks_per_owner','max_versions_per_task','max_receipts_per_task'):
            if type(getattr(self,name)) is not int or not 1<=getattr(self,name)<=10000:raise ValueError('Bounded integer limits required')
    def authenticate(self,token):
        if not isinstance(token,str) or not 32<=len(token)<=1024:return None
        token_hash=hashlib.sha256(token.encode()).hexdigest()
        matched=None
        for credential in self.credentials:
            if hmac.compare_digest(token_hash,credential.token_sha256):matched=credential
        return matched
    def owner_root(self,principal):
        return self.store/hashlib.sha256(principal.encode()).hexdigest()
    def binding(self):
        return digest({'store':str(self.store),'credentials':[{'principal':c.principal,'token_sha256':c.token_sha256,'scopes':sorted(c.scopes)} for c in self.credentials],
          'public_base_url':self.public_base_url,'origins':self.origins,'limits':[self.requests_per_minute,self.max_tasks_per_owner,self.max_versions_per_task,self.max_receipts_per_task]})

def load_config(path,store):
    path=Path(path)
    if path.is_symlink() or path.stat().st_mode&0o077:raise ValueError('Credential config must be a private regular file (chmod 600)')
    data=read_json(path)
    if set(data)-{'credentials','public_base_url','origins','requests_per_minute','max_tasks_per_owner','max_versions_per_task','max_receipts_per_task'}:raise ValueError('Unknown configuration fields')
    creds=tuple(Credential(c['principal'],c['token_sha256'],frozenset(c['scopes'])) for c in data.pop('credentials'))
    if 'origins' in data:data['origins']=tuple(data['origins'])
    return Config(Path(store).resolve(),creds,**data)
