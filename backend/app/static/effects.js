/* CrossAIO 共享动态效果 JS — 滚动渐入 + 数字计数 */
(function(){
  // 滚动渐入
  var els = document.querySelectorAll('.reveal');
  function check(){
    els.forEach(function(el){
      var r = el.getBoundingClientRect();
      if(r.top < window.innerHeight - 60) el.classList.add('in');
    });
  }
  window.addEventListener('scroll', check, {passive:true});
  window.addEventListener('load', check);
  check();

  // 数字滚动计数
  document.querySelectorAll('.count-up').forEach(function(el){
    var target = parseInt(el.textContent.trim());
    if(isNaN(target)) return;
    var start = 0, dur = 1200, t0 = null;
    function step(ts){
      if(!t0) t0 = ts;
      var p = Math.min((ts - t0) / dur, 1);
      el.textContent = Math.floor(p * target);
      if(p < 1) requestAnimationFrame(step);
    }
    var r = el.getBoundingClientRect();
    if(r.top < window.innerHeight) requestAnimationFrame(step);
  });

  // 语言切换器：<640px 折叠为原生下拉（从现有 .lang-switch 按钮构建，保持当前页路径）
  var _sw = document.querySelector('.lang-switch');
  if(_sw && !document.querySelector('.lang-switch-mobile')){
    var _links = _sw.querySelectorAll('a[data-lang]');
    var _opts = [];
    _links.forEach(function(x){
      var _code = x.getAttribute('data-lang');
      var _sel = x.getAttribute('aria-current') ? ' selected' : '';
      _opts.push('<option value="'+x.getAttribute('href')+'" data-lang="'+_code+'"'+_sel+'>'+x.textContent.trim()+'</option>');
    });
    if(_opts.length){
      var _d = document.createElement('span');
      _d.innerHTML = '<select class="lang-switch-mobile" role="navigation" aria-label="Language" onchange="location.href=this.value">'+_opts.join('')+'</select>';
      _sw.parentNode.insertBefore(_d.firstChild, _sw.nextSibling);
      var _css = document.createElement('style');
      _css.textContent = '.lang-switch-mobile{display:none;padding:6px 12px;font-size:13px;border:1px solid #cbd5e1;border-radius:999px;color:#0f172a;background:#fff;max-width:132px}@media(max-width:639px){.lang-switch{display:none!important}.lang-switch-mobile{display:inline-flex!important}}';
      document.head.appendChild(_css);
    }
  }
})();
