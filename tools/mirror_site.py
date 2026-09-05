#!/usr/bin/env python3
"""Mirror a chatgpt.site page into a self-contained static folder for GitHub Pages.

    python3 tools/mirror_site.py https://uchastki-pod-minskom.alexautorental.chatgpt.site/ public/uchastki

chatgpt.site (OpenAI hosting) is unreachable from Russia/Belarus without a VPN, GitHub Pages is.
The server-rendered HTML is kept verbatim; what changes:
  - the React/vinext runtime (module scripts, modulepreloads, RSC bootstrap) and the Cloudflare
    challenge script are dropped -- the page needs neither once it is static;
  - stylesheets move to assets/, photos to photos/, all paths become relative so the page
    works under any sub-path (GitHub Pages serves the repo at /panamera-studio/);
  - the origin's `Link: <photo>; rel=preload` response header becomes a <link rel=preload> tag;
  - a small inline script re-creates the page's only client behaviour: photo-strip prev/next
    buttons with the "1 / 3" counter, the Share button (navigator.share / clipboard) and, like the
    origin's router, manual scroll restoration that re-scrolls to the #hash on back/forward.
The folder is built in <dst>.build and swapped in only when every file is present, so a failed
run never leaves a half-built page. Re-run after the source site changes.
"""
import os, re, shutil, sys, time, urllib.request
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
    strip.addEventListener('scroll',function(){
      var i=Math.round(strip.scrollLeft/(strip.clientWidth||1));
      if(i===idx)return;
      idx=i;counter.textContent=(idx+1)+' / '+n;prev.disabled=idx===0;next.disabled=idx===n-1;
    },{passive:true});
    function go(d){strip.scrollTo({left:Math.min(n-1,Math.max(0,idx+d))*strip.clientWidth,behavior:'smooth'});}
    prev.addEventListener('click',function(){go(-1);});
    next.addEventListener('click',function(){go(1);});
  });
  if('scrollRestoration' in history)history.scrollRestoration='manual';
  window.addEventListener('popstate',function(){
    var id=location.hash.slice(1),el=id&&document.getElementById(decodeURIComponent(id));
    if(el)el.scrollIntoView();
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
    try{
      if(navigator.share){navigator.share({title:document.title,url:url}).then(done,fail);}
      else if(navigator.clipboard&&navigator.clipboard.writeText){navigator.clipboard.writeText(url).then(function(){status='Ссылка скопирована';done();},fail);}
      else fail(null);
    }catch(e){fail(e);}
  });
})();
</script>"""


def fetch(url, attempts=3):
    """GET url through the environment's proxy settings; returns (bytes, headers)."""
    for i in range(attempts):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': UA})
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read(), r.headers
        except Exception as e:  # noqa: BLE001 - retry any transport error, re-raise the last one
            if i == attempts - 1:
                raise RuntimeError(f'{url}: {e}') from e
            time.sleep(2 ** i)


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    base, dst = sys.argv[1].rstrip('/'), sys.argv[2].rstrip('/')
    raw, headers = fetch(base + '/')
    h = raw.decode('utf-8')
    stats = {}
    # Cloudflare challenge (external script + inline bootstrap)
    h, stats['cf_script'] = re.subn(r"<script[^>]*src=['\"]/cdn-cgi/[^'\"]+['\"][^>]*>\s*</script>", '', h)
    h, stats['cf_inline'] = re.subn(r"<script>\(function\(\)\{function c\(\).*?__CF\$cv\$params.*?</script>", '', h, flags=re.S)
    # React / vinext runtime
    h, stats['module_scripts'] = re.subn(r'<script[^>]*src="/_next/static/chunks/[^"]+"[^>]*>\s*</script>', '', h)
    h, stats['modulepreload'] = re.subn(r'<link rel="modulepreload"[^>]*>', '', h)
    h, stats['rsc_bootstrap'] = re.subn(r'<script>[^<]*vinext\.navigationRuntime[^<]*</script>', '', h)
    leftover_scripts = re.findall(r'<script[^>]*>.{0,120}', h, flags=re.S)
    if leftover_scripts:
        sys.exit(f'unexpected <script> left after stripping the runtime, adjust the script: {leftover_scripts[:3]}')
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
    # the origin preloads the hero photo via a Link response header; keep that as a tag
    preloads = [p for p in re.findall(r'<(/photos/[^>]+)>;\s*rel=preload;\s*as="?image"?', headers.get('link', ''))]
    if preloads:
        tags = ''.join(f'<link rel="preload" as="image" href="{p.lstrip("/")}"/>' for p in preloads)
        h = h.replace('<link rel="stylesheet"', tags + '<link rel="stylesheet"', 1)
    stats['preload_tags'] = len(preloads)
    # nothing root-absolute may remain: it would resolve against github.io/ instead of the page folder
    leftovers = re.findall(r'(?:href|src|poster|srcset)="/(?!/)[^"]*"', h) + re.findall(r'url\(["\']?/(?!/)[^)]*\)', h)
    if leftovers:
        sys.exit(f'root-absolute references left, adjust the script: {leftovers[:5]}')
    assert h.count('</body>') == 1
    h = h.replace('</body>', CLIENT_JS + '</body>')
    # build into a temp folder, swap in when complete
    tmp = dst + '.build'
    shutil.rmtree(tmp, ignore_errors=True)
    os.makedirs(os.path.join(tmp, 'photos'))
    os.makedirs(os.path.join(tmp, 'assets'))
    with open(os.path.join(tmp, 'index.html'), 'w', encoding='utf-8') as f:
        f.write(h)
    for css_path in css_paths:
        with open(os.path.join(tmp, 'assets', os.path.basename(css_path)), 'wb') as f:
            f.write(fetch(base + css_path)[0])

    def grab(p):
        data = fetch(base + p)[0]
        if data[:3] != b'\xff\xd8\xff':
            raise RuntimeError(f'{p}: not a JPEG ({data[:20]!r})')
        with open(os.path.join(tmp, p.lstrip('/')), 'wb') as f:
            f.write(data)
        return len(data)
    with ThreadPoolExecutor(8) as ex:
        sizes = list(ex.map(grab, photos))
    # verify every referenced local file exists, then swap
    refs = set(re.findall(r'(?:href|src)="((?:photos|assets)/[^"]+)"', h))
    missing = [r for r in refs if not os.path.isfile(os.path.join(tmp, r))]
    if missing:
        sys.exit(f'missing files after build: {missing[:5]}')
    shutil.rmtree(dst, ignore_errors=True)
    os.replace(tmp, dst)
    print(f"{dst}/index.html: {len(h)} bytes; {len(photos)} photos ({sum(sizes)/1e6:.1f} MB); "
          f"css {', '.join(os.path.basename(c) for c in css_paths)}; "
          + ', '.join(f'{k}={v}' for k, v in stats.items()))
    print(f"referenced local files: {len(refs)}, all present; chatgpt.site mentions: {h.count('chatgpt.site')}")


if __name__ == '__main__':
    main()
