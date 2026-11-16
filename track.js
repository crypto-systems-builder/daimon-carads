/* Ad attribution without a backend.
   Reads where the visitor came from (utm_* in the address) and which package they
   picked, and writes both into the email they send. Nothing is stored on the device.
   The Meta pixel loads only when PIXEL_ID is set and the visitor accepts. */
(function () {
  var PIXEL_ID = ''; // Meta pixel id, digits only. Empty: no pixel, no banner.

  var q = new URLSearchParams(location.search), src = {};
  ['utm_source', 'utm_medium', 'utm_campaign', 'utm_content'].forEach(function (k) {
    var v = (q.get(k) || '').replace(/[^\w.\-]/g, '').slice(0, 40);
    if (v) src[k] = v;
  });
  var ref = [src.utm_source, src.utm_campaign, src.utm_content].filter(Boolean).join('/');
  var nl = document.documentElement.lang === 'nl';
  var pkg = '';

  function send(name, data) { if (window.fbq) window.fbq('track', name, data || {}); }

  function mailHref() {
    var subject = (nl ? 'Aanvraag filmische auto-ad' : 'Cinematic car ad request') + (pkg ? ' - ' + pkg : '');
    var body = nl
      ? 'Hoi Daimon Media,\n\nIk wil graag een filmische ad van mijn auto.\nPakket: ' + (pkg || '(nog niet gekozen)') + '\nLink of foto van de auto: \n'
      : 'Hi Daimon Media,\n\nI would like a cinematic ad of my car.\nPackage: ' + (pkg || '(not chosen yet)') + '\nLink or photo of the car: \n';
    if (ref) body += '\n[ref: ' + ref + ']';
    return 'mailto:jonathan@daimonmedia.com?subject=' + encodeURIComponent(subject) + '&body=' + encodeURIComponent(body);
  }

  var mails = document.querySelectorAll('a[href^="mailto:"]');
  function refreshMail() { mails.forEach(function (a) { a.href = mailHref(); }); }
  refreshMail();

  document.querySelectorAll('a.card[data-pkg]').forEach(function (card) {
    card.addEventListener('click', function () {
      pkg = card.getAttribute('data-pkg');
      refreshMail();
      send('ViewContent', { content_name: pkg });
    });
  });
  mails.forEach(function (a) {
    a.addEventListener('click', function () { send('Contact', { method: 'email', content_name: pkg }); });
  });
  document.querySelectorAll('a[href*="instagram.com"]').forEach(function (a) {
    a.addEventListener('click', function () { send('Contact', { method: 'instagram', content_name: pkg }); });
  });

  // Keep the campaign tags when the visitor switches language.
  var keep = new URLSearchParams(src).toString();
  if (keep) document.querySelectorAll('a[href*="lang="]').forEach(function (a) { a.href += '&' + keep; });

  if (!/^\d+$/.test(PIXEL_ID)) return;
  function loadPixel() {
    !function (f, b, e, v, n, t, s) { if (f.fbq) return; n = f.fbq = function () { n.callMethod ? n.callMethod.apply(n, arguments) : n.queue.push(arguments); }; if (!f._fbq) f._fbq = n; n.push = n; n.loaded = !0; n.version = '2.0'; n.queue = []; t = b.createElement(e); t.async = !0; t.src = v; s = b.getElementsByTagName(e)[0]; s.parentNode.insertBefore(t, s); }(window, document, 'script', 'https://connect.facebook.net/en_US/fbevents.js');
    window.fbq('init', PIXEL_ID);
    window.fbq('track', 'PageView');
  }
  var choice = null;
  try { choice = localStorage.getItem('dm_consent'); } catch (e) {}
  if (choice === 'yes') return loadPixel();
  if (choice === 'no') return;
  var bar = document.createElement('div');
  bar.setAttribute('role', 'dialog');
  bar.style.cssText = 'position:fixed;left:12px;right:12px;bottom:12px;z-index:50;background:#15171d;border:1px solid #262a33;border-radius:14px;padding:14px 16px;color:#f3f4f6;font-size:14px;display:flex;gap:12px;align-items:center;flex-wrap:wrap';
  var text = document.createElement('span');
  text.style.flex = '1 1 220px';
  text.textContent = nl ? 'Mogen we meten welke advertentie je hier bracht? Daarvoor gebruiken we een Meta-pixel.' : 'May we measure which ad brought you here? We use a Meta pixel for that.';
  bar.appendChild(text);
  [['yes', nl ? 'Akkoord' : 'Accept'], ['no', nl ? 'Liever niet' : 'No thanks']].forEach(function (o) {
    var btn = document.createElement('button');
    btn.textContent = o[1];
    btn.style.cssText = 'border:1px solid #262a33;border-radius:999px;padding:8px 14px;font-weight:700;cursor:pointer;' + (o[0] === 'yes' ? 'background:#c9a24b;color:#15120a' : 'background:transparent;color:#f3f4f6');
    btn.addEventListener('click', function () {
      try { localStorage.setItem('dm_consent', o[0]); } catch (e) {}
      bar.remove();
      if (o[0] === 'yes') loadPixel();
    });
    bar.appendChild(btn);
  });
  document.body.appendChild(bar);
})();
