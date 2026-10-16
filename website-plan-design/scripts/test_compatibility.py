"""Cross-package fixtures use the supplied real builder, not a copied schema."""
import json,os,subprocess,sys,tempfile,unittest,shutil
from pathlib import Path
from compatibility_check import inspect

class Integration(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name);self.builder=Path(os.environ['BUILDER_SKILL']);self.project=self.root/'site'
  subprocess.run([sys.executable,str(self.builder/'scripts/create_site.py'),str(self.project),'--runtime','node'],check=True,capture_output=True)
  self.doc={'recordVersion':'2.0','projectVersion':'fixture-1','researchStatus':'unverified','designQuestions':{},'references':[],'decisions':[{'id':'layout','page':'/','section':'main','basis':'Product selection task','decision':'Compare available product directions','referenceIds':[],'implementation':[],'verification':{'status':'unverified'}}],'journeys':[{'id':'inquire','steps':['Choose product','Submit requirement'],'reason':'Primary visitor task','verification':{'status':'unverified'}}]}
  self.save()
 def save(self):(self.project/'docs/design-record.json').write_text(json.dumps(self.doc),encoding='utf-8')
 def test_pending_design_is_compatible_without_certifying_quality(self):
  r=inspect(self.builder,self.project,'fixture-1');self.assertTrue(r['compatible'],r);self.assertFalse(r['websiteQualityCertified']);self.assertFalse(r['checks']['design_check.py']['verificationRecorded'])
  c=json.loads((self.project/'site.contract.json').read_text());expected=json.loads((self.builder/'assets/interface-contract.json').read_text());self.assertEqual(c['skillVersion'],expected['builderVersion'])
 def test_array_observations_rejected_by_actual_builder(self):
  (self.project/'docs/source.txt').write_text('Source inspection')
  self.doc['references']=[{'id':'source','source':'fixture reference','observationType':'source','observedAt':'2026-10-16T12:00:00+08:00','viewport':'n/a: source','observations':['Wrong type'],'evidence':['docs/source.txt']}];self.save()
  r=inspect(self.builder,self.project,'fixture-1');self.assertFalse(r['compatible']);self.assertTrue(any('observations' in e for e in r['checks']['design_check.py']['errors']))
 def test_stale_website_version_rejected(self):self.assertFalse(inspect(self.builder,self.project,'fixture-2')['compatible'])
 def test_contract_cannot_hide_modified_core(self):
  (self.project/'lib/app.mjs').write_text('// stale core')
  self.assertFalse(inspect(self.builder,self.project,'fixture-1')['compatible'])
 def test_missing_legacy_contract_rejected(self):self.assertFalse(inspect(self.root/'legacy')['compatible'])
 def test_incompatible_project_interface_rejected(self):
  p=self.project/'site.contract.json';c=json.loads(p.read_text());c['interfaces']['theme']='future-v2';p.write_text(json.dumps(c));self.assertFalse(inspect(self.builder,self.project,'fixture-1')['compatible'])
 def test_missing_current_version_rejected(self):self.assertFalse(inspect(self.builder,self.project)['compatible'])
 def test_worker_generation_uses_same_interfaces(self):
  worker=self.root/'worker';subprocess.run([sys.executable,str(self.builder/'scripts/create_site.py'),str(worker),'--runtime','cloudflare-workers'],check=True,capture_output=True)
  (worker/'docs/design-record.json').write_text(json.dumps(self.doc),encoding='utf-8')
  self.assertTrue(inspect(self.builder,worker,'fixture-1')['compatible'])
 def test_tampered_builder_adapter_rejected(self):
  clone=self.root/'builder';shutil.copytree(self.builder,clone)
  (clone/'assets/runtime/public/assets/inquiry-adapter.js').write_text('// broken adapter')
  self.assertFalse(inspect(clone)['compatible'])

if __name__=='__main__':unittest.main()
