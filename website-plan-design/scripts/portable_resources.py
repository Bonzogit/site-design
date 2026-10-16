#!/usr/bin/env python3
"""Export and verify an offline Skill + source bundle; never execute source code."""
import argparse,hashlib,json,os,re,shutil,tempfile,zipfile
from pathlib import Path,PurePosixPath
from resources import configuration,entries

SKIP={'.git','node_modules','__pycache__','.venv','venv','.cache'}
PRIVATE={'credentials.json','secrets.json','id_rsa','id_ed25519','.npmrc'}
def digest(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
 return h.hexdigest()
def safe(value):
 if not isinstance(value,str) or not value or '\\' in value or ':' in value:raise ValueError('Unsafe relative path')
 parts=PurePosixPath(value).parts
 if value.startswith('/') or any(x in ('..','.') for x in value.split('/')) or not parts:raise ValueError('Unsafe relative path')
 return parts
def is_private(name):
 n=name.lower();return n in PRIVATE or n=='.env' or n.startswith('.env.') or n.endswith(('.clixml','.pem','.key'))
def files(root,omit_private=False):
 for p in sorted(root.rglob('*')):
  rel=p.relative_to(root)
  if any(x in SKIP for x in rel.parts):continue
  if p.is_symlink():raise ValueError('Symlink requires explicit handling: '+rel.as_posix())
  if not p.is_file():continue
  if is_private(p.name):
   if omit_private:continue
   raise ValueError('Private credential filename refused: '+rel.as_posix())
  yield p,rel.as_posix()
def write(path,obj):path.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def verify(root):
 root=Path(root).resolve();m=json.loads((root/'bundle-manifest.json').read_text('utf-8'));errors=[]
 if m.get('schemaVersion')!=1:raise ValueError('Unsupported bundle schema')
 expected=set()
 for row in m['files']:
  rel=row['path'];safe(rel)
  if rel in expected:raise ValueError('Duplicate manifest path')
  expected.add(rel);p=(root/rel).resolve()
  if not p.is_relative_to(root) or not p.is_file() or p.is_symlink() or digest(p)!=row['sha256']:errors.append(rel)
 actual={rel for p,rel in files(root)}-{'bundle-manifest.json'}
 if actual!=expected:errors.append('Unexpected or missing bundle files')
 sources,warnings=configuration(root/'resources.json');checks=[]
 for source in sources:
  # Reject configurations that still depend on the exporting machine.
  if not source['root'].is_relative_to(root):raise ValueError('Source root leaves portable bundle')
  try:
   rows=list(entries(source));missing=[x['id'] for x in rows if x.get('available') is False]
   checks.append({'id':source['id'],'entries':len(rows),'readable':not missing})
   if missing:errors.extend(missing)
  except (OSError,ValueError,KeyError) as e:errors.append(str(e))
 return {'passed':not errors,'version':m['version'],'files':len(expected),'sources':checks,'warnings':warnings,'errors':errors,'runtimeToolsVerified':False}

def export(config,output,skill=None):
 output=Path(output).resolve()
 if output.exists():raise ValueError('Output exists; choose a new bundle name')
 sources,warnings=configuration(config)
 if warnings or not sources:raise ValueError('Explicit readable resource configuration required')
 for source in sources:
  if not re.fullmatch(r'[A-Za-z0-9_-]+',source['id']):raise ValueError('Unsafe source ID')
  if not source['root'].is_dir():raise ValueError('Source root missing: '+source['id'])
 skill=Path(skill or Path(__file__).resolve().parents[1]).resolve()
 version=re.search(r'version:\s*"([0-9.]+)"',(skill/'SKILL.md').read_text('utf-8')).group(1)
 with tempfile.TemporaryDirectory(prefix='website-portable-') as temp:
  root=Path(temp);rows=[]
  for source in sources:
   dest=root/'sources'/source['id'];dest.mkdir(parents=True)
   # Complete source roots preserve relative imports, examples, fonts and notices.
   for p,rel in files(source['root'],omit_private=True):
    target=dest/rel;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,target)
   row={k:v for k,v in source.items() if k!='root'};row['root']='sources/'+source['id'];rows.append(row)
  target=root/'website-plan-design';target.mkdir()
  for p,rel in files(skill,omit_private=True):
   out=target/rel;out.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,out)
  write(root/'resources.json',{'schemaVersion':1,'sources':rows})
  (root/'START-HERE.txt').write_text('网站策划与设计：完整离线迁移包\n先解压到新电脑准备长期保留的目录，再在该目录打开终端。需要Python 3.10或以上。\n校验：python website-plan-design/scripts/portable_resources.py verify .\n安装：python website-plan-design/scripts/portable_resources.py install .\n安装后保留整个资料目录。若已有同名Skill或资源配置，安装器会停止以保留现状，需比较后合并。\n完整资源使用相对路径，不依赖旧电脑磁盘。外部订阅、运行环境、原生编辑器和凭据不在包内。\n这是私有迁移副本，第三方许可和素材权利继续保留，不意味着可公开转载全部内容。\n',encoding='utf-8')
  manifest={'schemaVersion':1,'version':version,'distribution':'private-migration-copy','excluded':'Credentials, environment secrets, dependency caches, Git metadata and symlinks are not transferable resources.','files':[{'path':rel,'sha256':digest(p)} for p,rel in files(root)]}
  write(root/'bundle-manifest.json',manifest);report=verify(root)
  if not report['passed']:raise ValueError('Export verification failed: '+str(report['errors']))
  output.parent.mkdir(parents=True,exist_ok=True)
  try:
   with zipfile.ZipFile(output,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for p,rel in files(root):z.write(p,rel)
  except BaseException:
   output.unlink(missing_ok=True);raise
 return {'zip':str(output),'sha256':digest(output),'bytes':output.stat().st_size,**report}

def unpack(archive,target):
 target=Path(target).resolve()
 if target.exists():raise ValueError('Unpack target must not exist')
 with zipfile.ZipFile(archive) as z:
  seen=set();total=0
  for item in z.infolist():
   safe(item.filename.rstrip('/'))
   if item.filename in seen:raise ValueError('Duplicate archive entry')
   seen.add(item.filename);total+=item.file_size
   if total>2*1024**3 or len(seen)>30000:raise ValueError('Archive exceeds migration limits')
   if (item.external_attr>>16)&0o170000==0o120000:raise ValueError('Archive symlink refused')
  target.mkdir(parents=True)
  z.extractall(target)
 report=verify(target)
 if not report['passed']:raise ValueError('Extracted files did not match bundle manifest')
 return report

def install(root,home=None):
 root=Path(root).resolve();report=verify(root)
 if not report['passed']:raise ValueError('Bundle verification failed')
 home=Path(home or os.environ.get('CODEX_HOME') or Path.home()/'.codex').resolve()
 dest=home/'skills/website-plan-design';config=home/'private-config/website-resources.json'
 if dest.exists() or config.exists():raise ValueError('Existing Skill or config preserved; review and merge instead of overwriting')
 shutil.copytree(root/'website-plan-design',dest)
 # Local install points at the moved bundle; public/source config remains relative.
 cfg=json.loads((root/'resources.json').read_text('utf-8'))
 for source in cfg['sources']:source['root']=str((root/source['root']).resolve())
 config.parent.mkdir(parents=True,exist_ok=True);write(config,cfg)
 return {'installed':True,'version':report['version'],'resourceFolderMustRemain':str(root),'runtimeToolsVerified':False}

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='action',required=True)
 x=sub.add_parser('export');x.add_argument('--config',required=True);x.add_argument('--output',required=True)
 x=sub.add_parser('verify');x.add_argument('root')
 x=sub.add_parser('unpack');x.add_argument('archive');x.add_argument('target')
 x=sub.add_parser('install');x.add_argument('root');x.add_argument('--home')
 a=p.parse_args()
 try:
  if a.action=='export':r=export(a.config,a.output)
  elif a.action=='verify':r=verify(a.root)
  elif a.action=='unpack':r=unpack(a.archive,a.target)
  else:r=install(a.root,a.home)
  print(json.dumps(r,ensure_ascii=False,indent=2));raise SystemExit(0 if r.get('passed',True) else 1)
 except (OSError,ValueError,KeyError,zipfile.BadZipFile) as e:p.exit(2,str(e)+'\n')
