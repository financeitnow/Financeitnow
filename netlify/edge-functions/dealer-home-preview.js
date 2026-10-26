const firstLinePreview = {
  dealerId: '10040797',
  title: '1ST LINE MOTORS LTD | Find Your Next Car',
  description: 'Import vehicle specialists. Part exchange. Finance available.',
  dealerName: '1ST LINE MOTORS LTD',
  dealerAddress: '617 Great Horton Road, Bradford, England, BD7 4ED',
  companyNumber: '17038277',
  companyType: 'Private limited company',
  companiesHouseUrl: 'https://find-and-update.company-information.service.gov.uk/company/17038277',
};
const DEALER_PREVIEWS = {
  '1stlinemotors.netlify.app': firstLinePreview,
  '1stlinemotors.com': firstLinePreview,
  'www.1stlinemotors.com': firstLinePreview,
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
  if (!['/', '/index', '/index.html'].includes(url.pathname)) {
    return Response.redirect(new URL('/', url), 302);
  }

  const response = await context.next();
  if (!response.headers.get('content-type')?.includes('text/html')) return response;

  let html = await response.text();
  const whatsAppHref = `whatsapp://send?phone=${await dealerWhatsAppPhone(url.origin, preview)}`;
  const previewImage = new URL('/1stline-logo.svg', url.origin).toString();
  const financeLogo = /FinanceIt<a class=\\?"n-icon\\?"><img src=\\?"netlifyicon3\.png\\?" alt=\\?"N\\?" \/><\/a>OW!/g;
  html = html.replace(financeLogo, escapeHtmlAttribute(preview.dealerName));
  const dealerFooter = `<footer class="dealer-site-footer"><p><strong>${escapeHtmlAttribute(preview.dealerName)}</strong></p><p>${escapeHtmlAttribute(preview.companyType)} registered in England and Wales. Company number <a href="${escapeHtmlAttribute(preview.companiesHouseUrl)}">${escapeHtmlAttribute(preview.companyNumber)}</a>.</p><p>Registered office: ${escapeHtmlAttribute(preview.dealerAddress)}</p><p>Vehicle details and availability should be confirmed with the dealer.</p></footer>`;
  html = html.replace(/<footer\b[^>]*>[\s\S]*?<\/footer>/i, dealerFooter);
  html = html.replace(/<title>[\s\S]*?<\/title>/i, `<title>${escapeHtmlAttribute(preview.title)}</title>`);
  html = html.replace(/(<h2\b[^>]*class="finance-title"[^>]*>)[\s\S]*?(<\/h2>)/i, (_, opening, closing) => `${opening}Finance Calculator${closing}`);
  html = replaceMetaContent(html, 'property="og:site_name"', preview.dealerName);
  html = replaceMetaContent(html, 'name="description"', preview.description);
  html = replaceMetaContent(html, 'property="og:title"', preview.title);
  html = replaceMetaContent(html, 'property="og:description"', preview.description);
  html = replaceMetaContent(html, 'property="og:image"', previewImage);
  html = replaceMetaContent(html, 'property="og:image:type"', 'image/svg+xml');
  html = replaceMetaContent(html, 'property="og:image:alt"', `${preview.dealerName} vehicle stock`);
  html = replaceMetaContent(html, 'name="twitter:title"', preview.title);
  html = replaceMetaContent(html, 'name="twitter:description"', preview.description);
  html = replaceMetaContent(html, 'name="twitter:image"', previewImage);
  html = html.replace(/\s*<meta property="og:image:(?:width|height)" content="[^"]*">/gi, '');
  html = html.replace(/<link rel="icon"[^>]*>/i, '<link rel="icon" type="image/svg+xml" href="/1stline-mark.svg">');
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
