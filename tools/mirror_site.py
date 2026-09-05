#!/usr/bin/env python3
"""Mirror a chatgpt.site page into a self-contained static folder for GitHub Pages.

    python3 tools/mirror_site.py https://uchastki-pod-minskom.alexautorental.chatgpt.site/ public/uchastki

chatgpt.site (OpenAI hosting) is unreachable from Russia/Belarus without a VPN, GitHub Pages is.
The server-rendered HTML is kept verbatim; what changes:
  - the React/vinext runtime (module scripts, modulepreloads, RSC bootstrap) and the Cloudflare
    challenge script are dropped -- the page needs neither once it is static;
  - the stylesheet moves to assets/, photos to photos/, all paths become relative so the page
    works under any sub-path (GitHub Pages serves the repo at /panamera-studio/);
  - a small inline script re-creates the page's only client behaviour: photo-strip prev/next
    buttons with the "1 / 3" counter, and the Share button (navigator.share / clipboard).
Re-run after the source site changes; the folder is rebuilt from scratch.
"""
import os, re, shutil, sys, urllib.request
from concurrent.futures import ThreadPoolExecutor

UA = 'Mozilla/5.0 (Linux; Android 15) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128 Mobile Safari/537.36'

CLIENT_JS = r"""<script>
(function(){
  document.querySelectorAll('article.property').forEach(function(card){
    var strip=card.querySelector('.photo-strip'),controls=card.querySelector('.photo-controls');
    if(!strip||!controls)return;
    var n=strip.querySelectorAll('.photo-slide').length;
    var prev=controls.querySelector('button[aria-label="Предыдущее фото"]');
    var next=controls.querySelector('button[aria-label="Следующее фото"]');
    var counter=controls.querySelector('span');
    if(!prev||!next||!counter||n<2)return;
    var idx=0;
    function render(){counter.textContent=(idx+1)+' / '+n;prev.disabled=idx===0;next.disabled=idx===n-1;}
    strip.addEventListener('scroll',function(){idx=Math.round(strip.scrollLeft/(strip.clientWidth||1));render();},{passive:true});
    function go(d){idx=Math.min(n-1,Math.max(0,idx+d));strip.scrollTo({left:idx*strip.clientWidth,behavior:'smooth'});render();}
    prev.addEventListener('click',function(){go(-1);});
    next.addEventListener('click',function(){go(1);});
  });
  var share=document.querySelector('button.share-button');
  if(share)share.addEventListener('click',function(){
    var url=location.origin+location.pathname,status='';
    var done=function(){
      if(!status)return;
      var out=document.querySelector('output.share-status');
      if(!out){out=document.createElement('output');out.className='share-status';share.closest('.intro').insertAdjacentElement('afterend',out);}
      out.textContent=status;
    };
    var fail=function(e){if(!(e&&e.name==='AbortError'))status='Можно скопировать адрес из строки браузера';done();};
    if(navigator.share){navigator.share({title:document.title,url:url}).then(done,fail);}
    else if(navigator.clipboard&&navigator.clipboard.writeText){navigator.clipboard.writeText(url).then(function(){status='Ссылка скопирована';done();},fail);}
    else fail(null);
  });
})();
</script>"""


def fetch(url):
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    base, dst = sys.argv[1].rstrip('/'), sys.argv[2].rstrip('/')
    h = fetch(base + '/').decode('utf-8')
    stats = {}
    # Cloudflare challenge (external script + inline bootstrap)
    h, stats['cf_script'] = re.subn(r"<script[^>]*src=['\"]/cdn-cgi/[^'\"]+['\"][^>]*>\s*</script>", '', h)
    h, stats['cf_inline'] = re.subn(r"<script>\(function\(\)\{function c\(\).*?__CF\$cv\$params.*?</script>", '', h, flags=re.S)
    # React / vinext runtime
    h, stats['module_scripts'] = re.subn(r'<script[^>]*src="/_next/static/chunks/[^"]+"[^>]*>\s*</script>', '', h)
    h, stats['modulepreload'] = re.subn(r'<link rel="modulepreload"[^>]*>', '', h)
    h, stats['rsc_bootstrap'] = re.subn(r'<script>[^<]*vinext\.navigationRuntime[^<]*</script>', '', h)
    # stylesheets -> assets/ (the origin may ship more than one CSS chunk; keep each under its own name)
    css_paths = []
    def css_link(m):
        css_paths.append(m.group(1))
        return f'<link rel="stylesheet" href="assets/{os.path.basename(m.group(1))}"/>'
    h, stats['css_links'] = re.subn(r'<link rel="stylesheet" href="(/_next/static/css/[^"]+\.css)"[^>]*/>', css_link, h)
    if not css_paths:
        sys.exit('no stylesheet link found, adjust the script')
    # photos -> relative
    photos = sorted(set(re.findall(r'(?<![\w/.:])/photos/[^"\'\s)]+', h)))
    h, stats['photo_paths'] = re.subn(r'(?<![\w/.:])/photos/', 'photos/', h)
    leftovers = re.findall(r'(?<![\w/.:])/(?:_next|cdn-cgi)/[^"\'\s)]*', h) + re.findall(r'<script[^>]*src=', h)
    if leftovers:
        sys.exit(f'unexpected references left, adjust the script: {leftovers[:5]}')
    assert h.count('</body>') == 1
    h = h.replace('</body>', CLIENT_JS + '</body>')
    # write
    for d in ('photos', 'assets'):
        shutil.rmtree(os.path.join(dst, d), ignore_errors=True)
    os.makedirs(os.path.join(dst, 'photos'), exist_ok=True)
    os.makedirs(os.path.join(dst, 'assets'), exist_ok=True)
    with open(os.path.join(dst, 'index.html'), 'w', encoding='utf-8') as f:
        f.write(h)
    for css_path in css_paths:
        with open(os.path.join(dst, 'assets', os.path.basename(css_path)), 'wb') as f:
            f.write(fetch(base + css_path))

    def grab(p):
        data = fetch(base + p)
        if data[:3] != b'\xff\xd8\xff':
            raise RuntimeError(f'{p}: not a JPEG ({data[:20]!r})')
        with open(os.path.join(dst, p.lstrip('/')), 'wb') as f:
            f.write(data)
        return len(data)
    with ThreadPoolExecutor(8) as ex:
        sizes = list(ex.map(grab, photos))
    # verify every referenced local file exists
    refs = set(re.findall(r'(?:href|src)="((?:photos|assets)/[^"]+)"', h))
    missing = [r for r in refs if not os.path.isfile(os.path.join(dst, r))]
    if missing:
        sys.exit(f'missing files after build: {missing[:5]}')
    print(f"{dst}/index.html: {len(h)} bytes; {len(photos)} photos ({sum(sizes)/1e6:.1f} MB); "
          f"css {', '.join(os.path.basename(c) for c in css_paths)}; "
          + ', '.join(f'{k}={v}' for k, v in stats.items()))
    print(f"referenced local files: {len(refs)}, all present; chatgpt.site mentions: {h.count('chatgpt.site')}")


if __name__ == '__main__':
    main()
