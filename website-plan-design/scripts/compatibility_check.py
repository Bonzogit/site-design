#!/usr/bin/env python3
"""Read the builder-owned contract and check the real project without mutation."""
import argparse,hashlib,json,subprocess,sys
from pathlib import Path

SUPPORTED={'theme':'unified-theme-v1','inquiry':'unified-inquiry-v1','designRecord':'2.0','translation':2}

def inspect(builder,project=None,version=None):
 builder=Path(builder).resolve();errors=[];checks={}
 def load(p):return json.loads(p.read_text('utf-8-sig'))
 def tool(name,args):
  result=subprocess.run([sys.executable,str(builder/'scripts'/name),*args],capture_output=True,text=True,encoding='utf-8')
  try:report=json.loads(result.stdout)
  except ValueError:report={'errors':['Builder checker did not return JSON'], 'exitCode':result.returncode}
  checks[name]=report
  if result.returncode:errors.append(name+': failed; inspect checks')
 try:
  contract=load(builder/'assets/interface-contract.json')
  if contract.get('schemaVersion')!=1:errors.append('Unsupported interface contract schema')
  if contract.get('interfaces')!=SUPPORTED:errors.append('Unsupported builder interfaces')
  adapter=contract['adapter'];p=(builder/adapter['path']).resolve()
  if not p.is_relative_to(builder) or not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest()!=adapter['sha256']:errors.append('Builder adapter digest mismatch')
  if project:
   if not version:errors.append('Current website version is required with --project')
   project=Path(project).resolve();actual=load(project/'site.contract.json')
   if actual.get('interfaces')!=SUPPORTED:errors.append('Project interfaces missing or incompatible; review original core before updating')
   tool('check_core_sync.py',[str(project),'--json'])
   tool('design_check.py',[str(project),*(['--version',version] if version else [])])
 except (OSError,ValueError,KeyError,TypeError) as exc:
  errors.append('Contract unavailable or malformed: '+str(exc))
 return {'compatible':not errors,'builderVersion':locals().get('contract',{}).get('builderVersion'),'interfaces':SUPPORTED,'checks':checks,'errors':errors,'websiteQualityCertified':False}

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--builder',required=True);p.add_argument('--project');p.add_argument('--version');a=p.parse_args();report=inspect(a.builder,a.project,a.version);print(json.dumps(report,ensure_ascii=False,indent=2));sys.exit(0 if report['compatible'] else 1)
