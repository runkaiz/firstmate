import os, sys, subprocess as sp, time, pathlib, json, re, shutil, hashlib
R=pathlib.Path('/home/runkai/.no-mistakes/worktrees/6b05071b95c8/01M4SDZYSXHY7YZWBA8DQSEBZ1')
E=pathlib.Path('/home/runkai/.no-mistakes/evidence/01M4SDZYSXHY7YZWBA8DQSEBZ1')
S=R/'.lv/s'
env={k:v for k,v in os.environ.items() if not k.startswith(('FM_','TASKS_AXI_')) and k not in ('TMUX','NO_MISTAKES_GATE','HERDR_ENV','CMUX_WORKSPACE_ID')}
env.update(TMUX=str(S)+',0,0',FM_POLL='1',FM_SIGNAL_GRACE='1',FM_CHECK_INTERVAL='999999',FM_HEARTBEAT='999999',FM_SECONDMATE_LIVENESS_SECS='99999999',FM_WATCH_HANDLING_SUCCESSOR='1',FM_PAUSE_RESURFACE_SECS='999',GIT_CONFIG_GLOBAL='/dev/null',GIT_CONFIG_NOSYSTEM='1')
log=open(E/'live-transcript.log','w',buffering=1)
def note(s): print(s,flush=True);log.write(s+'\n')
def run(args,**kw):
    p=sp.run([str(x) for x in args],env=kw.pop('env',env),text=True,stdout=sp.PIPE,stderr=sp.PIPE,**kw)
    if p.returncode: raise RuntimeError(f'{args}: {p.returncode}\n{p.stdout}\n{p.stderr}')
    return p.stdout
def tm(*a): return run(['tmux','-S',S,*a])
watchers=[]
class Case:
 def __init__(self,name,base=False,away=False):
    self.name=name; self.home=R/'.lv'/name; self.state=self.home/'state'; self.bin=R/('.lv/base/bin' if base else 'bin'); self.p=None
    run([R/'bin/fm-lab-home.sh','create',self.home])
    self.env=dict(env,FM_HOME=str(self.home))
    (self.home/'config/backend').write_text('tmux\n')
    (self.home/'.tasks.toml').write_text('backend = "markdown"\n[markdown]\npath = "data/backlog.md"\narchive = "data/done-archive.md"\ndone_keep = 10\n')
    (self.home/'data/backlog.md').write_text('## In flight\n\n## Queued\n\n## Done\n')
    run(['tasks-axi','add','worker','preserved finished worker','--file','data/backlog.md'],cwd=self.home,env=self.env)
    self.window=f'fm-lab-alert:{name}'
    tm('new-window','-d','-t','fm-lab-alert','-n',name,'-c',str(R),'bash --noprofile --norc')
    worktree=self.home/'projects/worker';worktree.mkdir()
    run(['git','init','-q','-b','unlanded-result',worktree])
    (worktree/'preserved-work.txt').write_text('unlanded result must survive supervision\n')
    run(['git','-C',worktree,'add','preserved-work.txt'])
    run(['git','-C',worktree,'-c','user.name=Lab','-c','user.email=lab@example.invalid','-c','core.hooksPath=/dev/null','-c','commit.gpgsign=false','commit','-qm','preserved lab work'])
    self.head=run(['git','-C',worktree,'rev-parse','HEAD']).strip()
    (self.state/'worker.meta').write_text(f'window={self.window}\nkind=ship\nharness=claude\nbackend=tmux\nworktree={worktree}\n')
    (self.state/'worker.status').write_text('done: preserved result\n')
    run([R/'bin/fm-busy-event.sh','arm',self.state,'worker','--state','idle','--source','claude-hook','--event','Stop'],env=self.env)
    if away: (self.state/'.afk').touch()
    self.key=self.window.translate(str.maketrans(':/.','___'))
    self.marker=self.state/('.terminal-resurfaced-'+self.key)
    self.prime()
    note(f'CASE {name}: real tmux 100x30, real watcher + crew-state, home={self.home}; '+run([self.bin/'fm-crew-state.sh','worker'],env=self.env).strip())
 def prime(self):
    run(['bash','-c','. "$1"; fm_wake_status_mark_current "$2" "$3"','_',self.bin/'fm-wake-lib.sh',self.state,self.state/'worker.status'],env=self.env)
 def draw(self,text):
    tm('send-keys','-t',self.window,'-l',"printf '\\033[2J\\033[H%s\\n' '"+text+"'")
    tm('send-keys','-t',self.window,'Enter');time.sleep(.25)
    capture=tm('capture-pane','-p','-t',self.window,'-S','-40')
    self.expected_hash=hashlib.md5(capture.rstrip('\n').encode()).hexdigest()
    note('TERMINAL '+self.name+': '+repr(capture.strip()))
 def start(self):
    self.output=open(E/(self.name+'-watch.log'),'a')
    self.p=sp.Popen([str(self.bin/'fm-watch.sh')],env=self.env,stdout=self.output,stderr=sp.STDOUT,start_new_session=True);watchers.append(self.p)
 def queue(self):
    p=self.state/'.wake-queue'
    return p.read_text() if p.is_file() else ''
 def surfaced(self,text,kind='stale'):
    self.draw(text);self.start()
    try: rc=self.p.wait(timeout=25)
    except sp.TimeoutExpired: self.stop();raise AssertionError(self.name+' did not surface '+text)
    self.output.close();q=self.queue();note(f'WAKE {self.name} rc={rc}: {q.strip()}')
    assert rc==0 and '\t'+kind+'\t' in q,(self.name,rc,q)
 def ack(self):
    p=sp.run([str(self.bin/'fm-wake-drain.sh')],env=self.env,text=True,capture_output=True)
    note('DRAIN '+self.name+':\n'+p.stdout+p.stderr)
    m=re.search(r'--ack-through (\d+) --recovery-generation ([A-Za-z0-9._-]+)',p.stderr)
    assert m,(p.stdout,p.stderr)
    run([self.bin/'fm-wake-drain.sh','--ack-through',m[1],'--recovery-generation',m[2]],env=self.env)
    assert not self.queue().strip()
 def stop(self):
    if self.p and self.p.poll() is None:self.p.terminate();self.p.wait(timeout=15)
    if hasattr(self,'output'):self.output.close()
 def silent(self,text):
    self.draw(text)
    if not self.p or self.p.poll() is not None:self.start()
    deadline=time.time()+20
    # Require the actual captured new hash to have settled and been classified.
    while time.time()<deadline:
      assert self.p.poll() is None,(self.name,'unexpected exit',self.queue())
      sf=self.state/('.stale-'+self.key); hf=self.state/('.hash-'+self.key);cf=self.state/('.count-'+self.key)
      if sf.exists() and hf.exists() and cf.exists() and sf.read_text()==hf.read_text()==self.expected_hash and int(cf.read_text())>=2:break
      time.sleep(.2)
    else:raise AssertionError(self.name+' no completed settled scan')
    time.sleep(1.2)
    assert self.p.poll() is None and not self.queue().strip(),(self.name,self.queue())
    note(f'ABSORBED {self.name}: {text}; settled_count={cf.read_text().strip()}; queue empty; watcher still running')
 def close(self):
    self.stop()
    assert (self.home/'projects/worker/preserved-work.txt').read_text()=='unlanded result must survive supervision\n'
    assert run(['git','-C',self.home/'projects/worker','rev-parse','HEAD']).strip()==self.head
    assert run(['git','-C',self.home/'projects/worker','branch','--show-current']).strip()=='unlanded-result'
    note('PRESERVED '+self.name+': unlanded branch, commit, and result unchanged')
    tm('kill-window','-t',self.window)

try:
 tm('-f','/dev/null','new-session','-d','-s','fm-lab-alert','-n','control','-x','100','-y','30','bash --noprofile --norc')
 for name,base,away in [('baseline',True,False),('target',False,False),('target-away',False,True)]:
    c=Case(name,base,away)
    c.surfaced('idle tick 1');c.ack()
    if base:
      for n in (2,3):c.surfaced(f'idle tick {n}');c.ack()
      note('MEASURE baseline: 3 settled hashes -> 3 stale wake requests')
    else:
      stamp=c.marker.stat().st_mtime_ns
      for n in (2,3):c.silent(f'idle tick {n}')
      assert c.marker.stat().st_mtime_ns==stamp
      note(f'MEASURE {name}: 3 settled hashes -> 1 stale wake request; absorbed redraws did not advance cadence')
      c.stop();c.ack()
      old=time.time()-5000;os.utime(c.marker,(old,old))
      c.surfaced('idle after cadence');c.ack()
      replacement=c.state/'replacement';replacement.write_text('done: preserved result\n');replacement.replace(c.state/'worker.status');c.prime()
      c.surfaced('idle replacement generation');c.ack()
      run([R/'bin/fm-busy-event.sh','arm',c.state,'worker','--state','idle'],env=c.env)
      c.surfaced('idle successor incarnation');c.ack()
      note('PASS '+name+' cadence, replacement generation, successor incarnation')
    c.close()
 for i,event in enumerate(['done: second result','needs-decision [key=new]: choose release','blocked [key=new]: release unavailable','failed: new validation failure']):
    for path in ('signal','stale'):
      c=Case(f'event-{i}-{path}');c.surfaced('old result');c.ack()
      with (c.state/'worker.status').open('a') as f:f.write(event+'\n')
      if path=='stale':c.prime()
      c.surfaced('new event '+event,kind=path);c.ack();note('PASS '+path+' preserves '+event);c.close()
 c=Case('queue-retry');(c.state/'.wake-queue').mkdir();c.draw('first result');c.start();rc=c.p.wait(timeout=25);c.output.close()
 assert rc!=0 and not c.marker.exists()
 note(f'QUEUE REFUSAL exit={rc}; no delivery throttle created')
 (c.state/'.wake-queue').rmdir();c.surfaced('retry result');c.ack();c.close()
 for away in (False,True):
    c=Case('busy-reset-'+str(away),away=away)
    run([R/'bin/fm-busy-event.sh','arm',c.state,'worker','--state','idle'],env=c.env)
    c.surfaced('old result before activity');c.ack()
    run([R/'bin/fm-busy-event.sh','apply',c.state,'worker','busy','--current-gen','--source','claude-hook','--event','UserPromptSubmit'],env=c.env)
    c.draw('resumed activity');c.start()
    deadline=time.time()+20
    while c.marker.exists() and time.time()<deadline:
      assert c.p.poll() is None
      time.sleep(.2)
    assert not c.marker.exists() and not c.queue().strip()
    note('BUSY '+c.name+': real semantic event cleared delivery throttle; queue empty')
    c.stop();c.ack()
    run([R/'bin/fm-busy-event.sh','apply',c.state,'worker','idle','--current-gen','--source','claude-hook','--event','Stop'],env=c.env)
    c.surfaced('quiet after activity');c.ack();c.close()
 c=Case('captain-call');c.surfaced('done before new call');c.ack()
 run([R/'bin/fm-captain-hold.sh','hold','worker','--reason','choose release in isolated lab'],env=c.env,cwd=R)
 c.surfaced('new captain call');c.ack();c.silent('same held call redraw');c.stop();c.ack();c.close()
 for status in ('blocked: still blocked','working: stopped without a result'):
    c=Case('nonterminal-'+status.split(':')[0]);(c.state/'worker.status').write_text(status+'\n');c.prime()
    for n in (1,2):c.surfaced('unheld status tick '+str(n));c.ack()
    note('PASS repeated unheld '+status);c.close()
 note('PASS all live checks; no LLM calls made; counts measure wake requests only')
except Exception as exc:
 note('FAIL '+repr(exc));raise
finally:
 for p in watchers:
    if p.poll() is None:p.terminate();p.wait(timeout=15)
 sp.run(['tmux','-S',str(S),'kill-server'],env=env,capture_output=True)
 log.close()
