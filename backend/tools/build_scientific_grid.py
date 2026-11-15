"""Operator-triggered US50 gridded build. Cached cells resume; all missing cells stay transparent.

Example: python tools/build_scientific_grid.py --year 2020 --crop maize_grain --states KS --max-cells 4
Omit --states for US50; omit --max-cells to process the entire plan (many provider requests).
"""
import argparse
import asyncio
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.services.grid_pipeline import build,build_all,plan

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--year',type=int,required=True);p.add_argument('--crop',default='maize_grain')
    p.add_argument('--states',nargs='+',type=str.upper);p.add_argument('--max-cells',type=int);p.add_argument('--plan-only',action='store_true')
    p.add_argument('--all-crops',action='store_true');p.add_argument('--concurrency',type=int,default=3)
    args=p.parse_args()
    if args.max_cells is not None and args.max_cells<1:p.error('--max-cells must be positive')
    if args.plan_only:print(json.dumps(dict(cells=len(plan(args.states)),states=args.states or 'US50')))
    elif args.all_crops:print(json.dumps(asyncio.run(build_all(args.year,args.states,args.concurrency)),indent=2))
    else:print(json.dumps(asyncio.run(build(args.year,args.crop,args.states,args.max_cells)),indent=2))
