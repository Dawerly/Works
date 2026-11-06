/* Optional developer checks: requires Playwright and an installed Chromium browser. */
const fs = require('node:fs');
const path = require('node:path');
const http = require('node:http');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const ROOT = path.resolve(__dirname, '..');
const results = [];
const errors = [];
const localFailures = [];
let browser, server, origin;

async function check(name, task){
  try { await task(); results.push({name, status:'PASS'}); }
  catch(e){ results.push({name, status:'FAIL', detail:e.message}); }
}
async function frames(page){
  await page.evaluate(() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r))));
}
async function context(options={}){
  const ctx = await browser.newContext(options);
  await ctx.route('**/*', route => {
    const url = route.request().url();
    if(url.startsWith(origin + '/') || url.startsWith('file://')) return route.continue();
    return route.fulfill({status:204,body:''});
  });
  ctx.on('page', page => {
    page.on('pageerror', e => errors.push(e.message));
    page.on('response', response => {
      if(response.url().startsWith(origin + '/') && response.status() >= 400){
        localFailures.push({url:response.url(),status:response.status()});
      }
    });
  });
  return ctx;
}
async function confirmed(options={}){
  const ctx = await context(options);
  await ctx.addInitScript(() => { try { localStorage.setItem('dymok_age_ok','1'); } catch(e) {} });
  const page = await ctx.newPage();
  await page.goto(origin, {waitUntil:'load'});
  await frames(page);
  return {ctx,page};
}

(async () => {
  server = http.createServer((req,res) => {
    let file;
    try {
      const pathname = decodeURIComponent(new URL(req.url,'http://localhost').pathname);
      file = path.resolve(ROOT,'.' + (pathname==='/' ? '/index.html' : pathname));
      if(!file.startsWith(ROOT + path.sep)) throw Error('outside root');
      const mime = {'.html':'text/html','.css':'text/css','.js':'text/javascript','.png':'image/png','.json':'application/json'};
      const content = fs.readFileSync(file);
      res.writeHead(200,{'Content-Type':(mime[path.extname(file)]||'text/plain')+'; charset=utf-8'});
      res.end(content);
    } catch(e) { res.writeHead(404);res.end('Not found'); }
  });
  await new Promise(r => server.listen(0,'127.0.0.1',r));
  origin = 'http://127.0.0.1:' + server.address().port;
  const installedChrome = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
  const executablePath = process.env.CHROME_PATH || (fs.existsSync(installedChrome) ? installedChrome : undefined);
  browser = await chromium.launch({headless:true,executablePath});

  const manifest = JSON.parse(fs.readFileSync(path.join(ROOT,'src/manifest.json'),'utf8'));
  for(const entry of manifest.scripts){
    await check('JavaScript syntax: '+entry.file, () => {
      new vm.Script(fs.readFileSync(path.join(ROOT,entry.file),'utf8'),{filename:entry.file});
    });
  }
  await check('Combined scripts: no duplicate lexical declarations', () => {
    new vm.Script(manifest.scripts.map(e => fs.readFileSync(path.join(ROOT,e.file),'utf8')).join('\n'));
  });

  const first = await context({viewport:{width:390,height:844}});
  const gate = await first.newPage();
  await gate.goto(origin,{waitUntil:'load'});
  await check('First visit: age dialog and initial focus', async () => {
    assert(await gate.locator('#ageGate').evaluate(el => el.classList.contains('open')));
    assert.equal(await gate.evaluate(() => document.activeElement.id),'ageYes');
    assert.equal(await gate.locator('#ageGate').getAttribute('aria-hidden'),'false');
  });
  await check('Open age dialog: background is inert and scrolling locked', async () => {
    assert(await gate.locator('main').evaluate(el => el.inert));
    assert(await gate.locator('header').evaluate(el => el.inert));
    assert(await gate.locator('footer').evaluate(el => el.inert));
    assert.equal(await gate.evaluate(() => document.body.style.overflow),'hidden');
  });
  await check('Age dialog: Tab wraps forward', async () => {
    await gate.keyboard.press('Tab');
    assert.equal(await gate.evaluate(() => document.activeElement.id),'ageNo');
    await gate.keyboard.press('Tab');
    assert.equal(await gate.evaluate(() => document.activeElement.id),'ageYes');
  });
  await check('Age dialog: Shift+Tab wraps backward', async () => {
    await gate.keyboard.press('Shift+Tab');
    assert.equal(await gate.evaluate(() => document.activeElement.id),'ageNo');
  });
  await check('Age dialog: background cannot receive focus', async () => {
    await gate.locator('header .logo').evaluate(el => el.focus());
    assert(await gate.evaluate(() => document.getElementById('ageGate').contains(document.activeElement)));
  });
  await check('Escape does not dismiss required age dialog', async () => {
    await gate.keyboard.press('Escape');
    assert(await gate.locator('#ageGate').evaluate(el => el.classList.contains('open')));
  });
  await check('Confirm age: restore background, scrolling and content focus', async () => {
    await gate.locator('#ageYes').click();
    assert.equal(await gate.locator('#ageGate').getAttribute('aria-hidden'),'true');
    assert.equal(await gate.locator('main').evaluate(el => el.inert),false);
    assert.equal(await gate.evaluate(() => document.body.style.overflow),'');
    assert.equal(await gate.evaluate(() => document.activeElement.tagName),'H1');
    assert.equal(await gate.evaluate(() => localStorage.getItem('dymok_age_ok')),'1');
  });
  await check('Reload: saved age confirmation retained', async () => {
    await gate.reload({waitUntil:'load'});
    assert.equal(await gate.locator('#ageGate').evaluate(el => el.classList.contains('open')),false);
  });
  await first.close();

  const {ctx,page} = await confirmed({viewport:{width:1440,height:900}});
  await check('Main landmark, navigation labels and unique IDs', async () => {
    assert.equal(await page.locator('main').count(),1);
    assert.equal(await page.locator('nav:not([aria-label])').count(),0);
    const ids = await page.locator('[id]').evaluateAll(els=>els.map(el=>el.id));
    assert.equal(new Set(ids).size,ids.length);
  });
  await check('All static images have alternative text and local logos have sizes', async () => {
    assert.equal(await page.locator('img:not([alt])').count(),0);
    const logos = await page.locator('img[src="logo.png"]').evaluateAll(els => els.map(el => ({w:el.width,h:el.height,loaded:el.complete&&el.naturalWidth>0})));
    assert(logos.every(el=>el.w>0&&el.h>0&&el.loaded));
  });
  await check('Stylesheets loaded and usability overrides applied', async () => {
    assert.equal(await page.evaluate(() => [...document.styleSheets].filter(s=>s.href&&s.href.includes('/assets/css/')).length),15);
    assert.equal(await page.locator('.skip-link').evaluate(el=>getComputedStyle(el).position),'fixed');
  });
  await check('Desktop navigation: home marked current', async () => {
    assert.equal(await page.locator('#navLinks [aria-current="page"]').getAttribute('data-nav'),'home');
  });
  await check('Desktop navigation: account route and heading focus', async () => {
    await page.locator('#navLinks [data-nav="cabinet"]').click();
    await page.waitForFunction(()=>document.querySelector('.page.active').id==='page-cabinet');
    assert.equal(await page.locator('#navLinks [aria-current="page"]').getAttribute('data-nav'),'cabinet');
    assert(await page.evaluate(()=>document.querySelector('#page-cabinet').contains(document.activeElement)));
  });
  await check('Skip link preserves current page and focuses main', async () => {
    const hash = new URL(page.url()).hash;
    await page.locator('#skipLink').focus();
    await page.keyboard.press('Enter');
    assert.equal(await page.evaluate(()=>document.activeElement.id),'main-content');
    assert.equal(new URL(page.url()).hash,hash);
  });
  await check('Logo is a keyboard-operable home link', async () => {
    await page.locator('header .logo').focus();
    await page.keyboard.press('Enter');
    await page.waitForFunction(()=>document.querySelector('.page.active').id==='page-home');
  });
  await check('Unknown route safely falls back to home', async () => {
    await page.evaluate(()=>location.hash='unknown');
    await frames(page);
    assert.equal(await page.locator('.page.active').getAttribute('id'),'page-home');
    assert.equal(await page.locator('#navLinks [aria-current="page"]').getAttribute('data-nav'),'home');
  });

  for(const width of [320,360,390,480,600,760,768,820,1024,1100,1440,1920]){
    await check('Responsive home and header at '+width+' px', async () => {
      await page.setViewportSize({width,height:900});
      await frames(page);
      const layout = await page.evaluate(() => {
        const visible = el => el.getClientRects().length && getComputedStyle(el).visibility!=='hidden';
        return {
          scrollWidth:document.documentElement.scrollWidth,
          width:innerWidth,
          header:[...document.querySelectorAll('header .logo,header .nav-links,header .header-actions')].filter(visible).map(el=>({left:el.getBoundingClientRect().left,right:el.getBoundingClientRect().right})),
          bottomNav:getComputedStyle(document.querySelector('.mobile-nav')).display
        };
      });
      assert(layout.scrollWidth<=width+1,JSON.stringify(layout));
      assert(layout.header.every(r=>r.left>=-1&&r.right<=width+1),JSON.stringify(layout));
      assert.equal(layout.bottomNav==='none',width>760);
    });
  }
  await check('Mobile touch targets: navigation links at least 44 px', async () => {
    await page.setViewportSize({width:390,height:844});
    const sizes = await page.locator('.mobile-nav a').evaluateAll(els=>els.map(el=>({w:el.getBoundingClientRect().width,h:el.getBoundingClientRect().height})));
    assert(sizes.every(s=>s.w>=44&&s.h>=44));
  });
  await check('Mobile navigation: current item and account route', async () => {
    await page.locator('.mobile-nav [data-nav="cabinet"]').click();
    await page.waitForFunction(()=>document.querySelector('.page.active').id==='page-cabinet');
    assert.equal(await page.locator('.mobile-nav [aria-current="page"]').getAttribute('data-nav'),'cabinet');
  });
  await check('Keyboard focus outline remains visible', async () => {
    await page.locator('.mobile-nav [data-nav="home"]').focus();
    await page.keyboard.press('Tab');
    const outline=await page.evaluate(()=>({style:getComputedStyle(document.activeElement).outlineStyle,width:parseFloat(getComputedStyle(document.activeElement).outlineWidth)}));
    assert.equal(outline.style,'solid');assert(outline.width>=2);
  });
  await check('Privacy disclosure works with keyboard', async () => {
    await page.locator('.privacy-info summary').focus();
    await page.keyboard.press('Enter');
    assert(await page.locator('.privacy-info').evaluate(el=>el.open));
    await page.keyboard.press('Enter');
    assert.equal(await page.locator('.privacy-info').evaluate(el=>el.open),false);
  });
  await check('Back-to-top: shows on scroll and returns focus to main', async () => {
    await page.locator('.mobile-nav [data-nav="home"]').click();
    await page.waitForFunction(()=>document.querySelector('.page.active').id==='page-home');
    await page.evaluate(()=>scrollTo(0,1000));
    await page.waitForFunction(()=>!document.getElementById('backToTop').hidden);
    await page.locator('#backToTop').click();
    await page.waitForFunction(()=>scrollY===0,{},{timeout:5000});
    assert.equal(await page.evaluate(()=>document.activeElement.id),'main-content');
    await frames(page);
    assert(await page.locator('#backToTop').evaluate(el=>el.hidden));
  });
  await check('Header measurement updates after resize', async () => {
    const measured=await page.locator('header').evaluate(el=>Math.ceil(el.getBoundingClientRect().height));
    const value=await page.evaluate(()=>parseInt(getComputedStyle(document.documentElement).getPropertyValue('--site-header-height')));
    assert.equal(value,measured);
  });
  await check('Home reflows at 200% text size', async () => {
    await page.setViewportSize({width:768,height:900});
    await page.evaluate(()=>document.documentElement.style.fontSize='200%');
    await frames(page);
    const overflow=await page.locator('#page-home h1,header .logo,header .nav-links,header .header-actions').evaluateAll(els=>els.filter(el=>el.getClientRects().length).map(el=>({right:el.getBoundingClientRect().right,width:el.clientWidth,scroll:el.scrollWidth})));
    await page.evaluate(()=>document.documentElement.style.fontSize='');
    assert(overflow.every(el=>el.right<=769&&el.scroll<=el.width+1),JSON.stringify(overflow));
  });
  await page.setViewportSize({width:1440,height:900});
  await page.reload({waitUntil:'load'});
  await frames(page);
  await page.screenshot({path:path.join(ROOT,'tests/desktop.png'),animations:'disabled'});
  await page.setViewportSize({width:390,height:844});
  await page.reload({waitUntil:'load'});
  await frames(page);
  await page.screenshot({path:path.join(ROOT,'tests/mobile.png'),animations:'disabled'});
  await ctx.close();

  const blocked = await context({viewport:{width:320,height:568}});
  await blocked.addInitScript(()=>{
    Object.defineProperty(window,'localStorage',{get(){throw new DOMException('Storage denied','SecurityError');}});
  });
  const denied=await blocked.newPage();
  await check('Unavailable localStorage: age dialog still works', async () => {
    await denied.goto(origin,{waitUntil:'load'});
    assert(await denied.locator('#ageGate').evaluate(el=>el.classList.contains('open')));
    await denied.locator('#ageYes').click();
    assert.equal(await denied.locator('#ageGate').evaluate(el=>el.classList.contains('open')),false);
    assert.equal(await denied.locator('main').evaluate(el=>el.inert),false);
  });
  await blocked.close();

  const short=await context({viewport:{width:812,height:320}});
  const landscape=await short.newPage();
  await check('Short landscape viewport: age controls remain reachable', async () => {
    await landscape.goto(origin,{waitUntil:'load'});
    await landscape.locator('#ageNo').focus();
    const rect=await landscape.locator('#ageNo').boundingBox();
    assert(rect.y>=0&&rect.y+rect.height<=320);
  });
  await short.close();

  const reduce=await confirmed({viewport:{width:390,height:844},reducedMotion:'reduce'});
  await check('Reduced motion preference: animations reduced', async () => {
    const duration=await reduce.page.locator('.logo-mark').first().evaluate(el=>getComputedStyle(el).animationDuration);
    assert(parseFloat(duration)<=0.01);
    assert.equal(await reduce.page.evaluate(()=>getComputedStyle(document.documentElement).scrollBehavior),'auto');
  });
  await reduce.ctx.close();

  const nojs=await context({javaScriptEnabled:false});
  const disabled=await nojs.newPage();
  await check('JavaScript disabled: visible explanation', async () => {
    await disabled.goto(origin,{waitUntil:'load'});
    assert(await disabled.locator('.noscript-note').isVisible());
  });
  await nojs.close();

  const local=await context({viewport:{width:390,height:844}});
  const direct=await local.newPage();
  await check('Double-click file:// opening: scripts, styles and age dialog load', async () => {
    await direct.goto('file://'+path.join(ROOT,'index.html'),{waitUntil:'load'});
    assert(await direct.locator('#ageGate').evaluate(el=>el.classList.contains('open')));
    await direct.locator('#ageYes').click();
    assert.equal(await direct.locator('.page.active').getAttribute('id'),'page-home');
    assert.equal(await direct.locator('.skip-link').evaluate(el=>getComputedStyle(el).position),'fixed');
  });
  await local.close();

  await check('No uncaught JavaScript errors during the tested scenarios', ()=>assert.deepEqual(errors,[]));
  await check('No failed local resource requests', ()=>assert.deepEqual(localFailures,[]));
  const report={date:new Date().toISOString(),browser:browser.version(),network:'External requests replaced by empty responses; no live transactions.',results,passed:results.filter(r=>r.status==='PASS').length,failed:results.filter(r=>r.status==='FAIL').length};
  fs.writeFileSync(path.join(ROOT,'tests/browser-results.json'),JSON.stringify(report,null,2)+'\n');
  console.log(JSON.stringify(report,null,2));
  process.exitCode=report.failed ? 1 : 0;
})().catch(e=>{console.error(e);process.exitCode=1;}).finally(async()=>{
  if(browser) await browser.close();
  if(server) await new Promise(r=>server.close(r));
});
