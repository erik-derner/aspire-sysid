"""The single page of the web app: structure, style and script.

The page uses the style of the HTML report (:data:`aspire_sysid.report.html_report.CSS`) and adds
the forms. Its script does three things: it asks the server for the changes of the state and places
the blocks it receives, it shows the form of the pending prompt, and it sends the user's input. All
content is rendered on the server; the script loads nothing from another site.
"""

from __future__ import annotations

from ..report import html_report as H

__all__ = ["render_page"]

EXTRA_CSS = r"""
#status{position:sticky;top:0;z-index:5;background:var(--page);border-bottom:1px solid var(--grid);padding:8px 0;margin:6px 0 4px;
font-size:14px;color:var(--ink2);display:flex;gap:10px;align-items:center}
#status .dot{width:9px;height:9px;border-radius:50%;background:var(--muted);flex:none}
#status.busy .dot{background:var(--accent);animation:pulse 1.2s ease-in-out infinite}
#status.wait .dot{background:var(--warn)}
@keyframes pulse{50%{opacity:.25}}
.block{margin:10px 0}
.block h2{margin-top:28px}
.cardtitle{font-size:12.5px;font-weight:650;color:var(--ink2);text-transform:none;margin-bottom:4px}
.card.question{border-left:4px solid var(--s7)}
.card.user{border-left:4px solid var(--accent);background:var(--accent-wash)}
.logline{font-size:12.5px;color:var(--ink2);font-family:ui-monospace,SFMono-Regular,Consolas,monospace;word-break:break-word}
.logerr{font-size:13.5px;color:var(--bad);font-weight:600;word-break:break-word}
iframe.page{width:100%;border:1px solid var(--ring);border-radius:8px;background:var(--page);min-height:420px;margin-top:8px}
#prompt{border-top:1px solid var(--grid);padding:10px 0 14px;margin-top:18px}
#prompt .card{margin:6px 0}
#prompt h3{margin:2px 0 8px}
textarea,input[type=text],input[type=number],select{width:100%;font:inherit;color:var(--ink);background:var(--surface);
border:1px solid var(--axis);border-radius:6px;padding:7px 9px}
textarea{min-height:76px;resize:vertical}
textarea.code{font-family:ui-monospace,SFMono-Regular,Consolas,monospace;font-size:12.5px;min-height:420px;white-space:pre;overflow:auto}
label{display:block;font-size:13.5px;color:var(--ink2);margin:8px 0 3px}
button.act{background:var(--accent);color:#fff;border:1px solid var(--accent);border-radius:6px;padding:7px 14px;font:inherit;
font-weight:600;cursor:pointer}
button.alt{background:var(--surface);color:var(--ink);border:1px solid var(--axis);border-radius:6px;padding:7px 14px;font:inherit;cursor:pointer}
button.danger{background:var(--surface);color:var(--bad);border:1px solid var(--bad);border-radius:6px;padding:7px 14px;font:inherit;cursor:pointer}
button:disabled{opacity:.5;cursor:default}
.row{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-top:10px}
.cols{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:12px}
.change{display:grid;grid-template-columns:minmax(170px,1.2fr) minmax(90px,.6fr) minmax(90px,.5fr) 2fr auto;gap:6px;margin:6px 0;align-items:start}
@media (max-width:760px){.change{grid-template-columns:1fr}}
.note{color:var(--bad);font-size:13.5px;margin:4px 0}
.ok{color:var(--good);font-weight:600}
.ack{font-size:14px}
"""

SCRIPT = r"""
(function(){
'use strict';
var version=-1, promptId=null, lastAck='', busy=false;
var blocksEl=document.getElementById('blocks'), promptEl=document.getElementById('prompt'), statusEl=document.getElementById('status');
var root=document.documentElement;
try{var t=localStorage.getItem('aspire-report-theme');if(t)root.setAttribute('data-theme',t);}catch(e){}

function esc(s){return String(s==null?'':s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');}
function post(path,body){return fetch(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body||{})})
  .then(function(r){return r.json();});}
function $(id){return document.getElementById(id);}
var HINT='<span class="muted small">Ctrl+Enter sends.</span>';
// Ctrl+Enter (Cmd+Enter on a Mac) in a text field presses the button named by its data-submit attribute
document.addEventListener('keydown',function(ev){
  if(ev.key!=='Enter'||!(ev.ctrlKey||ev.metaKey))return;
  var id=ev.target&&ev.target.getAttribute&&ev.target.getAttribute('data-submit');
  var b=id&&$(id);
  if(b&&!b.disabled){ev.preventDefault();b.click();}
});

// ---- blocks
function fitFrames(el){el.querySelectorAll('iframe.page').forEach(function(f){f.addEventListener('load',function(){
  function fit(){try{f.style.height=(f.contentDocument.documentElement.scrollHeight+24)+'px';}catch(e){}}
  fit();try{new ResizeObserver(fit).observe(f.contentDocument.body);}catch(e){}});});}
function nearBottom(){return window.innerHeight+window.scrollY>=document.body.scrollHeight-260;}
function applyBlock(b){
  var el=$('block-'+b.id), stick=nearBottom();
  if(!el){el=document.createElement('section');el.id='block-'+b.id;el.className='block '+(b.cls||'');el.innerHTML=b.html;
    blocksEl.appendChild(el);fitFrames(el);}
  else{var open=Array.prototype.map.call(el.querySelectorAll('details'),function(d){return d.open;});
    // what the user unfolded stays unfolded; a course that has just ended is folded by the server
    var ended=(b.cls||'').indexOf('final')>=0&&el.className.indexOf('final')<0;
    el.className='block '+(b.cls||'');el.innerHTML=b.html;
    var ds=el.querySelectorAll('details');
    for(var i=ended?1:0;i<ds.length&&i<open.length;i++){ds[i].open=open[i];}
    fitFrames(el);}
  if(stick){window.scrollTo(0,document.body.scrollHeight);}
}
function setStatus(s){var text=s.status||'';var waiting=!!s.prompt&&s.prompt.kind!=='ended'&&s.prompt.kind!=='start';
  statusEl.className=waiting?'wait':(s.phase==='running'?'busy':'');
  statusEl.innerHTML='<span class=dot></span><span>'+esc(text||(s.phase==='start'?'No session is running.':s.phase==='ended'?'The session has ended.':''))+'</span>';}

// ---- sending an input
function send(reply,ack){lastAck=ack||'';var id=promptId;
  promptEl.innerHTML='<div class="card ack"><b>Received.</b> '+esc(lastAck)+'</div>';
  post('api/reply',{prompt:id,reply:reply}).then(function(r){if(!r.ok){promptEl.innerHTML='<div class=card><span class=note>'+esc(r.error||'The input was not accepted.')+'</span></div>';promptId=null;}});}
function working(s){var text=s.phase==='running'?'The agent or the harness is working; nothing is needed from you now.':'';
  promptEl.innerHTML=(lastAck||text)?'<div class="card ack">'+(lastAck?'<b>Received.</b> '+esc(lastAck)+' ':'')+esc(text)+'</div>':'';}

// ---- prompts
var forms={};
forms.start=function(p){
  var opts=(p.tasks||[]).map(function(t){return '<option value="'+esc(t.id)+'">'+esc(t.id)+' – '+esc(t.title)+'</option>';}).join('');
  promptEl.innerHTML='<div class=cols>'
   +'<div class=card><h3>Session on an existing task</h3><label for=task>Task (folder in '+esc(p.tasks_root)+')</label><select id=task>'+opts+'</select>'
   +'<div class=row><button class=act id=go-task'+(opts?'':' disabled')+'>Start the session</button><button class=alt id=edit-task'+(opts?'':' disabled')+'>Edit task.yaml</button></div></div>'
   +'<div class=card><h3>Session from data files</h3>'
   +'<label for=f-train>Training data (required; a CSV file with a header row)</label><input type=file id=f-train accept=".csv,text/csv">'
   +'<label for=f-val>Validation data (optional)</label><input type=file id=f-val accept=".csv,text/csv">'
   +'<label for=f-test>Test data (optional; one file per test trajectory; no agent can read them)</label><input type=file id=f-test accept=".csv,text/csv" multiple>'
   +'<label for=new-task>Name of the new task (optional; lower-case letters, digits and hyphens)</label><input type=text id=new-task placeholder="task-'+esc(p.today)+'-01">'
   +'<div class=row><button class=act id=go-data>Prepare the task with the agent</button></div>'
   +'<p class="muted small">Your files are copied into a new task folder; the originals stay where they are. The agent then examines the training data and asks you what the data do not show.</p></div>'
   +'</div><p class="muted small">Model: '+esc(p.model)+'. '+esc(p.note||'')+'</p><div id=start-note class=note></div>';
  function fail(m){$('start-note').textContent=m;busy=false;}
  function started(r){if(!r.ok){fail(r.error||'The session could not be started.');}}
  if($('go-task')){$('go-task').onclick=function(){if(busy)return;busy=true;$('start-note').textContent='Starting…';
    post('api/start',{task:$('task').value}).then(started).catch(function(){fail('The harness did not answer.');});};}
  if($('edit-task')){$('edit-task').onclick=function(){openEditor($('task').value,null,p);};}
  $('go-data').onclick=function(){
    var tr=$('f-train').files[0];if(!tr){fail('Choose the file with the training data.');return;}
    if(busy)return;busy=true;$('start-note').textContent='Copying the files…';
    function read(f){return f.text().then(function(t){return {name:f.name,text:t};});}
    var jobs=[read(tr),$('f-val').files[0]?read($('f-val').files[0]):Promise.resolve(null),
              Promise.all(Array.prototype.map.call($('f-test').files,read))];
    Promise.all(jobs).then(function(a){return post('api/start',{train:a[0],val:a[1],tests:a[2],new_task:$('new-task').value.trim()});})
      .then(started).catch(function(){fail('The files could not be read or sent.');});};
};
forms.question=function(p){
  // p.html is the question rendered by the server (Markdown, expressions); the plain text is the fallback
  promptEl.innerHTML='<div class=card><h3>The agent asks you a question</h3>'
   +(p.html?p.html:'<div class=say>'+esc(p.question)+'</div>'+(p.decision?'<p class="muted small">Decision affected, as stated by the agent: '+esc(p.decision)+'</p>':''))
   +'<label for=answer>Your answer</label><textarea id=answer data-submit=send></textarea>'
   +'<div class=row><button class=act id=send>Send the answer</button><button class=alt id=none>Give no answer</button>' + HINT + '</div></div>';
  $('answer').focus();
  $('send').onclick=function(){var t=$('answer').value.trim();if(!t){$('answer').focus();return;}
    send({text:t},'Your answer was passed to the agent. The agent continues.');};
  $('none').onclick=function(){send({text:''},'No answer. The agent was told that you gave none and continues.');};
};
forms.verdict=function(p){
  promptEl.innerHTML='<div class=card><h3>Is this the task you want?</h3><p class=small>Read the task brief above. It is what the identification agent will receive.</p>'
   +'<div class=row><button class=act id=accept>Accept and start the identification</button>'
   +(p.editable?'<button class=alt id=edit>Edit task.yaml yourself</button>':'')+'<button class=danger id=stop>Stop</button></div>'
   +'<label for=change>Or ask the agent for a change</label><textarea id=change data-submit=ask-change placeholder="For example: the output is the heading, not the position."></textarea>'
   +'<div class=row><button class=alt id=ask-change>Send the change request</button>' + HINT + '</div></div>';
  $('accept').onclick=function(){send({verdict:'accept'},'The task is accepted. The identification starts.');};
  $('stop').onclick=function(){send({verdict:'stop'},'Stopped. The identification does not start; the task folder is kept.');};
  $('ask-change').onclick=function(){var t=$('change').value.trim();if(!t){$('change').focus();return;}
    send({verdict:'change',text:t},'Your change request was passed to the agent, which continues the preparation of the task.');};
  if($('edit')){$('edit').onclick=function(){openEditor(null,p);};}
};
forms.choice=function(p){
  var reqs=p.requirements||[];
  promptEl.innerHTML=(p.note?'<div class=note>'+esc(p.note)+'</div>':'')
   +'<p class="muted small">Remaining for this session: '+esc(p.remaining)+'. One analysis request may use up to '+esc(p.analysis_limits)+'.</p>'
   +'<div class=cols>'
   +'<div class=card><h3>Ask the agent for an analysis or an explanation</h3><p class="muted small">The models stay as they are.</p>'
   +'<textarea id=analysis data-submit=go-analysis placeholder="For example: why did you choose the midpoint rule?"></textarea><div class=row><button class=act id=go-analysis>Send the request</button>' + HINT + '</div></div>'
   +'<div class=card><h3>Start a new identification round</h3><label for=feedback>Your feedback on the models</label><textarea id=feedback data-submit=go-round></textarea>'
   +'<div id=changes></div><div class=row><button class=alt id=add-change>Add a change of the task</button><button class=act id=go-round>Start the round</button>' + HINT + '</div></div>'
   +'</div><div class=row><button class=danger id=go-end>End the session</button></div>';
  var kinds=[['add_nl_requirement','add a requirement in words']];
  if(reqs.length){kinds=[['allow_violation','allow a violation of'],['restore_exclusion','exclude again on a violation of'],['set_tolerance','set the tolerance of']].concat(kinds);}
  $('add-change').onclick=function(){var d=document.createElement('div');d.className='change';
    d.innerHTML='<select class=k>'+kinds.map(function(k){return '<option value="'+k[0]+'">'+k[1]+'</option>';}).join('')+'</select>'
     +'<select class=r>'+reqs.map(function(r){return '<option>'+esc(r)+'</option>';}).join('')+'</select>'
     +'<input class=v type=number step=any placeholder="tolerance">'
     +'<input class=i type=text placeholder="your instruction, in your words"><button class=alt type=button>Remove</button>';
    function show(){var k=d.querySelector('.k').value;d.querySelector('.r').style.visibility=(k==='add_nl_requirement')?'hidden':'visible';
      d.querySelector('.v').style.visibility=(k==='set_tolerance')?'visible':'hidden';
      d.querySelector('.i').placeholder=(k==='add_nl_requirement')?'the requirement, in your words':'your instruction, in your words';}
    d.querySelector('.k').onchange=show;d.querySelector('button').onclick=function(){d.remove();};show();$('changes').appendChild(d);};
  $('go-analysis').onclick=function(){var t=$('analysis').value.trim();if(!t){$('analysis').focus();return;}
    send({action:'analysis',text:t},'Your analysis request was passed to the agent.');};
  $('go-round').onclick=function(){
    var ch=Array.prototype.map.call(document.querySelectorAll('#changes .change'),function(d){var k=d.querySelector('.k').value;
      return {kind:k,requirement:k==='add_nl_requirement'?null:(d.querySelector('.r').value||null),
              value:k==='set_tolerance'?d.querySelector('.v').value:null,instruction:d.querySelector('.i').value.trim()};});
    send({action:'new_round',text:$('feedback').value.trim(),changes:ch},
         'Your feedback'+(ch.length?' and '+ch.length+' task change'+(ch.length>1?'s':''):'')+' are recorded. A new round starts.');};
  $('go-end').onclick=function(){send({action:'end'},'The session ends. The harness writes the record and the report; this can take a moment.');};
};
forms.ended=function(p){
  lastAck='';
  promptEl.innerHTML='<div class=card><h3>'+esc(p.title||'The session has ended.')+'</h3>'+(p.html||'')
   +'<div class=row><button class=act id=again>Start another session</button><button class=alt id=down>Shut down the web app</button></div></div>';
  $('again').onclick=function(){post('api/reset',{});};
  $('down').onclick=function(){post('api/shutdown',{}).then(function(){promptEl.innerHTML='<div class=card>The web app is shut down. You can close this page.</div>';
    statusEl.innerHTML='<span class=dot></span><span>The web app is shut down.</span>';});};
};

// ---- the editor of task.yaml
function openEditor(taskId,verdictPrompt,startPrompt){
  var q=taskId?('?id='+encodeURIComponent(taskId)):'';
  fetch('api/task'+q).then(function(r){return r.json();}).then(function(d){
    if(!d.ok){promptEl.innerHTML='<div class=card><span class=note>'+esc(d.error)+'</span></div>';return;}
    promptEl.innerHTML='<div class=card><h3>Edit task.yaml</h3><p class="muted small">'+esc(d.path)+'. Check shows the errors of the text, or the task brief it gives; '
     +'Save writes the file only when the text is valid.</p><textarea id=yaml class=code spellcheck=false></textarea>'
     +'<div class=row><button class=alt id=y-check>Check</button><button class=act id=y-save>Save</button><button class=alt id=y-cancel>Cancel</button></div>'
     +'<div id=y-result></div></div>';
    $('yaml').value=d.text;
    function back(){if(verdictPrompt){forms.verdict(verdictPrompt);}else if(startPrompt){forms.start(startPrompt);}}
    function show(r,saved){var el=$('y-result');
      if(!r.ok&&r.error){el.innerHTML='<p class=note>'+esc(r.error)+'</p>';return;}
      if(!r.valid){el.innerHTML='<p class=note>The text is not a valid task definition:</p><pre>'+esc(r.errors)+'</pre>';return;}
      el.innerHTML='<p class=ok>'+(saved?'Saved. ':'The text is valid. ')+'The task brief it gives:</p><div class="card doc">'+r.brief_html+'</div>';
      if(saved){setTimeout(back,700);}}
    $('y-check').onclick=function(){post('api/task/check',{id:taskId,text:$('yaml').value}).then(function(r){show(r,false);});};
    $('y-save').onclick=function(){post('api/task/save',{id:taskId,text:$('yaml').value}).then(function(r){show(r,true);});};
    $('y-cancel').onclick=back;
  });
}

// ---- the state loop
function apply(s){
  var ids={};(s.order||[]).forEach(function(i){ids['block-'+i]=1;});
  Array.prototype.slice.call(blocksEl.children).forEach(function(el){if(!ids[el.id]){el.remove();}});
  (s.blocks||[]).forEach(applyBlock);
  setStatus(s);
  var pid=s.prompt?s.prompt.id:null;
  if(pid!==promptId){promptId=pid;busy=false;
    if(s.prompt&&forms[s.prompt.kind]){lastAck='';forms[s.prompt.kind](s.prompt);window.scrollTo(0,document.body.scrollHeight);}
    else{working(s);}}
  else if(!s.prompt){working(s);}
  version=s.version;
}
// "?snapshot=1" shows the present state once and does not wait for changes (for a picture of the page)
var snapshot=/[?&]snapshot=1/.test(location.search);
function poll(){
  fetch('api/state?since='+version+(snapshot?'&wait=0':'')).then(function(r){return r.json();}).then(function(s){apply(s);if(!snapshot){poll();}})
   .catch(function(){statusEl.className='';statusEl.innerHTML='<span class=dot></span><span>The connection to the harness is lost. Is the web app still running?</span>';setTimeout(poll,2000);});
}
document.addEventListener('click',function(ev){
  var b=ev.target.closest('button.theme');
  if(b){var cur=root.getAttribute('data-theme')||(matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light');
    var nxt=cur==='dark'?'light':'dark';root.setAttribute('data-theme',nxt);try{localStorage.setItem('aspire-report-theme',nxt);}catch(e){}return;}
  var o=ev.target.closest('[data-open]');
  if(o){var scope=o.closest('.block')||document, on=o.getAttribute('data-state')!=='open';
    scope.querySelectorAll(o.getAttribute('data-open')).forEach(function(d){d.open=on;});
    o.setAttribute('data-state',on?'open':'closed');o.textContent=o.getAttribute(on?'data-hide':'data-show');}
});
poll();
})();
"""


def render_page() -> str:
    """The HTML of the page (served at the root of the token path)."""
    return (
        "<!doctype html><html lang=en><head><meta charset=utf-8>"
        '<meta name=viewport content="width=device-width,initial-scale=1"><meta name=referrer content=no-referrer>'
        f"<title>ASPIRE – interactive session</title><style>{H.CSS}{EXTRA_CSS}</style></head><body><main>"
        "<div class=toolbar><div class=crumb><b>ASPIRE</b> · interactive session</div>"
        "<button class=theme type=button>Light / dark</button></div>"
        "<div id=status><span class=dot></span><span>Connecting…</span></div>"
        "<div id=blocks></div><div id=prompt></div>"
        f"</main><script>{SCRIPT}</script></body></html>"
    )
