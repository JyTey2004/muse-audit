"""Launch locally by default; reviewed external ingress/config is an operations gate."""
import argparse
import uvicorn
from .app import create_app
from .config import load_config

def main():
    p=argparse.ArgumentParser();p.add_argument('--store',required=True);p.add_argument('--config',required=True)
    p.add_argument('--host',default='127.0.0.1');p.add_argument('--port',type=int,default=8765)
    p.add_argument('--reviewed-external-ingress',action='store_true');args=p.parse_args()
    config=load_config(args.config,args.store)
    if args.host not in ('127.0.0.1','localhost') and not (args.reviewed_external_ingress and config.public_base_url):p.error('Non-loopback serving needs a separately reviewed HTTPS ingress and explicit launch flag')
    uvicorn.run(create_app(config),host=args.host,port=args.port,workers=1,proxy_headers=False,access_log=False,log_level='warning')
if __name__=='__main__':main()
