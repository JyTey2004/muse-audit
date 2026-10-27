"""One read-only tool. No arbitrary path, command, evidence or approval arguments."""
import argparse
from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from .store import Store
from .review import review_run as execute

def create_server(root,principal):
 Store(root,readonly=True)
 if not principal or len(principal)>200:raise ValueError('Explicit launch-scoped principal required')
 server=FastMCP('stardive-local-acceptance')
 @server.tool(annotations=ToolAnnotations(readOnlyHint=True,destructiveHint=False,openWorldHint=False,idempotentHint=False))
 def review_run(run_id:str,claimed_outcome:str)->dict:
  """Execute fixed expense API checks against current locally collected run. No browser/security assurance. Advisory."""
  return execute(root,principal,run_id,claimed_outcome)
 return server

def main():
 p=argparse.ArgumentParser();p.add_argument('--store',required=True);p.add_argument('--principal',required=True);a=p.parse_args()
 create_server(a.store,a.principal).run(transport='stdio')
if __name__=='__main__':main()
