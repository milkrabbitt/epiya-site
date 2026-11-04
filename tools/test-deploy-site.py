#!/usr/bin/env python3
import ast, hashlib, io, json, os, pathlib, sys, tarfile, tempfile, types, unittest
# All writes occur in TemporaryDirectory; probes never call the network.
SCRIPT=pathlib.Path(__file__).resolve().parent/'deploy-site.sh'
SOURCE=SCRIPT.read_text(encoding='utf-8').split("<<'PY'\n",1)[1].rsplit('\nPY',1)[0]
if sys.version_info >= (3,8):
 ast.parse(SOURCE,feature_version=(3,6))
else:
 ast.parse(SOURCE)
m=types.ModuleType('deploy_under_test');exec(compile(SOURCE,str(SCRIPT),'exec'),m.__dict__)
OLD='edc2d5a1a08b462266b7281757a20b54ef76140f';NEW='a'*40;RID='epiya-20261104-'+NEW[:12]
HOME='<main>杭州壹湃科技有限公司 浙ICP备2026086186号-1 浙公网安备33011302001543号</main>'

def content():
 return {name:('epiya.cn\n' if name=='CNAME' else HOME if name=='index.html' else '<main>content '+name+'</main>').encode() for name in m.REQUIRED if name!='release.json'}

def manifest(entries,commit):
 return {'sourceCommit':commit,'date':'2026-11-04','files':[{'path':k,'size':len(v),'sha256':m.sha(v)} for k,v in sorted(entries.items()) if not k.startswith('.well-known/')]}

class Tests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.base=pathlib.Path(self.tmp.name);self.old=self.base/'releases/old'
  self.old.mkdir(parents=True);(self.base/'website-releases').mkdir();self.live=self.base/'site-20261009';self.original='../'+self.base.name+'/releases/old';os.symlink(self.original,self.live)
  self.entries=content();self.entries.update({'.nojekyll':b'','assets/old-fiber.svg':b'<svg/>','.well-known/acme-challenge/keep':b'certificate challenge'})
  for name,data in dict(self.entries,**{'release.json':json.dumps(manifest(self.entries,OLD)).encode()}).items():
   path=self.old/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
  self.new=content();self.new.update({'.nojekyll':b'','assets/logo-dark.svg':b'<svg>new</svg>','services.html':b'<main>services</main>'})
  self.new['index.html']=(HOME+' new').encode();self.archive=self.base/'new.tar.gz';self.fail_path=None;self.backend_changed=False
  self.write_archive()
 def write_archive(self,mutate=None):
  entries=dict(self.new);entries['release.json']=json.dumps(manifest(entries,NEW)).encode()
  if mutate:mutate(entries)
  with tarfile.open(self.archive,'w:gz') as tar:
   for name,data in entries.items():
    info=tarfile.TarInfo(name);info.size=len(data);tar.addfile(info,io.BytesIO(data))
  self.hash=m.sha(self.archive.read_bytes())
 def get(self,path):
  active=self.live.resolve()!=self.old.resolve()
  if active and path==self.fail_path:return 200,b'mismatch'
  if path in m.BACKEND:
   if path=='/healthz':return 200,b'{"ok":true,"service":"relic","version":2}'
   return 200,('backend '+path+(' changed' if active and self.backend_changed else '')).encode()
  p=self.live/path.lstrip('/')
  if p.is_dir():p=p/'index.html'
  if p.is_file():return 200,p.read_bytes()
  return 404,(self.live/'404.html').read_bytes()
 def deploy(self,**kwargs):
  return m.deploy(self.archive,kwargs.pop('archive_hash',self.hash),kwargs.pop('release_id',RID),kwargs.pop('old_commit',OLD),self.base,self.get,kwargs.pop('config',lambda:'unchanged-config'))
 def receipt(self):return json.loads((self.base/'website-releases'/RID/'deployment.json').read_text())
 def test_success_all_hashes_and_private_backup(self):
  result=self.deploy();self.assertEqual(result['result'],'deployed');self.assertEqual(self.receipt()['phase'],'healthy')
  self.assertEqual(os.readlink(self.live),str(self.base/'releases'/RID));self.assertTrue((self.live/'.well-known/acme-challenge/keep').is_file());self.assertFalse((self.live/'assets/old-fiber.svg').exists())
  backup=self.base/'website-releases'/RID;self.assertEqual(backup.stat().st_mode&0o777,0o700);self.assertEqual((backup/'deployment.json').stat().st_mode&0o777,0o600)
  self.assertTrue((backup/'previous-root/assets/old-fiber.svg').exists());self.assertEqual(self.receipt()['oldSymlink'],self.original)
  self.assertTrue(any(row['path']=='/meow/' for row in self.receipt()['verified']))
 def test_wrong_current_commit_fails_before_switch(self):
  with self.assertRaisesRegex(RuntimeError,'sourceCommit changed'):self.deploy(old_commit='b'*40)
  self.assertEqual(os.readlink(self.live),self.original)
 def test_wrong_archive_hash(self):
  with self.assertRaisesRegex(RuntimeError,'SHA256'):self.deploy(archive_hash='0'*64)
 def test_wrong_release_id(self):
  with self.assertRaisesRegex(RuntimeError,'manifest date and commit'):self.deploy(release_id='epiya-20261103-'+NEW[:12])
 def test_complete_manifest_detects_extra_file(self):
  self.write_archive(lambda entries:entries.update({'assets/undeclared.svg':b'<svg/>'}))
  with self.assertRaisesRegex(RuntimeError,'complete public file set'):self.deploy()
 def test_manifest_hash_tamper(self):
  self.write_archive(lambda entries:entries.update({'index.html':b'tampered'}))
  with self.assertRaisesRegex(RuntimeError,'Manifest'):self.deploy()
 def test_old_html_paths_retained(self):
  oldonly=self.old/'older-policy.html';oldonly.write_bytes(b'legacy policy')
  self.entries['older-policy.html']=oldonly.read_bytes();(self.old/'release.json').write_text(json.dumps(manifest(self.entries,OLD)))
  with self.assertRaisesRegex(RuntimeError,'HTML paths'):self.deploy()
 def test_cname_cannot_change(self):
  self.new['CNAME']=b'other.example\n';self.write_archive()
  with self.assertRaisesRegex(RuntimeError,'CNAME changed'):self.deploy()
 def test_filing_cannot_disappear(self):
  self.new['index.html']=b'new home';self.write_archive()
  with self.assertRaisesRegex(RuntimeError,'filing'):self.deploy()
 def test_private_key_rejected(self):
  self.new['assets/key.js']=b''.join((b'-----BEGIN ', b'PRIVATE', b' KEY-----'));self.write_archive()
  with self.assertRaisesRegex(RuntimeError,'Potential secret'):self.deploy()
 def test_changed_asset_rolls_back(self):
  self.fail_path='/assets/logo-dark.svg'
  with self.assertRaisesRegex(RuntimeError,'rolled-back'):self.deploy()
  self.assertEqual(os.readlink(self.live),self.original);self.assertEqual(self.receipt()['phase'],'rolled-back')
 def test_directory_alias_mismatch_rolls_back(self):
  self.fail_path='/meow/'
  with self.assertRaisesRegex(RuntimeError,'rolled-back'):self.deploy()
  self.assertEqual(os.readlink(self.live),self.original)
 def test_backend_body_change_rolls_back(self):
  self.backend_changed=True
  with self.assertRaisesRegex(RuntimeError,'rolled-back'):self.deploy()
  self.assertEqual(os.readlink(self.live),self.original)
 def test_nginx_change_rolls_back_and_reports_attention(self):
  calls=[]
  def config():calls.append(1);return 'unchanged-config' if len(calls)<3 else 'changed-config'
  with self.assertRaisesRegex(RuntimeError,'rollback-needs-attention'):self.deploy(config=config)
  self.assertEqual(os.readlink(self.live),self.original)
 def test_error_immediately_after_rename_restores_link(self):
  original=m.set_link;calls=[]
  def fail_once(*args):
   original(*args);calls.append(1)
   if len(calls)==1:raise OSError('injected post-rename failure')
  m.set_link=fail_once
  try:
   with self.assertRaisesRegex(RuntimeError,'rolled-back'):self.deploy()
  finally:m.set_link=original
  self.assertEqual(os.readlink(self.live),self.original)
 def test_reused_release_refused(self):
  (self.base/'releases'/RID).mkdir()
  with self.assertRaisesRegex(RuntimeError,'already used'):self.deploy()
 def test_archive_symlink_refused(self):
  with tarfile.open(self.archive,'w:gz') as tar:
   row=tarfile.TarInfo('assets/link');row.type=tarfile.SYMTYPE;row.linkname='/tmp/other';tar.addfile(row)
  self.hash=m.sha(self.archive.read_bytes())
  with self.assertRaisesRegex(RuntimeError,'Links/devices'):self.deploy()
 def test_archive_traversal_refused(self):
  with tarfile.open(self.archive,'w:gz') as tar:
   row=tarfile.TarInfo('../bad.html');row.size=1;tar.addfile(row,io.BytesIO(b'x'))
  self.hash=m.sha(self.archive.read_bytes())
  with self.assertRaisesRegex(RuntimeError,'Unsafe archive'):self.deploy()
 def test_backend_resource_shadow_refused(self):
  self.new['upload.js']=b'bad';self.write_archive()
  with self.assertRaisesRegex(RuntimeError,'protected backend'):self.deploy()
 def test_publisher_cannot_replace_certificate_challenge(self):
  self.new['.well-known/acme-challenge/keep']=b'bad';self.write_archive()
  with self.assertRaisesRegex(RuntimeError,'Certificate workflow'):self.deploy()

if __name__=='__main__':unittest.main(verbosity=2)
