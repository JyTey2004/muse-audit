import argparse
import json
from .contract import CONTRACT
from .store import prepare,approve
from .collector import build,review_phase
from .review import review_run

def main():
 p=argparse.ArgumentParser(description='Trusted-local two-phase Claude app task. Review exact contract before approving.')
 p.add_argument('--store',required=True);p.add_argument('--principal',required=True)
 sub=p.add_subparsers(dest='action',required=True)
 x=sub.add_parser('prepare');x.add_argument('--workspace',required=True)
 x=sub.add_parser('approve');x.add_argument('run_id');x.add_argument('--contract-sha256',required=True)
 for name in ('build','review','inspect'):
  x=sub.add_parser(name);x.add_argument('run_id')
 a=p.parse_args()
 if a.action=='prepare':result=prepare(a.store,a.principal,a.workspace,CONTRACT)
 elif a.action=='approve':approve(a.store,a.principal,a.run_id,a.contract_sha256);result={'approved':a.run_id}
 elif a.action=='build':result=build(a.store,a.principal,a.run_id)
 elif a.action=='review':result=review_phase(a.store,a.principal,a.run_id)
 else:result=review_run(a.store,a.principal,a.run_id,'The app is done')
 print(json.dumps(result,indent=2))
if __name__=='__main__':main()
