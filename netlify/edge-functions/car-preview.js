/**
 * Netlify Edge Function: car-preview
 * Handles /car/:carId paths.
 * 
 * - WhatsApp / link-preview bots get a page with Open Graph meta tags
 *   (car image, title, price, description) so the preview looks great.
 * - Real visitors are instantly redirected into the main app with ?car=ID
 *   so it opens the card view for that specific car.
 */
export default async (request, context) => {
  const url = new URL(request.url);

  // Extract car ID from path  e.g. /car/ABC123  → "ABC123"
  const rawId = url.pathname.split('/car/')[1] ?? '';
  const carId = decodeURIComponent(rawId.replace(/\/$/, '').trim());

  // Fallback URL: main app root
  const appBase = new URL('/src/index.html', url.origin).toString();

  if (!carId) {
    return Response.redirect(appBase, 302);
  }

  // Fetch cars.json from the same origin (served at /data/cars.json)
  let car = null;
  try {
    const resp = await fetch(new URL('/data/cars.json', url.origin).toString());
    if (resp.ok) {
      const cars = await resp.json();
      car = cars.find(c => String(c.car_id) === carId);
    }
  } catch (_) {
    // silently fall through to redirect
  }

  if (!car) {
    return Response.redirect(appBase, 302);
  }

  // Build the app deep-link that opens just this car
  const appUrl = new URL(
    `/index.html?car=${encodeURIComponent(car.car_id)}`,
    url.origin
  ).toString();

  // ── Build OG content ──────────────────────────────────────────────────────
  const price = (parseInt(car.price) || 0) + 300;
  const yearStr = car.year_reg || car.year || '';
  const isUnknown = (v) =>
    !v || ['unknown', 'n/a', ''].includes(String(v).trim().toLowerCase());

  const title =
    [yearStr, car.make, car.model].filter(Boolean).join(' ') +
    ` — £${price.toLocaleString()} | FinanceItNOW`;

  const details = [
    !isUnknown(car.mileage)
      ? `${parseInt(car.mileage).toLocaleString()} miles`
      : null,
    car.Gearbox || car.gearbox || null,
    car.fuel_type || null,
    car.body_type || null,
  ]
    .filter(Boolean)
    .join(' · ');

  const description = details
    ? `${details}\n\nAvailable now on flexible finance at FinanceItNOW.`
    : 'Available now on flexible finance at FinanceItNOW.';

  // First non-empty image URL
  const image =
    (car.images && car.images.find((i) => i && i.trim())) || '';

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
  <meta property="og:site_name"   content="FinanceItNOW">
  ${image ? `<meta property="og:image" content="${e(image)}">
  <meta property="og:image:width"  content="1200">
  <meta property="og:image:height" content="630">` : ''}

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
