(function(){
var b=document.querySelector('.menu-btn'),n=document.getElementById('nav');
if(b&&n){b.addEventListener('click',function(){var o=n.classList.toggle('open');b.setAttribute('aria-expanded',o?'true':'false');});}
var r=document.getElementById('results');
if(r){
  var q=(new URLSearchParams(location.search).get('q')||'').trim();
  var inp=document.getElementById('q');if(inp){inp.value=q;}
  var cnt=document.getElementById('count');
  fetch(r.getAttribute('data-src')).then(function(x){return x.json();}).then(function(list){
    var t=q.toLowerCase().split(/\s+/).filter(Boolean);
    var m=t.length?list.filter(function(p){var s=(p.t+' '+p.c).toLowerCase();return t.every(function(w){return s.indexOf(w)>-1;});}):list;
    if(cnt){cnt.textContent=m.length+(m.length===1?' result':' results')+(q?' for "'+q+'"':'');}
    m.forEach(function(p){
      var a=document.createElement('article');a.className='card';
      var l=document.createElement('a');l.className='thumb';l.href=p.u;
      var i=document.createElement('img');i.src=p.i;i.alt=p.t;i.loading='lazy';i.width=400;i.height=500;
      i.onerror=function(){i.onerror=null;i.src=r.getAttribute('data-ph');};
      l.appendChild(i);a.appendChild(l);
      var d=document.createElement('div');d.className='cbody';
      var tg=document.createElement('span');tg.className='tag';tg.textContent=p.c;d.appendChild(tg);
      var h=document.createElement('h3');var ha=document.createElement('a');ha.href=p.u;ha.textContent=p.t;h.appendChild(ha);d.appendChild(h);
      a.appendChild(d);r.appendChild(a);
    });
  }).catch(function(){if(cnt){cnt.textContent='Search is unavailable right now.';}});
}
})();
