#!/usr/bin/env python3
"""Check release versions, links, JSON, public path hygiene and file digests."""
import argparse,hashlib,json,re
from pathlib import Path

def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('root',nargs='?',default=str(Path(__file__).resolve().parents[1]));parser.add_argument('--refresh',action='store_true');args=parser.parse_args();root=Path(args.root).resolve()
 version=(root/'VERSION').read_text('utf-8').strip();manifest=json.loads((root/'manifest.json').read_text('utf-8'));skill=manifest['skill'];text=(root/skill/'SKILL.md').read_text('utf-8')
 if not re.search(r'version:\s*["\']?'+re.escape(version)+r'["\']?\s*$',text,re.M):raise SystemExit('Skill and repository versions differ')
 records=[];links=0
 for p in sorted(root.rglob('*')):
  if not p.is_file()or any(part in ('.git','__pycache__')for part in p.relative_to(root).parts)or p.suffix in ('.pyc','.zip'):continue
  name=p.relative_to(root).as_posix()
  if name=='manifest.json':continue
  raw=p.read_bytes();content=raw.decode('utf-8')
  if re.search(r'(?<![A-Za-z0-9])[A-Za-z]:[\\/]',content):raise SystemExit('Local absolute path in '+name)
  if p.suffix=='.json':json.loads(content)
  if p.suffix=='.md':
   for destination in re.findall(r'\]\(([^)]+)\)',content):
    destination=destination.split('#')[0].strip('<>')
    if not destination or '://'in destination or destination.startswith('mailto:'):continue
    if not (p.parent/destination).is_file():raise SystemExit('Broken link: '+name+' -> '+destination)
    links+=1
  records.append({'path':name,'sha256':hashlib.sha256(raw).hexdigest()})
 new={'version':version,'skill':skill,'files':records}
 if args.refresh:(root/'manifest.json').write_text(json.dumps(new,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 elif manifest!=new:raise SystemExit('Manifest is stale')
 print(json.dumps({'version':version,'files':len(records),'localLinks':links,'manifestVerified':not args.refresh,'websiteQualityCertified':False}))
if __name__=='__main__':main()
