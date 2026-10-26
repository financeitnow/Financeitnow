const DEALER_PREVIEWS = {
  '1stlinemotors.netlify.app': {
    dealerId: '10040797',
    title: '1ST LINE MOTORS LTD | Find Your Next Car',
    description: 'Browse our latest used cars.',
    dealerName: '1ST LINE MOTORS LTD',
    dealerAddress: '617 Great Horton Road, Bradford, England, BD7 4ED',
    image: 'https://m.atcdn.co.uk/a/media/w1024/b513e6ecdba844e98644a823a3f751a4.jpg',
  },
};

function escapeHtmlAttribute(value) {
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/"/g, '&quot;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

function replaceMetaContent(html, attribute, value) {
  const pattern = new RegExp(`(<meta\\s+${attribute}\\s+content=")[^"]*(">)`, 'i');
  return html.replace(pattern, (_, before, after) => `${before}${escapeHtmlAttribute(value)}${after}`);
}

function replaceLinkById(html, id, href, label) {
  const pattern = new RegExp(`(<a\\b[^>]*\\bid="${id}"[^>]*>)[\\s\\S]*?(<\\/a>)`, 'i');
  return html.replace(pattern, (_, opening, closing) => {
    const updatedOpening = opening.replace(/\bhref="[^"]*"/i, `href="${escapeHtmlAttribute(href)}"`);
    return `${updatedOpening}${escapeHtmlAttribute(label)}${closing}`;
  });
}

async function dealerWhatsAppPhone(origin, preview) {
  let phone = '07506301308';
  try {
    const response = await fetch(new URL('/data/dealers/phone-index.json', origin));
    if (response.ok) {
      const phoneIndex = await response.json();
      phone = phoneIndex[preview.dealerId] || phone;
    }
  } catch (_) {
    // Keep the default number if the dealer phone index is unavailable.
  }
  const digits = String(phone).replace(/\D/g, '');
  return digits.startsWith('0') ? `44${digits.slice(1)}` : digits;
}

export default async (request, context) => {
  const url = new URL(request.url);
  const preview = DEALER_PREVIEWS[url.hostname.toLowerCase()];
  if (!preview) return context.next();
  if (request.method !== 'GET') return context.next();
  if (url.pathname !== '/') return Response.redirect(new URL('/', url), 302);

  const response = await context.next();
  if (!response.headers.get('content-type')?.includes('text/html')) return response;

  let html = await response.text();
  const whatsAppHref = `whatsapp://send?phone=${await dealerWhatsAppPhone(url.origin, preview)}`;
  const dealerFooter = `<footer class="dealer-site-footer"><p>${escapeHtmlAttribute(preview.dealerName)}</p><p>${escapeHtmlAttribute(preview.dealerAddress)}</p><p>Contact the dealer to confirm vehicle details and availability.</p></footer>`;
  html = html.replace(/<footer\b[^>]*>[\s\S]*?<\/footer>/i, dealerFooter);
  html = html.replace(/<title>[\s\S]*?<\/title>/i, `<title>${escapeHtmlAttribute(preview.title)}</title>`);
  html = html.replace(/(<h2\b[^>]*class="finance-title"[^>]*>)[\s\S]*?(<\/h2>)/i, (_, opening, closing) => `${opening}Finance Calculator${closing}`);
  html = replaceMetaContent(html, 'property="og:site_name"', preview.dealerName);
  html = replaceMetaContent(html, 'name="description"', preview.description);
  html = replaceMetaContent(html, 'property="og:title"', preview.title);
  html = replaceMetaContent(html, 'property="og:description"', preview.description);
  html = replaceMetaContent(html, 'property="og:image"', preview.image);
  html = replaceMetaContent(html, 'property="og:image:type"', 'image/jpeg');
  html = replaceMetaContent(html, 'property="og:image:alt"', `${preview.dealerName} vehicle stock`);
  html = replaceMetaContent(html, 'name="twitter:title"', preview.title);
  html = replaceMetaContent(html, 'name="twitter:description"', preview.description);
  html = replaceMetaContent(html, 'name="twitter:image"', preview.image);
  html = html.replace(/\s*<meta property="og:image:(?:width|height)" content="[^"]*">/gi, '');
  html = html.replace(/<link rel="icon"[^>]*>/i, '');
  for (const id of ['getQuote', 'modalGetQuote', 'getQuoteSheet']) {
    html = replaceLinkById(html, id, whatsAppHref, 'Enquire on WhatsApp');
  }

  const headers = new Headers(response.headers);
  headers.delete('content-length');
  headers.delete('content-encoding');
  headers.delete('etag');

  return new Response(html, {
    status: response.status,
    statusText: response.statusText,
    headers,
  });
};
