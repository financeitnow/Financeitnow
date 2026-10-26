const DEALER_PREVIEWS = {
  '1stlinemotors.netlify.app': {
    title: '1ST LINE MOTORS LTD | Find Your Next Car',
    description: 'Browse our latest used cars.',
    dealerName: '1ST LINE MOTORS LTD',
    dealerAddress: '617 Great Horton Road, Bradford, England, BD7 4ED',
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

export default async (request, context) => {
  const preview = DEALER_PREVIEWS[new URL(request.url).hostname.toLowerCase()];
  if (!preview || request.method !== 'GET') return context.next();

  const response = await context.next();
  if (!response.headers.get('content-type')?.includes('text/html')) return response;

  let html = await response.text();
  const dealerFooter = `<footer class="dealer-site-footer"><p>${escapeHtmlAttribute(preview.dealerName)}</p><p>${escapeHtmlAttribute(preview.dealerAddress)}</p><p>Contact the dealer to confirm vehicle details and availability.</p></footer>`;
  html = html.replace(/<footer\b[^>]*>[\s\S]*?<\/footer>/i, dealerFooter);
  html = html.replace(/<title>[\s\S]*?<\/title>/i, `<title>${escapeHtmlAttribute(preview.title)}</title>`);
  html = replaceMetaContent(html, 'name="description"', preview.description);
  html = replaceMetaContent(html, 'property="og:title"', preview.title);
  html = replaceMetaContent(html, 'property="og:description"', preview.description);
  html = replaceMetaContent(html, 'name="twitter:title"', preview.title);
  html = replaceMetaContent(html, 'name="twitter:description"', preview.description);

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
