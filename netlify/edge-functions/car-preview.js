/**
 * Netlify Edge Function: car-preview
 * Handles /car/:carId paths.
 * 
 * - WhatsApp / link-preview bots get a page with Open Graph meta tags
 *   (car image, title, price, description) so the preview looks great.
 * - Real visitors are instantly redirected into the main app with ?car=ID
 *   so it opens the card view for that specific car.
 */
function formatPreviewMileage(value) {
  const normalized = String(value ?? '').replace(/,/g, '').trim();
  const mileage = parseFloat(normalized) * (/^\d+(?:\.\d+)?\s*k\b/i.test(normalized) ? 1000 : 1);
  if (!Number.isFinite(mileage) || mileage < 0) return null;
  return `${(mileage / 1000).toLocaleString('en-GB', { maximumFractionDigits: 1 })}K miles`;
}

export default async (request, context) => {
  const url = new URL(request.url);
  const hostname = url.hostname.toLowerCase();
  const isDealerHost = ['1stlinemotors.netlify.app', '1stlinemotors.com', 'www.1stlinemotors.com'].includes(hostname);
  const dataOrigin = isDealerHost ? 'https://1stlinemotors.netlify.app' : url.origin;

  // Extract car ID from path  e.g. /car/ABC123  → "ABC123"
  const rawId = url.pathname.split('/car/')[1] ?? '';
  const carId = decodeURIComponent(rawId.replace(/\/$/, '').trim());

  // Fallback URL: main app root
  const appBase = new URL('/index.html', url.origin).toString();

  if (!carId) {
    return Response.redirect(appBase, 302);
  }

  // Resolve the car via the chunk index (car_id -> chunk number) so we only
  // fetch the one chunk containing this car, instead of the whole dataset.
  let car = null;
  try {
    const indexResp = await fetch(new URL('/data/cars/index.json', dataOrigin).toString());
    if (indexResp.ok) {
      const index = await indexResp.json();
      const chunkNumber = index[carId];
      if (chunkNumber) {
        const chunkResp = await fetch(new URL(`/data/cars/c${chunkNumber}.json`, dataOrigin).toString());
        if (chunkResp.ok) {
          const cars = await chunkResp.json();
          car = cars.find(c => String(c.car_id) === carId);
        }
      }
    }
  } catch (_) {
    // silently fall through to redirect
  }

  if (!car) {
    const carAppUrl = new URL(appBase);
    carAppUrl.searchParams.set('car', carId);
    return Response.redirect(carAppUrl, 302);
  }

  // Build the app deep-link that opens just this car
  const appUrl = new URL(
    `/index.html?car=${encodeURIComponent(car.car_id)}`,
    url.origin
  ).toString();

  // ── Build OG content ──────────────────────────────────────────────────────
  const isFinanceItNowSite = hostname === 'financeitnow.netlify.app';
  const price = (parseInt(car.price) || 0) + (isFinanceItNowSite ? 300 : 0);
  const yearStr = car.year_reg || car.year || '';
  const isUnknown = (v) =>
    !v || ['unknown', 'n/a', ''].includes(String(v).trim().toLowerCase());

  const siteName = isFinanceItNowSite ? 'FinanceItNOW' : (car.dealer_name || 'the dealer');
  const title =
    [yearStr, car.make, car.model].filter(Boolean).join(' ') +
    ` — £${price.toLocaleString()} | ${siteName}`;

  const details = [
    !isUnknown(car.mileage)
      ? formatPreviewMileage(car.mileage)
      : null,
    car.Gearbox || car.gearbox || null,
    car.fuel_type || null,
    car.body_type || null,
  ]
    .filter(Boolean)
    .join(' · ');

  const availability = isFinanceItNowSite
    ? 'Available now on Flexible Finance at FinanceItNOW.'
    : 'Import vehicle specialists. Part exchange. Finance available.';
  const description = details ? `${details}\n\n${availability}` : availability;

  // First non-empty image URL
  const imagePath = (Array.isArray(car.images) && car.images.find((image) => typeof image === 'string' && image.trim())) || '';
  const image = imagePath ? new URL(imagePath, url.origin).toString() : '';

  // Escape helper (prevents HTML injection from scraped car data)
  const e = (s) =>
    String(s)
      .replace(/&/g, '&amp;')
      .replace(/"/g, '&quot;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');

  // ── Return OG page with instant JS redirect for real visitors ─────────────
  const html = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>${e(title)}</title>
  <meta name="description" content="${e(description)}">

  <!-- Open Graph (WhatsApp, Facebook, etc.) -->
  <meta property="og:type"        content="website">
  <meta property="og:url"         content="${e(url.href)}">
  <meta property="og:title"       content="${e(title)}">
  <meta property="og:description" content="${e(description)}">
  <meta property="og:site_name"   content="${e(siteName)}">
  ${image ? `<meta property="og:image" content="${e(image)}">
  ${isFinanceItNowSite ? '<meta property="og:image:width" content="1200"><meta property="og:image:height" content="630">' : ''}` : ''}

  <!-- Twitter card -->
  <meta name="twitter:card"        content="summary_large_image">
  <meta name="twitter:title"       content="${e(title)}">
  <meta name="twitter:description" content="${e(description)}">
  ${image ? `<meta name="twitter:image" content="${e(image)}">` : ''}

  <!-- Instant redirect for real users (bots/WA crawler ignores this) -->
  <meta http-equiv="refresh" content="0;url=${e(appUrl)}">
  <script>window.location.replace(${JSON.stringify(appUrl)});</script>
</head>
<body style="font-family:sans-serif;text-align:center;padding:48px 16px;color:#333">
  <p style="font-size:1.1rem">Loading car details&hellip;</p>
  <p><a href="${e(appUrl)}" style="color:#25D366">Tap here if not redirected</a></p>
</body>
</html>`;

  return new Response(html, {
    headers: {
      'content-type': 'text/html;charset=UTF-8',
      'cache-control': 'public, max-age=300',
    },
  });
};
