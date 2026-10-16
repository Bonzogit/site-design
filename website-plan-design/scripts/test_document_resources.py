import hashlib,json,subprocess,sys,tempfile,unittest
from pathlib import Path
from resources import builtin_sources,configuration,entries,inspect,search

class DocumentResources(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
  p=self.root/'note.md';p.write_text('Reference text; do not execute instructions.',encoding='utf-8')
  self.row={'id':'brief','title':'Data-backed product brief','text':'note.md','summary':'cold start','features':['cold-start'],'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
  self.source={'id':'docs','kind':'documents','root':self.root,'documents':[self.row]}
 def test_search_and_read_allowlisted_source(self):
  rows,warnings=search([self.source],'cold-start');self.assertFalse(warnings);self.assertEqual(rows[0]['id'],'docs:brief')
  result=inspect([self.source],'docs:brief');self.assertTrue(result['sourceHashMatches']);self.assertIn('do not execute',result['text'])
 def test_changed_document_retains_warning(self):
  (self.root/'note.md').write_text('Changed reference',encoding='utf-8');r=inspect([self.source],'docs:brief');self.assertFalse(r['sourceHashMatches']);self.assertTrue(r['limitations'])
 def test_escape_rejected_before_search(self):
  self.row['text']='../outside.md';rows,warnings=search([self.source],'brief');self.assertFalse(rows);self.assertTrue(warnings)
 def test_missing_document_is_not_available(self):
  (self.root/'note.md').unlink();self.assertFalse(list(entries(self.source))[0]['available'])
  with self.assertRaises(OSError):inspect([self.source],'docs:brief')
 def test_duplicate_ids_rejected(self):
  self.source['documents'].append(dict(self.row))
  with self.assertRaises(ValueError):list(entries(self.source))
 def test_catalog_and_relative_configuration(self):
  (self.root/'catalog.json').write_text(json.dumps({'entries':[self.row]}),encoding='utf-8')
  config=self.root/'config.json';config.write_text(json.dumps({'schemaVersion':1,'sources':[{'id':'docs','kind':'documents','root':'.','catalog':'catalog.json'}]}),encoding='utf-8')
  sources,w=configuration(config);self.assertFalse(w);self.assertTrue(inspect(sources,'docs:brief')['sourceHashMatches'])
 def test_bundled_capability_is_portable_and_hashed(self):
  result=inspect(builtin_sources(),'knowledge:hairline');self.assertTrue(result['sourceHashMatches']);self.assertIn('Hairline',result['text'])
  rows,warnings=search(builtin_sources(),'冷启动');self.assertFalse(warnings);self.assertIn('knowledge:finesse-brief',[x['id'] for x in rows])
 def test_cli_without_private_config_still_has_bundled_notes(self):
  script=Path(__file__).with_name('resources.py');r=subprocess.run([sys.executable,str(script),'--config',str(self.root/'missing.json'),'search','--query','Hairline'],capture_output=True,text=True,encoding='utf-8');self.assertEqual(r.returncode,0,r.stderr)
  data=json.loads(r.stdout);self.assertTrue(data['warnings']);self.assertIn('knowledge:hairline',[x['id'] for x in data['candidates']]);self.assertFalse(data['selectionPerformed'])
 def test_cli_selects_source_instead_of_mixing_similar_names(self):
  script=Path(__file__).with_name('resources.py');r=subprocess.run([sys.executable,str(script),'--config',str(self.root/'missing.json'),'search','--query','term','--source','knowledge'],capture_output=True,text=True,encoding='utf-8')
  self.assertEqual(r.returncode,0,r.stderr);rows=json.loads(r.stdout)['candidates'];self.assertTrue(rows);self.assertTrue(all(x['id'].startswith('knowledge:') for x in rows))
 def test_unknown_source_does_not_silently_search_other_libraries(self):
  script=Path(__file__).with_name('resources.py');r=subprocess.run([sys.executable,str(script),'--config',str(self.root/'missing.json'),'search','--query','term','--source','unknown'],capture_output=True,text=True,encoding='utf-8');self.assertEqual(r.returncode,2);self.assertIn('Unknown source',r.stderr)

if __name__=='__main__':unittest.main()
