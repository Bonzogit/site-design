import json,tempfile,unittest,zipfile
from pathlib import Path
from portable_resources import export,unpack,verify,install
from resources import configuration,inspect

class Portable(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
  src=self.root/'original-source';src.mkdir();(src/'note.md').write_text('Portable full source',encoding='utf-8');(src/'module.js').write_text('export const dependency=1;',encoding='utf-8')
  (src/'.env').write_text('SYNTHETIC_SECRET=not-for-export',encoding='utf-8')
  self.config=self.root/'private.json';self.config.write_text(json.dumps({'schemaVersion':1,'sources':[{'id':'docs','kind':'documents','root':str(src),'documents':[{'id':'note','title':'Note','text':'note.md'}]}]}),encoding='utf-8')
  self.skill=self.root/'skill';self.skill.mkdir();(self.skill/'SKILL.md').write_text('---\nname: website-plan-design\nmetadata:\n  version: "0.5.0"\n---\n',encoding='utf-8')
  self.archive=self.root/'bundle.zip';self.source=src
 def make(self):return export(self.config,self.archive,self.skill)
 def test_relocation_full_sources_and_install(self):
  self.assertTrue(self.make()['passed']);moved=self.root/'another-device';self.assertTrue(unpack(self.archive,moved)['passed'])
  # Original source becomes inaccessible before reading the migrated copy.
  self.source.rename(self.root/'unavailable-original')
  sources,w=configuration(moved/'resources.json');self.assertFalse(w);self.assertEqual(inspect(sources,'docs:note')['text'],'Portable full source');self.assertTrue((moved/'sources/docs/module.js').is_file())
  home=self.root/'new-codex-home';self.assertTrue(install(moved,home)['installed']);installed,w=configuration(home/'private-config/website-resources.json');self.assertTrue(inspect(installed,'docs:note')['text'])
 def test_secrets_are_not_exported(self):
  self.make()
  with zipfile.ZipFile(self.archive) as z:self.assertFalse(any(n.endswith('.env') for n in z.namelist()));self.assertFalse(any(b'SYNTHETIC_SECRET' in z.read(n) for n in z.namelist()))
 def test_corruption_rejected(self):
  self.make();dest=self.root/'moved';unpack(self.archive,dest);(dest/'sources/docs/note.md').write_text('tampered',encoding='utf-8');self.assertFalse(verify(dest)['passed'])
 def test_extra_file_rejected(self):
  self.make();dest=self.root/'moved';unpack(self.archive,dest);(dest/'extra.js').write_text('unexpected',encoding='utf-8');self.assertFalse(verify(dest)['passed'])
 def test_existing_install_preserved(self):
  self.make();dest=self.root/'moved';unpack(self.archive,dest);home=self.root/'home';(home/'skills/website-plan-design').mkdir(parents=True)
  with self.assertRaises(ValueError):install(dest,home)
 def test_existing_archive_not_overwritten(self):
  self.make();before=self.archive.read_bytes()
  with self.assertRaises(ValueError):self.make()
  self.assertEqual(self.archive.read_bytes(),before)
 def test_zip_traversal_refused(self):
  with zipfile.ZipFile(self.archive,'w') as z:z.writestr('../escaped.txt','bad')
  with self.assertRaises(ValueError):unpack(self.archive,self.root/'moved')
  self.assertFalse((self.root/'escaped.txt').exists())
 def test_portable_config_cannot_refer_to_exporting_machine(self):
  self.make();dest=self.root/'moved';unpack(self.archive,dest)
  # Manifest catches config tampering; source boundary is checked independently too.
  cfg=json.loads((dest/'resources.json').read_text());cfg['sources'][0]['root']=str(self.source);(dest/'resources.json').write_text(json.dumps(cfg),encoding='utf-8')
  with self.assertRaises(ValueError):verify(dest)

if __name__=='__main__':unittest.main()
